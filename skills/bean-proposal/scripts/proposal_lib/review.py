"""제출 전 자동 점검 (references/review-rules.md 의 Q01~Q12).

판단(채점·논리 검토)은 Claude 가 하고, 이 모듈은 기계로 확인할 수 있는 사실만 낸다.
등급: red(치명, 제출 불가) / yellow(주의) / green(권장)
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import tone

# ---------------------------------------------------------------- 규칙 데이터

MEMO_STRONG = re.compile(
    r"(넣기\b|넣을 ?것|해야 ?함|이래서|나눠서|이것저것|받은 것|말을 주면|추후 ?작성|작성 ?예정|확인 후 기재|TBD|TODO|\?\?|"
    r"좌우 나눠|문의\(|수정 ?필요|확인 ?필요함|여기에|넣어야|빼야|바꿔야)")
MEMO_LABEL = re.compile(r"^(수정|확인|메모|삭제|추가|검토|TODO|FIXME|수정필요|확인필요)[!\.]?$")
PLAIN_END = re.compile(r"(?<!니)다\.?$")
COLLOQUIAL = re.compile(r"(거든|잖아|같음|인듯|듯함|ㅇㅇ|ㅋㅋ)")
PLACEHOLDER = re.compile(r"(\[확인 ?필요[^\]]*\]|\bXX+\b|OOO|○○|◯◯|TBD|(?<![\d,])0{3,}원|\?{2,})")
ENGLISH_OR = re.compile(r"\bor\b")
TYPOS = {
    "정채": "정책", "되요": "돼요", "몇일": "며칠", "어떻해": "어떻게", "금새": "금세", "할께": "할게",
    "역활": "역할", "왠만": "웬만", "희안": "희한", "설겆": "설거", "오랫만": "오랜만", "로써 제공": "로서 제공",
    "않되": "안 되", "됬": "됐", "베송": "배송", "물류비욜": "물류비용", "재고관리시스탬": "재고관리시스템",
}
SUPERLATIVE = tone.SUPERLATIVE


def _norm_area(text):
    """'약 3.2만평' → 32000, '3만 5천평' → 35000. 만 평 단위(회사 총 면적급)만 본다."""
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*만\s*(?:(\d)\s*천)?\s*평", text):
        v = float(m.group(1)) * 10000 + (int(m.group(2)) * 1000 if m.group(2) else 0)
        out.append((int(v), m.group(0)))
    return out


METRICS = {
    "총 면적(평)": _norm_area,
    "매출(억원)": lambda t: [(m.group(1).replace(",", ""), m.group(0)) for m in re.finditer(r"매출\s*([\d,]+(?:\.\d+)?)\s*억", t)],
    "임직원(명)": lambda t: [(m.group(1) or m.group(2), m.group(0)) for m in re.finditer(r"(?:(\d+)\s*명\s*이상의\s*임직원|임직원\s*[:：]?\s*(\d+)\s*명)", t)],
    # 회사 문맥(전국·현재 … 운영)에서만 센터 수를 본다 — 고객사 센터 통합안('3개 센터 → 1개 센터') 등은 제외
    "센터 수(개)": lambda t: [(m.group(1) or m.group(2), m.group(0)) for m in re.finditer(
        r"(?:전국|현재)\s*(\d+)\s*개(?:의)?\s*(?:물류센터|센터|WH)|(\d+)\s*개(?:의)?\s*(?:물류센터|센터|WH)(?:를|을)?\s*운영", t)],
    "CAGR 서비스건수": lambda t: [(m.group(1), m.group(0)) for m in re.finditer(r"CAGR[^+]{0,12}서비스\s*건수\s*\+(\d+)%", t)],
    "CAGR 매출": lambda t: [(m.group(1), m.group(0)) for m in re.finditer(r"CAGR.{0,30}?매출\s*\+(\d+)%", t)],
}


def _content(slide):
    return " ".join(sh["text"] for sh in slide["shapes"] if sh.get("text"))


def _paras(slide):
    for sh in slide["shapes"]:
        for p in sh.get("paras") or []:
            yield sh, p
        if sh.get("kind") == "table":
            for ri, row in enumerate(sh.get("table") or []):
                for c in row:
                    if c:
                        yield sh, {"text": c, "size": None, "font": None, "color": None, "head": ri == 0}


# ---------------------------------------------------------------- 헤더·목차 해석

def header_of(slide):
    """본문 슬라이드 상단의 (번호, 섹션명, 제목, 메시지)를 추정한다."""
    tops = [sh for sh in slide["shapes"] if sh.get("text") and sh.get("top") is not None and sh["top"] < 4.0]
    num = label = title = msg = None
    for sh in sorted(tops, key=lambda s: (s["top"], s["left"] or 0)):
        t = sh["text"].strip()
        size = max([p.get("size") or 0 for p in sh.get("paras") or []] or [0])
        if num is None and re.fullmatch(r"\d{1,2}\.?", t) and (size >= 20 or sh["top"] < 2.0):
            num = int(t.rstrip("."))
            continue
        m = re.match(r"^(\d{1,2})\.\s*(.+?)\s*\|", t)
        if num is None and m and sh["top"] < 1.0:   # '16. 운영 현황 | …' 형식 상단 표기
            num, label = int(m.group(1)), m.group(2).strip()
            continue
        if label is None and sh["top"] < 0.6 and len(t) <= 25 and size <= 12:
            label = t
            continue
        if title is None and size >= 18 and len(t) <= 40:
            title = t
            continue
        if msg is None and 1.6 <= sh["top"] <= 3.9 and len(t) >= 20:
            msg = t
    return {"num": num, "label": label, "title": title, "message": msg}


def find_toc(deck):
    height = (deck.get("size_cm") or [0, 19.05])[1]
    for s in deck["slides"][:5]:
        # 쪽번호(하단의 숫자만 있는 상자)는 목차 해석에서 뺀다
        txt = " ".join(sh["text"] for sh in s["shapes"] if sh.get("text")
                       and not (re.fullmatch(r"\d{1,3}", sh["text"].strip()) and (sh.get("top") or 0) > height - 2.5))
        if re.search(r"(목\s*차|CONTENTS)", txt, re.I):
            items = []
            for m in re.finditer(r"(\d{1,2})\s*\.?\s*([가-힣A-Za-z][^\d|]*?)(?=\s*\|?\s*\d{1,2}\s*\.?\s*[가-힣A-Za-z]|\s*$|\s*\|)", txt):
                name = m.group(2).strip(" .|")
                if name and not re.fullmatch(r"(목\s*차|CONTENTS)", name, re.I):
                    items.append((int(m.group(1)), name))
            if items:
                return s["n"], items
    return None, []


def _same(a, b):
    a = re.sub(r"[\s·/]", "", a or "")
    b = re.sub(r"[\s·/]", "", b or "")
    return bool(a) and bool(b) and (a in b or b in a)


# ---------------------------------------------------------------- 점검

def review(deck, config=None, company=None, known_clients=None, client=None, requirements=None, outline=None):
    F = []

    def add(sev, code, slide, msg, evidence=None):
        F.append({"sev": sev, "code": code, "slide": slide, "msg": msg, "evidence": (evidence or "")[:160]})

    slides = deck["slides"]
    toc_slide, toc = find_toc(deck)
    headers = {s["n"]: header_of(s) for s in slides}

    # Q02 작성자 메모 / Q05 빈칸 / Q10 오타 / Q09 말투 / Q11 기호
    tone_msgs = 0
    for s in slides:
        n = s["n"]
        for sh, p in _paras(s):
            t = p["text"]
            if MEMO_LABEL.match(t) and not p.get("head"):  # 표 머리글의 "확인" 같은 열 이름은 메모가 아니다
                add("red", "Q02", n, f"작성자 라벨 '{t}' 이(가) 남아 있습니다", t)
            elif MEMO_STRONG.search(t) or COLLOQUIAL.search(t):
                add("red", "Q02", n, "작성자 메모로 보이는 문장", t)
            elif PLAIN_END.search(t) and len(t) > 8 and not t.startswith(("“", "\"", "'")):
                add("yellow", "Q09", n, "반말 종결(~다) — 메모이거나 말투 규칙 위반", t)
            elif ENGLISH_OR.search(t):
                add("yellow", "Q09", n, "영문 'or' — 본문은 '또는'·'/' 로 (메모일 수도 있음)", t)
            if PLACEHOLDER.search(t):
                add("red", "Q05", n, "빈칸·임시 표기가 남아 있습니다", t)
            for wrong, right in TYPOS.items():
                if wrong in t:
                    add("yellow", "Q10", n, f"오타 의심: '{wrong}' → '{right}'", t)
            if SUPERLATIVE.search(t):
                add("yellow", "Q13", n, "근거 없는 최상급 표현", t)
            if "ㆍ" in t:
                add("green", "Q11", n, "가운뎃점은 'ㆍ'(한글 아래아) 대신 '·' 를 씁니다", t)
            if (p.get("color") or "").upper() in ("FF0000",) and len(t) > 4:
                add("green", "Q02", n, "빨간 글씨 — 강조인지 작성 메모인지 확인", t)
        if s.get("notes") and (MEMO_STRONG.search(s["notes"]) or COLLOQUIAL.search(s["notes"])):
            add("yellow", "Q02", n, "슬라이드 노트에 작성 메모가 있습니다 (발표자 노트는 고객에게 전달될 수 있음)", s["notes"])
        h = headers[n]
        if h["message"]:
            tone_msgs += 1
            for issue in tone.check_message(h["message"]):
                add("green", "Q09", n, issue, h["message"])

    # Q03 수치 일치
    seen = defaultdict(lambda: defaultdict(list))
    for s in slides:
        txt = PLACEHOLDER.sub(" ", _content(s))   # [확인 필요: …] 안내 문구 속 숫자는 비교하지 않는다
        for metric, fn in METRICS.items():
            for val, raw in fn(txt):
                seen[metric][str(val)].append((s["n"], raw))
    for metric, vals in seen.items():
        if len(vals) > 1:
            detail = "; ".join(f"{v} ← p{', p'.join(str(x[0]) for x in occ)} ('{occ[0][1]}')" for v, occ in vals.items())
            add("red", "Q03", None, f"같은 지표 '{metric}' 에 서로 다른 값", detail)
    if company:
        facts = company.get("facts", {})
        ref = {"총 면적(평)": facts.get("floor_area"), "매출(억원)": facts.get("revenue_2025"),
               "임직원(명)": facts.get("employees"), "센터 수(개)": facts.get("centers_count")}
        for metric, fact in ref.items():
            if not fact or fact.get("status") != "confirmed" or metric not in seen:
                continue
            for v, occ in seen[metric].items():
                if str(fact.get("value")) != v:
                    add("red", "Q03", occ[0][0], f"'{metric}' 이(가) 회사 프로필 확정값({fact.get('value')}, 기준 {fact.get('asof')})과 다릅니다", occ[0][1])

    # Q04 다른 고객사명
    if known_clients:
        cover = _content(slides[0]) if slides else ""
        mine = client or next((c for c in known_clients if c in cover), None)
        for s in slides:
            txt = _content(s)
            for c in known_clients:
                if c != mine and c in txt and not (mine and c in mine):
                    add("yellow", "Q04", s["n"], f"다른 고객사명 '{c}' 이(가) 있습니다 — 재사용 장표 잔존인지, 실적 소개로 의도한 것인지 확인", c)

    # Q06 목차 ↔ 본문 번호·섹션명
    if toc:
        nums = [x[0] for x in toc]
        for a, b in zip(nums, nums[1:]):
            if b != a + 1:
                add("yellow", "Q06", toc_slide, f"목차 번호가 {a:02d} 다음에 {b:02d} 로 건너뜁니다")
        toc_map = dict(toc)
        # 원인 단위로 묶는다: (상단 번호, 섹션명) 한 쌍 = 한 건
        groups = defaultdict(list)
        for s in slides:
            h = headers[s["n"]]
            if s["n"] == toc_slide or h["num"] is None:
                continue
            groups[(h["num"], h["label"] or "")].append(s["n"])
        mism = []   # (첫 슬라이드, 상단번호, 섹션명, 목차상 번호 또는 None, 슬라이드들)
        for (num, label), sl in sorted(groups.items(), key=lambda x: x[1][0]):
            where = f"슬라이드 {', '.join(map(str, sl))}"
            if num not in toc_map:
                hit = next((k for k, v in toc_map.items() if _same(label, v)), None) if label else None
                hint = f" — 목차에서는 {hit:02d}번 '{toc_map[hit]}'" if hit else ""
                add("yellow", "Q06", sl[0], f"상단 번호 {num:02d}{' ' + label if label else ''} 이(가) 목차에 없습니다{hint} ({where})")
            elif label and not _same(label, toc_map[num]):
                hit = next((k for k, v in toc_map.items() if _same(label, v)), None)
                mism.append((sl[0], num, label, hit, sl))
        offs = [m[3] - m[1] for m in mism if m[3] is not None]
        main_off = Counter(offs).most_common(1)[0][0] if offs else None
        explained = [m for m in mism if m[3] is not None and m[3] - m[1] == main_off] if len(offs) >= 3 and offs.count(main_off) >= len(offs) * 0.7 else []
        if explained:
            secs = ", ".join(f"{m[1]:02d}→{m[3]:02d} {m[2]}" for m in explained)
            add("yellow", "Q06", explained[0][0],
                f"본문 섹션 번호가 목차와 {abs(main_off)}씩 어긋납니다 ({len(explained)}개 섹션: {secs}) — 목차에 섹션을 추가·삭제한 뒤 본문 번호를 갱신하지 않은 것으로 보입니다 (원인 추정)")
        for m in mism:
            if m in explained:
                continue
            hint = f" — 목차에서는 {m[3]:02d}번" if m[3] else ""
            add("yellow", "Q06", m[0], f"상단 '{m[1]:02d} {m[2]}' ≠ 목차 '{m[1]:02d} {toc_map[m[1]]}'{hint} (슬라이드 {', '.join(map(str, m[4]))})")

    # Q07 헤더 규격 · Q08 폰트·마스터
    allowed = set()
    if config:
        for v in (config.get("fonts") or {}).values():
            if v:
                allowed.add(v.split()[0])
    fonts = Counter()
    font_slides = defaultdict(set)
    for s in slides:
        for sh, p in _paras(s):
            if p.get("font"):
                fam = p["font"].split()[0].split("-")[0]
                fonts[fam] += 1
                font_slides[fam].add(s["n"])
    if allowed:
        foreign = {f: c for f, c in fonts.items() if not any(f.startswith(a) for a in allowed) and f not in ("+mn", "+mj")}
        if foreign:
            sl = sorted(set().union(*(font_slides[f] for f in foreign)))
            desc = ", ".join(f"{f} {c}곳" for f, c in sorted(foreign.items(), key=lambda x: -x[1])[:6])
            add("yellow", "Q08", sl[0], f"하우스 폰트가 아닌 글꼴: {desc} (슬라이드 {', '.join(map(str, sl[:15]))}{'…' if len(sl) > 15 else ''})")
    if deck.get("masters", 1) > 1:
        add("yellow", "Q08", None, f"슬라이드 마스터가 {deck['masters']}개입니다 — 다른 덱에서 붙여 넣은 장표가 섞였을 가능성")
    if config and config.get("header", {}).get("number"):
        spec = config["header"]["number"]
        off = []
        for s in slides:
            for sh in s["shapes"]:
                if re.fullmatch(r"\d{1,2}\.", (sh.get("text") or "").strip()) and (sh.get("top") or 9) < 2.5:
                    if abs((sh["left"] or 0) - spec["left"]) > 0.4 or abs((sh["top"] or 0) - spec["top"]) > 0.4:
                        off.append(s["n"])
                    break
        if off:
            add("yellow", "Q07", off[0], f"섹션 번호 위치가 기준과 다른 슬라이드 {len(off)}장: {', '.join(map(str, off[:15]))}")

    # Q12 크기
    if deck.get("mb", 0) > 50:
        add("green", "Q12", None, f"파일이 {deck['mb']}MB 입니다 — 메일 첨부 한도(보통 25MB)를 넘을 수 있습니다. 이미지 압축 권장")
    if deck.get("size_cm") and config and config.get("slide_size_cm"):
        w, h = deck["size_cm"]
        cw, ch = config["slide_size_cm"]
        if abs(w - cw) > 0.5 or abs(h - ch) > 0.5:
            add("yellow", "Q07", None, f"슬라이드 크기 {w}×{h}cm 가 기준 {cw}×{ch}cm 와 다릅니다")

    # Q01 요건 커버리지 (requirements 가 있을 때)
    coverage = None
    if requirements:
        deck_txt = " ".join(_content(s) for s in slides)
        kinds = ("작성요청", "평가", "SLA", "업무범위")
        targets = [r for r in requirements if r.get("분류", "") in kinds] or list(requirements)   # RFP 없으면 전부
        miss = []
        for r in targets:
            words = [w for w in re.findall(r"[가-힣A-Za-z]{2,}", r.get("요약", "")) if len(w) >= 2][:6]
            hit = sum(1 for w in words if w in deck_txt)
            if words and hit / len(words) < 0.5:
                miss.append(r["ID"])
                add("red", "Q01", None, f"요건 {r['ID']} ({r.get('요약','')[:30]}) 을(를) 다룬 흔적이 약합니다", f"핵심어 {hit}/{len(words)} 일치")
        coverage = {"checked": len(targets), "weak": miss}

    # 정리
    order = {"red": 0, "yellow": 1, "green": 2}
    # 같은 슬라이드·코드·문장 중복 제거
    uniq, keys = [], set()
    for f in F:
        k = (f["code"], f["slide"], f["evidence"] or f["msg"])
        if k not in keys:
            keys.add(k)
            uniq.append(f)
    uniq.sort(key=lambda f: (order[f["sev"]], f["slide"] or 0, f["code"]))
    counts = Counter(f["sev"] for f in uniq)
    content_slides = [s for s in slides if headers[s["n"]]["num"] is not None]
    stats = {
        "slides": len(slides), "content_slides": len(content_slides),
        "messages_found": tone_msgs,
        "message_ratio": round(tone_msgs / max(1, len(content_slides)), 2),
        "numbers_in_messages": sum(1 for s in slides if headers[s["n"]]["message"] and re.search(r"\d", headers[s["n"]]["message"])),
        "tables": sum(1 for s in slides for sh in s["shapes"] if sh.get("kind") == "table"),
        "fonts_top": fonts.most_common(5), "masters": deck.get("masters"), "toc": toc,
    }
    verdict = "제출 불가 (치명 문제 있음)" if counts.get("red") else ("보완 후 제출" if counts.get("yellow", 0) > 5 else "형식상 제출 가능")
    return {
        "ok": True, "code": "reviewed",
        "summary": f"치명 {counts.get('red', 0)} · 주의 {counts.get('yellow', 0)} · 권장 {counts.get('green', 0)} — {verdict}",
        "counts": {"red": counts.get("red", 0), "yellow": counts.get("yellow", 0), "green": counts.get("green", 0)},
        "verdict_hint": verdict, "findings": uniq, "stats": stats, "coverage": coverage,
        "next": "Claude 가 6축 채점(references/review-rules.md)으로 논리·차별성·근거를 판단해 review_vNN.md 를 작성",
    }


SEV_ICON = {"red": "🟥 치명", "yellow": "🟨 주의", "green": "🟩 권장"}


def to_markdown(result, deck_path):
    lines = [f"# 자동 점검 결과", "", f"- 대상: `{Path(deck_path).name}`", f"- 요약: {result['summary']}", ""]
    lines += ["| 등급 | 코드 | 슬라이드 | 내용 | 근거 |", "|---|---|---|---|---|"]
    for f in result["findings"]:
        ev = (f["evidence"] or "").replace("|", "/")
        lines.append(f"| {SEV_ICON[f['sev']]} | {f['code']} | {f['slide'] or '-'} | {f['msg'].replace('|', '/')} | {ev} |")
    lines += ["", "## 6축 채점 (Claude 작성)", "", "| 축 | 점수 | 근거 |", "|---|---|---|"]
    for ax in ("1 RFP 적합성", "2 논리 구조", "3 메시지", "4 근거·수치", "5 차별성", "6 완성도·형식"):
        lines.append(f"| {ax} |  |  |")
    return "\n".join(lines) + "\n"
