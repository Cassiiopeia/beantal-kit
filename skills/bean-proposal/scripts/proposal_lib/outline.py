"""outline.md / requirements.md 해석과 형식 검사.

outline.md 형식 (슬라이드 한 장 = '## ' 블록):

    # <덱 제목>
    - 고객사: <고객사명>
    - 건명: <건명>
    - 날짜: 2026.01.31

    ## 01 · T01
    - 메시지: (표지 부제)

    ## 04 · C03
    - 섹션: 01 Summary
    - 제목: RFP 이해 및 제안 방향
    - 메시지: ...
    - 근거: R-WRT-01, R-SOW-02
    - 본문:
      - 【 소제목 】
      - 불릿
    - 표:
      | 요구 사항 | 우리 대응 |
      |---|---|
      | ... | ... |
    - 단계:
      - 입고 | PDA 전수 검수
    - 데이터:
      | 월 | 택배 | 우편 |
      | 1월 | 1200 | 800 |
    - 차트: 막대 | 선형 | 원형                 ('데이터:' 를 그릴 모양, 생략하면 막대)
    - 조직:                                   (들여쓰기가 곧 상하 관계, C13 운영조직)
      - 총괄 PM | 계약·보고
        - 운영팀 | 입출고; 재고
    - 기간: 10월 4W, 11월 1W, 11월 2W        (C12 타임테이블의 열)
    - 일정:
      | 항목 | 세부 일정 | 시작 | 끝 | 표시 |
      | 계약 | 계약 체결 | 10월 4W | 10월 4W | |
    - 포인트: 유사 SKU 오출고를 막습니다      (장 하단 POINT 막대, 모든 장 같은 자리 · 결과만)
    - 배치: 좌1우2 6:4                         (블록 2~3개를 묶는 모양: 좌우 · 상하 · 좌1우2 · 상1하2, 생략하면 자동)
    - 사진: 곤지암 센터                        (한 칸에 1~4장, 레퍼런스 사진 ref:<id>/<키> 또는 파일 경로)
      - ref:ably-2603/s11-1 | 센터 외관
    - 출처: ably-2603 11장                     (가져온 레퍼런스 장, 렌더하지 않음)
    블록 필드 뒤에 글을 쓰면 블록 위 소제목이 된다:  - 표: 입고 기준  (아래 줄에 표)
    - 상태: 초안
"""
import re
from pathlib import Path

FIELD = re.compile(r"^-\s*([^:：]+?)\s*[:：]\s*(.*)$")
HEAD = re.compile(r"^##\s+(\d{1,3})\s*[·\-|]\s*([A-Z]\d{2})\b\s*(.*)$")
TYPES = {
    "T01": "표지", "T02": "목차", "T03": "간지", "T04": "마무리",
    "C01": "제안 방향", "C02": "요건 대응 총괄", "C03": "요건 대응표", "C04": "프로세스/흐름",
    "C05": "현황 분석(차트)", "C06": "거점/센터", "C07": "비교안", "C08": "일정",
    "C09": "사례/실적", "C10": "보안·증빙", "C11": "정산·단가", "C12": "타임테이블", "C13": "운영조직",
    "L01": "회사 소개", "L02": "회사 소개", "L03": "회사 소개", "L04": "회사 소개", "L05": "회사 소개", "L06": "회사 소개",
}
LIST_FIELDS = {"본문", "단계", "사진"}
TABLE_FIELDS = {"표", "데이터", "일정"}
TREE_FIELDS = {"조직"}
CHART_KINDS = {"": "bar", "막대": "bar", "세로막대": "bar", "bar": "bar", "column": "bar",
               "선형": "line", "꺾은선": "line", "line": "line",
               "원형": "pie", "파이": "pie", "pie": "pie"}
BLOCK_FIELDS = ("본문", "표", "단계", "데이터", "조직", "일정", "사진")
# 배치: 한 장에 블록 2~3개를 묶는 모양. h = 좌우로 나란히, v = 위아래, l12 = 왼쪽 1 | 오른쪽 2, t12 = 위 1 / 아래 2
LAYOUTS = {"좌우": "h", "가로": "h", "상하": "v", "세로": "v", "위아래": "v",
           "좌1우2": "l12", "좌1우2단": "l12", "상1하2": "t12", "위1아래2": "t12"}
SINGLE_OK = {"C01", "C07", "C12", "C13"}      # 전용 배치라 한 블록으로 장을 채우는 유형
NEEDS_HEADER = {k for k in TYPES if k[0] in "CL"}
REQUIRED_KINDS = ("작성요청", "평가", "SLA", "업무범위")


