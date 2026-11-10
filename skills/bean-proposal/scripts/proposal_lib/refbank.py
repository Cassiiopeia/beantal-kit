"""레퍼런스 자료 은행: 등록된 과거 제안서에서 장별 글 · 표 · 사진을 뽑아 색인하고, RFP 요건으로 찾아 쓴다.

- 색인: references/<id>/index.json (장마다 제목 · 글 · 표 · 사진 · 주제), 사진은 references/<id>/images/
- DRM 덱은 PowerPoint 로 임시 평문 사본을 만들어 읽고, 사본은 바로 지운다. 색인과 사진은 이 PC 안(~/.beantal-kit)에만 둔다.
- 로고 · 아이콘처럼 작거나 여러 장에 반복되는 그림은 사진으로 치지 않는다.
- outline 에서는 `- 사진:` 블록에 `ref:<id>/<사진키> | 캡션` 으로 쓴다 (render 가 그대로 그린다).
"""
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import date
from pathlib import Path

from . import refs

SKIP_EXT = {"emf", "wmf", "svg", "tif", "tiff"}
MIN_W, MIN_H = 3.0, 2.0         # cm, 이보다 작은 그림은 아이콘 · 로고로 본다
TOPICS = {
    "입고": ["입고", "검수", "하차", "도크", "asn", "inbound"],
    "보관·재고": ["보관", "재고", "로케이션", "실사", "적치", "선입선출", "fifo", "fefo", "유통기한", "로트"],
    "출고": ["출고", "피킹", "패킹", "포장", "합포", "출하", "outbound", "picking"],
    "배송": ["배송", "택배", "라스트마일", "당일", "새벽", "익일", "운송", "차량", "밀크런", "milk-run", "cj대한통운"],
    "반품": ["반품", "회수", "교환", "재입고", "검품", "rma"],
    "B2B": ["b2b", "도매", "대리점", "납품", "팔레트", "파렛트", "점포"],
    "센터·거점": ["센터", "거점", "평", "부지", "창고", "곤지암", "용인", "이천", "레이아웃", "층"],
    "시스템": ["wms", "oms", "tms", "시스템", "api", "연동", "edi", "#mate", "mate", "대시보드", "pda", "바코드", "rfid"],
    "냉장·식품": ["냉장", "냉동", "저온", "상온", "온도", "식품", "haccp", "콜드"],
    "보안·개인정보": ["보안", "개인정보", "cctv", "출입", "마스킹", "암호화", "isms"],
    "조직·인력": ["조직", "인력", "인원", "pm", "센터장", "tft", "담당자", "교육"],
    "일정·전환": ["일정", "전환", "오픈", "이관", "go-live", "milestone", "마일스톤", "주차", "w1"],
    "정산·단가": ["정산", "단가", "요금", "비용", "청구", "견적", "원가"],
    "품질·KPI": ["kpi", "sla", "오출고", "정확도", "품질", "클레임", "불량", "99", "리드타임"],
    "실적·사례": ["실적", "사례", "고객사", "레퍼런스", "운영 중", "성과", "개선"],
    "부가서비스": ["키팅", "세트", "임가공", "라벨", "샘플", "판촉", "증정", "사은품"],
    "회사소개": ["회사", "연혁", "매출", "인증", "수상", "비전", "아워박스", "ourbox"],
}
ROLE_ORDER = ("최종", "틀", "작업중")


def _index_path(pid):
    return refs.REF_DIR / pid / "index.json"


def _deck_of(proj):
    for role in ROLE_ORDER:
        for f in proj.get("files", []):
            p = Path(os.path.expanduser(f["path"]))
            if f.get("role") == role and p.suffix.lower() == ".pptx" and p.exists():
                return p
    return None


def _walk(shapes):
    from pptx.enum.shapes import MSO_SHAPE_TYPE as MSO
    for sh in shapes:
        if sh.shape_type == MSO.GROUP:
            yield from _walk(sh.shapes)
        else:
            yield sh


def _clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def topics_of(text):
    low = text.lower()
    return [t for t, kws in TOPICS.items() if sum(low.count(k) for k in kws) >= 2 or any(k in low for k in kws[:2])]


