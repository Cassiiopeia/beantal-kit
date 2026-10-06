"""레퍼런스 보관: 파일을 ~/.beantal-kit/configs/bean-proposal/references/<id>/ 로 복사하고 목록(references.json)에 등록한다.

- 원본은 건드리지 않는다 (복사만). DRM 환경에서는 복사본도 암호화되며, 읽을 때는 PowerPoint 를 거친다.
- digest.md 는 평문 요약(구성 · 스타일)이라 DRM 이 걸리지 않고, 에이전트가 덱을 열지 않고 읽을 수 있다.
"""
import json
import os
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path.home() / ".beantal-kit" / "configs" / "bean-proposal"
REF_DIR = ROOT / "references"
REF_JSON = ROOT / "references.json"
QUALITY = ("gold", "reference", "wip")
DIGEST_ROLES = ("최종", "틀", "작업중")


def load():
    if REF_JSON.exists():
        return json.loads(REF_JSON.read_text(encoding="utf-8"))
    return {"schema": 1, "updated": "", "projects": [], "company_assets": []}


def save(data):
    data["updated"] = date.today().isoformat()
    REF_JSON.parent.mkdir(parents=True, exist_ok=True)
    REF_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def slug(text):
    s = re.sub(r"[^\w가-힣-]+", "-", text.strip()).strip("-").lower()
    return s or "ref"


def is_inside(path):
    try:
        Path(path).resolve().relative_to(REF_DIR.resolve())
        return True
    except ValueError:
        return False


def tilde(path):
    p = Path(path).resolve()
    try:
        return "~/" + p.relative_to(Path.home()).as_posix()
    except ValueError:
        return str(p)


def copy_in(src, project_id):
    """src 를 references/<id>/원본/ 으로 복사. 이미 같은 이름이 있으면 덮어쓰지 않고 그대로 쓴다."""
    src = Path(os.path.expanduser(str(src)))
    if not src.exists():
        return None, f"파일이 없습니다: {src}"
    dest_dir = REF_DIR / project_id / "원본"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists() and dest.stat().st_size == src.stat().st_size:
        return dest, "이미 복사됨"
    shutil.copy2(src, dest)
    return dest, "복사함"


def add(project_id, client, title, year, quality, files, note=None):
    """files: [(role, path)] — 복사 후 목록에 등록(같은 id 가 있으면 파일을 합친다)."""
    data = load()
    proj = next((p for p in data["projects"] if p["id"] == project_id), None)
    if not proj:
        proj = {"id": project_id, "client": client, "title": title, "year": year, "quality": quality, "files": []}
        data["projects"].append(proj)
    proj.update({k: v for k, v in (("client", client), ("title", title), ("year", year), ("quality", quality)) if v})
    if note:
        proj["note"] = note
    log = []
    for role, path in files:
        dest, msg = copy_in(path, project_id)
        if dest is None:
            log.append({"role": role, "ok": False, "message": msg})
            continue
        entry = {"role": role, "path": tilde(dest)}
        old = next((f for f in proj["files"] if f["role"] == role and Path(os.path.expanduser(f["path"])).name == dest.name), None)
        if old:
            old.update(entry)
        else:
            proj["files"].append(entry)
        log.append({"role": role, "ok": True, "message": msg, "path": entry["path"], "mb": round(dest.stat().st_size / 1e6, 1)})
    save(data)
    return proj, log


def migrate():
    """목록에 경로만 적힌 항목을 모두 references/ 로 복사하고 경로를 복사본으로 바꾼다."""
    data = load()
    log = []
    for proj in data["projects"]:
        for f in proj["files"]:
            if is_inside(os.path.expanduser(f["path"])):
                continue
            dest, msg = copy_in(f["path"], proj["id"])
            if dest is None:
                log.append({"id": proj["id"], "role": f["role"], "ok": False, "message": msg})
                continue
            f["path"] = tilde(dest)
            f.pop("drm", None)
            log.append({"id": proj["id"], "role": f["role"], "ok": True, "message": msg, "mb": round(dest.stat().st_size / 1e6, 1)})
        save(data)
    return log


def digest(project_id, brief_fn, profile_fn, read_fn):
    """프로젝트의 최종·틀 덱을 읽어 references/<id>/digest.md 로 쓴다. 덱이 없으면 None."""
    data = load()
    proj = next((p for p in data["projects"] if p["id"] == project_id), None)
    if not proj:
        return {"ok": False, "message": f"등록되지 않은 id: {project_id}"}
    lines = [f"# {proj.get('client', '')} — {proj.get('title', '')} ({proj.get('year', '')}, {proj.get('quality', '')})", ""]
    if proj.get("note"):
        lines += [f"> {proj['note']}", ""]
    made = 0
    for f in proj["files"]:
        p = Path(os.path.expanduser(f["path"]))
        if f["role"] not in DIGEST_ROLES or p.suffix.lower() != ".pptx":
            continue
        d = read_fn(p)
        if d.get("error"):
            lines += [f"## {f['role']}: {p.name}", f"읽기 실패: {d.get('message')}", ""]
            continue
        prof = profile_fn(d)
        lines += [f"## {f['role']}: {p.name}", "", f"- {prof.get('summary')}", f"- DRM: {'예' if d.get('drm') else '아니오'}"]
        if f.get("note"):
            lines.append(f"- 메모: {f['note']}")
        sc = prof.get("suggested_config") or {}
        for k in ("fonts", "colors"):
            if sc.get(k):
                lines.append(f"- {k}: {json.dumps(sc[k], ensure_ascii=False)}")
        lines += ["", "| 장 | 번호 | 구분 | 제목 / 본문 앞부분 |", "|---|---|---|---|"]
        for s in brief_fn(d):
            title = (s.get("title") or "").replace("|", "/")
            body = s["text"][:90].replace("|", "/").replace("\n", " ")
            lines.append(f"| {s['n']} | {s.get('num') or ''} | {s.get('label') or ''} | {title} — {body} |")
        lines.append("")
        made += 1
    if not made:
        return {"ok": True, "id": project_id, "digest": None, "message": "요약할 pptx(최종·틀·작업중)가 없습니다"}
    out = REF_DIR / project_id / "digest.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "id": project_id, "digest": tilde(out), "decks": made}