def _table(lines):
    rows = []
    for ln in lines:
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def parse_outline(text):
    meta, slides, cur, field, buf = {}, [], None, None, []

    def flush():
        nonlocal field, buf
        if cur is not None and field:
            if field in TABLE_FIELDS:
                cur[field] = _table(buf)
            elif field in LIST_FIELDS:
                items = [re.sub(r"^\s*-\s*", "", b).rstrip() for b in buf if b.strip().startswith("-")]
                cur[field] = items
            elif field in TREE_FIELDS:      # 들여쓰기로 상하 관계를 읽으므로 앞 공백을 남긴다
                cur[field] = [b.rstrip() for b in buf if b.strip().startswith("-")]
            cap = f"{field}_제목"
            if not cur[field] and cap in cur:   # '- 본문: 한 줄' 처럼 아래 줄 없이 쓴 값은 소제목이 아니라 내용이다
                val = cur.pop(cap)
                cur[field] = [val] if field in LIST_FIELDS else val
        field, buf = None, []

    for raw in text.splitlines():
        line = raw.rstrip()
        m = HEAD.match(line)
        if m:
            flush()
            cur = {"n": int(m.group(1)), "type": m.group(2), "note": m.group(3).strip(), "line": None}
            slides.append(cur)
            continue
        if line.startswith("# ") and cur is None:
            meta["title"] = line[2:].strip()
            continue
        if line.startswith("## "):
            flush()
            cur = {"n": None, "type": None, "bad_head": line}
            slides.append(cur)
            continue
        if raw.startswith("- ") or raw.startswith("-\t"):
            flush()
            fm = FIELD.match(raw.strip())
            if fm:
                key, val = fm.group(1).strip(), fm.group(2).strip()
                target = meta if cur is None else cur
                if key in LIST_FIELDS | TABLE_FIELDS | TREE_FIELDS and (not val or cur is not None):
                    field = key
                    if val:     # '- 표: 입고 기준' → 블록 위 소제목
                        cur[f"{key}_제목"] = val
                else:
                    target[key] = val
            continue
        if field and (raw.startswith(" ") or raw.startswith("\t")) and raw.strip():
            buf.append(raw.strip() if field in TABLE_FIELDS else raw)
    flush()
    return {"meta": meta, "slides": slides}


def parse_requirements(text):
    """requirements.md 의 마크다운 표에서 요건 행을 읽는다 (첫 열 = ID)."""
    reqs, header = [], None
    for ln in text.splitlines():
        if not ln.strip().startswith("|"):
            header = None if not ln.strip() else header
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        if header is None:
            header = cells
            continue
        row = dict(zip(header, cells))
        rid = cells[0]
        if re.fullmatch(r"R-[A-Z]{2,5}-\d{2,3}", rid):
            row["ID"] = rid
            reqs.append(row)
    return reqs


def timeline_periods(s):
    return [p.strip() for p in re.split(r"[,，]", s.get("기간", "")) if p.strip()]


def check_timeline(s, where):
    """C12: 기간 열과 일정 행(항목 | 세부 일정 | 시작 | 끝 | 표시)이 맞는지."""
    f, periods = [], timeline_periods(s)
    rows = s.get("일정") or []
    if not periods or len(rows) < 2:
        return [{"sev": "warn", "slide": where, "code": "O14", "msg": "타임테이블인데 '기간:' 또는 '일정:' 이 없습니다"}]
    for r in rows[1:]:
        start, end = (r + ["", "", "", ""])[2:4]
        if start not in periods or end not in periods:
            f.append({"sev": "error", "slide": where, "code": "O15", "msg": f"일정 '{r[1] if len(r) > 1 else r}' 의 시작·끝이 기간에 없습니다 ({start} ~ {end})"})
        elif periods.index(start) > periods.index(end):
            f.append({"sev": "error", "slide": where, "code": "O15", "msg": f"일정 '{r[1]}' 의 시작이 끝보다 늦습니다"})
    return f


def chart_kind(name):
    """'차트:' 값 → bar/line/pie. 생략은 bar, 모르는 값은 None."""
    return CHART_KINDS.get((name or "").strip().lower())


def chart_number(value):
    """차트 칸 값 → 숫자. 읽을 수 없는 칸([확인 필요] 등)은 0 으로 꾸미지 않고 None."""
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except ValueError:
        return None