def _title(slide_shapes):
    """위쪽 4cm 안에서 가장 큰 글자 문단 = 제목. '01.' 같은 번호만 있는 문단은 뺀다."""
    best = (0, "")
    for sh in slide_shapes:
        if not getattr(sh, "has_text_frame", False) or not sh.has_text_frame or sh.top is None:
            continue
        if sh.top / 360000 > 4.0:
            continue
        for p in sh.text_frame.paragraphs:
            t = _clean(p.text)
            if not t or re.fullmatch(r"[\d.\s]+", t) or len(t) > 60:
                continue
            size = next((r.font.size.pt for r in p.runs if r.font.size), 0) or 0
            if size > best[0]:
                best = (size, t)
    return best[1]


def _save_image(sh, out_dir):
    try:
        img = sh.image
    except Exception:
        return None
    ext = (img.ext or "").lower()
    if ext in SKIP_EXT:
        return None
    crop = (sh.crop_left, sh.crop_top, sh.crop_right, sh.crop_bottom)
    digest = hashlib.sha1(img.blob + repr(crop).encode()).hexdigest()[:12]
    name = f"{digest}.{'jpg' if ext == 'jpeg' else ext}"
    path = out_dir / name
    if not path.exists():
        if any(crop):
            try:
                import io
                from PIL import Image
                im = Image.open(io.BytesIO(img.blob))
                W, H = im.size
                im.crop((round(crop[0] * W), round(crop[1] * H), round(W - crop[2] * W), round(H - crop[3] * H))).save(path)
            except Exception:
                path.write_bytes(img.blob)
        else:
            path.write_bytes(img.blob)
    return digest, name


def build_index(pid, plain_copy_fn):
    """한 레퍼런스의 덱을 읽어 index.json 과 images/ 를 만든다."""
    from pptx import Presentation
    data = refs.load()
    proj = next((p for p in data["projects"] if p["id"] == pid), None)
    if not proj:
        return {"ok": False, "id": pid, "message": f"등록되지 않은 id: {pid}"}
    deck = _deck_of(proj)
    if deck is None:
        return {"ok": False, "id": pid, "message": "색인할 pptx(최종·틀·작업중)가 없습니다"}
    img_dir = refs.REF_DIR / pid / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        try:
            plain = plain_copy_fn(deck, td)
            prs = Presentation(str(plain))
        except Exception as e:
            return {"ok": False, "id": pid, "message": f"덱을 열지 못했습니다: {e}"}
        SW, SH = prs.slide_width / 360000, prs.slide_height / 360000
        slides, seen = [], {}
        for n, s in enumerate(prs.slides, 1):
            shapes = list(_walk(s.shapes))
            texts, tables, images = [], [], []
            for sh in shapes:
                if getattr(sh, "has_table", False) and sh.has_table:
                    rows = [[_clean(c.text) for c in r.cells] for r in sh.table.rows]
                    if rows and any(any(c for c in r) for r in rows):
                        tables.append(rows)
                    continue
                if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
                    t = _clean(sh.text_frame.text)
                    if t:
                        texts.append(t)
                w = (sh.width or 0) / 360000
                h = (sh.height or 0) / 360000
                if hasattr(sh, "image") and w >= MIN_W and h >= MIN_H:
                    saved = _save_image(sh, img_dir)
                    if saved:
                        digest, name = saved
                        seen.setdefault(digest, set()).add(n)
                        images.append({"hash": digest, "file": f"images/{name}", "w": round(w, 1), "h": round(h, 1),
                                       "full": w * h > SW * SH * 0.8})
            body = " / ".join(dict.fromkeys(texts))
            slides.append({"n": n, "title": _title(shapes), "text": body, "tables": tables, "images": images})
    # 여러 장에 반복되는 그림(로고 · 배경)은 뺀다
    many = {d for d, ns in seen.items() if len(ns) >= 3 and len(ns) >= 0.2 * len(slides)}
    for s in slides:
        kept = [im for im in s["images"] if im["hash"] not in many]
        for i, im in enumerate(kept, 1):
            im["key"] = f"s{s['n']}-{i}"
            im.pop("hash")
        s["images"] = kept
        blob = " ".join([s["title"], s["text"]] + [" ".join(" ".join(r) for r in t) for t in s["tables"]])
        s["topics"] = topics_of(blob)
    used = {Path(im["file"]).name for s in slides for im in s["images"]}
    for f in img_dir.iterdir():     # 반복 그림 · 지난 색인의 남은 파일 정리
        if f.name not in used:
            f.unlink()
    out = {"id": pid, "client": proj.get("client"), "title": proj.get("title"), "year": proj.get("year"),
           "quality": proj.get("quality"), "source": deck.name, "source_mtime": int(deck.stat().st_mtime),
           "built": date.today().isoformat(), "slides": slides}
    _index_path(pid).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"ok": True, "id": pid, "slides": len(slides), "images": len(used),
            "tables": sum(len(s["tables"]) for s in slides), "index": refs.tilde(_index_path(pid))}


