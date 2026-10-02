"""프로젝트 폴더 생성과 상태 조회. 모든 산출물은 평문(md/json)이다."""
import datetime as dt
import json
import re
from pathlib import Path

DIRS = ["00_입력", "01_분석", "02_설계", "03_부서회신", "04_제작", "05_점검", "06_제출"]
STAGES = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]

REQ_TEMPLATE = """# 요건 목록

> ID 는 `R-<분류약어>-<nn>` (WRT 작성요청 · SOW 업무범위 · SLA · EVL 평가 · SUB 제출물 · PRC 견적 · SCH 일정 · ETC 기타). 삭제해도 번호를 재사용하지 않는다.
> 대응: 즉시 / 협의 / 확인필요 / 불가

| ID | 출처 | 분류 | 요약 | 배점 | 대응 | 담당 | 슬라이드 | 메모 |
|---|---|---|---|---|---|---|---|---|
"""

STRATEGY_TEMPLATE = """# 제안 방향

## 고객 핵심 요구
-

## 평가 기준 (상위)
-

## 우리 강점 (회사 프로필·실적 인용)
-

## 제안 방향 3대 축
①
②
③

## 리스크와 대응
-

## 차별 포인트 (한 문장)
"""

OUTLINE_TEMPLATE = """# {title}
- 고객사: {client}
- 건명: {title}
- 날짜: {date}

## 01 · T01
- 메시지: [확인 필요: 표지 부제 — 핵심 약속 한 줄]

## 02 · T02
"""


def slug(s):
    s = re.sub(r"[\\/:*?\"<>|]", "", s).strip()
    return re.sub(r"\s+", "", s)[:40]


def init_project(root, client, title, due=None, today=None, layout="{client}/{yymmdd}_{title}"):
    today = today or dt.date.today()
    root = Path(root).expanduser()
    rel = layout.format(client=slug(client), yymmdd=f"{today:%y%m%d}", title=slug(title))
    pdir = root / Path(rel)
    pid = pdir.name
    if pdir.exists() and any(pdir.iterdir()):
        return {"ok": False, "code": "exists", "summary": f"이미 있는 프로젝트 폴더입니다: {pdir}", "path": str(pdir)}
    for d in DIRS:
        (pdir / d).mkdir(parents=True, exist_ok=True)
    project = {
        "schema": 1, "id": pid, "client": client, "title": title,
        "created": today.isoformat(), "due": due, "situation": None, "role": None,
        "stage": "S1", "gates": {g: None for g in ("G1", "G2", "G3", "G4", "G5")}, "skipped": [],
        "company_profile_asof": None, "versions": [],
    }
    (pdir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (pdir / "01_분석" / "requirements.md").write_text(REQ_TEMPLATE, encoding="utf-8")
    (pdir / "02_설계" / "strategy.md").write_text(STRATEGY_TEMPLATE, encoding="utf-8")
    (pdir / "02_설계" / "outline.md").write_text(
        OUTLINE_TEMPLATE.format(title=title, client=client, date=(due or today.isoformat()).replace("-", ".")), encoding="utf-8")
    return {"ok": True, "code": "created", "summary": f"프로젝트 폴더를 만들었습니다: {pdir}", "path": str(pdir), "id": pid}


def status(pdir):
    pdir = Path(pdir).expanduser()
    pj = pdir / "project.json"
    if not pj.exists():
        return {"ok": False, "code": "not_project", "summary": f"project.json 이 없습니다: {pdir}"}
    p = json.loads(pj.read_text(encoding="utf-8"))
    files = {}
    for d in DIRS:
        sub = pdir / d
        files[d] = sorted(x.name for x in sub.iterdir()) if sub.exists() else []
    decks = sorted((pdir / "04_제작").glob("*.pptx"))
    nxt = None
    m = re.search(r"_v(\d+)\.pptx$", decks[-1].name) if decks else None
    nxt = f"v{int(m.group(1)) + 1:02d}" if m else "v01"
    return {"ok": True, "code": "ok", "summary": f"{p['client']} / {p['title']} — 단계 {p['stage']}", "project": p, "files": files, "next_version": nxt}


def record_version(pdir, file, change):
    pj = Path(pdir) / "project.json"
    p = json.loads(pj.read_text(encoding="utf-8"))
    v = re.search(r"_(v\d+)\.pptx$", str(file))
    p["versions"].append({"v": v.group(1) if v else None, "date": dt.date.today().isoformat(), "file": str(file), "change": change})
    pj.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
