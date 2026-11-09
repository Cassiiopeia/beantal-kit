# 레포 구조와 업데이트 전달

## 구조

| 경로 | 역할 | 자동 수리 |
|---|---|---|
| `skills/bean-*/` | skill 본체 (SKILL.md, references, scripts, config.json.example) | 대상 (`bean-skill-manager` 제외) |
| `hooks/` | 플러그인 hook | 제외 |
| `src/`, `bin/` | 설치기 | 제외 |
| `scripts/` | `new-skill`, `check-skills`, `sync-version` | 실행만 |
| `.claude-plugin/`, `.codex-plugin/`, `.agents/` | 마켓플레이스 매니페스트 | 제외 |
| `version.yml` | 버전 단일 기준. projectops 가 관리 | 직접 수정 금지 |

## 브랜치와 배포

- 작업은 `develop` 에 통합하고, `develop` 에서 `main` 으로 가는 릴리스 PR 로 배포한다.
- 릴리스 워크플로우는 head 가 `develop` 인 PR 만 automerge 한다. `main` 기준 hotfix 는 쓰지 않는다.
- `main` 에 push 되면 버전이 올라가고 매니페스트가 동기화되며 npm 에 배포된다. 커밋 제목의 `feat` 는 minor, 그 외는 patch 를 올린다.
- 공개 레포다. 고객사 자료, 토큰, 내부 주소를 넣지 않는다.

## 사용자에게 전달되는 방식

1. Claude Code 는 플러그인을 `<Claude 설정 폴더>/plugins/cache/<마켓플레이스>/beantal-kit/<버전>/` 에 버전별로 보관한다.
2. 어느 폴더를 쓰는지는 `<Claude 설정 폴더>/plugins/installed_plugins.json` 의 `installPath` 에 있다. Claude 설정 폴더는 `CLAUDE_CONFIG_DIR`, 없으면 `~/.claude` 다.
3. 새 버전이 배포되어야 다른 사용자가 받는다. 그 전에 지금 PC에서 쓰려면 `apply-cache` 로 현재 `installPath` 에 덮어쓴다.
4. 덮어쓴 내용은 새 대화부터 적용된다. 플러그인이 업데이트되면 새 폴더가 생기므로, 공용 반영이 안 된 수정은 사라진다. 그래서 대기 건은 대기열에 남겨 재시도한다.
5. 사용자 설정은 `~/.beantal-kit/` 에 있어 업데이트와 무관하다.