def stale(pid):
    """색인이 없거나 덱이 더 새로우면 True."""
    data = refs.load()
    proj = next((p for p in data["projects"] if p["id"] == pid), None)
    deck = _deck_of(proj) if proj else None
    ip = _index_path(pid)
    if deck is None:
        return False
    if not ip.exists():
        return True
    try:
        return json.loads(ip.read_text(encoding="utf-8")).get("source_mtime") != int(deck.stat().st_mtime)
    except ValueError:
        return True


def load_index(pid):
    ip = _index_path(pid)
    return json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else None


# ---------------------------------------------------------------- 찾기

def _terms(text):
    words = re.findall(r"[가-힣]+|[A-Za-z#][A-Za-z0-9#+\-]*|\d+", (text or "").lower())
    out = []
    for w in words:
        if len(w) < 2 and not w.isdigit():
            continue
        out.append(w)
        if re.fullmatch(r"[가-힣]{3,}", w):       # 붙여 쓴 말도 맞도록 두 글자 조각을 더한다 ('반품처리' ↔ '반품')
            out += [w[i:i + 2] for i in range(len(w) - 1)]
    return out


STOP = {"및", "등", "위한", "대한", "있는", "하는", "합니다", "제안", "제안사", "운영", "관리", "방안", "계획", "요청", "제시", "기술",
        "구체적", "내용", "사항", "포함", "여부", "업무", "수행"}


def _docs(ids=None):
    data = refs.load()
    for proj in data["projects"]:
        if ids and proj["id"] not in ids:
            continue
        idx = load_index(proj["id"])
        if not idx:
            continue
        for s in idx["slides"]:
            if len(s["text"]) < 20 and not s["tables"] and not s["images"]:
                continue        # 표지 · 간지 · 빈 장
            yield idx, s


def search(query, ids=None, top=8, photos=False, topic=None):
    q = [t for t in _terms(query) if t not in STOP]
    docs = list(_docs(ids))
    if not docs or (not q and not topic):
        return []
    toks = []
    for idx, s in docs:
        blob = " ".join([s["title"], s["text"]] + [" ".join(" ".join(r) for r in t) for t in s["tables"]])
        toks.append((set(_terms(blob)), set(_terms(s["title"]))))
    n = len(docs)
    df = {t: sum(1 for body, _ in toks if t in body) for t in set(q)}
    avg = sum(len(body) for body, _ in toks) / n
    res = []
    for (idx, s), (body, title) in zip(docs, toks):
        if photos and not s["images"]:
            continue
        if topic and topic not in s["topics"]:
            continue
        score = 0.0
        for t in set(q):
            if t in body:
                w = math.log(1 + n / (1 + df[t]))
                score += w * (3.0 if t in title else 1.0) *(0.5 if len(t) == 2 and re.fullmatch(r"[가-힣]{2}", t) and t not in query else 1.0)
        if topic:
            score += 1.0
        if score <= 0:
            continue
        score /= (0.4 + 0.6 * len(body) / avg) ** 0.5        # 말이 많은 장(전체 프로세스 등)이 늘 이기지 않게
        score *= 1.15 if idx.get("quality") == "gold" else 1.0
        res.append({"ref": idx["id"], "client": idx.get("client"), "year": idx.get("year"), "n": s["n"], "title": s["title"],
                    "score": round(score, 2), "topics": s["topics"], "snippet": s["text"][:160],
                    "tables": len(s["tables"]), "photos": [im["key"] for im in s["images"]]})
    res.sort(key=lambda r: -r["score"])
    return res[:top]