def org_tree(lines):
    """'조직:' 줄들 → 노드 트리. 더 깊게 들여쓴 줄이 바로 위 줄의 하위 조직이다."""
    roots, stack = [], []
    for ln in lines:
        indent = len(ln) - len(ln.lstrip())
        name, _, desc = re.sub(r"^\s*-\s*", "", ln).partition("|")
        node = {"name": name.strip(), "desc": " · ".join(d.strip() for d in desc.split(";") if d.strip()), "kids": []}
        while stack and stack[-1][0] >= indent:
            stack.pop()
        (stack[-1][1]["kids"] if stack else roots).append(node)
        stack.append((indent, node))
    return roots


def org_layout(roots, max_cols=7):
    """노드에 격자 위치(x 열 중심, row 줄, level 깊이)를 매기고 열·줄 수를 돌려준다.

    옆으로 max_cols 열을 넘으면 말단 팀원을 부모 아래 세로로 쌓는다 (최상위 바로 아래는 제외).
    """
    def walk(nodes):
        for n in nodes:
            yield n
            yield from walk(n["kids"])

    def width(n):
        return sum(width(k) for k in n["kids"]) if n["kids"] and not n.get("stack") else 1

    if sum(width(n) for n in roots) > max_cols:
        for root in roots:
            for n in walk(root["kids"]):
                n["stack"] = bool(n["kids"]) and not any(k["kids"] for k in n["kids"])

    def place(n, col, row, level):
        n["row"], n["level"] = row, level
        if n["kids"] and n.get("stack"):
            n["x"] = col + 0.5
            for i, k in enumerate(n["kids"]):
                k.update(x=n["x"], row=row + i + 1, level=level + 1, hang=True)
            return col + 1
        if not n["kids"]:
            n["x"] = col + 0.5
            return col + 1
        for k in n["kids"]:
            col = place(k, col, row + 1, level + 1)
        n["x"] = (n["kids"][0]["x"] + n["kids"][-1]["x"]) / 2
        return col

    cols = 0
    for n in roots:
        cols = place(n, cols, 0, 0)
    nodes = list(walk(roots))
    return {"roots": roots, "nodes": nodes, "cols": cols, "rows": max((n["row"] for n in nodes), default=-1) + 1}


def check_visual_fields(s, where):
    """O18 차트 종류·원형 데이터, O19 조직도 입력·크기."""
    f = []
    warn = lambda code, msg: f.append({"sev": "warn", "slide": where, "code": code, "msg": msg})
    rows = s.get("데이터") or []
    if s.get("차트"):
        kind = chart_kind(s["차트"])
        if not rows:
            warn("O18", "'차트:' 는 있는데 '데이터:' 가 없습니다")
        elif kind is None:
            warn("O18", f"차트 종류 '{s['차트']}' 를 모릅니다 — 막대 · 선형 · 원형 중 하나로 쓰세요 (지금은 막대로 그립니다)")
        elif kind == "pie":
            if len(rows[0]) > 2:
                warn("O18", "원형 차트는 첫 계열만 그립니다 — 계열이 여럿이면 막대나 선형으로 바꾸세요")
            if len(rows) - 1 > 6:
                warn("O18", f"원형 조각이 {len(rows) - 1}개입니다 — 6개 이하로 묶으세요")
            if any((chart_number(r[1]) or 0) < 0 for r in rows[1:] if len(r) > 1):
                warn("O18", "원형 차트에 음수가 있습니다 — 막대로 바꾸세요")
    if s["type"] == "C13" and not s.get("조직"):
        warn("O19", "운영조직 유형인데 '조직:' 이 없습니다")
    if s.get("조직"):
        size = org_layout(org_tree(s["조직"]))
        if size["cols"] > 8 or size["rows"] > 5:
            warn("O19", f"조직도가 {size['cols']}열 {size['rows']}줄이라 글자가 작아집니다 — 8열 5줄 이내로 묶거나 두 장으로 나누세요")
    return f


def blocks(s):
    """장에 든 블록을 outline 에 쓴 순서대로. 이 순서가 왼쪽→오른쪽, 위→아래 배치 순서다."""
    return [k for k in s if k in BLOCK_FIELDS and s.get(k)]


def parse_layout(value):
    """'좌우 6:4' → ('h', [6, 4]). 비우면 (None, None) = 자동, 모르는 값이면 ('?', None)."""
    value = (value or "").strip()
    if not value:
        return None, None
    m = re.match(r"^(\S+)\s*(?:(\d+(?:\.\d+)?)\s*[:：]\s*(\d+(?:\.\d+)?)(?:\s*[:：]\s*(\d+(?:\.\d+)?))?)?\s*$", value)
    if not m or m.group(1) not in LAYOUTS:
        return "?", None
    weights = [float(g) for g in m.groups()[1:] if g]
    return LAYOUTS[m.group(1)], weights or None


