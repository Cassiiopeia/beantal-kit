"""outline.md → pptx. 템플릿 없이 하우스 스타일(config)로 그린다.

레이아웃 원칙 (references/page-types.md):
- 본문 슬라이드는 공통 헤더(섹션명 · 번호 · 제목 · 메시지) + 본문 영역(body_top ~ 하단 1.0cm)
- 본문 요소는 내용 양에 맞춰 높이를 잡고, 남는 공간은 요소 사이에 고르게 나눈다 (위로 몰지 않는다)
- C01 은 [핵심 과제 | 대응 역량] 2단 + 하단 [제안 방향 3대 축] 전용 배치
"""
import re

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_MARKER_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Cm, Pt

from . import fonts as fontcheck
from .outline import blocks, chart_kind, chart_number, org_layout, org_tree, parse_layout

DEFAULT_HEADER = {
    "section_label": {"left": 2.8, "top": 0.0, "width": 15.2, "height": 0.7, "size": 11, "font": "label", "color": "muted"},
    "number": {"left": 0.4, "top": 0.5, "width": 2.2, "height": 1.3, "size": 32, "font": "title", "color": "primary"},
    "title": {"left": 2.7, "top": 0.8, "width": 16.8, "height": 1.1, "size": 24, "font": "title", "color": "primary"},
    "client_mark": {"left": 22.7, "top": 0.6, "width": 4.1, "height": 0.9, "size": 14, "font": "emphasis", "color": "primary"},
    "message": {"left": 1.1, "top": 2.2, "width": 25.3, "height": 1.4, "size": 14, "font": "emphasis", "color": "primary", "bold": True},
    "body_top": 3.9,
}
DEFAULT_FONTS = {"title": "G마켓 산스 Bold", "body": "Pretendard Light", "emphasis": "Pretendard Medium", "label": "Pretendard SemiBold"}
DEFAULT_COLORS = {"primary": "1B2D4F", "accent": "009FE3", "text": "444444", "muted": "A5ABBD", "white": "FFFFFF"}
LIGHT_FILL = "F2F4F8"
GRID = "D9DDE5"
CHECK = re.compile(r"\[확인 ?필요[^\]]*\]")
HEX = re.compile(r"[0-9A-Fa-f]{6}")
LINE_H = 0.0353 * 1.45          # pt → cm 줄 높이 계수


class Style:
    def __init__(self, cfg):
        cfg = cfg or {}
        wanted = {**DEFAULT_FONTS, **{k: v for k, v in (cfg.get("fonts") or {}).items() if v}}
        self.fonts, self.font_swaps = fontcheck.resolve(wanted)
        self.colors = {**DEFAULT_COLORS, **{k: v for k, v in (cfg.get("colors") or {}).items() if v}}
        hdr = dict(DEFAULT_HEADER)
        for k, v in (cfg.get("header") or {}).items():
            hdr[k] = {**hdr.get(k, {}), **{kk: vv for kk, vv in v.items() if not kk.startswith("_")}} if isinstance(v, dict) else v
        self.header = hdr
        self.size = cfg.get("slide_size_cm") or [27.5, 19.05]
        # design: 생략하면 기존 모양. card "band" = 둥근 띠 소제목 + 테두리 박스, divider "light" = 흰 간지,
        # cover "panel" · toc "list", rule = 헤더 아래 가로줄 위치(cm), footer_logo = 하단 왼쪽 로고 이미지 경로
        self.design = dict(cfg.get("design") or {})
        self.client_logo = None
        self.cover_image = None
        self.footer_right = None

    def band(self):
        return self.design.get("card") == "band"

    def font(self, key):
        return self.fonts.get(key, key)

    def color(self, key):
        val = self.colors.get(key, key)
        if isinstance(val, str) and val.startswith("#"):
            val = val[1:]
        return RGBColor.from_string(val if HEX.fullmatch(val or "") else DEFAULT_COLORS["text"])


