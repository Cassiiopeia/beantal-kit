"""PPT ↔ HTML 작업본.

작업 폴더 구성:
  deck.html        AI 가 고치는 파일. 장은 <section class="slide">, 요소는 cm 단위 절대 위치.
  deck.css/js      화면 표시용.
  assets/          그림. 차트·자유형 도형은 PowerPoint 가 찍은 PNG (data-kind="frozen").
  .baseline.html   변환 직후의 deck.html. PPT 로 되돌릴 때 비교 기준.
  deck.json        원본 pptx 경로.

되돌릴 때는 원본 PPT 를 다시 그리지 않는다. deck.html 과 .baseline.html 을 비교해 바뀐 요소·속성만
원본 복사본에 반영하므로, 건드리지 않은 차트·도형·마스터는 원본 그대로 남는다.
"""
import copy
import colorsys
import hashlib
import html as _html
import json
import platform
import re
import shutil
import tempfile
from pathlib import Path

from lxml import html as lxml_html
from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml import parse_xml
from pptx.oxml.ns import qn
from lxml import etree

EMU = 360000
ANS = "http://schemas.openxmlformats.org/drawingml/2006/main"
RPR_ORDER = ["ln", "noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill", "effectLst", "effectDag", "highlight", "uLnTx", "uLn", "uFillTx", "uFill", "latin", "ea", "cs", "sym", "hlinkClick", "hlinkMouseOver", "rtl", "extLst"]
PPR_ORDER = ["lnSpc", "spcBef", "spcAft", "buClrTx", "buClr", "buSzTx", "buSzPct", "buSzPts", "buFontTx", "buFont", "buNone", "buAutoNum", "buChar", "buBlip", "tabLst", "defRPr", "extLst"]
SPPR_ORDER = ["xfrm", "custGeom", "prstGeom", "noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill", "ln", "effectLst", "effectDag", "scene3d", "sp3d", "extLst"]
TCPR_ORDER = ["lnL", "lnR", "lnT", "lnB", "lnTlToBr", "lnBlToTr", "cell3D", "noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill", "headers", "extLst"]
LN_ORDER = ["noFill", "solidFill", "gradFill", "pattFill", "prstDash", "custDash", "round", "bevel", "miter", "headEnd", "tailEnd", "extLst"]
FILLS = ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")
ALIGN = {"l": "left", "ctr": "center", "r": "right", "just": "justify", "dist": "justify"}
ALIGN_BACK = {"left": "l", "center": "ctr", "right": "r", "justify": "just"}
ANCHOR = {"t": "flex-start", "ctr": "center", "b": "flex-end"}
ANCHOR_BACK = {v: k for k, v in ANCHOR.items()}
VALIGN = {"t": "top", "ctr": "middle", "b": "bottom"}
VALIGN_BACK = {v: k for k, v in VALIGN.items()}
DASH_BACK = {"dashed": "dash", "dotted": "sysDot", "solid": "solid"}
ADJ_NAME = {"roundRect": "adj", "chevron": "adj", "homePlate": "adj", "round2SameRect": "adj1", "rightArrow": "adj2", "leftArrow": "adj2", "upArrow": "adj2", "downArrow": "adj2", "notchedRightArrow": "adj2"}
ADJ_DEFAULT = {"roundRect": 16667, "chevron": 50000, "homePlate": 50000, "round2SameRect": 16667, "rightArrow": 50000, "leftArrow": 50000, "upArrow": 50000, "downArrow": 50000, "notchedRightArrow": 50000}
CSS_GEOMS = {"rect", "flowChartProcess", "roundRect", "round2SameRect", "ellipse", "chevron", "homePlate", "diamond", "flowChartDecision", "triangle", "parallelogram", "rightArrow", "leftArrow", "upArrow", "downArrow", "notchedRightArrow"}
PRSTCLR = {"black": "000000", "white": "FFFFFF", "red": "FF0000", "green": "008000", "blue": "0000FF", "yellow": "FFFF00", "gray": "808080", "grey": "808080"}
BODY_PH = {"body", "subTitle", "obj", "chart", "tbl", "clipArt", "dgm", "media", "pic"}


def a(t):
    return qn("a:" + t)


def local(el):
    return etree.QName(el).localname if isinstance(el.tag, str) else ""


def cm(emu):
    return round((emu or 0) / EMU, 3)


def num(v):
    s = f"{float(v):.3f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def put(parent, child, order):
    name = local(child)
    rank = order.index(name)
    for i, c in enumerate(parent):
        n = local(c)
        if (order.index(n) if n in order else 999) > rank:
            parent.insert(i, child)
            return child
    parent.append(child)
    return child


def drop(parent, *names):
    for c in list(parent):
        if local(c) in names:
            parent.remove(c)


def sub(tag, **attrs):
    el = etree.Element(a(tag), nsmap={"a": ANS})
    for k, v in attrs.items():
        el.set(k, str(v))
    return el


# ───────────── 색 · 테마 ─────────────
class Theme:
    def __init__(self, master):
        root = etree.fromstring(master.part.part_related_by(RT.THEME).blob)
        self.colors, self.fonts = {}, {}
        scheme = root.find(".//" + a("clrScheme"))
        for c in scheme if scheme is not None else []:
            v = c[0]
            self.colors[local(c)] = v.get("val") if local(v) == "srgbClr" else (v.get("lastClr") or "000000")
        for kind, tag in (("mj", "majorFont"), ("mn", "minorFont")):
            f = root.find(".//" + a(tag))
            if f is not None:
                self.fonts[kind + "-lt"] = f.find(a("latin")).get("typeface") if f.find(a("latin")) is not None else ""
                self.fonts[kind + "-ea"] = f.find(a("ea")).get("typeface") if f.find(a("ea")) is not None else ""
        cm_el = master._element.find(qn("p:clrMap"))
        self.map = dict(cm_el.attrib) if cm_el is not None else {"bg1": "lt1", "tx1": "dk1", "bg2": "lt2", "tx2": "dk2"}

    def scheme(self, name):
        return self.colors.get(self.map.get(name, name), "000000")

    def font(self, face):
        if face and face.startswith("+"):
            return self.fonts.get(face[1:], "")
        return face or ""


