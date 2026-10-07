"""이름 붙은 디자인 프리셋. ~/.beantal-kit/configs/bean-proposal/designs/<이름>.json

프리셋 한 개 = 참고 제안서에서 가져온 모양(글꼴 · 색 · 헤더 위치 · design 옵션).
render --design <이름> 이면 config 위에 프리셋을 덮고, --color 로 고객사 색만 바꿔 쓴다.
"""
import json

from .setup import CONFIG_PATH

DESIGNS_DIR = CONFIG_PATH.parent / "designs"
MERGE_KEYS = ("fonts", "colors", "header", "design", "slide_size_cm")


def list_designs():
    out = []
    for p in sorted(DESIGNS_DIR.glob("*.json")) if DESIGNS_DIR.exists() else []:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            out.append({"name": p.stem, "error": str(e)})
            continue
        out.append({"name": d.get("name", p.stem), "description": d.get("description", ""),
                    "source": d.get("source", ""), "color_policy": d.get("color_policy", "")})
    return out


def load_design(name):
    p = DESIGNS_DIR / f"{name}.json"
    if not p.exists():
        names = [d["name"] for d in list_designs()]
        raise FileNotFoundError(f"디자인 '{name}' 없음. 있는 것: {', '.join(names) or '(없음)'}")
    return json.loads(p.read_text(encoding="utf-8"))


def save_design(name, data):
    DESIGNS_DIR.mkdir(parents=True, exist_ok=True)
    data = {**data, "name": name}
    p = DESIGNS_DIR / f"{name}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return p


def apply_design(cfg, design, colors=None):
    """config(proposal 부분) 위에 프리셋을 덮고, colors(dict) 로 색을 마지막에 바꾼다."""
    merged = dict(cfg or {})
    for k in MERGE_KEYS:
        if k not in design:
            continue
        if isinstance(design[k], dict):
            base = dict(merged.get(k) or {}) if k != "header" else {}
            merged[k] = {**base, **design[k]}
        else:
            merged[k] = design[k]
    if colors:
        merged["colors"] = {**(merged.get("colors") or {}), **colors}
    return merged


def parse_colors(spec):
    """'primary=17469E,accent=4A7BD0' → dict"""
    out = {}
    for part in (spec or "").split(","):
        k, _, v = part.partition("=")
        if k.strip() and v.strip():
            out[k.strip()] = v.strip().lstrip("#")
    return out
