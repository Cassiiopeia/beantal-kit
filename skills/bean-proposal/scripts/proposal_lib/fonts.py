"""설치된 글꼴 확인 (Windows: 레지스트리, macOS: 글꼴 폴더 파일명). 없으면 대체 글꼴을 고른다."""
import os
import platform
import re
from pathlib import Path

FALLBACKS = {
    "title": ["Pretendard ExtraBold", "Pretendard SemiBold", "Noto Sans KR Black", "맑은 고딕"],
    "body": ["Pretendard Light", "Noto Sans KR Light", "맑은 고딕"],
    "emphasis": ["Pretendard Medium", "Noto Sans KR Medium", "맑은 고딕"],
    "label": ["Pretendard SemiBold", "Noto Sans KR Medium", "맑은 고딕"],
}
_cache = None


def installed():
    global _cache
    if _cache is not None:
        return _cache
    names = set()
    if platform.system() == "Windows":
        import winreg
        for root, path in ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"),
                           (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts")):
            try:
                with winreg.OpenKey(root, path) as k:
                    i = 0
                    while True:
                        try:
                            n, _, _ = winreg.EnumValue(k, i)
                        except OSError:
                            break
                        names.add(re.sub(r"\s*\((TrueType|OpenType)\)$", "", n).strip())
                        i += 1
            except OSError:
                pass
    else:
        for d in (Path.home() / "Library" / "Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path.home() / ".fonts"):
            if d.exists():
                names.update(f.stem.replace("-", " ") for f in d.iterdir())
    _cache = names
    return names


def is_installed(font):
    if not font:
        return False
    key = re.sub(r"[\s\-]", "", font).lower()
    for n in installed():
        for part in n.split("&"):
            if re.sub(r"[\s\-]", "", part).lower().startswith(key):
                return True
    return False


def resolve(fonts):
    """{역할: 글꼴} → (실제 쓸 글꼴, 대체 내역)."""
    out, swaps = {}, []
    if not installed():          # 확인 수단이 없으면 그대로 둔다
        return dict(fonts), swaps
    for role, font in fonts.items():
        if is_installed(font):
            out[role] = font
            continue
        alt = next((f for f in FALLBACKS.get(role, []) if is_installed(f)), font)
        out[role] = alt
        swaps.append({"role": role, "wanted": font, "used": alt})
    return out, swaps
