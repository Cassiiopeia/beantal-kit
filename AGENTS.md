# beantal-kit Agent Instructions

이 레포는 에이전트 skill 패키지다. `skills/` 가 Claude Code와 Codex가 공유하는 skill 저장소다.

## Skill 사용

응답하기 전에 적용할 skill이 있는지 확인한다. skill 본문 위치:

```text
skills/bean-{이름}/SKILL.md
```

적용되는 skill이 있으면 해당 `SKILL.md`를 읽고 그대로 따른다. Codex는 슬래시 UI가 없어도 이 파일을 직접 읽으면 된다.

## 설치

권장: 마켓플레이스 등록

```bash
npx beantal-kit
# 또는
codex plugin marketplace add Cassiiopeia/beantal-kit
```

폴백: 직접 clone 후 심링크

```bash
git clone https://github.com/Cassiiopeia/beantal-kit.git ~/.codex/beantal-kit
mkdir -p ~/.agents/skills
ln -s ~/.codex/beantal-kit/skills ~/.agents/skills/beantal-kit
```

## 작업 규칙

규칙은 `CLAUDE.md`를 따른다. push는 사용자가 명시적으로 요청할 때만 한다.