def cases(names, ids=None, top=6, about=None):
    """고객 사례 찾기: 여러 제안서에 실적 · 사례로 들어간 고객사(예: 동원, 유한킴벌리)의 장을 모은다.
    이름은 부분 일치('동원' → 동원F&B · 동원디어푸드). 최신 연도 · gold · 제목에 이름 · 표/사진 있는 장을 앞에 둔다."""
    out = {}
    docs = list(_docs(ids))
    want = {t for t in _terms(about or "") if t not in STOP}     # RFP 가 강조하는 말과 겹치는 사례를 앞으로
    for name in names:
        key = name.lower().replace(" ", "")
        hits = []
        for idx, s in docs:
            tables = " ".join(" ".join(" ".join(r) for r in t) for t in s["tables"])
            blob = (s["title"] + " " + s["text"] + " " + tables).lower().replace(" ", "")
            cnt = blob.count(key)
            if not cnt:
                continue
            if (idx.get("client") or "").lower().replace(" ", "") == key and "실적·사례" not in s["topics"]:
                continue        # 그 고객사에 낸 제안서 본문은 사례가 아니다
            in_title = key in s["title"].lower().replace(" ", "")
            try:
                year = int(str(idx.get("year") or 0)[:4])
            except ValueError:
                year = 0
            raw = s["title"] + " " + s["text"] + " " + tables
            ctx = _around(raw, name, 40)
            listed = ctx.count("·") + ctx.count(",") + ctx.count("/") >= 4      # 고객사 이름 나열 속 한 줄
            case_title = bool(re.search(r"레퍼런스|사례|실적|reference|case", s["title"], re.I))
            score = min(cnt, 5) + (4 if in_title else 0) + (3 if case_title else 0) + (2 if "실적·사례" in s["topics"] else 0) \
                + (1.5 if s["tables"] else 0) + (1.5 if s["images"] else 0) + (1 if idx.get("quality") == "gold" else 0) \
                - (3 if listed and not in_title else 0)
            if want:
                score += 1.5 * len(want & set(_terms(raw)))
            hits.append({"ref": idx["id"], "client": idx.get("client"), "year": idx.get("year"), "n": s["n"], "title": s["title"],
                         "score": round(score, 1), "_year": year, "mentions": cnt, "topics": s["topics"],
                         "snippet": _around(s["text"] + " " + tables, name), "tables": len(s["tables"]),
                         "photos": [im["key"] for im in s["images"]]})
        hits.sort(key=lambda h: (-h["score"], -h["_year"]))
        for h in hits:
            h.pop("_year")
        out[name] = hits[:top]
    return out


def _around(text, name, width=70):
    i = text.lower().find(name.lower())
    if i < 0:
        return text[:width * 2]
    return ("…" if i > width else "") + text[max(0, i - width):i + len(name) + width] + "…"


def show(pid, n):
    idx = load_index(pid)
    if not idx:
        return None
    s = next((x for x in idx["slides"] if x["n"] == n), None)
    if not s:
        return None
    base = refs.REF_DIR / pid
    return {**s, "ref": pid, "client": idx.get("client"), "year": idx.get("year"), "source": idx.get("source"),
            "images": [{**im, "src": f"ref:{pid}/{im['key']}", "path": str(base / im["file"])} for im in s["images"]]}


def resolve_photo(src):
    """'ref:<id>/<키>' 또는 파일 경로 → 실제 파일 Path. 없으면 None."""
    src = (src or "").strip()
    m = re.fullmatch(r"ref:([^/]+)/(s\d+-\d+)", src)
    if m:
        idx = load_index(m.group(1))
        for s in (idx or {}).get("slides", []):
            for im in s["images"]:
                if im["key"] == m.group(2):
                    p = refs.REF_DIR / m.group(1) / im["file"]
                    return p if p.exists() else None
        return None
    p = Path(os.path.expanduser(src))
    return p if src and p.exists() and p.is_file() else None


def client_names():
    """등록된 레퍼런스의 고객사 이름들 (다른 고객사 이름이 새 덱에 남았는지 점검용)."""
    return sorted({p.get("client") for p in refs.load()["projects"] if p.get("client")})
