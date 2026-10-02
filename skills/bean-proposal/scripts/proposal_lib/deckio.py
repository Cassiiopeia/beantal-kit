"""문서 읽기: pptx/docx/xlsx/pdf 를 공통 구조(dict)로 만든다.

- 평문 파일은 python 라이브러리로 읽는다.
- DRM(사내 문서 보안) 파일은 Windows 에서 PowerPoint 를 통해 읽기 전용으로 열어 메모리에서만 구조를 뽑는다.
  복호화된 사본을 디스크에 만들지 않는다.
"""
import json
import os
import platform
import re
import subprocess
from pathlib import Path

EMU_PER_CM = 360000


def cm(v):
    return round(v / EMU_PER_CM, 2) if v is not None else None


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def file_kind(path):
    """'plain' | 'drm' | 'missing' — 파일 앞 8바이트로 판정."""
    p = Path(path)
    if not p.exists():
        return "missing"
    with open(p, "rb") as f:
        head = f.read(8)
    if head.startswith(b"PK") or head.startswith(b"%PDF"):
        return "plain"
    if head.startswith(b"BMS"):
        return "drm"
    return "unknown"


# ---------------------------------------------------------------- pptx (python)

def _shape_record(sh, MSO):
    rec = {
        "name": sh.name,
        "left": cm(sh.left), "top": cm(sh.top), "width": cm(sh.width), "height": cm(sh.height),
        "kind": "other", "text": "", "paras": [],
    }
    t = sh.shape_type
    if t == MSO.PICTURE:
        rec["kind"] = "picture"
    elif getattr(sh, "has_chart", False) and sh.has_chart:
        rec["kind"] = "chart"
    elif getattr(sh, "has_table", False) and sh.has_table:
        rec["kind"] = "table"
        rows = []
        for r in sh.table.rows:
            rows.append([clean(c.text) for c in r.cells])
        rec["table"] = rows
        rec["text"] = " | ".join(" | ".join(r) for r in rows)
    elif t == MSO.LINE or "Connector" in type(sh).__name__:
        rec["kind"] = "line"
    elif t == MSO.AUTO_SHAPE:
        rec["kind"] = "autoshape"
    elif t == MSO.TEXT_BOX:
        rec["kind"] = "textbox"
    elif t == MSO.PLACEHOLDER:
        rec["kind"] = "placeholder"
    if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
        paras = []
        for p in sh.text_frame.paragraphs:
            txt = clean(p.text)
            if not txt:
                continue
            size = next((r.font.size.pt for r in p.runs if r.font.size), None)
            font = next((r.font.name for r in p.runs if r.font.name), None)
            bold = any(bool(r.font.bold) for r in p.runs)
            color = None
            for r in p.runs:
                try:
                    if r.font.color and r.font.color.type is not None and r.font.color.rgb is not None:
                        color = str(r.font.color.rgb)
                        break
                except Exception:
                    pass
            paras.append({"text": txt, "size": size, "font": font, "bold": bold, "color": color, "level": p.level})
        rec["paras"] = paras
        if not rec["text"]:
            rec["text"] = " ".join(x["text"] for x in paras)
    return rec


def _walk(shapes, MSO):
    for sh in shapes:
        if sh.shape_type == MSO.GROUP:
            yield from _walk(sh.shapes, MSO)
        else:
            yield sh


def read_pptx_python(path):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE as MSO
    prs = Presentation(path)
    fonts_theme = set()
    slides = []
    for i, s in enumerate(prs.slides, 1):
        shapes = [_shape_record(sh, MSO) for sh in _walk(s.shapes, MSO)]
        notes = ""
        if s.has_notes_slide and s.notes_slide.notes_text_frame is not None:
            notes = clean(s.notes_slide.notes_text_frame.text)
        slides.append({"n": i, "layout": s.slide_layout.name, "notes": notes, "shapes": shapes})
    return {
        "format": "pptx", "via": "python",
        "size_cm": [cm(prs.slide_width), cm(prs.slide_height)],
        "masters": len(prs.slide_masters),
        "slides": slides,
    }


# ---------------------------------------------------------------- pptx (PowerPoint, DRM)

def read_pptx_powerpoint(path):
    if platform.system() != "Windows":
        return {"error": "drm_unsupported_os", "message": "DRM 파일은 Windows 의 PowerPoint 로만 읽을 수 있습니다."}
    script = Path(__file__).resolve().parent.parent / "drm_read_pptx.ps1"
    cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Path", str(path)]
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=600)
    except subprocess.TimeoutExpired:
        return {"error": "powerpoint_timeout", "message": "PowerPoint 로 여는 데 10분을 넘겼습니다."}
    raw = out.stdout.decode("utf-8", errors="replace").strip()
    try:
        data = json.loads(raw[raw.index("{"):]) if "{" in raw else None
    except ValueError:
        data = None
    if not data:
        err = out.stderr.decode("utf-8", errors="replace")[-400:]
        return {"error": "powerpoint_failed", "message": err or raw[-400:]}
    data["format"] = "pptx"
    data["via"] = "powerpoint"
    return data


def read_pptx(path):
    kind = file_kind(path)
    if kind == "missing":
        return {"error": "missing", "message": f"파일이 없습니다: {path}"}
    if kind == "drm":
        d = read_pptx_powerpoint(path)
    else:
        d = read_pptx_python(path)
    d["drm"] = kind == "drm"
    d["path"] = str(path)
    d["mb"] = round(Path(path).stat().st_size / 1e6, 1)
    return d


# ---------------------------------------------------------------- docx / xlsx / pdf (평문만)

def read_docx(path):
    import docx
    d = docx.Document(path)
    paras = []
    for p in d.paragraphs:
        t = clean(p.text)
        if t:
            paras.append({"text": t, "style": p.style.name})
    tables = []
    for tb in d.tables:
        tables.append([[clean(c.text) for c in r.cells] for r in tb.rows])
    return {"format": "docx", "paras": paras, "tables": tables}


def read_xlsx(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheets = {}
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            vals = ["" if v is None else clean(str(v)) for v in row]
            while vals and not vals[-1]:
                vals.pop()
            if any(vals):
                rows.append(vals)
        sheets[ws.title] = rows
    return {"format": "xlsx", "sheets": sheets}


def read_pdf(path):
    from pypdf import PdfReader
    r = PdfReader(path)
    return {"format": "pdf", "pages": [{"n": i, "text": (pg.extract_text() or "").strip()} for i, pg in enumerate(r.pages, 1)]}


def read_any(path):
    p = Path(os.path.expanduser(str(path)))
    ext = p.suffix.lower()
    if ext == ".pptx":
        return read_pptx(p)
    kind = file_kind(p)
    if kind == "missing":
        return {"error": "missing", "message": f"파일이 없습니다: {p}"}
    if kind == "drm":
        return {"error": "drm_not_supported_for_format", "drm": True, "path": str(p),
                "message": f"{ext} DRM 파일은 아직 직접 읽지 못합니다. 원본을 열어 필요한 부분을 대화로 붙여 주거나, 승인된 평문본을 지정하세요."}
    fn = {".docx": read_docx, ".xlsx": read_xlsx, ".pdf": read_pdf}.get(ext)
    if not fn:
        return {"error": "unsupported", "message": f"지원하지 않는 형식입니다: {ext}"}
    d = fn(p)
    d.update({"drm": False, "path": str(p)})
    return d


def slide_text(slide):
    return " ".join(sh["text"] for sh in slide["shapes"] if sh.get("text"))
