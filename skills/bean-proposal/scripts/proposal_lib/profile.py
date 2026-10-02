"""예시 덱의 스타일 지문: 크기 · 폰트 · 색 · 헤더 위치 · 페이지 유형 · 목차.

결과의 suggested_config 는 config.json 의 fonts / colors / header 에 그대로 넣을 수 있는 형태다.
"""
import re
from collections import Counter

from .review import find_toc, header_of


def _mode(values):
    vals = [v for v in values if v is not None]
    return Counter(vals).most_common(1)[0][0] if vals else None


def page_type(slide, idx, toc_n):
    shapes = slide["shapes"]
    txt = " ".join(sh["text"] for sh in shapes if sh.get("text"))
    chars = len(txt)
    kinds = Counter(sh["kind"] for sh in shapes)
    if idx == 1:
        return "T01"
    if slide["n"] == toc_n:
        return "T02"
    if chars < 60 and not kinds["table"]:
        return "T03/T04"
    if kinds["chart"]:
        return "C05"
    if kinds["table"] >= 2 or (kinds["table"] and chars > 300):
        return "C03"
    if kinds["picture"] >= 15:
        return "L04"
    if kinds["line"] >= 4 or re.search(r"(→|STEP|단계|프로세스|Flow)", txt):
        return "C04"
    if kinds["autoshape"] >= 8:
        return "C01/카드"
    if kinds["picture"] >= 2:
        return "C06/이미지"
    return "텍스트"


def profile(deck):
    slides = deck["slides"]
    toc_n, toc = find_toc(deck)
    fonts, colors = Counter(), Counter()
    roles = {"number": [], "label": [], "title": [], "message": []}
    types = Counter()
    for i, s in enumerate(slides, 1):
        types[page_type(s, i, toc_n)] += 1
        for sh in s["shapes"]:
            for p in sh.get("paras") or []:
                if p.get("font"):
                    fonts[p["font"]] += 1
                if p.get("color"):
                    colors[p["color"].upper()] += 1
        h = header_of(s)
        if h["num"] is None:
            continue
        for sh in s["shapes"]:
            t = (sh.get("text") or "").strip()
            p0 = (sh.get("paras") or [{}])[0]
            rec = (sh.get("left"), sh.get("top"), sh.get("width"), sh.get("height"), p0.get("size"), p0.get("font"), (p0.get("color") or "").upper() or None)
            if re.fullmatch(r"\d{1,2}\.?", t) and (sh.get("top") or 9) < 2.5:
                roles["number"].append(rec)
            elif h["label"] and t == h["label"]:
                roles["label"].append(rec)
            elif h["title"] and t == h["title"]:
                roles["title"].append(rec)
            elif h["message"] and t == h["message"]:
                roles["message"].append(rec)

    def spec(key, font_role, default_color):
        r = roles[key]
        if not r:
            return None
        out = {
            "left": _mode(round(x[0], 1) for x in r if x[0] is not None),
            "top": _mode(round(x[1], 1) for x in r if x[1] is not None),
            "width": _mode(round(x[2], 1) for x in r if x[2] is not None),
            "height": _mode(round(x[3], 1) for x in r if x[3] is not None),
            "size": _mode(x[4] for x in r),
            "font": font_role, "color": default_color, "_font_seen": _mode(x[5] for x in r), "_color_seen": _mode(x[6] for x in r), "_n": len(r),
        }
        return out

    top_fonts = [f for f, _ in fonts.most_common(8)]
    pick = lambda pat: next((f for f in top_fonts if re.search(pat, f, re.I)), None)
    suggested = {
        "slide_size_cm": deck.get("size_cm"),
        "fonts": {
            "title": (spec("title", "title", "primary") or {}).get("_font_seen") or pick("Bold|산스|EB|Black"),
            "body": pick("Light|L00|Regular|R00") or (top_fonts[0] if top_fonts else None),
            "emphasis": pick("Medium|M00|SemiBold|SB"),
            "label": (spec("label", "label", "muted") or {}).get("_font_seen") or pick("SemiBold|SB"),
        },
        "colors": {},
        "header": {k: v for k, v in {
            "number": spec("number", "title", "primary"), "section_label": spec("label", "label", "muted"),
            "title": spec("title", "title", "primary"), "message": spec("message", "emphasis", "primary"),
        }.items() if v},
    }
    title_c = (suggested["header"].get("title") or {}).get("_color_seen")
    number_c = (suggested["header"].get("number") or {}).get("_color_seen")
    label_c = (suggested["header"].get("section_label") or {}).get("_color_seen")
    common = [c for c, _ in colors.most_common(12) if c not in ("FFFFFF", "000000")]
    grays = ("444444", "333333", "404040", "262626", "595959", "3F3F3F", "414756", "44546A")
    primary = title_c or number_c or next((c for c in common if c not in grays), None)
    text_c = next((c for c in common if c in grays), "444444")
    accent = next((c for c in common if c not in (primary, label_c, text_c) and c not in grays and c != "FF0000"), None)
    suggested["colors"] = {"primary": primary, "muted": label_c, "text": text_c, "accent": accent}
    notes = []
    if number_c and title_c and number_c != title_c:
        notes.append(f"섹션 번호 색({number_c})이 제목 색({title_c})과 다릅니다 — 고객사 브랜드 색을 번호에 쓴 덱일 수 있습니다")
    if not title_c:
        notes.append("슬라이드 제목 요소를 찾지 못해 기본색은 자주 쓰인 색으로 추정했습니다 — 사용자 확인 필요")
    suggested["_notes"] = notes
    return {
        "ok": True, "code": "profiled",
        "summary": f"{len(slides)}장 · {deck.get('size_cm')}cm · 폰트 {', '.join(top_fonts[:3])} · 목차 {len(toc)}개 항목",
        "slides": len(slides), "masters": deck.get("masters"), "drm": deck.get("drm"),
        "fonts": fonts.most_common(8), "colors": colors.most_common(10), "page_types": types.most_common(),
        "toc": toc, "suggested_config": suggested,
        "outline_skeleton": [{"n": s["n"], **{k: v for k, v in header_of(s).items() if v is not None}} for s in slides],
        "next": "suggested_config 를 사용자에게 보여 주고 승인되면 setup-save 로 저장",
    }