def lines_needed(text, width_cm, size):
    char_w = size * 0.0353 * 0.95
    per_line = max(1, int(width_cm / char_w))
    return sum(max(1, -(-len(t) // per_line)) for t in text.split("\n"))


def _fit_size(text, width_cm, height_cm, size, min_size=9):
    while size > min_size and lines_needed(text, width_cm, size) * size * LINE_H > height_cm:
        size -= 1
    return size


def text(slide, st, left, top, width, height, value, size=11, font="body", color="text", bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, fit=True, spacing=None):
    box = slide.shapes.add_textbox(Cm(left), Cm(top), Cm(width), Cm(height))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Cm(0.1)
    tf.margin_top = tf.margin_bottom = Cm(0.05)
    tf.vertical_anchor = anchor
    lines = value if isinstance(value, list) else str(value).split("\n")
    if fit:
        size = _fit_size("\n".join(lines), width - 0.2, height, size)
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.name = st.font(font)
        r.font.bold = bold
        r.font.color.rgb = st.color("accent") if CHECK.search(ln) else st.color(color)
    return box


def rect(slide, st, left, top, width, height, fill, line=None, shape=MSO_SHAPE.RECTANGLE):
    r = slide.shapes.add_shape(shape, Cm(left), Cm(top), Cm(width), Cm(height))
    r.fill.solid()
    r.fill.fore_color.rgb = RGBColor.from_string(fill) if HEX.fullmatch(fill) else st.color(fill)
    if line:
        r.line.color.rgb = st.color(line)
        r.line.width = Pt(0.75)
    else:
        r.line.fill.background()
    r.shadow.inherit = False
    return r


def label_in(shape, st, value, size, color="white", font="emphasis", bold=True):
    tf = shape.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Cm(0.05)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = value
    r.font.size = Pt(size)
    r.font.name = st.font(font)
    r.font.bold = bold
    r.font.color.rgb = st.color(color)


# ---------------------------------------------------------------- 헤더 · 공통

def header(slide, st, sec_num, sec_label, title, message, client_mark=None):
    h = st.header

    def put(key, value):
        spec = h[key]
        text(slide, st, spec["left"], spec["top"], spec["width"], spec["height"], value, size=spec["size"],
             font=spec["font"], color=spec["color"], bold=spec.get("bold", False), fit=False)
    if sec_label:
        put("section_label", sec_label)
    if sec_num is not None:
        put("number", f"{sec_num:02d}.")
    if title:
        put("title", title)
    if st.client_logo:
        spec = h["client_mark"]
        _picture(slide, st.client_logo, spec["left"], spec["top"], spec["width"], spec["height"])
    elif client_mark:
        put("client_mark", client_mark)
    rule = st.design.get("rule")
    if rule:
        rect(slide, st, 0, float(rule), st.size[0], 0.04, GRID)
    if message:
        spec = h["message"]
        text(slide, st, spec["left"], spec["top"], spec["width"], spec["height"], message, size=spec["size"],
             font=spec["font"], color=spec["color"], bold=spec.get("bold", True), fit=True)
        if not rule:
            y = spec["top"] + spec["height"] + 0.1
            line = slide.shapes.add_connector(1, Cm(spec["left"]), Cm(y), Cm(spec["left"] + spec["width"]), Cm(y))
            line.line.color.rgb = st.color("muted")
            line.line.width = Pt(0.5)


def _picture(slide, path, left, top, width, height, align="right"):
    """비율을 지키며 상자 안에 맞춘다 (기본 오른쪽 정렬). 파일이 없으면 건너뛴다."""
    from pathlib import Path
    p = Path(str(path)).expanduser()
    if not p.exists():
        return None
    pic = slide.shapes.add_picture(str(p), Cm(left), Cm(top))
    ratio = pic.width / pic.height
    w, h = width, width / ratio
    if h > height:
        h, w = height, height * ratio
    pic.width, pic.height = Cm(w), Cm(h)
    pic.left = Cm(left + (width - w if align == "right" else 0))
    pic.top = Cm(top + (height - h) / 2)
    return pic


def footer(slide, st):
    """design.footer_logo 가 있으면 하단 가로줄 + 로고 (footer_logo_align: right 기본 · left)."""
    logo = st.design.get("footer_logo")
    if not logo:
        return
    W, H = st.size
    if st.design.get("footer_rule", True):
        rect(slide, st, 0, H - 1.25, W, 0.03, "muted")
    if st.footer_right:     # 고객사 로고가 있으면 왼쪽 우리 로고 · 오른쪽 고객사 로고
        _picture(slide, logo, 1.0, H - 1.0, 2.6, 0.6, align="left")
        _picture(slide, st.footer_right, W - 1.0 - 3.2, H - 1.0, 3.2, 0.6, align="right")
    elif st.design.get("footer_logo_align", "right") == "left":
        _picture(slide, logo, 1.0, H - 1.0, 2.6, 0.6, align="left")
    else:
        _picture(slide, logo, W - 1.0 - 2.6, H - 1.0, 2.6, 0.6, align="right")


POINT_LABEL = "POINT"
POINT_DEFAULT = {"left": 1.2, "height": 1.15, "bottom_gap": 2.45, "size": 11.5, "fill_mix": 0.9}


def point_box(st):
    """POINT 막대의 고정 자리 (left, top, width, height). 모든 본문 장이 같은 자리를 쓴다.
    기본: 좌우 1.2cm 여백, 높이 1.15cm, 아래 끝이 슬라이드 아래에서 2.45cm (27.5×19.05 → 위 15.45cm).
    design.point 로 left · top · width · height 를 덮어쓸 수 있다."""
    W, H = st.size
    cfg = {**POINT_DEFAULT, **{k: v for k, v in (st.design.get("point") or {}).items() if not str(k).startswith("_")}}
    left, height = float(cfg["left"]), float(cfg["height"])
    width = float(cfg.get("width") or (W - 2 * left))
    top = float(cfg["top"]) if cfg.get("top") is not None else H - float(cfg["bottom_gap"]) - height
    return left, top, width, height


def point_bar(slide, st, value):
    """장 하단 POINT 막대: 연한 강조색 둥근 상자 한 개 안에 'POINT' 라벨 + 결과 한 문장."""
    cfg = {**POINT_DEFAULT, **(st.design.get("point") or {})}
    left, top, width, height = point_box(st)
    accent = st.colors.get("accent", DEFAULT_COLORS["accent"]).lstrip("#")
    accent = accent if HEX.fullmatch(accent) else DEFAULT_COLORS["accent"]
    box = rect(slide, st, left, top, width, height, _mix_white(accent, float(cfg["fill_mix"])), shape=MSO_SHAPE.ROUNDED_RECTANGLE)
    box.adjustments[0] = 0.18
    box.name = "POINT"
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Cm(0.4)
    tf.margin_top = tf.margin_bottom = Cm(0.15)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    body = re.sub(r"^\s*POINT\s*", "", str(value)).strip()
    size = _fit_size(POINT_LABEL + "  " + body, width - 0.8, height - 0.3, float(cfg["size"]), min_size=9)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    for txt, font, color in ((POINT_LABEL, "label", "accent"), ("  " + body, "emphasis", "text")):
        r = p.add_run()
        r.text = txt
        r.font.size = Pt(size)
        r.font.name = st.font(font)
        r.font.bold = False
        r.font.color.rgb = st.color(color)
    return box


def number_position(st):
    """쪽 번호 자리: 하단 로고 배치에 따라 center · left · right."""
    if not st.design.get("footer_logo"):
        return "right"
    if st.footer_right:
        return "center"
    return "right" if st.design.get("footer_logo_align", "right") == "left" else "left"


def page_number(slide, st, n):
    W, H = st.size
    pos = number_position(st)
    if pos == "left":
        text(slide, st, 1.0, H - 0.9, 1.6, 0.5, str(n), size=9, color="muted", fit=False)
        return
    if pos == "center":
        text(slide, st, W / 2 - 0.8, H - 0.9, 1.6, 0.5, str(n), size=9, color="muted", align=PP_ALIGN.CENTER, fit=False)
        return
    text(slide, st, W - 2.0, H - 0.8, 1.6, 0.5, str(n), size=9, color="muted", align=PP_ALIGN.RIGHT, fit=False)


# ---------------------------------------------------------------- 본문 구성 요소 (각 함수는 쓴 높이를 돌려준다)

def _groups(items):
    groups, cur = [], None
    for it in items or []:
        m = re.match(r"^【\s*(.+?)\s*】\s*(.*)$", it)
        if m:
            cur = {"title": m.group(1), "items": [m.group(2)] if m.group(2) else []}
            groups.append(cur)
        else:
            if cur is None:
                cur = {"title": None, "items": []}
                groups.append(cur)
            cur["items"].append(it)
    return groups


def _split_conclusion(items):
    """'▶ ' 로 시작하는 항목은 카드 맨 아래 결론 상자로 뺀다."""
    body = [t for t in items if not t.startswith("▶")]
    concl = [t.lstrip("▶").strip() for t in items if t.startswith("▶")]
    return body, concl


def _band_card(slide, st, g, x, y, w, h, size=13, highlight=None):
    band_h = 1.0 if g["title"] else 0
    if g["title"]:
        title = g["title"] + ("  (권고안)" if highlight else "")
        fill = "primary" if highlight or highlight is None else "muted"
        b = rect(slide, st, x, y, w, band_h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        b.adjustments[0] = 0.2
        label_in(b, st, title, _fit_size(title, w - 0.6, 0.8, size + 1))
    top = y + band_h + (0.25 if band_h else 0)
    box = rect(slide, st, x, top, w, h - (top - y), "FFFFFF", line="primary" if highlight else "muted")
    if highlight:
        box.line.width = Pt(2)
    body, concl = _split_conclusion(g["items"])
    concl_h = 1.3 * len(concl)
    text(slide, st, x + 0.4, top + 0.35, w - 0.8, h - (top - y) - 0.6 - concl_h, [f"• {t}" for t in body],
         size=size, spacing=8)
    for i, c in enumerate(concl):
        cb = rect(slide, st, x + 0.3, y + h - 0.2 - concl_h + i * 1.3, w - 0.6, 1.1, LIGHT_FILL)
        label_in(cb, st, c, _fit_size(c, w - 1.0, 0.9, size), color="primary", font="emphasis")


def _card(slide, st, g, x, y, w, h, size=13, highlight=None):
    if st.band():
        return _band_card(slide, st, g, x, y, w, h, size, highlight)
    rect(slide, st, x, y, w, h, LIGHT_FILL, line="accent" if highlight else None)
    rect(slide, st, x, y, w, 0.12, "accent" if highlight else "primary")
    if highlight:
        badge = rect(slide, st, x + w - 2.6, y + 0.3, 2.3, 0.7, "accent", shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        label_in(badge, st, "권고안", 11)
    top = y + 0.35
    if g["title"]:
        text(slide, st, x + 0.4, top, w - 0.8, 0.8, g["title"], size=size + 1, font="emphasis", color="primary", bold=True, fit=False)
        top += 1.0
    text(slide, st, x + 0.4, top, w - 0.8, h - (top - y) - 0.3, [f"· {t}" for t in g["items"]], size=size, spacing=6)


def card_height(g, w, size=13):
    items, concl = _split_conclusion(g["items"])
    body = "\n".join(f"· {t}" for t in items)
    n = lines_needed(body, w - 1.0, size)
    return 0.35 + (1.25 if g["title"] else 0) + n * size * LINE_H * 1.35 + 0.6 + 1.3 * len(concl)


MIN_CARD = 4.2      # 카드가 너무 납작해 보이지 않게 하는 최소 높이(cm)


def recommended_index(groups, message):
    """비교안(C07)에서 권고안 찾기: 그룹 제목의 '권고·추천' 표시, 또는 메시지의 'N안으로/N안을'."""
    for i, g in enumerate(groups):
        if g["title"] and re.search(r"(권고|추천)", g["title"]):
            return i
    m = re.search(r"(\d)\s*안\s*(으로|을|를|이)\s*(운영|추천|권고|제안|시작|진행)", message or "")
    if m:
        for i, g in enumerate(groups):
            if g["title"] and re.match(rf"^{m.group(1)}\s*안", g["title"]):
                return i
    return None


def body_groups(slide, st, items, left, top, width, height, dry=False, message=None, fill=False):
    """fill: 묶음 장의 한 칸을 꽉 채운다. 칸이 좁아 카드가 5.5cm 보다 좁아지면 카드를 세로로 쌓는다."""
    groups = _groups(items)
    if not groups:
        return 0
    titled = [g for g in groups if g["title"]]
    size = 13 if width >= 14 else 12
    if len(titled) >= 2 and len(groups) <= 4:
        gap = 0.5
        n = len(groups)
        rec = recommended_index(groups, message) if message is not None else None
        hl = lambda i: None if rec is None else i == rec
        w = (width - gap * (n - 1)) / n
        # fill 은 칸 크기 그대로 그리고(글자는 칸에 맞춰 줄어든다) 필요한 높이를 돌려줘 넘침을 알린다
        if fill and w < 5.5:        # 좁은 칸: 세로로 쌓기
            h = (height - gap * (n - 1)) / n
            if not dry:
                for i, g in enumerate(groups):
                    _card(slide, st, g, left, top + i * (h + gap), width, h, size=size, highlight=hl(i))
            need = sum(card_height(g, width, size) for g in groups) + gap * (n - 1)
            return max(height, need * 0.8)
        need = max(MIN_CARD, max(card_height(g, w, size) for g in groups))
        if fill:
            if not dry:
                for i, g in enumerate(groups):
                    _card(slide, st, g, left + i * (w + gap), top, w, height, size=size, highlight=hl(i))
            return max(height, need * 0.8)
        h = min(height, need)
        if not dry:
            for i, g in enumerate(groups):
                _card(slide, st, g, left + i * (w + gap), top, w, h, size=size, highlight=hl(i))
        return h
    lines = []
    for g in groups:
        if g["title"]:
            lines.append(f"【 {g['title']} 】")
        lines += [f"· {t}" for t in g["items"]]
    if fill:        # 칸을 옅은 상자로 채우고 그 안에 글
        need = lines_needed("\n".join(lines), width - 0.8, size) * size * LINE_H * 1.3 + 0.8
        if not dry:
            rect(slide, st, left, top, width, height, LIGHT_FILL)
            text(slide, st, left + 0.4, top + 0.4, width - 0.8, height - 0.6, lines, size=size, spacing=6)
        return max(height, need * 0.8)
    need = min(height, lines_needed("\n".join(lines), width, 13) * 13 * LINE_H * 1.3 + 0.4)
    if not dry:
        text(slide, st, left, top, width, need, lines, size=13, spacing=4)
    return need


def body_c01(slide, st, items, left, top, width, height, dry=False, fill=False):
    """핵심 과제 | 대응 역량 2단 + 하단 3대 축. 그룹이 3개가 아니면 일반 카드로."""
    groups = _groups(items)
    if len(groups) != 3 or not all(g["title"] for g in groups):
        return body_groups(slide, st, items, left, top, width, height, dry, fill=fill)
    gap = 0.5
    axis_h = 3.2
    w = (width - gap) / 2
    upper_h = min(height - axis_h - 0.9, max(MIN_CARD, max(card_height(g, w) for g in groups[:2])))
    if dry:
        return upper_h + 0.9 + axis_h
    for i, g in enumerate(groups[:2]):
        _card(slide, st, g, left + i * (w + gap), top, w, upper_h)
    # 화살표 → 3대 축
    arrow = rect(slide, st, left + width / 2 - 0.6, top + upper_h + 0.1, 1.2, 0.6, "muted", shape=MSO_SHAPE.DOWN_ARROW)
    y = top + upper_h + 0.8
    axis = groups[2]
    text(slide, st, left, y, width, 0.7, f"【 {axis['title']} 】", size=13, font="emphasis", color="primary", bold=True, fit=False)
    items3 = axis["items"][:4]
    n = max(1, len(items3))
    aw = (width - gap * (n - 1)) / n
    for i, it in enumerate(items3):
        box = rect(slide, st, left + i * (aw + gap), y + 0.8, aw, axis_h - 0.9, "primary")
        label_in(box, st, it, _fit_size(it, aw - 0.4, axis_h - 1.2, 15), font="emphasis")
    return upper_h + 0.9 + axis_h


def body_table(slide, st, rows, left, top, width, height, dry=False, fill=False):
    """fill: 칸 높이를 채우도록 본문 행을 늘린다. 좁은 칸에서는 글자를 한 단계 줄이고 줄바꿈만큼 행을 키운다."""
    if not rows:
        return 0
    nrows, ncols = len(rows), max(len(r) for r in rows)
    size = 12 if nrows <= 6 else (11 if nrows <= 9 else 10)
    first = 0.28 if ncols >= 3 else 0.32
    widths = [width * first] + [width * (1 - first) / (ncols - 1)] * (ncols - 1) if ncols > 1 else [width]
    if fill:
        if width < 14:
            size -= 1
        need = [max(0.9, max(lines_needed(r[j] if j < len(r) else "", widths[j] - 0.6, size) for j in range(ncols))
                    * size * LINE_H * 1.15 + 0.35) for r in rows]
        extra = max(0.0, height - sum(need)) / max(1, nrows - 1)     # 머리 행은 그대로, 남는 높이는 본문 행에
        heights = [need[0]] + [h + extra for h in need[1:]]     # 옆 블록과 아래 선이 맞게 칸 끝까지
    else:
        heights = [max(0.9, min(1.6, height / nrows))] * nrows
    if dry:
        return sum(heights)
    shape = slide.shapes.add_table(nrows, ncols, Cm(left), Cm(top), Cm(width), Cm(sum(heights)))
    tbl = shape.table
    for j, w in enumerate(widths):
        tbl.columns[j].width = Cm(w)
    for i in range(nrows):
        tbl.rows[i].height = Cm(heights[i])
    for i, row in enumerate(rows):
        for j in range(ncols):
            cell = tbl.cell(i, j)
            val = row[j] if j < len(row) else ""
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            r = p.add_run()
            r.text = val
            r.font.size = Pt(size)
            r.font.name = st.font("emphasis" if i == 0 or j == 0 else "body")
            r.font.bold = i == 0
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = cell.margin_right = Cm(0.25)
            cell.fill.solid()
            if i == 0:
                r.font.color.rgb = st.color("white")
                cell.fill.fore_color.rgb = st.color("primary")
                p.alignment = PP_ALIGN.CENTER
            else:
                r.font.color.rgb = st.color("accent") if CHECK.search(val) else st.color("primary" if j == 0 else "text")
                cell.fill.fore_color.rgb = RGBColor.from_string("FFFFFF" if i % 2 else LIGHT_FILL)
    return sum(heights)


def _steps_vertical(slide, st, parsed, descs, left, top, width, height, dry):
    """좁은 칸의 흐름도: 단계를 위에서 아래로. 왼쪽 단계 이름(아래 화살표 모양), 오른쪽 설명."""
    n = len(parsed)
    gap = 0.4
    name_w = min(5.0, width * 0.38)
    need_rows = [max(1.1, lines_needed("\n".join(d) or " ", width - name_w - 0.8, 11) * 11 * LINE_H * 1.3 + 0.4) for d in descs]
    row_h = max(max(need_rows), (height - gap * (n - 1)) / n)
    used = row_h * n + gap * (n - 1)
    if dry:
        return used
    name_size = min(_fit_size(f"{i + 1:02d} {nm}", name_w - 0.4, row_h * 0.5, 13) for i, (nm, _) in enumerate(parsed))
    for i, (name, _) in enumerate(parsed):
        y = top + i * (row_h + gap)
        fill_key = "primary" if i == 0 or st.band() else "accent"
        box = rect(slide, st, left, y, name_w, row_h, fill_key)
        label_in(box, st, f"{i + 1:02d} {name}", name_size)
        if i < n - 1:       # 다음 단계로 가는 작은 아래 삼각형
            tri = rect(slide, st, left + name_w / 2 - 0.35, y + row_h - 0.01, 0.7, gap * 0.8, fill_key,
                       shape=MSO_SHAPE.ISOSCELES_TRIANGLE)
            tri.rotation = 180
        rect(slide, st, left + name_w + 0.2, y, width - name_w - 0.2, row_h, LIGHT_FILL)
        if descs[i]:
            text(slide, st, left + name_w + 0.45, y + 0.15, width - name_w - 0.7, row_h - 0.3, descs[i], size=11,
                 spacing=3, anchor=MSO_ANCHOR.MIDDLE)
    return used


def body_steps(slide, st, steps, left, top, width, height, dry=False, fill=False, compact=False):
    """fill: 설명 칸을 칸 높이까지 늘린다. 단계 하나가 3.4cm 보다 좁아지면 위→아래 흐름으로 그린다.
    compact: 묶음 장에서 위아래로 나눌 때 필요한 높이만 잰다 (최소 카드 높이 없이)."""
    parsed = [(n.strip(), d.strip()) for n, _, d in (s.partition("|") for s in steps)]
    if not parsed:
        return 0
    n = len(parsed)
    gap = 0.25
    w = (width - gap * (n - 1)) / n
    descs = [[f"· {d.strip()}" for d in re.split(r"\s*;\s*", desc) if d.strip()] for _, desc in parsed]
    if fill and w < 3.4:
        return _steps_vertical(slide, st, parsed, descs, left, top, width, height, dry)
    chev_h = 1.5
    name_size = min(_fit_size(f"{i + 1:02d} {nm}", w - 1.4, 0.7, 14) for i, (nm, _) in enumerate(parsed))
    need = max([lines_needed("\n".join(d), w - 0.6, 12) for d in descs] + [1]) * 12 * LINE_H * 1.3 + 0.8
    if compact:
        card_h = max(need, 2.2)
    elif fill:
        card_h = max(need, height - chev_h - 0.3)
    else:
        card_h = min(height - chev_h - 0.3, max(need, MIN_CARD))
    if dry:
        return chev_h + 0.3 + card_h
    for i, (name, _) in enumerate(parsed):
        x = left + i * (w + gap)
        chev = rect(slide, st, x, top, w, chev_h, "primary" if i == 0 or st.band() else "accent",
                    shape=MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON)
        label_in(chev, st, f"{i + 1:02d} {name}", name_size)
        if descs[i]:
            rect(slide, st, x, top + chev_h + 0.3, w, card_h, LIGHT_FILL)
            text(slide, st, x + 0.25, top + chev_h + 0.55, w - 0.5, card_h - 0.4, descs[i], size=12, spacing=6)
    return chev_h + 0.3 + card_h


def _mix_white(hexcolor, t):
    """색을 흰색 쪽으로 t(0~1) 만큼 섞은 6자리 hex."""
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))
    return "".join(f"{int(c + (255 - c) * t):02X}" for c in (r, g, b))


def _cell_border(cell, color="BFBFBF", width_pt=0.75):
    from lxml import etree
    from pptx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr()
    for i, tag in enumerate(("a:lnL", "a:lnR", "a:lnT", "a:lnB")):
        old = tcPr.find(qn(tag))
        if old is not None:
            tcPr.remove(old)
        ln = etree.Element(qn(tag), w=str(int(width_pt * 12700)), cap="flat", cmpd="sng", algn="ctr")
        etree.SubElement(etree.SubElement(ln, qn("a:solidFill")), qn("a:srgbClr"), val=color)
        etree.SubElement(ln, qn("a:prstDash"), val="solid")
        tcPr.insert(i, ln)       # 테두리는 채우기보다 앞에 와야 한다


def _cell_text(cell, st, value, size, color, font="body", bold=False, align=PP_ALIGN.CENTER, fill=None):
    cell.text = ""
    p = cell.text_frame.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = value
    r.font.size = Pt(size)
    r.font.name = st.font(font)
    r.font.bold = bold
    r.font.color.rgb = RGBColor.from_string(color) if HEX.fullmatch(color) else st.color(color)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    cell.margin_left = cell.margin_right = Cm(0.15)
    cell.margin_top = cell.margin_bottom = Cm(0.02)
    cell.fill.solid()
    cell.fill.fore_color.rgb = RGBColor.from_string(fill or "FFFFFF")
    _cell_border(cell)


def body_timeline(slide, st, rows, periods, left, top, width, height, dry=False, fill=False):
    """타임테이블(간트): 월·주 2단 머리 + 항목 묶음 + 기간 칸 위 화살표 막대.
    rows: [머리, (항목, 세부 일정, 시작, 끝, 표시)...], periods: ['10월 4W', '11월 1W', ...]"""
    data = [r + [""] * (5 - len(r)) for r in rows[1:]]
    if not data or not periods:
        return 0
    two = any(" " in p for p in periods)
    nh = 2 if two else 1
    nrows, ncols = len(data) + nh, 2 + len(periods)
    row_h = max(0.5, min(0.8, (height - 0.3) / nrows))
    if dry:
        return row_h * nrows
    c0, c1 = 2.4, min(7.0, width * 0.3)
    ww = (width - c0 - c1) / len(periods)
    shape = slide.shapes.add_table(nrows, ncols, Cm(left), Cm(top), Cm(width), Cm(row_h * nrows))
    tbl = shape.table
    tbl.first_row = tbl.horz_banding = False
    for j, w in enumerate([c0, c1] + [ww] * len(periods)):
        tbl.columns[j].width = Cm(w)
    for i in range(nrows):
        tbl.rows[i].height = Cm(row_h)
    head_fill = st.colors.get("text", "414756")
    months = [p.split(" ", 1)[0] for p in periods]
    weeks = [p.split(" ", 1)[1] if " " in p else p for p in periods]
    # 머리 1단: Time Table | 월(묶음)
    for j in range(ncols):
        _cell_text(tbl.cell(0, j), st, "", 11, "white", "emphasis", fill=head_fill)
    _cell_text(tbl.cell(0, 0), st, rows[0][0] if rows[0] and rows[0][0] not in ("", "항목") else "Time Table",
               11, "white", "emphasis", fill=head_fill)
    tbl.cell(0, 0).merge(tbl.cell(0, 1))
    j = 0
    while j < len(periods):
        k = j
        while two and k + 1 < len(periods) and months[k + 1] == months[j]:
            k += 1
        _cell_text(tbl.cell(0, 2 + j), st, months[j] if two else periods[j], 11, "white", "emphasis", fill=head_fill)
        if k > j:
            tbl.cell(0, 2 + j).merge(tbl.cell(0, 2 + k))
        j = k + 1
    if two:     # 머리 2단: 항목 | 세부 일정 | 주
        for j, v in enumerate(["항목", "세부 일정"] + weeks):
            _cell_text(tbl.cell(1, j), st, v, 10, "white", "emphasis", fill=_mix_white(head_fill, 0.15))
    # 본문: 항목은 같은 값끼리 세로로 합친다
    for i, r in enumerate(data):
        ri = nh + i
        same = i > 0 and r[0] in (data[i - 1][0], "")
        _cell_text(tbl.cell(ri, 0), st, "" if same else r[0], 10, "text", "emphasis")   # 합칠 칸은 첫 칸에만 글자
        _cell_text(tbl.cell(ri, 1), st, r[1], 10, "text", align=PP_ALIGN.LEFT)
        for j in range(len(periods)):
            _cell_text(tbl.cell(ri, 2 + j), st, "", 9, "text")
    i = 0
    while i < len(data):
        k = i
        while k + 1 < len(data) and data[k + 1][0] in (data[i][0], ""):
            k += 1
        if k > i:
            tbl.cell(nh + i, 0).merge(tbl.cell(nh + k, 0))
        i = k + 1
    # 막대: 시작 칸 왼쪽 ~ 끝 칸 오른쪽, 짙은·옅은 색 번갈아
    dark, light = st.colors.get("accent", "4D74B4"), _mix_white(st.colors.get("accent", "4D74B4"), 0.45)
    for i, r in enumerate(data):
        if r[2] not in periods or r[3] not in periods:
            continue
        si, ei = periods.index(r[2]), periods.index(r[3])
        x0 = left + c0 + c1 + si * ww
        bw = (ei - si + 1) * ww
        y = top + (nh + i) * row_h + row_h * 0.14
        bar = rect(slide, st, x0, y, bw, row_h * 0.72, dark if i % 2 == 0 else light, shape=MSO_SHAPE.PENTAGON)
        bar.adjustments[0] = min(0.5, 0.35 * (row_h * 0.72) / bw * 2)
        label = r[4] if r[4] not in ("", "-") else ("완료" if r[4] == "" else "")
        if label:
            tf = bar.text_frame
            tf.margin_right = Cm(0.45)
            tf.margin_left = Cm(0.05)
            tf.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT
            run = p.add_run()
            run.text = label
            run.font.size = Pt(10)
            run.font.name = st.font("emphasis")
            run.font.color.rgb = st.color("white") if i % 2 == 0 else st.color("text")
    return row_h * nrows


def _style_pie(ch, st, palette):
    plot = ch.plots[0]
    plot.has_data_labels = True
    labels = plot.data_labels
    labels.show_percentage = True
    labels.show_value = False
    labels.show_category_name = False
    labels.number_format = "0%"
    labels.number_format_is_linked = False
    labels.position = XL_LABEL_POSITION.OUTSIDE_END
    labels.font.size = Pt(11)
    labels.font.color.rgb = st.color("text")
    series = ch.series[0]
    for i in range(len(list(series.values))):
        point = series.points[i]
        point.format.fill.solid()
        point.format.fill.fore_color.rgb = RGBColor.from_string(palette[i % len(palette)])
        point.format.line.color.rgb = st.color("white")
    ch.has_legend = True
    ch.legend.position = XL_LEGEND_POSITION.RIGHT
    ch.legend.include_in_layout = False
    ch.legend.font.size = Pt(11)
    ch.font.name = st.font("body")


def body_chart(slide, st, rows, left, top, width, height, dry=False, kind="bar", fill=False):
    if not rows or len(rows) < 2:
        return 0
    if dry:
        return height
    head, data = rows[0], rows[1:]
    if kind == "pie":       # 원형은 계열 하나만 뜻이 있다
        head = head[:2]
    values = {j: [chart_number(r[j]) if j < len(r) else None for r in data] for j in range(1, len(head))}
    decimal = any(v is not None and v % 1 for vals in values.values() for v in vals)   # 98.5 를 99 로 반올림해 보이지 않게
    number_format = "#,##0.0" if decimal else "#,##0"
    cd = CategoryChartData(number_format=number_format)
    cd.categories = [r[0] for r in data]
    for j, name in enumerate(head[1:], start=1):
        cd.add_series(name, values[j])
    chart_type = {"bar": XL_CHART_TYPE.COLUMN_CLUSTERED, "line": XL_CHART_TYPE.LINE_MARKERS, "pie": XL_CHART_TYPE.PIE}[kind]
    gf = slide.shapes.add_chart(chart_type, Cm(left), Cm(top), Cm(width), Cm(height), cd)
    ch = gf.chart
    ch.has_legend = len(head) > 2
    palette = [st.colors["primary"], st.colors["accent"], st.colors["muted"], "6B7A99"]
    if kind == "pie":
        palette += [_mix_white(st.colors["primary"], 0.45), _mix_white(st.colors["accent"], 0.55)]
    if len(head) == 2:      # 계열 하나: 제목은 작게, 값 표시
        ch.has_title = True
        ch.chart_title.text_frame.text = head[1]
        tr = ch.chart_title.text_frame.paragraphs[0].runs[0]
        tr.font.size = Pt(12)
        tr.font.bold = False
        tr.font.name = st.font("emphasis")
        tr.font.color.rgb = st.color("text")
        if kind != "pie":
            plot = ch.plots[0]
            plot.has_data_labels = True
            plot.data_labels.number_format = number_format
            plot.data_labels.number_format_is_linked = False
            plot.data_labels.font.size = Pt(10)
            plot.data_labels.font.color.rgb = st.color("text")
            if kind == "line":
                plot.data_labels.position = XL_LABEL_POSITION.ABOVE
    if kind == "pie":
        _style_pie(ch, st, palette)
        return height
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.TOP
        ch.legend.include_in_layout = False
        ch.legend.font.size = Pt(11)
    va = ch.value_axis
    va.has_major_gridlines = True
    va.major_gridlines.format.line.color.rgb = RGBColor.from_string(GRID)
    va.format.line.fill.background()
    va.tick_labels.number_format = number_format
    va.tick_labels.number_format_is_linked = False
    va.tick_labels.font.size = Pt(10)
    ch.category_axis.tick_labels.font.size = Pt(11)
    ch.category_axis.format.line.color.rgb = RGBColor.from_string(GRID)
    for i, s in enumerate(ch.series):
        rgb = RGBColor.from_string(palette[i % len(palette)])
        if kind == "line":
            s.smooth = False
            s.format.line.color.rgb = rgb
            s.format.line.width = Pt(2.25)
            s.marker.style = XL_MARKER_STYLE.CIRCLE
            s.marker.size = 7
            s.marker.format.fill.solid()
            s.marker.format.fill.fore_color.rgb = rgb
            s.marker.format.line.color.rgb = rgb
        else:
            s.format.fill.solid()
            s.format.fill.fore_color.rgb = rgb
    if kind == "bar":
        ch.plots[0].gap_width = 60
    ch.font.name = st.font("body")
    return height


def _org_line(slide, st, x1, y1, x2, y2):
    line = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Cm(x1), Cm(y1), Cm(x2), Cm(y2))
    line.line.color.rgb = st.color("muted")
    line.line.width = Pt(1)
    line.element.xpath(".//a:effectRef")[0].set("idx", "0")     # 테마 기본 그림자를 끈다


def _org_box(slide, st, node, left, top, width, height):
    """최상위는 primary, 둘째 줄은 accent, 그 아래는 옅은 칸. 빈칸 표시가 묻히지 않게 [확인 필요]는 옅은 칸에 그린다."""
    name, desc = node["name"], node["desc"]
    pending = CHECK.search(name) or CHECK.search(desc)
    dark = node["level"] < 2 and not pending
    box = rect(slide, st, left, top, width, height,
               ("primary" if node["level"] == 0 else "accent") if dark else LIGHT_FILL, line=None if dark else GRID)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Cm(0.08)
    tf.margin_top = tf.margin_bottom = Cm(0.03)
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    room = width - 0.2
    lines = [(name, _fit_size(name, room, height * (0.5 if desc else 0.9), 12), "emphasis", True)]
    if desc:
        lines.append((desc, _fit_size(desc, room, height * 0.45, 10, min_size=8), "body", False))
    for i, (value, size, font, bold) in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = value
        r.font.size = Pt(size)
        r.font.name = st.font(font)
        r.font.bold = bold
        r.font.color.rgb = st.color("accent") if CHECK.search(value) else st.color("white" if dark else "text")


def body_org(slide, st, items, left, top, width, height, dry=False, fill=False):
    """조직도: 위에서 아래로 뻗는 트리. 팀원이 많으면 말단은 부모 아래 세로로 쌓는다."""
    org = org_layout(org_tree(items))
    if not org["nodes"]:
        return 0
    gap = 0.6
    box_h = min(1.8, (height - gap * (org["rows"] - 1)) / org["rows"])
    used = org["rows"] * box_h + gap * (org["rows"] - 1)
    if dry:
        return used
    cw = width / org["cols"]
    box_w = min(5.6, cw - 0.35)
    center = lambda n: left + n["x"] * cw
    y_of = lambda n: top + n["row"] * (box_h + gap)
    for n in org["nodes"]:      # 선을 먼저 그려 상자가 위에 오게 한다
        kids, bottom = n["kids"], y_of(n) + box_h
        if not kids:
            continue
        if n.get("stack"):
            rail = center(n) - box_w / 2 + 0.25
            _org_line(slide, st, rail, bottom, rail, y_of(kids[-1]) + box_h / 2)
            for k in kids:
                _org_line(slide, st, rail, y_of(k) + box_h / 2, rail + 0.45, y_of(k) + box_h / 2)
            continue
        mid = bottom + gap / 2
        _org_line(slide, st, center(n), bottom, center(n), mid)
        if len(kids) > 1:
            _org_line(slide, st, center(kids[0]), mid, center(kids[-1]), mid)
        for k in kids:
            _org_line(slide, st, center(k), mid, center(k), y_of(k))
    for n in org["nodes"]:
        x, w = center(n) - box_w / 2, box_w
        if n.get("hang"):
            x, w = x + 0.7, w - 0.7
        _org_box(slide, st, n, x, y_of(n), w, box_h)
    return used


def _photo_cell(slide, st, path, cap, x, y, w, h, fit=False):
    """사진을 칸에 꽉 차게(비율 유지, 넘치는 쪽을 잘라) 넣고 아래에 캡션 띠. fit 이면 자르지 않고 칸 안 가운데에."""
    cap_h = 0.8 if cap else 0
    ph = h - cap_h
    if path is None:
        box = rect(slide, st, x, y, w, ph, LIGHT_FILL, line=GRID)
        label_in(box, st, "[확인 필요: 사진]", 11, color="accent", font="body", bold=False)
    elif fit:
        rect(slide, st, x, y, w, ph, "FFFFFF", line=GRID)
        try:
            from PIL import Image
            with Image.open(path) as im:
                iw, ih = im.size
            s = min((w - 0.2) / iw, (ph - 0.2) / ih)
            pw, pph = iw * s, ih * s
        except Exception:
            pw, pph = w - 0.2, ph - 0.2
        slide.shapes.add_picture(str(path), Cm(x + (w - pw) / 2), Cm(y + (ph - pph) / 2), Cm(pw), Cm(pph))
    else:
        pic = slide.shapes.add_picture(str(path), Cm(x), Cm(y), Cm(w), Cm(ph))
        try:
            from PIL import Image
            with Image.open(path) as im:
                iw, ih = im.size
            r_img, r_box = iw / ih, w / ph
            if r_img > r_box:       # 사진이 더 넓다 → 좌우를 자른다
                c = (1 - r_box / r_img) / 2
                pic.crop_left = pic.crop_right = c
            elif r_img < r_box:
                c = (1 - r_img / r_box) / 2
                pic.crop_top = pic.crop_bottom = c
        except Exception:
            pass
    if cap:
        band = rect(slide, st, x, y + ph, w, cap_h, "primary")
        label_in(band, st, cap, _fit_size(cap, w - 0.4, 0.6, 11), font="emphasis", bold=False)


def body_photos(slide, st, items, left, top, width, height, dry=False, fill=False):
    """사진 1~4장: 1장 = 칸 전체, 2~3장 = 나란히(칸이 세로로 길면 위아래), 4장 = 2×2."""
    from .outline import photo_items
    from .refbank import resolve_photo
    photos = photo_items(items)[:4]
    if not photos:
        return 0
    if not fill:
        height = min(height, width * 0.5)
    if dry:
        return height
    n, gap = len(photos), 0.3
    if n == 4:
        grid = [(c, r) for r in range(2) for c in range(2)]
        cols, rows = 2, 2
    elif n > 1 and height > width * 1.1:
        grid, cols, rows = [(0, i) for i in range(n)], 1, n
    else:
        grid, cols, rows = [(i, 0) for i in range(n)], n, 1
    cw = (width - gap * (cols - 1)) / cols
    rh = (height - gap * (rows - 1)) / rows
    for (src, cap, fit), (c, r) in zip(photos, grid):
        _photo_cell(slide, st, resolve_photo(src), cap, left + c * (cw + gap), top + r * (rh + gap), cw, rh, fit)
    return height


# ---------------------------------------------------------------- 묶음 배치 (한 장에 블록 2~3개)

GRID_GAP = 0.6
CAP_H = 0.85        # 블록 소제목 줄 높이
NATURAL = {"단계", "일정"}      # 위아래로 나눌 때 필요한 만큼만 높이를 받는 블록


def caption(slide, st, left, top, width, value):
    """블록 위 소제목: 짧은 색 막대 + 굵은 글."""
    rect(slide, st, left, top + 0.12, 0.18, 0.5, "accent")
    text(slide, st, left + 0.35, top, width - 0.35, 0.75, value, size=13, font="emphasis", color="primary", bold=True,
         anchor=MSO_ANCHOR.MIDDLE)


def _wide(s, k):
    return k == "일정" or (k == "단계" and len(s.get("단계") or []) >= 4)


def layout_tree(s, parts):
    """블록 순서 + '배치:' → 나누기 나무. ('h'|'v', [(자식, 비율|None)...]) 또는 블록 이름.
    자동: 2개는 좌우(넓은 흐름도·일정이 있으면 위아래), 3개는 좌1우2(넓은 블록이 있으면 그것을 위에 둔 상1하2), 4개 이상은 위아래."""
    n = len(parts)
    if n == 1:
        return parts[0]
    kind, weights = parse_layout(s.get("배치"))
    if kind in (None, "?"):
        kind, weights = None, None
        wide = [k for k in parts if _wide(s, k)]
        kind = ("v" if wide else "h") if n == 2 else (("t12" if wide else "l12") if n == 3 else "v")
        if kind == "t12":
            parts = [wide[0]] + [k for k in parts if k != wide[0]]
    if kind in ("l12", "t12") and n != 3:
        kind = "h" if kind == "l12" else "v"
    if kind in ("h", "v"):
        w = weights if weights and len(weights) == n else None
        return (kind, [(k, w[i] if w else (1 if kind == "h" else None)) for i, k in enumerate(parts)])
    a, b = (weights[:2] if weights and len(weights) >= 2 else (1, 1)) if kind == "l12" else \
           (weights[:2] if weights and len(weights) >= 2 else (None, None))
    if kind == "l12":
        return ("h", [(parts[0], a), (("v", [(parts[1], None), (parts[2], None)]), b)])
    return ("v", [(parts[0], a), (("h", [(parts[1], 1), (parts[2], 1)]), b)])


def place_tree(node, x, y, w, h, natural_h, out):
    """나무를 칸으로 나눠 out 에 (블록, x, y, w, h) 를 쌓는다. natural_h(블록, 폭) = 그 폭에서 필요한 높이."""
    if isinstance(node, str):
        out.append((node, x, y, w, h))
        return
    d, kids = node
    m = len(kids)
    if d == "h":
        avail = w - GRID_GAP * (m - 1)
        tot = sum(wt for _, wt in kids)
        cx = x
        for child, wt in kids:
            cw = avail * wt / tot
            place_tree(child, cx, y, cw, h, natural_h, out)
            cx += cw + GRID_GAP
        return
    avail = h - GRID_GAP * (m - 1)
    if all(wt for _, wt in kids):
        tot = sum(wt for _, wt in kids)
        sizes = [avail * wt / tot for _, wt in kids]
    else:
        nat = {i: natural_h(c, w) for i, (c, _) in enumerate(kids) if isinstance(c, str) and c in NATURAL}
        rest = avail - sum(nat.values())
        others = m - len(nat)
        if not nat or not others or rest < 3.5 * others:      # 나머지 칸이 너무 납작해지면 똑같이 나눈다
            sizes = [avail / m] * m
        else:
            sizes = [nat[i] if i in nat else rest / others for i in range(m)]
    cy = y
    for (child, _), ch in zip(kids, sizes):
        place_tree(child, x, cy, w, ch, natural_h, out)
        cy += ch + GRID_GAP


# ---------------------------------------------------------------- 유형별 슬라이드

def _section_parts(sec):
    m = re.match(r"^\s*(\d{1,2})\s*\.?\s*(.*)$", sec or "")
    return (int(m.group(1)), m.group(2).strip()) if m else (None, (sec or "").strip())


SECTION_WORDS = ["ZERO", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]


def cover_panel(slide, st, meta, s):
    """표지: 왼쪽 고객사 로고 · 건명 · 제안사, 오른쪽 사선 색 면."""
    W, H = st.size
    panel = rect(slide, st, W * 0.47, 1.2, W * 0.53 - 1.0, H - 2.6, "primary", shape=MSO_SHAPE.PARALLELOGRAM)
    panel.adjustments[0] = 0.18
    if st.cover_image:
        size = min(W * 0.53 - 1.0, H - 2.6) * 0.5
        cx, cy = W * 0.47 + (W * 0.53 - 1.0) / 2, 1.2 + (H - 2.6) / 2
        _picture(slide, st.cover_image, cx - size / 2, cy - size / 2, size, size)
    if st.client_logo:
        _picture(slide, st.client_logo, 2.0, 3.2, 9.5, 1.8, align="left")
    else:
        text(slide, st, 2.0, 3.4, 11, 1.2, meta.get("고객사", ""), size=24, font="emphasis", color="primary", fit=False)
    text(slide, st, 2.0, 7.6, 11.0, 2.8, meta.get("건명", meta.get("title", "")), size=26, font="emphasis", color="text")
    if s.get("메시지"):
        text(slide, st, 2.0, 10.6, 10.5, 1.8, s["메시지"], size=13, color="muted")
    text(slide, st, 2.0, H - 4.0, 10, 0.8, meta.get("제안사", ""), size=14, color="text", fit=False)
    text(slide, st, 2.0, H - 3.2, 10, 0.8, meta.get("날짜", ""), size=14, color="text", fit=False)


def toc_list(slide, st, sections):
    """목차: 왼쪽 색 면, 오른쪽 'N장 이름' 목록."""
    W, H = st.size
    rect(slide, st, 0, 0, W * 0.4, H, "primary")
    text(slide, st, 1.8, H / 2 - 1.2, W * 0.4 - 3, 1.6, "CONTENTS", size=30, font="emphasis", color="white", fit=False)
    x = W * 0.4 + 2.5
    text(slide, st, x, 3.0, 10, 1.4, "목차", size=26, font="emphasis", color="primary", fit=False)
    for i, (num, name) in enumerate(sections):
        y = 5.0 + i * 1.45
        text(slide, st, x, y, 1.8, 0.9, f"{num}장", size=16, font="emphasis", color="primary", fit=False)
        text(slide, st, x + 1.9, y, W - x - 3, 0.9, name, size=16, color="text", fit=False)


def divider_light(slide, st, num, name):
    """간지: 흰 바탕, 큰 회색 번호 위에 SECTION 표기와 장 이름, 바닥 그라데이션 띠."""
    W, H = st.size
    if num is not None:
        text(slide, st, 0, H / 2 - 3.2, W, 5.0, f"{num:02d}", size=120, font="title", color="E3E5EA",
             align=PP_ALIGN.CENTER, fit=False)
        word = SECTION_WORDS[num] if num < len(SECTION_WORDS) else str(num)
        text(slide, st, 0, H / 2 - 2.6, W, 0.8, f"S E C T I O N   {' '.join(word)}", size=12, font="emphasis",
             color="primary", align=PP_ALIGN.CENTER, fit=False)
    text(slide, st, 0, H / 2 - 1.5, W, 1.8, name, size=34, font="emphasis", color="text", align=PP_ALIGN.CENTER, fit=False)
    rect(slide, st, W / 2 - 3.3, H / 2 + 1.6, 6.6, 0.22, "E3E5EA")
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Cm(H - 0.45), Cm(W), Cm(0.45))
    bar.line.fill.background()
    bar.fill.gradient()
    bar.fill.gradient_angle = 0
    stops = bar.fill.gradient_stops
    stops[0].color.rgb = st.color("primary")
    stops[0].position = 0.0
    stops[1].color.rgb = RGBColor.from_string("FFFFFF")
    stops[1].position = 1.0


def render(outline, cfg=None, out_path="deck.pptx", client_mark=None, client_logo=None, cover_image=None,
           footer_right=None):
    st = Style(cfg)
    st.footer_right = footer_right
    if client_logo:     # 우측 상단에 고객사 로고가 있으면 하단엔 다시 넣지 않는다: 왼쪽 회사 로고 · 오른쪽 쪽 번호
        st.footer_right = None
        if st.design.get("footer_logo"):
            st.design["footer_logo_align"] = "left"
    st.client_logo = client_logo
    st.cover_image = cover_image
    prs = Presentation()
    W, H = st.size
    prs.slide_width, prs.slide_height = Cm(W), Cm(H)
    blank = prs.slide_layouts[6]
    meta = outline["meta"]
    sections = []
    for s in outline["slides"]:
        num, name = _section_parts(s.get("섹션"))
        if num is not None and (num, name) not in sections:
            sections.append((num, name))
    hdr = st.header
    body_left, body_top = hdr["message"]["left"], hdr["body_top"]
    body_w, body_h = hdr["message"]["width"], H - body_top - (1.7 if st.design.get("footer_logo") else 1.1)
    made, tight = [], []
    for s in outline["slides"]:
        if not s.get("type"):
            continue
        slide = prs.slides.add_slide(blank)
        t = s["type"]
        if t == "T01" and st.design.get("cover") == "panel":
            cover_panel(slide, st, meta, s)
        elif t == "T02" and st.design.get("toc") == "list":
            toc_list(slide, st, sections)
        elif t == "T03" and st.design.get("divider") == "light":
            divider_light(slide, st, *_section_parts(s.get("섹션")))
        elif t == "T01":
            rect(slide, st, 0, 0, 1.2, H, "primary")
            text(slide, st, 2.5, 5.2, W - 5, 1.0, meta.get("고객사", ""), size=16, font="emphasis", color="muted", fit=False)
            text(slide, st, 2.5, 6.4, W - 5, 3.2, meta.get("건명", meta.get("title", "")), size=32, font="title", color="primary")
            if s.get("메시지"):
                text(slide, st, 2.5, 9.9, W - 5, 1.6, s["메시지"], size=15, font="emphasis", color="text")
            text(slide, st, 2.5, H - 3.0, 10, 0.8, meta.get("날짜", ""), size=12, color="muted", fit=False)
            if meta.get("제안사"):
                text(slide, st, W - 9, H - 3.0, 7, 0.8, meta["제안사"], size=12, font="emphasis", color="primary", align=PP_ALIGN.RIGHT, fit=False)
        elif t == "T02":
            text(slide, st, 1.5, 1.2, 10, 1.4, "목차", size=28, font="title", color="primary", fit=False)
            per_col = 7
            for i, (num, name) in enumerate(sections):
                col, row = divmod(i, per_col)
                x = 2.0 + col * 12.5
                y = 3.8 + row * 1.9
                text(slide, st, x, y, 1.8, 1.0, f"{num:02d}", size=22, font="title", color="accent", fit=False)
                text(slide, st, x + 2.0, y + 0.15, 10, 1.0, name, size=17, font="emphasis", color="primary", fit=False)
                rect(slide, st, x, y + 1.4, 11.5, 0.03, GRID)
        elif t == "T03":
            num, name = _section_parts(s.get("섹션"))
            rect(slide, st, 0, 0, W, H, "primary")
            if num is not None:
                text(slide, st, 2.5, H / 2 - 2.6, 6, 2.0, f"{num:02d}", size=54, font="title", color="accent", fit=False)
            text(slide, st, 2.5, H / 2 - 0.4, W - 5, 1.6, name or s.get("제목", ""), size=30, font="title", color="white", fit=False)
        elif t == "T04":
            text(slide, st, 0, H / 2 - 1.2, W, 2.0, s.get("제목") or "감사합니다.", size=36, font="title", color="primary", align=PP_ALIGN.CENTER, fit=False)
            if s.get("메시지"):
                text(slide, st, 2, H / 2 + 1.0, W - 4, 1.2, s["메시지"], size=14, font="emphasis", color="text", align=PP_ALIGN.CENTER)
        else:
            num, name = _section_parts(s.get("섹션"))
            header(slide, st, num, name, s.get("제목"), s.get("메시지"), client_mark)
            parts = blocks(s)
            if t[0] == "L" and not parts:
                text(slide, st, body_left, body_top + 2, body_w, 2, "[확인 필요: 회사 소개 라이브러리 장표 삽입 — library.json company-intro]", size=14)
            if t == "C01":
                body_fn = body_c01
            elif t == "C07":
                body_fn = lambda *a, **k: body_groups(*a, message=s.get("메시지"), **k)
            else:
                body_fn = body_groups
            periods = [p.strip() for p in re.split(r"[,，]", s.get("기간", "")) if p.strip()]
            kind = chart_kind(s.get("차트")) or "bar"
            draw = {"본문": body_fn, "표": body_table, "단계": body_steps, "조직": body_org, "사진": body_photos,
                    "데이터": lambda *a, **k: body_chart(*a, kind=kind, **k),
                    "일정": lambda sl, st_, rows, *a, **k: body_timeline(sl, st_, rows, periods, *a, **k)}

            point = "" if t == "C13" else (s.get("포인트") or s.get("POINT") or "").strip()   # 조직도는 구조가 곧 메시지라 POINT 를 두지 않는다
            slide_body_h = body_h
            if point:     # 본문은 POINT 막대 위 0.4cm 에서 끝난다
                slide_body_h = min(body_h, point_box(st)[1] - 0.4 - body_top)

            cap_of = lambda k: (s.get(f"{k}_제목") or "").strip()

            if len(parts) >= 2:     # 묶음 장: 블록 2~3개로 본문 영역을 꽉 채운다
                def natural_h(k, w):
                    extra = {"compact": True} if k == "단계" else {}
                    return draw[k](slide, st, s[k], 0, 0, w, slide_body_h, dry=True, **extra) + (CAP_H if cap_of(k) else 0)
                cells = []
                place_tree(layout_tree(s, parts), body_left, body_top + 0.2, body_w, slide_body_h - 0.2, natural_h, cells)
                for k, x, y, w, h in cells:
                    if cap_of(k):
                        caption(slide, st, x, y, w, cap_of(k))
                        y, h = y + CAP_H, h - CAP_H
                    used = draw[k](slide, st, s[k], x, y, w, h, dry=False, fill=True)
                    if used > h + 0.15:
                        tight.append({"n": len(prs.slides), "block": k, "need_cm": round(used, 1), "room_cm": round(h, 1)})
            else:
                def layout(dry, y0):
                    y, remain = y0, slide_body_h - 0.2
                    for i, k in enumerate(parts):
                        last = i == len(parts) - 1
                        if cap_of(k):
                            if not dry:
                                caption(slide, st, body_left, y, body_w, cap_of(k))
                            y += CAP_H
                            remain -= CAP_H
                        avail = remain if last else remain * (0.45 if k == "본문" else 0.55)
                        used = draw[k](slide, st, s[k], body_left, y, body_w, avail, dry=dry)
                        y += used + 0.5
                        remain -= used + 0.5
                    return y - y0 - 0.5
                total = layout(True, 0)
                free = max(0.0, slide_body_h - 0.2 - total)
                layout(False, body_top + 0.2 + free * 0.3)   # 남는 공간은 위 30% · 아래 70% 로 나눈다
            if point:
                point_bar(slide, st, point)
        if t not in ("T01", "T03"):
            page_number(slide, st, len(prs.slides))
        if t not in ("T01", "T02", "T03", "T04"):
            footer(slide, st)
        made.append({"n": len(prs.slides), "outline_n": s.get("n"), "type": t})
    prs.save(out_path)
    # tight: 묶음 장에서 칸보다 내용이 긴 블록 — 글을 줄이거나 '배치:' 비율을 바꾼다
    return {"slides": len(prs.slides), "made": made, "font_swaps": st.font_swaps, "tight": tight}