def _mods(hexv, el):
    r, g, b = (int(hexv[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    alpha = None
    for m in el:
        n, v = local(m), int(m.get("val", "0")) / 100000
        if n == "lumMod":
            l *= v
        elif n == "lumOff":
            l += v
        elif n == "tint":
            l = l * v + (1 - v)
        elif n == "shade":
            l *= v
        elif n == "alpha":
            alpha = v
    r, g, b = colorsys.hls_to_rgb(h, min(1, max(0, l)), s)
    out = "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))
    if alpha is not None and alpha < 1:
        out += "%02X" % round(alpha * 255)
    return out


def color_of(node, th):
    if node is None:
        return None
    for c in node:
        n = local(c)
        if n == "srgbClr":
            h = c.get("val")
        elif n == "schemeClr":
            if c.get("val") == "phClr":
                continue
            h = th.scheme(c.get("val"))
        elif n == "sysClr":
            h = c.get("lastClr") or ("FFFFFF" if c.get("val") == "window" else "000000")
        elif n == "prstClr":
            h = PRSTCLR.get(c.get("val"), "000000")
        else:
            continue
        return _mods(h.upper(), c)
    return None


def fill_css(pr, th):
    """'' = 지정 없음, None = 채움 없음."""
    if pr is None:
        return ""
    for c in pr:
        n = local(c)
        if n == "noFill":
            return None
        if n == "solidFill":
            return color_of(c, th)
        if n == "pattFill":
            return color_of(c.find(a("fgClr")), th)
        if n == "gradFill":
            stops = [(int(g.get("pos", "0")) / 1000, color_of(g, th)) for g in c.iter(a("gs"))]
            lin = c.find(a("lin"))
            ang = int(lin.get("ang", "0")) / 60000 + 90 if lin is not None else 90
            return f"linear-gradient({num(ang)}deg," + ",".join(f"{col} {num(p)}%" for p, col in sorted(stops)) + ")"
    return ""


def css_color(v):
    if not v:
        return None
    v = v.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{3})", v)
    if m:
        return "#" + "".join(ch * 2 for ch in m[1]).upper()
    if re.fullmatch(r"#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?", v):
        return v.upper()
    m = re.fullmatch(r"rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)(?:[\s,/]+([\d.]+))?\s*\)", v)
    if m:
        out = "#%02X%02X%02X" % (int(m[1]), int(m[2]), int(m[3]))
        if m[4] and float(m[4]) < 1:
            out += "%02X" % round(float(m[4]) * 255)
        return out
    low = v.lower()
    if low in ("transparent", "none"):
        return None
    if low in PRSTCLR:
        return "#" + PRSTCLR[low]
    return v


# ───────────── PPT → 요소 모델 ─────────────
class Reader:
    def __init__(self, prs, out_dir):
        self.prs, self.dir, self.exports, self.warn = prs, Path(out_dir), [], []
        self.assets = self.dir / "assets"
        self.themes = {}
        self.default = prs.part._element.find(qn("p:defaultTextStyle"))

    def theme(self, master):
        key = str(master.part.partname)
        if key not in self.themes:
            self.themes[key] = Theme(master)
        return self.themes[key]

    def walk(self, shapes, T, sink, master=False):
        for sh in shapes:
            el = sh._element
            nv = el.find(".//" + qn("p:cNvPr"))
            if nv is not None and nv.get("hidden") == "1":
                continue
            if local(el) == "grpSp":
                x = el.find(qn("p:grpSpPr")).find(a("xfrm"))
                if x is None or x.get("rot") or x.get("flipH") or x.get("flipV"):
                    sink.append((sh, T, True))
                    continue
                off, ext, co, ce = (x.find(a(t)) for t in ("off", "ext", "chOff", "chExt"))
                gx = int(ext.get("cx")) / (int(ce.get("cx")) or 1)
                gy = int(ext.get("cy")) / (int(ce.get("cy")) or 1)
                gtx, gty = int(off.get("x")) - int(co.get("x")) * gx, int(off.get("y")) - int(co.get("y")) * gy
                self.walk(sh.shapes, (T[0] * gx, T[1] * gy, T[0] * gtx + T[2], T[1] * gty + T[3]), sink, master)
            else:
                sink.append((sh, T, False))

    # 글자 상속: 도형 lstStyle → 레이아웃 → 마스터 → 기본
    def chains(self, sh, th, master):
        own, bodies, ph_el = [], [], None
        tx = getattr(sh._element, "txBody", None)
        if tx is not None:
            own.append(tx.find(a("lstStyle")))
            bodies.append(tx.find(a("bodyPr")))
        try:
            ph_el = sh._element.ph
        except AttributeError:
            pass
        if ph_el is not None:
            base = sh
            for _ in range(2):
                try:
                    base = base._base_placeholder
                except (AttributeError, KeyError):
                    base = None
                if base is None:
                    break
                t = getattr(base._element, "txBody", None)
                if t is not None:
                    own.append(t.find(a("lstStyle")))
                    bodies.append(t.find(a("bodyPr")))
            typ = ph_el.get("type", "obj")
            ts = master._element.find(qn("p:txStyles"))
            if ts is not None:
                own.append(ts.find(qn("p:titleStyle") if typ in ("title", "ctrTitle") else qn("p:bodyStyle") if typ in BODY_PH else qn("p:otherStyle")))
        return [c for c in own if c is not None], [b for b in bodies if b is not None]

    def para(self, p, chain, th, base_color, scale, n, counter):
        ppr = p.find(a("pPr"))
        lvl = int(ppr.get("lvl", "0")) if ppr is not None else 0
        name = f"lvl{lvl + 1}pPr"
        levels = [c.find(a(name)) for c in chain]
        levels = [x for x in levels if x is not None]
        dflt = self.default.find(a(name)) if self.default is not None else None
        pnodes = ([ppr] if ppr is not None else []) + levels + ([dflt] if dflt is not None else [])
        def pget(attr):
            for x in pnodes:
                if x.get(attr) is not None:
                    return x.get(attr)
            return None
        def pchild(tag):
            for x in pnodes:
                c = x.find(a(tag))
                if c is not None:
                    return c
            return None
        def rnodes(rpr):
            return ([rpr] if rpr is not None else []) + [x.find(a("defRPr")) for x in levels if x.find(a("defRPr")) is not None]
        dr = dflt.find(a("defRPr")) if dflt is not None else None
        def run_style(rpr):
            ns = rnodes(rpr)
            allns = ns + ([dr] if dr is not None else [])
            def rget(attr):
                for x in allns:
                    if x.get(attr) is not None:
                        return x.get(attr)
                return None
            col = None
            for x in ns:
                if x.find(a("solidFill")) is not None:
                    col = color_of(x.find(a("solidFill")), th)
                    break
            if col is None:
                col = base_color
            if col is None and dr is not None and dr.find(a("solidFill")) is not None:
                col = color_of(dr.find(a("solidFill")), th)
            face = ""
            for x in allns:
                for t in ("ea", "latin"):
                    c = x.find(a(t))
                    if c is not None and c.get("typeface"):
                        face = th.font(c.get("typeface"))
                        if face:
                            break
                if face:
                    break
            face = face or th.fonts.get("mn-ea") or th.fonts.get("mn-lt") or ""
            st = {"size": round(int(rget("sz") or 1800) / 100 * scale, 1), "color": col or "#" + th.scheme("tx1"), "font": face}
            if rget("b") in ("1", "true"):
                st["bold"] = True
            if rget("i") in ("1", "true"):
                st["italic"] = True
            if rget("u") not in (None, "none"):
                st["underline"] = True
            return st
        out = {"align": ALIGN.get(pget("algn") or "l"), "runs": []}
        if pget("marL"):
            out["ml"] = cm(int(pget("marL")))
        if pget("indent"):
            out["indent"] = cm(int(pget("indent")))
        for key, tag in (("before", "spcBef"), ("after", "spcAft")):
            c = pchild(tag)
            if c is not None and len(c):
                k = c[0]
                out[key] = f"{num(int(k.get('val')) / 100)}pt" if local(k) == "spcPts" else f"{num(int(k.get('val')) / 100000)}em"
        c = pchild("lnSpc")
        if c is not None and len(c):
            k = c[0]
            if local(k) == "spcPts":
                out["lh"] = f"{num(int(k.get('val')) / 100)}pt"
            elif int(k.get("val")) != 100000:
                out["lh"] = num(int(k.get("val")) / 100000 * 1.2)
        for child in p:
            n_ = local(child)
            if n_ == "r":
                t = child.find(a("t"))
                self._add(out["runs"], {"t": t.text or "" if t is not None else "", **run_style(child.find(a("rPr")))})
            elif n_ == "br":
                out["runs"].append({"br": True})
            elif n_ == "fld":
                t = child.find(a("t"))
                txt = str(n) if child.get("type") == "slidenum" else (t.text or "" if t is not None else "")
                out["runs"].append({"t": txt, "field": child.get("type") or "field", **run_style(child.find(a("rPr")))})
        if not out["runs"]:
            out["empty"] = run_style(p.find(a("endParaRPr")))["size"]
        for x in pnodes:
            bu = next((c for c in x if local(c) in ("buNone", "buChar", "buAutoNum")), None)
            if bu is None:
                continue
            if local(bu) == "buChar" and out["runs"]:
                out["bullet"] = bu.get("char", "•")
                counter[0] = 0
            elif local(bu) == "buAutoNum" and out["runs"]:
                counter[0] += 1
                typ = bu.get("type", "arabicPeriod")
                i = counter[0] + int(bu.get("startAt", "1")) - 1
                lab = chr(96 + i) if typ.startswith("alphaLc") else chr(64 + i) if typ.startswith("alphaUc") else str(i)
                out["bullet"], out["autonum"] = lab + (")" if "ParenR" in typ else "."), True
            else:
                counter[0] = 0
            break
        return out

    @staticmethod
    def _add(runs, r):
        if runs and "t" in runs[-1] and "field" not in runs[-1] and {k: v for k, v in runs[-1].items() if k != "t"} == {k: v for k, v in r.items() if k != "t"}:
            runs[-1]["t"] += r["t"]
        else:
            runs.append(r)

    def body(self, tx, chain, bodies, th, base_color, n):
        scale = 1.0
        for b in bodies[:1]:
            fa = b.find(a("normAutofit"))
            if fa is not None and fa.get("fontScale"):
                scale = int(fa.get("fontScale")) / 100000
        counter, paras = [0], []
        for p in tx.findall(a("p")):
            paras.append(self.para(p, chain, th, base_color, scale, n, counter))
        return [] if len(paras) == 1 and "empty" in paras[0] else paras

    def box(self, sh, T):
        l, t, w, h = sh.left, sh.top, sh.width, sh.height
        if l is None or w is None:
            return None
        return {"x": cm(T[0] * l + T[2]), "y": cm(T[1] * t + T[3]), "w": cm(T[0] * w), "h": cm(T[1] * h)}

    def body_attrs(self, bodies, out):
        def get(attr, dflt):
            for b in bodies:
                if b.get(attr) is not None:
                    return b.get(attr)
            return dflt
        out["pad"] = [cm(int(get("tIns", 45720))), cm(int(get("rIns", 91440))), cm(int(get("bIns", 45720))), cm(int(get("lIns", 91440)))]
        out["anchor"] = get("anchor", "t")
        if get("wrap", "square") == "none":
            out["nowrap"] = True
        if get("vert", "horz") in ("vert", "eaVert", "wordArtVert"):
            out["vert"] = True

    def line_of(self, pr, style, th):
        ln = pr.find(a("ln")) if pr is not None else None
        if ln is None:
            if style is not None and style.find(a("lnRef")) is not None and style.find(a("lnRef")).get("idx") != "0":
                return {"w": 0.75, "color": color_of(style.find(a("lnRef")), th), "dash": "solid"}
            return None
        col = fill_css(ln, th)
        if col is None:
            return None
        if col == "":
            if style is not None and style.find(a("lnRef")) is not None and style.find(a("lnRef")).get("idx") != "0":
                col = color_of(style.find(a("lnRef")), th)
            else:
                return None
        d = ln.find(a("prstDash"))
        dash = "solid" if d is None or d.get("val") == "solid" else "dotted" if "ot" in d.get("val") and "ash" not in d.get("val") else "dashed"
        return {"w": round(int(ln.get("w", 9525)) / 12700, 2), "color": col, "dash": dash}

    def picture(self, sh):
        try:
            img = sh.image
        except Exception:
            return None
        crop = (sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom)
        ext = img.ext.lower()
        if ext not in ("png", "jpg", "jpeg", "gif", "bmp"):
            return None
        name = hashlib.sha1(img.blob + repr(crop).encode()).hexdigest()[:12] + "." + ext
        path = self.assets / name
        if not path.exists():
            if any(crop):
                import io
                from PIL import Image
                im = Image.open(io.BytesIO(img.blob))
                W, H = im.size
                im.crop((round(crop[0] * W), round(crop[1] * H), round(W - crop[2] * W), round(H - crop[3] * H))).save(path)
            else:
                path.write_bytes(img.blob)
        return "assets/" + name

    def element(self, sh, T, force_frozen, n, th, master, seen, layer=False):
        el, tag = sh._element, local(sh._element)
        box = self.box(sh, T)
        if box is None:
            return None
        sid = str(sh.shape_id)
        while sid in seen:
            sid += "~"
        seen.add(sid)
        out = {"id": sid, **box}
        x = el.find(".//" + a("xfrm"))
        if x is not None and x.get("rot"):
            out["rot"] = round(int(x.get("rot")) / 60000, 2)
        flip = ("h" if x is not None and x.get("flipH") == "1" else "") + ("v" if x is not None and x.get("flipV") == "1" else "")
        pr = el.find(qn("p:spPr"))
        style = el.find(qn("p:style"))
        prst = pr.find(a("prstGeom")) if pr is not None else None
        geom = prst.get("prst") if prst is not None else None
        kind = "frozen" if force_frozen else None
        if kind is None:
            if tag == "pic":
                kind = "image"
            elif tag == "graphicFrame":
                kind = "table" if sh.has_table else "frozen"
            elif tag == "cxnSp":
                kind = "line" if geom in ("line", "straightConnector1") else "frozen"
            elif tag == "sp":
                if geom in ("line", "straightConnector1"):
                    kind = "line"
                elif prst is None and not getattr(sh, "is_placeholder", False):
                    kind = "frozen"
                else:
                    kind = "shape"
            else:
                kind = "frozen"
        if kind == "image":
            src = self.picture(sh)
            if src is None:
                kind = "frozen"
            else:
                out.update(kind="image", src=src)
                if flip:
                    out["flip"] = flip
                return out
        if kind == "frozen":
            if layer:
                return None
            src = f"assets/s{n}-{sid.rstrip('~')}.png"
            self.exports.append({"slide": n, "id": int(sid.rstrip("~")), "out": str(self.assets / Path(src).name)})
            out.update(kind="frozen", src=src, source=tag)
            return out
        if kind == "line":
            out.update(kind="line", flip=flip, stroke=self.line_of(pr, style, th) or {"w": 0.75, "color": "#000000", "dash": "solid"})
            ln = pr.find(a("ln"))
            if ln is not None:
                for k, t in (("head", "headEnd"), ("tail", "tailEnd")):
                    e = ln.find(a(t))
                    if e is not None and e.get("type", "none") != "none":
                        out[k] = True
            return out
        if kind == "table":
            return self.table(sh, out, th, master, n)
        # 도형·글상자
        chain, bodies = self.chains(sh, th, master)
        fr = style.find(a("fontRef")) if style is not None else None
        base = color_of(fr, th) if fr is not None else None
        tx = getattr(el, "txBody", None)
        paras = self.body(tx, chain, bodies, th, base, n) if tx is not None else []
        ph = getattr(sh, "is_placeholder", False)
        fill = fill_css(pr, th)
        if fill == "" and style is not None and style.find(a("fillRef")) is not None and style.find(a("fillRef")).get("idx") != "0":
            fill = color_of(style.find(a("fillRef")), th)
        line = self.line_of(pr, style, th)
        if ph and not paras and not fill and not line:
            return None
        g = geom or "rect"
        if g not in CSS_GEOMS and not paras:
            if layer:
                return None
            src = f"assets/s{n}-{sid.rstrip('~')}.png"
            self.exports.append({"slide": n, "id": int(sid.rstrip("~")), "out": str(self.assets / Path(src).name)})
            out.update(kind="frozen", src=src, source=g)
            return out
        out.update(kind="shape", geom=g, fill=fill or None, line=line, paras=paras)
        self.body_attrs(bodies, out)
        if g in ADJ_NAME:
            v = None
            av = prst.find(a("avLst")) if prst is not None else None
            for gd in av if av is not None else []:
                if gd.get("name") == ADJ_NAME[g]:
                    v = int(gd.get("fmla").split()[-1])
            out["adj"] = v if v is not None else ADJ_DEFAULT[g]
        if flip and not paras:
            out["flip"] = flip
        return out

    def cell_border(self, tcpr, th):
        out = {}
        for side, t in (("left", "lnL"), ("right", "lnR"), ("top", "lnT"), ("bottom", "lnB")):
            ln = tcpr.find(a(t)) if tcpr is not None else None
            if ln is None:
                continue
            col = fill_css(ln, th)
            if col is None or col == "":
                out[side] = None
                continue
            out[side] = {"w": round(int(ln.get("w", 12700)) / 12700, 2), "color": col, "dash": "solid"}
        return out

    def table(self, sh, out, th, master, n):
        tbl = sh.table._tbl
        out.update(kind="table", cols=[cm(int(c.get("w"))) for c in tbl.find(a("tblGrid"))], rows=[])
        for tr in tbl.findall(a("tr")):
            row = {"h": cm(int(tr.get("h"))), "cells": []}
            for tc in tr.findall(a("tc")):
                if tc.get("hMerge") == "1" or tc.get("vMerge") == "1":
                    continue
                tcpr = tc.find(a("tcPr"))
                cell = {"paras": self.body(tc.find(a("txBody")), [], [], th, None, n), "fill": fill_css(tcpr, th) or None,
                        "pad": [cm(int((tcpr.get("marT") if tcpr is not None and tcpr.get("marT") else 45720))), cm(int((tcpr.get("marR") if tcpr is not None and tcpr.get("marR") else 91440))),
                                cm(int((tcpr.get("marB") if tcpr is not None and tcpr.get("marB") else 45720))), cm(int((tcpr.get("marL") if tcpr is not None and tcpr.get("marL") else 91440)))],
                        "anchor": (tcpr.get("anchor") if tcpr is not None and tcpr.get("anchor") else "t"), "border": self.cell_border(tcpr, th)}
                if tc.get("gridSpan"):
                    cell["colspan"] = int(tc.get("gridSpan"))
                if tc.get("rowSpan"):
                    cell["rowspan"] = int(tc.get("rowSpan"))
                row["cells"].append(cell)
            out["rows"].append(row)
        return out

    def background(self, part_el, part, th):
        bg = part_el.find(qn("p:cSld")).find(qn("p:bg"))
        if bg is None:
            return ""
        pr = bg.find(qn("p:bgPr"))
        if pr is not None:
            blip = pr.find(".//" + a("blip"))
            if blip is not None:
                try:
                    p = part.related_part(blip.get(qn("r:embed")))
                    name = hashlib.sha1(p.blob).hexdigest()[:12] + "." + str(p.partname).rsplit(".", 1)[-1]
                    (self.assets / name).write_bytes(p.blob)
                    return f"url(assets/{name}) center/100% 100%"
                except Exception:
                    return ""
            f = fill_css(pr, th)
            return f or ""
        ref = bg.find(qn("p:bgRef"))
        return color_of(ref, th) or "" if ref is not None else ""

    def slide(self, slide, n):
        layout, master = slide.slide_layout, slide.slide_layout.slide_master
        th = self.theme(master)
        bg = self.background(slide._element, slide.part, th) or self.background(layout._element, layout.part, th) or self.background(master._element, master.part, th) or "#FFFFFF"
        layer, sink = [], []
        parts = []
        if slide._element.get("showMasterSp") != "0":
            if layout._element.get("showMasterSp") != "0":
                parts.append(master)
            parts.append(layout)
        for part in parts:
            items = []
            self.walk(part.shapes, (1, 1, 0, 0), items, True)
            seen = set()
            for sh, T, ff in items:
                if getattr(sh, "is_placeholder", False):
                    continue
                e = self.element(sh, T, ff, n, th, master, seen, layer=True)
                if e:
                    layer.append(e)
        self.walk(slide.shapes, (1, 1, 0, 0), sink)
        seen, els = set(), []
        for sh, T, ff in sink:
            e = self.element(sh, T, ff, n, th, master, seen)
            if e:
                els.append(e)
        return {"n": n, "sid": str(slide.slide_id), "bg": bg, "hidden": slide._element.get("show") == "0", "layer": layer, "els": els}


# ───────────── 모델 → HTML ─────────────
def esc(t):
    return _html.escape(t, quote=False)


def style(d):
    return ";".join(f"{k}:{v}" for k, v in d.items() if v not in (None, ""))


def run_css(r):
    return style({"font-size": f"{num(r['size'])}pt", "color": r.get("color"), "font-family": f"'{r['font']}'" if r.get("font") else None,
                  "font-weight": "700" if r.get("bold") else None, "font-style": "italic" if r.get("italic") else None, "text-decoration": "underline" if r.get("underline") else None})


def paras_html(paras):
    out = []
    for p in paras:
        st = style({"text-align": p.get("align") if p.get("align") != "left" else None, "margin-left": f"{num(p['ml'])}cm" if p.get("ml") else None,
                    "text-indent": f"{num(p['indent'])}cm" if p.get("indent") else None, "line-height": p.get("lh"), "margin-top": p.get("before"), "margin-bottom": p.get("after"),
                    "font-size": f"{num(p['empty'])}pt" if "empty" in p else None})
        attrs = (f' data-bullet="{_html.escape(p["bullet"])}"' if p.get("bullet") else "") + (' data-autonum="1"' if p.get("autonum") else "") + (f' style="{_html.escape(st)}"' if st else "")
        body = ""
        for r in p["runs"]:
            if r.get("br"):
                body += "<br>"
            else:
                fld = f' data-field="{r["field"]}"' if r.get("field") else ""
                body += f'<span{fld} style="{_html.escape(run_css(r))}">{esc(r["t"])}</span>'
        out.append(f"<p{attrs}>{body}</p>")
    return "".join(out)


def pad_css(p):
    return " ".join(f"{num(v)}cm" for v in p)


def border_css(ln):
    return f"{num(ln['w'])}pt {ln.get('dash', 'solid')} {ln['color']}"


def geom_a(e):
    if e.get("adj") is None:
        return None
    base = min(e["w"], e["h"])
    return f"{num(base * e['adj'] / 100000)}cm"


def box_css(e):
    tf = []
    if e.get("rot"):
        tf.append(f"rotate({num(e['rot'])}deg)")
    if "h" in (e.get("flip") or "") and e["kind"] != "line":
        tf.append("scaleX(-1)")
    if "v" in (e.get("flip") or "") and e["kind"] != "line":
        tf.append("scaleY(-1)")
    return {"left": f"{num(e['x'])}cm", "top": f"{num(e['y'])}cm", "width": f"{num(e['w'])}cm", "height": f"{num(e['h'])}cm", "transform": " ".join(tf) or None}


def element_html(e, locked=False):
    idattr = "" if locked else f' data-id="{e["id"]}"'
    k = e["kind"]
    if k in ("image", "frozen"):
        src = f' data-source="{e["source"]}"' if e.get("source") else ""
        return f'<img class="el" alt=""{idattr} data-kind="{k}"{src} src="{e["src"]}" style="{style(box_css(e))}">'
    if k == "line":
        s = e["stroke"]
        x1, x2 = ("100%", "0") if "h" in e["flip"] else ("0", "100%")
        y1, y2 = ("100%", "0") if "v" in e["flip"] else ("0", "100%")
        extra = (' stroke-dasharray="6 4"' if s["dash"] == "dashed" else ' stroke-dasharray="2 3"' if s["dash"] == "dotted" else "")
        extra += ' marker-start="url(#ah)" data-head="1"' if e.get("head") else ""
        extra += ' marker-end="url(#ah)" data-tail="1"' if e.get("tail") else ""
        return (f'<div class="el line"{idattr} data-kind="line" data-flip="{e["flip"]}" style="{style(box_css(e))}"><svg><line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{s["color"]}" stroke-width="{num(s["w"])}pt"{extra}/></svg></div>')
    if k == "table":
        cols = "".join(f'<col style="width:{num(c)}cm">' for c in e["cols"])
        rows = ""
        for r in e["rows"]:
            cells = ""
            for c in r["cells"]:
                st = {"padding": pad_css(c["pad"]), "vertical-align": VALIGN.get(c["anchor"], "top"), "background": c.get("fill")}
                for side, ln in c["border"].items():
                    st[f"border-{side}"] = border_css(ln) if ln else "none"
                span = (f' colspan="{c["colspan"]}"' if c.get("colspan") else "") + (f' rowspan="{c["rowspan"]}"' if c.get("rowspan") else "")
                cells += f'<td{span} style="{_html.escape(style(st))}">{paras_html(c["paras"])}</td>'
            rows += f'\n<tr style="height:{num(r["h"])}cm">{cells}</tr>'
        return f'<table class="el"{idattr} data-kind="table" style="{style(box_css(e))}"><colgroup>{cols}</colgroup>{rows}\n</table>'
    st = box_css(e)
    # 글자 없는 도형에는 안쪽 여백을 쓰지 않는다 (얇은 선 모양 사각형이 여백만큼 두꺼워진다)
    st.update({"background": e.get("fill"), "border": border_css(e["line"]) if e.get("line") else None, "padding": pad_css(e["pad"]) if e["paras"] else None,
               "justify-content": ANCHOR.get(e["anchor"], "flex-start"), "white-space": "nowrap" if e.get("nowrap") else None,
               "writing-mode": "vertical-rl" if e.get("vert") else None, "--a": geom_a(e)})
    adj = f' data-adj="{e["adj"]}"' if e.get("adj") is not None else ""
    return f'<div class="el"{idattr} data-kind="shape" data-geom="{e["geom"]}"{adj} style="{_html.escape(style(st))}">{paras_html(e["paras"])}</div>'


CSS = """:root{--w:%(w)scm;--h:%(h)scm;--zoom:1}
*{box-sizing:border-box}html,body{margin:0;background:#E9EBEF}
body{padding:12px 0 40px;font-family:'Malgun Gothic',sans-serif}
.pg{width:calc(var(--w)*var(--zoom));margin:18px auto 6px;font:600 13px/1 sans-serif;color:#5A6270}
.slide{position:relative;width:var(--w);height:var(--h);margin:0 auto;overflow:hidden;background:#fff;box-shadow:0 1px 6px rgba(0,0,0,.25);zoom:var(--zoom)}
.slide[data-hidden]{opacity:.55}
.layer{position:absolute;inset:0;pointer-events:none}
.el{position:absolute;display:flex;flex-direction:column;margin:0}
img.el{display:block;object-fit:fill}
.el.line svg{position:absolute;left:0;top:0;width:100%%;height:100%%;min-width:1px;min-height:1px;overflow:visible}
table.el{display:table;table-layout:fixed;border-collapse:collapse;border-spacing:0}
table.el td{overflow:hidden}
p{margin:0;white-space:pre-wrap;line-height:1.2;word-break:keep-all;overflow-wrap:break-word}
p:empty::before{content:"\\200b"}
p[data-bullet]::before{content:attr(data-bullet);margin-right:.45em}
[data-geom=roundRect]{border-radius:var(--a)}
[data-geom=round2SameRect]{border-radius:var(--a) var(--a) 0 0}
[data-geom=ellipse]{border-radius:50%%}
[data-geom=chevron]{clip-path:polygon(0 0,calc(100%% - var(--a)) 0,100%% 50%%,calc(100%% - var(--a)) 100%%,0 100%%,var(--a) 50%%)}
[data-geom=homePlate]{clip-path:polygon(0 0,calc(100%% - var(--a)) 0,100%% 50%%,calc(100%% - var(--a)) 100%%,0 100%%)}
[data-geom=diamond],[data-geom=flowChartDecision]{clip-path:polygon(50%% 0,100%% 50%%,50%% 100%%,0 50%%)}
[data-geom=triangle]{clip-path:polygon(50%% 0,100%% 100%%,0 100%%)}
[data-geom=parallelogram]{clip-path:polygon(25%% 0,100%% 0,75%% 100%%,0 100%%)}
[data-geom=rightArrow]{clip-path:polygon(0 25%%,calc(100%% - var(--a)) 25%%,calc(100%% - var(--a)) 0,100%% 50%%,calc(100%% - var(--a)) 100%%,calc(100%% - var(--a)) 75%%,0 75%%)}
[data-geom=notchedRightArrow]{clip-path:polygon(0 25%%,calc(100%% - var(--a)) 25%%,calc(100%% - var(--a)) 0,100%% 50%%,calc(100%% - var(--a)) 100%%,calc(100%% - var(--a)) 75%%,0 75%%,12%% 50%%)}
[data-geom=leftArrow]{clip-path:polygon(100%% 25%%,var(--a) 25%%,var(--a) 0,0 50%%,var(--a) 100%%,var(--a) 75%%,100%% 75%%)}
[data-geom=downArrow]{clip-path:polygon(25%% 0,75%% 0,75%% calc(100%% - var(--a)),100%% calc(100%% - var(--a)),50%% 100%%,0 calc(100%% - var(--a)),25%% calc(100%% - var(--a)))}
[data-geom=upArrow]{clip-path:polygon(50%% 0,100%% var(--a),75%% var(--a),75%% 100%%,25%% 100%%,25%% var(--a),0 var(--a))}
"""
JS = """(function(){var r=document.documentElement;var w=parseFloat(getComputedStyle(r).getPropertyValue('--w'))*96/2.54;
function fit(){r.style.setProperty('--zoom',Math.min(1.5,(window.innerWidth-40)/w))}
window.addEventListener('resize',fit);fit();
document.querySelectorAll('.slide').forEach(function(s){var d=document.createElement('div');d.className='pg';d.textContent=s.getAttribute('data-n')+'쪽'+(s.hasAttribute('data-hidden')?' (숨김)':'');s.parentNode.insertBefore(d,s)});
})();
"""
DEFS = '<svg width="0" height="0" style="position:absolute"><defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs></svg>'


WEIGHT_WORDS = ("Thin", "ExtraLight", "UltraLight", "Light", "Regular", "Medium", "SemiBold", "DemiBold", "Bold", "ExtraBold", "UltraBold", "Black", "Heavy")


def font_faces(slides):
    """'Pretendard Light' 처럼 굵기가 이름에 붙은 글꼴은 브라우저가 이름으로 못 찾는다. 설치된 글꼴 파일을 직접 가리킨다."""
    names = set()
    def scan(paras):
        for p in paras:
            for r in p["runs"]:
                if r.get("font"):
                    names.add(r["font"])
    for s in slides:
        for e in s["els"] + s["layer"]:
            scan(e.get("paras") or [])
            for row in e.get("rows") or []:
                for c in row["cells"]:
                    scan(c["paras"])
    out = []
    for n in sorted(names):
        parts = n.rsplit(" ", 1)
        if len(parts) == 2 and parts[1] in WEIGHT_WORDS:
            out.append(f"@font-face{{font-family:'{n}';src:local('{n}'),local('{parts[0]}-{parts[1]}')}}\n")
    return "".join(out)


def slides_html(slides, title):
    out = [f'<!doctype html>\n<html lang="ko"><head><meta charset="utf-8"><title>{esc(title)}</title><link rel="stylesheet" href="deck.css"></head>\n<body>\n{DEFS}\n']
    for s in slides:
        hid = " data-hidden" if s["hidden"] else ""
        out.append(f'<!-- ===== {s["n"]}쪽 ===== -->\n<section class="slide" data-n="{s["n"]}" data-sid="{s["sid"]}"{hid} style="background:{_html.escape(s["bg"], quote=True)}">\n')
        out.append('<div class="layer">' + "".join(element_html(e, True) for e in s["layer"]) + "</div>\n")
        out.extend(element_html(e) + "\n" for e in s["els"])
        out.append("</section>\n")
    out.append('<script src="deck.js"></script>\n</body></html>\n')
    return "".join(out)


# ───────────── HTML → 요소 모델 ─────────────
def css_map(el):
    out = {}
    for part in (el.get("style") or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.strip()
    return out


def length(v, unit="cm"):
    if v is None:
        return None
    m = re.fullmatch(r"(-?[\d.]+)\s*(cm|mm|in|pt|px)?", v.strip())
    if not m:
        return None
    pt = float(m[1]) * {"cm": 72 / 2.54, "mm": 72 / 25.4, "in": 72, "pt": 1, "px": 0.75, None: 72 / 2.54 if unit == "cm" else 1}[m[2]]
    return round(pt * 2.54 / 72, 3) if unit == "cm" else round(pt, 2)


def parse_border(v):
    if v is None or v.strip().lower() in ("none", "0"):
        return None
    w, dash, col = 0.75, "solid", None
    for tok in re.findall(r"rgba?\([^)]*\)|\S+", v):
        if tok in ("solid", "dashed", "dotted"):
            dash = tok
        elif tok == "none":
            return None
        elif re.fullmatch(r"[\d.]+(pt|px|cm|mm)?", tok):
            w = length(tok, "pt")
        else:
            col = css_color(tok)
    return {"w": w, "color": col or "#000000", "dash": dash}


def parse_pad(v):
    if not v:
        return None
    vals = [length(x) or 0 for x in v.split()]
    if len(vals) == 1:
        vals *= 4
    elif len(vals) == 2:
        vals = [vals[0], vals[1], vals[0], vals[1]]
    elif len(vals) == 3:
        vals = [vals[0], vals[1], vals[2], vals[1]]
    return vals


def parse_runs(node, inherited, runs):
    def text(t, st):
        t = re.sub(r"\s*\n\s*", " ", t or "")
        if t:
            runs.append({"t": t, **st})
    text(node.text, inherited)
    for ch in node:
        if not isinstance(ch.tag, str):
            text(ch.tail, inherited)
            continue
        tag = ch.tag.lower()
        if tag == "br":
            runs.append({"br": True})
        else:
            st = {k: v for k, v in inherited.items() if k != "bare"}
            css = css_map(ch)
            if "font-size" in css:
                st["size"] = length(css["font-size"], "pt")
            if "color" in css:
                st["color"] = css_color(css["color"])
            if "font-family" in css:
                st["font"] = css["font-family"].split(",")[0].strip().strip("'\"")
            if css.get("font-weight") in ("700", "bold", "800", "900") or tag in ("b", "strong"):
                st["bold"] = True
            elif css.get("font-weight") in ("400", "normal"):
                st.pop("bold", None)
            if css.get("font-style") == "italic" or tag in ("i", "em"):
                st["italic"] = True
            if "underline" in css.get("text-decoration", "") or tag == "u":
                st["underline"] = True
            if not css and tag == "span" and inherited.get("bare"):
                st["bare"] = True
            if ch.get("data-field"):
                st["field"] = ch.get("data-field")
                runs.append({"t": "#", **st})
            else:
                parse_runs(ch, st, runs)
        text(ch.tail, inherited)


def parse_paras(node):
    paras = []
    ps = [c for c in node if isinstance(c.tag, str) and c.tag.lower() == "p"]
    for p in ps:
        css = css_map(p)
        runs = []
        parse_runs(p, {"bare": True}, runs)
        d = {"align": css.get("text-align", "left"), "ml": length(css.get("margin-left")), "indent": length(css.get("text-indent")),
             "lh": css.get("line-height"), "before": css.get("margin-top"), "after": css.get("margin-bottom"), "bullet": "auto" if p.get("data-autonum") else p.get("data-bullet"), "runs": runs}
        paras.append(d)
    return paras


def parse_element(el):
    css = css_map(el)
    k = el.get("data-kind") or ("image" if el.tag.lower() == "img" else "table" if el.tag.lower() == "table" else "shape")
    tf = css.get("transform", "")
    m = re.search(r"rotate\((-?[\d.]+)deg\)", tf)
    e = {"id": el.get("data-id"), "kind": k, "x": length(css.get("left")), "y": length(css.get("top")), "w": length(css.get("width")), "h": length(css.get("height")), "rot": float(m[1]) if m else 0}
    if k in ("image", "frozen"):
        e["src"] = el.get("src")
    elif k == "line":
        ln = el.find(".//line")
        if ln is None:
            ln = next((x for x in el.iter() if isinstance(x.tag, str) and x.tag.lower().endswith("line")), None)
        e["flip"] = el.get("data-flip", "")
        e["stroke"] = {"w": length(ln.get("stroke-width"), "pt") or 0.75, "color": css_color(ln.get("stroke")) or "#000000", "dash": ("dotted" if (ln.get("stroke-dasharray") or "").startswith("2") else "dashed") if ln.get("stroke-dasharray") else "solid"}
        e["head"], e["tail"] = bool(ln.get("data-head")), bool(ln.get("data-tail"))
    elif k == "table":
        e["cols"] = [length(css_map(c).get("width")) for c in el.iter("col")]
        e["rows"] = []
        for tr in el.iter("tr"):
            row = {"h": length(css_map(tr).get("height")), "cells": []}
            for td in tr:
                if not isinstance(td.tag, str) or td.tag.lower() not in ("td", "th"):
                    continue
                c = css_map(td)
                row["cells"].append({"paras": parse_paras(td), "fill": css_color(c.get("background")), "pad": parse_pad(c.get("padding")), "anchor": VALIGN_BACK.get(c.get("vertical-align", "top"), "t"),
                                     "border": {s: parse_border(c[f"border-{s}"]) for s in ("left", "right", "top", "bottom") if f"border-{s}" in c},
                                     "colspan": int(td.get("colspan", 1)), "rowspan": int(td.get("rowspan", 1))})
            e["rows"].append(row)
    else:
        e.update(geom=el.get("data-geom", "rect"), adj=int(el.get("data-adj")) if el.get("data-adj") else None, fill=css_color(css.get("background")), line=parse_border(css.get("border")),
                 pad=parse_pad(css.get("padding")), anchor=ANCHOR_BACK.get(css.get("justify-content", "flex-start"), "t"), nowrap=css.get("white-space") == "nowrap", paras=parse_paras(el))
    return e


def parse_html(text):
    root = lxml_html.fromstring(text)
    out = []
    for sec in root.iter("section"):
        if "slide" not in (sec.get("class") or "").split():
            continue
        css = css_map(sec)
        els = []
        for ch in sec:
            if isinstance(ch.tag, str) and "el" in (ch.get("class") or "").split():
                els.append(parse_element(ch))
        out.append({"sid": sec.get("data-sid"), "bg": css_color(css.get("background")), "els": els})
    return out


# ───────────── 변경분을 PPT 에 쓰기 ─────────────
def rgb_el(hexv):
    h = hexv.lstrip("#")
    c = sub("srgbClr", val=h[:6])
    if len(h) == 8:
        c.append(sub("alpha", val=round(int(h[6:], 16) / 255 * 100000)))
    return c


def is_hex(v):
    return bool(v) and bool(re.fullmatch(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?", v))


def set_fill(parent, val, order):
    drop(parent, *FILLS)
    if val is None:
        put(parent, sub("noFill"), order)
    else:
        f = sub("solidFill")
        f.append(rgb_el(val))
        put(parent, f, order)


def write_ln(ln, val):
    if val is None:
        drop(ln, *FILLS, "prstDash")
        put(ln, sub("noFill"), LN_ORDER)
        return
    ln.set("w", str(round(val["w"] * 12700)))
    set_fill(ln, val["color"], LN_ORDER)
    drop(ln, "prstDash")
    if val.get("dash", "solid") != "solid":
        put(ln, sub("prstDash", val=DASH_BACK[val["dash"]]), LN_ORDER)


def get_ln(pr):
    ln = pr.find(a("ln"))
    return ln if ln is not None else put(pr, sub("ln"), SPPR_ORDER)


def write_rpr(rpr, ref, new):
    if new.get("bare"):
        return
    for k in ("size", "color", "font", "bold", "italic", "underline"):
        v, o = new.get(k), ref.get(k)
        if v == o or (k in ("size", "color", "font") and v is None):
            continue
        if k == "size":
            rpr.set("sz", str(round(v * 100)))
        elif k == "bold":
            rpr.set("b", "1" if v else "0")
        elif k == "italic":
            rpr.set("i", "1" if v else "0")
        elif k == "underline":
            rpr.set("u", "sng" if v else "none")
        elif k == "color" and is_hex(v):
            set_fill(rpr, v, RPR_ORDER)
        elif k == "font":
            drop(rpr, "latin", "ea")
            put(rpr, sub("latin", typeface=v), RPR_ORDER)
            put(rpr, sub("ea", typeface=v), RPR_ORDER)


def write_ppr(p, old, new):
    ppr = p.find(a("pPr"))
    if ppr is None:
        ppr = sub("pPr")
        p.insert(0, ppr)
    if old.get("align") != new.get("align"):
        ppr.set("algn", ALIGN_BACK.get(new.get("align"), "l"))
    for key, attr in (("ml", "marL"), ("indent", "indent")):
        if old.get(key) != new.get(key):
            ppr.set(attr, str(round((new.get(key) or 0) * EMU)))
    if old.get("lh") != new.get("lh"):
        drop(ppr, "lnSpc")
        v = new.get("lh")
        if v:
            e = sub("lnSpc")
            if v.endswith("pt"):
                e.append(sub("spcPts", val=round(float(v[:-2]) * 100)))
            else:
                e.append(sub("spcPct", val=round(float(v) / 1.2 * 100000)))
            put(ppr, e, PPR_ORDER)
    for key, tag in (("before", "spcBef"), ("after", "spcAft")):
        if old.get(key) != new.get(key):
            drop(ppr, tag)
            v = new.get(key)
            if v:
                e = sub(tag)
                if v.endswith("em"):
                    e.append(sub("spcPct", val=round(float(v[:-2]) * 100000)))
                else:
                    e.append(sub("spcPts", val=round((length(v, "pt") or 0) * 100)))
                put(ppr, e, PPR_ORDER)
    if old.get("bullet") != new.get("bullet") and new.get("bullet") != "auto":
        drop(ppr, "buNone", "buChar", "buAutoNum")
        put(ppr, sub("buChar", char=new["bullet"]) if new.get("bullet") else sub("buNone"), PPR_ORDER)


def write_para(p, old, new):
    write_ppr(p, old, new)
    tpl = next((r.find(a("rPr")) for r in p.findall(a("r")) if r.find(a("rPr")) is not None), None)
    if tpl is None:
        tpl = p.find(a("endParaRPr"))
    tpl = copy.deepcopy(tpl) if tpl is not None else sub("rPr", lang="ko-KR")
    tpl.tag = a("rPr")
    ref = next((r for r in old.get("runs", []) if "t" in r), {})
    flds = [copy.deepcopy(f) for f in p.findall(a("fld"))]
    drop(p, "r", "br", "fld")
    end = p.find(a("endParaRPr"))
    pos = (1 if p.find(a("pPr")) is not None else 0)
    for run in new["runs"]:
        if run.get("br"):
            el = sub("br")
            el.append(copy.deepcopy(tpl))
        elif run.get("field") and flds:
            el = flds.pop(0)
        else:
            el = sub("r")
            rp = copy.deepcopy(tpl)
            write_rpr(rp, ref, run)
            el.append(rp)
            t = sub("t")
            t.text = run["t"]
            el.append(t)
        p.insert(pos, el)
        pos += 1
    if end is not None and p[-1] is not end:
        p.remove(end)
        p.append(end)


def write_text(tx, old, new):
    ps = tx.findall(a("p"))
    prev_old = None
    for i, np_ in enumerate(new):
        o = old[i] if i < len(old) else None
        if o == np_:
            prev_old = o
            continue
        if i < len(ps):
            write_para(ps[i], o or {"runs": []}, np_)
        else:
            p = copy.deepcopy(ps[-1])
            ps[-1].addnext(p)
            ps.append(p)
            write_para(p, prev_old or {"runs": []}, np_)
        prev_old = o or np_
    for p in ps[len(new) if new else 1:]:
        tx.remove(p)
    if not new and ps:
        write_para(ps[0], old[0] if old else {"runs": []}, {"runs": [], "align": old[0].get("align") if old else None})


class Writer:
    def __init__(self, prs, base_dir):
        self.prs, self.dir, self.warn, self.changed = prs, Path(base_dir), [], 0

    def image_path(self, src):
        p = (self.dir / src).resolve()
        if self.dir.resolve() not in p.parents or not p.is_file():
            raise FileNotFoundError(src)
        return p

    def box(self, sh, old, new, T):
        x, y = (new["x"] if new["x"] is not None else old["x"]), (new["y"] if new["y"] is not None else old["y"])
        w, h = (new["w"] if new["w"] is not None else old["w"]), (new["h"] if new["h"] is not None else old["h"])
        if (x, y, w, h) != (old["x"], old["y"], old["w"], old["h"]):
            if new["kind"] == "table":
                sh.left, sh.top = round((x * EMU - T[2]) / T[0]), round((y * EMU - T[3]) / T[1])
            else:
                L, Tp, W, H = round((x * EMU - T[2]) / T[0]), round((y * EMU - T[3]) / T[1]), round(w * EMU / T[0]), round(h * EMU / T[1])
                sh.left, sh.top, sh.width, sh.height = L, Tp, W, H
            self.changed += 1
        if new.get("rot") != old.get("rot"):
            x_el = sh._element.find(".//" + a("xfrm"))
            if x_el is not None:
                x_el.set("rot", str(round((new.get("rot") or 0) * 60000)))
                self.changed += 1

    def shape(self, sh, old, new, T):
        el = sh._element
        pr = el.find(qn("p:spPr"))
        if old["fill"] != new["fill"]:
            if new["fill"] is None or is_hex(new["fill"]):
                set_fill(pr, new["fill"], SPPR_ORDER)
                self.changed += 1
            else:
                self.warn.append(f"요소 {new['id']}: 채움색 '{new['fill']}' 은 단색(#RRGGBB)만 PPT 로 옮길 수 있어 건너뜀")
        if old["line"] != new["line"]:
            write_ln(get_ln(pr), new["line"])
            self.changed += 1
        prst = pr.find(a("prstGeom"))
        if prst is not None and (old["geom"] != new["geom"] or old["adj"] != new["adj"]):
            prst.set("prst", new["geom"])
            av = prst.find(a("avLst"))
            if av is None:
                av = etree.SubElement(prst, a("avLst"))
            for c in list(av):
                av.remove(c)
            if new["adj"] is not None and new["geom"] in ADJ_NAME:
                gd = etree.SubElement(av, a("gd"))
                gd.set("name", ADJ_NAME[new["geom"]])
                gd.set("fmla", f"val {new['adj']}")
            self.changed += 1
        if old["paras"] != new["paras"] or old["pad"] != new["pad"] or old["anchor"] != new["anchor"] or old["nowrap"] != new["nowrap"]:
            tx = sh.text_frame._txBody
            bp = tx.find(a("bodyPr"))
            if old["pad"] != new["pad"] and new["pad"]:
                for attr, v in zip(("tIns", "rIns", "bIns", "lIns"), new["pad"]):
                    bp.set(attr, str(round(v * EMU)))
            if old["anchor"] != new["anchor"]:
                bp.set("anchor", new["anchor"])
            if old["nowrap"] != new["nowrap"]:
                bp.set("wrap", "none" if new["nowrap"] else "square")
            if old["paras"] != new["paras"]:
                write_text(tx, old["paras"], new["paras"])
            self.changed += 1

    def line(self, sh, old, new):
        el = sh._element
        pr = el.find(qn("p:spPr"))
        if old["stroke"] != new["stroke"]:
            write_ln(get_ln(pr), new["stroke"])
            self.changed += 1
        if old["flip"] != new["flip"]:
            x = el.find(".//" + a("xfrm"))
            for attr, ch in (("flipH", "h"), ("flipV", "v")):
                if ch in new["flip"]:
                    x.set(attr, "1")
                elif attr in x.attrib:
                    del x.attrib[attr]
            self.changed += 1
        if (old["head"], old["tail"]) != (new["head"], new["tail"]):
            ln = get_ln(pr)
            drop(ln, "headEnd", "tailEnd")
            if new["head"]:
                put(ln, sub("headEnd", type="triangle"), LN_ORDER)
            if new["tail"]:
                put(ln, sub("tailEnd", type="triangle"), LN_ORDER)
            self.changed += 1

    def write_cell(self, tc, old, new):
        tx = tc.find(a("txBody"))
        if old is None or old["paras"] != new["paras"]:
            write_text(tx, old["paras"] if old else [], new["paras"])
            self.changed += 1
        tcpr = tc.find(a("tcPr"))
        if tcpr is None:
            tcpr = etree.SubElement(tc, a("tcPr"))
        if (old["fill"] if old else None) != new["fill"]:
            if new["fill"] is None or is_hex(new["fill"]):
                set_fill(tcpr, new["fill"], TCPR_ORDER)
                self.changed += 1
        if (old["anchor"] if old else "t") != new["anchor"]:
            tcpr.set("anchor", new["anchor"])
            self.changed += 1
        if (old["pad"] if old else None) != new["pad"] and new["pad"]:
            for attr, v in zip(("marT", "marR", "marB", "marL"), new["pad"]):
                tcpr.set(attr, str(round(v * EMU)))
            self.changed += 1
        for side, tag in (("left", "lnL"), ("right", "lnR"), ("top", "lnT"), ("bottom", "lnB")):
            ob, nb = (old["border"] if old else {}).get(side, "-"), new["border"].get(side, "-")
            if ob == nb or nb == "-":
                continue
            drop(tcpr, tag)
            ln = sub(tag)
            write_ln(ln, nb)
            put(tcpr, ln, TCPR_ORDER)
            self.changed += 1

    def table(self, sh, old, new):
        tbl = sh.table._tbl
        grid = tbl.find(a("tblGrid"))
        trs = tbl.findall(a("tr"))
        while len(new["cols"]) > len(grid):
            grid.append(copy.deepcopy(grid[-1]))
            for tr in trs:
                tr.findall(a("tc"))[-1].addnext(copy.deepcopy(tr.findall(a("tc"))[-1]))
        while len(new["cols"]) < len(grid):
            grid.remove(grid[-1])
            for tr in trs:
                tr.remove(tr.findall(a("tc"))[-1])
        for g, w in zip(grid, new["cols"]):
            if w is not None and round(int(g.get("w")) / EMU, 3) != w:
                g.set("w", str(round(w * EMU)))
                self.changed += 1
        trs = tbl.findall(a("tr"))
        while len(new["rows"]) > len(trs):
            t = copy.deepcopy(trs[-1])
            trs[-1].addnext(t)
            trs.append(t)
        while len(new["rows"]) < len(trs):
            tbl.remove(trs.pop())
        for i, (tr, nr) in enumerate(zip(trs, new["rows"])):
            orow = old["rows"][i] if i < len(old["rows"]) else None
            if nr["h"] is not None and (orow is None or orow["h"] != nr["h"]):
                tr.set("h", str(round(nr["h"] * EMU)))
                self.changed += 1
            tcs = [t for t in tr.findall(a("tc")) if t.get("hMerge") != "1" and t.get("vMerge") != "1"]
            if len(tcs) != len(nr["cells"]):
                self.warn.append(f"표 {new['id']} {i + 1}행: 병합 구조가 달라 칸 수가 맞지 않음. 앞쪽 칸만 반영")
            for j, (tc, nc) in enumerate(zip(tcs, nr["cells"])):
                oc = orow["cells"][j] if orow and j < len(orow["cells"]) else None
                if oc is None or oc != nc:
                    self.write_cell(tc, oc, nc)

    def apply(self, sh, old, new, T):
        self.box(sh, old, new, T)
        k = new["kind"]
        if k == "shape":
            self.shape(sh, old, new, T)
        elif k == "line":
            self.line(sh, old, new)
        elif k == "table":
            self.table(sh, old, new)
        elif k == "image" and old["src"] != new["src"]:
            _, rid = sh.part.get_or_add_image_part(str(self.image_path(new["src"])))
            blip = sh._element.find(".//" + a("blip"))
            blip.set(qn("r:embed"), rid)
            sr = sh._element.find(".//" + a("srcRect"))
            if sr is not None:
                sr.getparent().remove(sr)
            self.changed += 1
        elif k == "frozen" and old["src"] != new["src"]:
            self.warn.append(f"요소 {new['id']}: 차트·자유형은 그림만 바꿔도 PPT 에 반영되지 않음. PowerPoint 에서 고치세요")

    def add(self, slide, e):
        L, T_, W, H = (round((e[k] or 0) * EMU) for k in ("x", "y", "w", "h"))
        k = e["kind"]
        self.changed += 1
        if k in ("image", "frozen"):
            return slide.shapes.add_picture(str(self.image_path(e["src"])), L, T_, W, H)
        if k == "line":
            fx, fy = "h" in e["flip"], "v" in e["flip"]
            sh = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, L + (W if fx else 0), T_ + (H if fy else 0), L + (0 if fx else W), T_ + (0 if fy else H))
            self.line(sh, {"stroke": None, "flip": e["flip"], "head": False, "tail": False}, e)
            return sh
        if k == "table":
            gf = slide.shapes.add_table(len(e["rows"]), len(e["cols"]), L, T_, W, H)
            tbl = gf.table
            tbl.first_row = tbl.horz_banding = False
            self.table(gf, {"rows": [], "cols": []}, e)
            return gf
        sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, L, T_, W, H)
        st = sh._element.find(qn("p:style"))
        if st is not None:
            sh._element.remove(st)
        sh._element.find(qn("p:spPr")).find(a("prstGeom")).set("prst", e["geom"])
        self.shape(sh, {"fill": "x", "line": "x", "geom": "rect", "adj": None, "paras": [], "pad": [0.127, 0.254, 0.127, 0.254], "anchor": "ctr", "nowrap": False}, e, (1, 1, 0, 0))
        return sh


def shape_map(reader, slide):
    sink = []
    reader.walk(slide.shapes, (1, 1, 0, 0), sink)
    out, seen = {}, set()
    for sh, T, _ in sink:
        sid = str(sh.shape_id)
        while sid in seen:
            sid += "~"
        seen.add(sid)
        out[sid] = (sh, T)
    return out


def apply_html(prs, baseline, current, base_dir):
    """current(deck.html) 와 baseline 의 차이만 prs 에 쓴다. 반영한 속성 수와 경고를 돌려준다."""
    w = Writer(prs, base_dir)
    reader = Reader(prs, base_dir)
    by_sid = {str(s.slide_id): s for s in prs.slides}
    olds = {s["sid"]: s for s in baseline}
    used, order, touched = set(), [], []
    last_layout = None
    for sec in current:
        sid = sec["sid"]
        fresh = sid is None or sid in used or sid not in by_sid or sid not in olds
        if fresh:
            layout = last_layout or prs.slides[0].slide_layout
            slide = prs.slides.add_slide(layout)
            for ph in list(slide.placeholders):
                ph._element.getparent().remove(ph._element)
            old = {"bg": sec["bg"], "els": []}
            before = -1
        else:
            used.add(sid)
            slide, old = by_sid[sid], olds[sid]
            before = w.changed
        last_layout = slide.slide_layout
        order.append(str(slide.slide_id))
        mp = shape_map(reader, slide)
        oldmap = {e["id"]: e for e in old["els"]}
        if old["bg"] != sec["bg"] and is_hex(sec["bg"]):
            f = slide.background.fill
            f.solid()
            from pptx.dml.color import RGBColor
            f.fore_color.rgb = RGBColor.from_string(sec["bg"][1:7])
            w.changed += 1
        seen, tops = set(), []
        for e in sec["els"]:
            eid = e["id"]
            if eid and eid not in seen and eid in oldmap and eid in mp and not fresh:
                seen.add(eid)
                sh, T = mp[eid]
                if oldmap[eid] != e:
                    w.apply(sh, oldmap[eid], e, T)
                tops.append(sh._element)
            elif eid and eid in oldmap and eid not in mp and eid not in seen:
                w.warn.append(f"{sec['sid']} 장의 요소 {eid} 를 원본 PPT 에서 찾지 못해 건너뜀")
            else:
                sh = w.add(slide, e)
                tops.append(sh._element)
        for eid, oe in oldmap.items():
            if eid not in seen and eid in mp:
                el = mp[eid][0]._element
                el.getparent().remove(el)
                w.changed += 1
        # 요소 순서(앞뒤)가 바뀌면 HTML 순서대로 다시 쌓는다
        old_ids = [e["id"] for e in old["els"] if e["id"] in seen]
        new_ids = [e["id"] for e in sec["els"] if e["id"] in seen]
        if old_ids != new_ids:
            tree = slide.shapes._spTree
            ext = tree.find(qn("p:extLst"))
            roots = []
            for el in tops:
                r = el
                while r.getparent() is not tree:
                    r = r.getparent()
                if r not in roots:
                    roots.append(r)
            for r in roots:
                tree.remove(r)
                if ext is not None:
                    ext.addprevious(r)
                else:
                    tree.append(r)
            w.changed += 1
        if before == -1 or w.changed != before:
            touched.append(order.index(str(slide.slide_id)) + 1)
    # 장 삭제 · 순서
    lst = prs.part._element.find(qn("p:sldIdLst"))
    items = {x.get("id"): x for x in lst}
    for sid, x in list(items.items()):
        if sid not in order:
            prs.part.drop_rel(x.get(qn("r:id")))
            lst.remove(x)
            w.changed += 1
    current_order = [x.get("id") for x in lst]
    if current_order != order:
        for sid in order:
            lst.remove(items[sid])
            lst.append(items[sid])
        w.changed += 1
    return {"changed": w.changed, "warnings": w.warn, "touched_slides": touched}


# ───────────── 파일 흐름 ─────────────
def _is_drm(path):
    from proposal_lib.deckio import sniff
    return sniff(path) == "drm"


def _com(mode, path, out=None, list_json=None, timeout=600):
    from proposal_lib.deckio import run_app_script
    args = ["-Mode", mode, "-Path", str(path)]
    if out:
        args += ["-Out", str(out)]
    if list_json:
        args += ["-ListJson", str(list_json)]
    return run_app_script("pptx_com.ps1", args, "powerpoint", timeout=timeout)


def plain_copy(src, tmp_dir):
    """python-pptx 가 읽을 수 있는 사본을 임시 폴더에 만든다 (DRM 덱은 PowerPoint 경유)."""
    out = Path(tmp_dir) / "plain.pptx"
    if _is_drm(src):
        r = _com("plain", src, out)
        if r.get("error"):
            raise RuntimeError(r["message"])
    else:
        shutil.copy2(src, out)
    return out


def save_final(tmp, dest):
    """결과를 목적지에 저장한다. Windows 는 PowerPoint 로 저장해 이 PC 의 DRM 이 정상 적용되게 한다."""
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    if platform.system() == "Windows":
        r = _com("saveas", tmp, dest)
        if r.get("error"):
            raise RuntimeError(r["message"])
    else:
        shutil.copy2(tmp, dest)


def convert(plain, out_dir, source):
    """python-pptx 로 읽히는 pptx 를 작업 폴더로 변환한다."""
    out_dir = Path(out_dir)
    assets = out_dir / "assets"
    if assets.exists():
        shutil.rmtree(assets)
    assets.mkdir(parents=True)
    prs = Presentation(str(plain))
    rd = Reader(prs, out_dir)
    slides = [rd.slide(s, i) for i, s in enumerate(prs.slides, 1)]
    failed = []
    if rd.exports:
        if platform.system() == "Windows":
            with tempfile.TemporaryDirectory() as td:
                lj = Path(td) / "list.json"
                lj.write_text(json.dumps(rd.exports, ensure_ascii=False), encoding="utf-8")
                r = _com("export", plain, list_json=lj)
            if r.get("error"):
                failed = [r["message"]]
            else:
                failed = r.get("failed") or []
                failed = [failed] if isinstance(failed, str) else failed
        else:
            failed = ["PowerPoint 가 없어 차트·자유형을 그림으로 내보내지 못함"]
    text = slides_html(slides, Path(source).stem)
    (out_dir / "deck.html").write_text(text, encoding="utf-8")
    (out_dir / ".baseline.html").write_text(text, encoding="utf-8")
    (out_dir / "deck.css").write_text(font_faces(slides) + CSS % {"w": num(prs.slide_width / EMU), "h": num(prs.slide_height / EMU)}, encoding="utf-8")
    (out_dir / "deck.js").write_text(JS, encoding="utf-8")
    (out_dir / "deck.json").write_text(json.dumps({"source": str(source)}, ensure_ascii=False, indent=1), encoding="utf-8")
    counts = {}
    for s in slides:
        for e in s["els"]:
            counts[e["kind"]] = counts.get(e["kind"], 0) + 1
    return {"slides": len(slides), "elements": counts, "frozen_failed": failed}


def open_pptx(src, out_dir):
    with tempfile.TemporaryDirectory() as td:
        return convert(plain_copy(src, td), out_dir, src)


def from_outline(rendered_tmp, out_dir):
    """render 로 임시 폴더에 만든 pptx 를 base.pptx 로 저장하고 작업 폴더로 변환한다."""
    base = Path(out_dir).resolve() / "base.pptx"
    save_final(rendered_tmp, base)
    return convert(rendered_tmp, out_dir, base)


def build(work_dir, dest):
    """deck.html 의 변경분을 원본 사본에 반영해 dest 로 저장하고, 작업 폴더를 새 결과 기준으로 다시 만든다."""
    work_dir = Path(work_dir)
    meta = json.loads((work_dir / "deck.json").read_text(encoding="utf-8"))
    src = Path(meta["source"])
    if not src.exists():
        raise FileNotFoundError(f"원본 PPT 를 찾지 못했습니다: {src}")
    baseline = parse_html((work_dir / ".baseline.html").read_text(encoding="utf-8"))
    current = parse_html((work_dir / "deck.html").read_text(encoding="utf-8"))
    if not current:
        raise ValueError("deck.html 에 슬라이드(section.slide)가 없습니다")
    with tempfile.TemporaryDirectory() as td:
        plain = plain_copy(src, td)
        prs = Presentation(str(plain))
        res = apply_html(prs, baseline, current, work_dir)
        if dest is None:          # 점검만: 저장하지 않는다
            return res
        out = Path(td) / "built.pptx"
        prs.save(str(out))
        save_final(out, dest)
        conv = convert(out, work_dir, dest)
    return {**res, **conv}