def photo_items(items):
    """'- src | 캡션 [| 맞춤]' 목록 → [(src, 캡션, 맞춤여부)]. 맞춤 = 자르지 않고 칸 안에 전부 (도면 · 화면 캡처)."""
    out = []
    for it in items or []:
        parts = [p.strip() for p in it.split("|")]
        if parts[0]:
            out.append((parts[0], parts[1] if len(parts) > 1 else "", len(parts) > 2 and parts[2] in ("맞춤", "fit", "전체")))
    return out


def check_references(slides, client=None, others=()):
    """O21 사진 파일 확인, O22 다른 고객사 이름 (실적 사례로 일부러 쓴 것이면 무시해도 된다)."""
    from . import refbank
    f = []
    client = (client or "").replace(" ", "").lower()
    names = [n for n in others if n and n.replace(" ", "").lower() not in client and client not in n.replace(" ", "").lower()]
    for s in slides:
        if not (s.get("type") or "").startswith("C"):
            continue
        for src, _, _ in photo_items(s.get("사진")):
            if refbank.resolve_photo(src) is None:
                f.append({"sev": "warn", "slide": s.get("n"), "code": "O21", "msg": f"사진을 찾지 못했습니다: {src} — ref-show 로 키를 확인하거나 ref-index 를 다시 하세요. 렌더에는 빈 칸으로 나옵니다"})
        if not names:
            continue
        blob = " ".join(str(v) for k, v in s.items() if k not in ("출처", "사진", "n", "line"))
        found = [n for n in names if n in blob]
        if found and s.get("type") != "C09":
            f.append({"sev": "warn", "slide": s.get("n"), "code": "O22", "msg": f"다른 고객사 이름 {', '.join(found)} 이(가) 있습니다 — 실적 사례로 쓴 것이 아니면 지우거나 'A사(업종)' 로 바꾸세요"})
    return f


def check_composition(slides):
    """O20: 한 장 = 블록(표·카드·흐름도·차트) 2~3개 묶음이 기본. 한 블록뿐인 장이 많거나 4개 이상 넣으면 경고."""
    f = []
    body = [s for s in slides if (s.get("type") or "").startswith("C")]
    for s in body:
        n = len(blocks(s))
        kind, weights = parse_layout(s.get("배치"))
        if kind == "?":
            f.append({"sev": "warn", "slide": s.get("n"), "code": "O20", "msg": f"알 수 없는 배치 '{s['배치']}' — 좌우 · 상하 · 좌1우2 · 상1하2 중 하나(비율은 '좌우 6:4')로 쓰세요. 지금은 자동으로 놓습니다"})
        elif kind in ("l12", "t12") and n != 3:
            f.append({"sev": "warn", "slide": s.get("n"), "code": "O20", "msg": f"'{s['배치']}' 는 블록 3개일 때만 맞습니다 (지금 {n}개) — 좌우나 상하로 놓습니다"})
        if n > 3:
            f.append({"sev": "warn", "slide": s.get("n"), "code": "O20", "msg": f"블록이 {n}개라 글자가 작아집니다 — 3개 이내로 줄이거나 두 장으로 나누세요"})
    singles = [s for s in body if s.get("type") not in SINGLE_OK and len(blocks(s)) == 1]
    plain = [s for s in body if s.get("type") not in SINGLE_OK]
    if len(plain) >= 4 and len(singles) * 2 > len(plain):
        f.append({"sev": "warn", "slide": None, "code": "O20", "msg": f"본문 {len(plain)}장 중 {len(singles)}장이 블록 하나뿐입니다 — 표·카드('본문:')·흐름도('단계:')·차트('데이터:')를 2~3개씩 묶어 장을 채우세요 (page-types.md 3-2절)"})
    return f


def check_visual_mix(slides):
    """O17: 표만 있는 장이 본문의 절반을 넘거나 3장 이상 이어지면 경고한다. 표에 카드·흐름도·차트를 곁들인 장은 표만 있는 장이 아니다."""
    body = [s for s in slides if (s.get("type") or "").startswith("C")]
    flags = [blocks(s) == ["표"] for s in body]
    f = []
    if len(body) >= 6 and sum(flags) * 2 > len(body):
        f.append({"sev": "warn", "slide": None, "code": "O17", "msg": f"본문 {len(body)}장 중 {sum(flags)}장이 표만 있습니다 — 흐름도('단계:')·차트('데이터:')·타임테이블(C12)로 바꿀 장을 찾으세요"})
    run = 0
    for i, flag in enumerate(flags + [False]):
        if flag:
            run += 1
            continue
        if run >= 3:
            f.append({"sev": "warn", "slide": body[i - run].get("n"), "code": "O17", "msg": f"표만 있는 장이 {run}장 이어집니다 — 앞에 흐름도나 차트 장을 넣으세요"})
        run = 0
    return f


