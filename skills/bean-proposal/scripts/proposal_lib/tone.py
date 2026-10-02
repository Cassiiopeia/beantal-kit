"""말투 규칙 (references/tone.md 와 같은 기준)."""
import re

# 거버닝 메시지 글자 수. 실측(2026 우수 사례): 평균 51~58자, 두 문장형 85~114자.
# 14pt · 폭 25.3cm 에서 한 줄 약 55자 → 2줄 상한 110자.
MSG_MIN, MSG_MAX = 25, 110
BULLET_MAX = 45                    # 본문 불릿 한 줄 최대 글자 수
POLITE_END = re.compile(r"(니다|습니다|겠습니다|드립니다|입니다)[.!]?$")
PLAIN_END = re.compile(r"(한다|된다|있다|없다|이다|하다|필요하다|가능하다|해야함|해야 함|할것|할 것)[.!]?$")
SUPERLATIVE = re.compile(r"(업계 최고|국내 최고|최초이자|유일한|완벽한|100% 보장)")


def check_message(msg):
    issues = []
    m = msg.strip()
    n = len(m)
    if n < MSG_MIN:
        issues.append(f"메시지가 짧습니다({n}자) — 결론과 근거가 함께 드러나게 {MSG_MIN}자 이상")
    if n > MSG_MAX:
        issues.append(f"메시지가 깁니다({n}자) — 2줄 이내 {MSG_MAX}자 이하로")
    if not POLITE_END.search(m):
        issues.append("메시지는 존댓말 서술형으로 끝내야 합니다 (~합니다 / ~하겠습니다 / ~입니다)")
    if SUPERLATIVE.search(m):
        issues.append("근거 없는 최상급 표현이 있습니다")
    return issues


def check_bullet(text):
    issues = []
    t = text.strip()
    if t.endswith("."):
        issues.append("본문 불릿은 마침표 없이 명사형으로 끝냅니다")
    if PLAIN_END.search(t):
        issues.append("본문이 반말 종결입니다 — 명사형(~수립, ~관리)으로")
    if len(t) > BULLET_MAX and not t.startswith("【"):
        issues.append(f"불릿이 깁니다({len(t)}자) — 한 줄 {BULLET_MAX}자 이하로 나누세요")
    return issues
