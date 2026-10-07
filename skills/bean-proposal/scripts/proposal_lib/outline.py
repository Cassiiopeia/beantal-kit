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
    - 기간: 10월 4W, 11월 1W, 11월 2W        (C12 타임테이블의 열)
    - 일정:
      | 항목 | 세부 일정 | 시작 | 끝 | 표시 |
      | 계약 | 계약 체결 | 10월 4W | 10월 4W | |
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
    "C09": "사례/실적", "C10": "보안·증빙", "C11": "정산·단가", "C12": "타임테이블",
    "L01": "회사 소개", "L02": "회사 소개", "L03": "회사 소개", "L04": "회사 소개", "L05": "회사 소개", "L06": "회사 소개",
}
LIST_FIELDS = {"본문", "단계"}
TABLE_FIELDS = {"표", "데이터", "일정"}
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
                if key in LIST_FIELDS | TABLE_FIELDS and not val:
                    field = key
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
        if tone_check and s.get("메시지") and s["type"][0] == "C":
            for issue in tone_check(s["메시지"]):
                f.append({"sev": "warn", "slide": where, "code": "O09", "msg": issue})
        blob = " ".join(str(v) for v in s.values())
        if "[확인 필요" in blob:
            f.append({"sev": "info", "slide": where, "code": "O10", "msg": "[확인 필요] 빈칸이 있습니다 — 제출 전 채워야 합니다"})
    nums = [s["n"] for s in slides if s.get("n")]
    if nums and nums != sorted(nums):
        f.append({"sev": "warn", "slide": None, "code": "O11", "msg": "슬라이드 번호가 순서대로가 아닙니다"})
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
