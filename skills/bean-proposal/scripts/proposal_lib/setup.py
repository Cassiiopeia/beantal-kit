"""첫 실행 설정: 작업 루트 후보 찾기, 기존 정리 규칙 추정, config 읽기/쓰기.

설정 파일은 플러그인 폴더 밖 ~/.beantal-kit/configs/bean-proposal/config.json 에만 둔다.
"""
import json
import os
import re
from collections import Counter
from pathlib import Path

HOME = Path.home()
CONFIG_PATH = HOME / ".beantal-kit" / "configs" / "bean-proposal" / "config.json"
SHARED = HOME / ".beantal-kit" / "shared"
DOC_EXT = {".pptx", ".ppt", ".docx", ".doc", ".pdf", ".xlsx", ".hwp", ".hwpx"}
PROPOSAL_WORDS = re.compile(r"(제안|RFP|입찰|견적|과업|사업계획|proposal)", re.I)
SKIP_DIRS = {"AppData", "node_modules", ".git", "anaconda3", ".conda", "site-packages", ".cache", ".claude", ".beantal-kit"}
VERSION_TAIL = re.compile(r"(_v\d+|_\d+차|\(\d+\)|_최종|_F|_수정\d*)", re.I)
DATE_HEAD = re.compile(r"^(\d{6}|\d{8})[_\s-]")


def default_config():
    ex = Path(__file__).resolve().parents[2] / "config.json.example"
    data = json.loads(ex.read_text(encoding="utf-8"))
    return {k: v for k, v in data["proposal"].items() if not k.startswith("_")}


def load_config():
    """값 결정 순서: config.json → example 기본값. 빠진 키는 example 로 보충해 돌려준다."""
    base = default_config()
    if CONFIG_PATH.exists():
        cur = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("proposal", {})
        base.update({k: v for k, v in cur.items() if v not in (None, "", [], {})})
        return base, True
    return base, False


def save_config(values):
    """기존 값은 덮어쓰지 않는다 — values 에 명시된 키만 바꾼다."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8")) if CONFIG_PATH.exists() else {"proposal": {}, "language": "ko"}
    data.setdefault("proposal", {}).update(values)
    CONFIG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(CONFIG_PATH)


def _walk(root, max_depth):
    root = Path(root)
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        for e in entries:
            if e.is_dir(follow_symlinks=False):
                if e.name in SKIP_DIRS or e.name.startswith("$"):
                    continue
                if depth < max_depth:
                    stack.append((Path(e.path), depth + 1))
            elif e.is_file():
                yield Path(e.path)


def scan_roots(extra=None, max_depth=4):
    """제안서 문서가 모여 있는 폴더 후보를 찾는다 (파일 이름과 개수만 본다, 내용은 열지 않는다)."""
    bases = [HOME / "Desktop", HOME / "Documents", HOME / "Downloads", HOME / "OneDrive"]
    bases += [Path(os.path.expanduser(x)) for x in (extra or [])]
    folder_stats = {}
    for base in bases:
        if not base.exists():
            continue
        for f in _walk(base, max_depth):
            if f.suffix.lower() not in DOC_EXT:
                continue
            rel = f.relative_to(base)
            # 후보 = base 바로 아래 1단계 폴더 (Downloads 는 base 자체)
            top = base if len(rel.parts) == 1 else base / rel.parts[0]
            st = folder_stats.setdefault(str(top), {"path": str(top), "docs": 0, "proposal_like": 0, "pptx": 0, "subdirs": set()})
            st["docs"] += 1
            st["pptx"] += f.suffix.lower() == ".pptx"
            st["proposal_like"] += bool(PROPOSAL_WORDS.search(f.name))
            if len(rel.parts) > 2:
                st["subdirs"].add(rel.parts[1])
    out = []
    for st in folder_stats.values():
        st["subdirs"] = sorted(st["subdirs"])[:15]
        st["onedrive_synced"] = "OneDrive" in st["path"]
        st["is_downloads"] = st["path"].rstrip("\\/").endswith("Downloads")
        # 루트 추천: 하위 폴더로 정리돼 있고, 다운로드·클라우드 동기화 폴더가 아닌 곳
        if st["is_downloads"]:
            st["recommend"] = "비추천 — 다운로드 폴더는 임시 보관 장소 (여기 쌓인 파일은 프로젝트 폴더로 옮겨 정리 대상)"
        elif st["onedrive_synced"]:
            st["recommend"] = "주의 — 클라우드 동기화 폴더 (고객 자료가 외부로 동기화될 수 있음)"
        elif len(st["subdirs"]) >= 3:
            st["recommend"] = "추천 — 이미 하위 폴더로 정리해 쓰는 곳"
        else:
            st["recommend"] = "보통"
        out.append(st)
    rank = lambda x: (x["recommend"].startswith("추천"), x["proposal_like"], x["pptx"])
    out.sort(key=rank, reverse=True)
    for i, st in enumerate(out):
        st["path"] = st["path"].replace(str(HOME), "~")
    return out[:10]


def infer_layout(root, max_depth=3):
    """고른 루트의 하위 구조를 보고 정리 규칙을 추정한다."""
    root = Path(os.path.expanduser(root))
    if not root.exists():
        return {"exists": False}
    level1 = [d for d in root.iterdir() if d.is_dir()]
    level2 = [d2 for d in level1 for d2 in d.iterdir() if d2.is_dir()]
    files_lvl1 = sum(1 for d in level1 for f in d.iterdir() if f.is_file() and f.suffix.lower() in DOC_EXT)
    date_named_l2 = sum(1 for d in level2 if DATE_HEAD.match(d.name))
    versioned = Counter()
    for d in level1:
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() == ".pptx":
                versioned[VERSION_TAIL.sub("", f.stem)] += 1
    multi_version = sum(1 for v in versioned.values() if v > 1)
    guess = "{client}/{yymmdd}_{title}" if date_named_l2 >= max(1, len(level2) // 3) else (
        "{client}/{title}" if level2 else "{client}")
    marked = [d.name for d in level1 if re.match(r"^[\(\[【].{1,4}[\)\]】]", d.name)]
    obs = [
        f"1단계 폴더 {len(level1)}개 (고객사별로 보임)" if level1 else "하위 폴더가 없습니다",
        f"고객사 폴더 바로 아래 문서 {files_lvl1}개 — 건(프로젝트)별 하위 폴더 없이 버전 파일이 한곳에 쌓이는 구조" if files_lvl1 else "",
        f"버전이 여러 개인 문서 묶음 {multi_version}개" if multi_version else "",
        f"폴더 이름 앞 상태 표시 사용: {', '.join(marked[:5])} — 의미를 물어 규칙으로 저장" if marked else "",
    ]
    return {
        "status_prefixed_folders": marked,
        "exists": True,
        "level1_folders": [d.name for d in level1][:30],
        "level2_examples": [f"{d.parent.name}/{d.name}" for d in level2][:20],
        "docs_directly_in_client_folders": files_lvl1,
        "date_prefixed_subfolders": date_named_l2,
        "client_folders_with_multiple_versions": multi_version,
        "layout_guess": guess,
        "observations": [o for o in obs if o],
    }