def check_outline(parsed, reqs=None, tone_check=None):
    """형식·추적성 검사. 반환: findings 목록."""
    f = []
    seen = set()
    slides = parsed["slides"]
    for s in slides:
        where = s.get("n")
        if s.get("bad_head"):
            f.append({"sev": "error", "slide": None, "code": "O01", "msg": f"제목줄 형식 오류: '{s['bad_head']}' — '## 05 · C03' 형식이어야 합니다"})
            continue
        if s["n"] in seen:
            f.append({"sev": "error", "slide": where, "code": "O02", "msg": "슬라이드 번호 중복"})
        seen.add(s["n"])
        if s["type"] not in TYPES:
            f.append({"sev": "error", "slide": where, "code": "O03", "msg": f"알 수 없는 유형 코드 {s['type']}"})
            continue
        if s["type"] in NEEDS_HEADER and s["type"][0] == "C":
            for k in ("섹션", "제목", "메시지"):
                if not s.get(k):
                    f.append({"sev": "error", "slide": where, "code": "O04", "msg": f"'{k}' 이(가) 비어 있습니다"})
            if reqs is not None and not s.get("근거") and s["type"] not in ("C09",):
                f.append({"sev": "warn", "slide": where, "code": "O05", "msg": "근거 요건 ID가 없습니다"})
        if s["type"] in ("C03", "C02", "C11") and not s.get("표"):
            f.append({"sev": "warn", "slide": where, "code": "O06", "msg": "표 유형인데 '표:' 가 없습니다"})
        if s["type"] == "C04" and not s.get("단계"):
            f.append({"sev": "warn", "slide": where, "code": "O07", "msg": "프로세스 유형인데 '단계:' 가 없습니다"})
        if s["type"] == "C05" and not s.get("데이터"):
            f.append({"sev": "warn", "slide": where, "code": "O08", "msg": "차트 유형인데 '데이터:' 가 없습니다"})
        if s["type"] == "C12":
            f += check_timeline(s, where)
        f += check_visual_fields(s, where)
        if tone_check and s.get("메시지") and s["type"][0] == "C":
            for issue in tone_check(s["메시지"]):
                f.append({"sev": "warn", "slide": where, "code": "O09", "msg": issue})
        point = s.get("포인트") or s.get("POINT")
        if point and s["type"] == "C13":
            f.append({"sev": "warn", "slide": where, "code": "O16", "msg": "운영조직(조직도) 장에는 POINT 를 두지 않습니다 — 렌더할 때 빠집니다"})
        elif point and s["type"][0] == "C":
            from .tone import check_point
            for issue in check_point(point):
                f.append({"sev": "warn", "slide": where, "code": "O16", "msg": issue})
        blob = " ".join(str(v) for v in s.values())
        if "[확인 필요" in blob:
            f.append({"sev": "info", "slide": where, "code": "O10", "msg": "[확인 필요] 빈칸이 있습니다 — 제출 전 채워야 합니다"})
    nums = [s["n"] for s in slides if s.get("n")]
    if nums and nums != sorted(nums):
        f.append({"sev": "warn", "slide": None, "code": "O11", "msg": "슬라이드 번호가 순서대로가 아닙니다"})
    f += check_visual_mix(slides)
    f += check_composition(slides)
    coverage = None
    if reqs is not None:
        linked = {}
        for s in slides:
            for rid in re.findall(r"R-[A-Z]{2,5}-\d{2,3}", s.get("근거", "")):
                linked.setdefault(rid, []).append(s.get("n"))
        ids = {r["ID"] for r in reqs}
        must = {r["ID"] for r in reqs if r.get("분류", "") in REQUIRED_KINDS} or ids   # RFP 없는 상황(D·E)은 가상 요건 전부가 필수
        missing = sorted(must - set(linked))
        unknown = sorted(set(linked) - ids)
        for rid in missing:
            f.append({"sev": "error", "slide": None, "code": "O12", "msg": f"요건 {rid} 를 다루는 슬라이드가 없습니다"})
        for rid in unknown:
            f.append({"sev": "warn", "slide": None, "code": "O13", "msg": f"근거에 적힌 {rid} 가 requirements.md 에 없습니다"})
        coverage = {"required": len(must), "covered": len(must) - len(missing), "map": linked}
    return f, coverage


def load(path):
    return Path(path).read_text(encoding="utf-8")
