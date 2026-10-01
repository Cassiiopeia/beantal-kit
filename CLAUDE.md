# beantal-kit 규칙

빈털 전용 `bean-*` skill 모음 레포. `npx beantal-kit` 이 Claude Code·Codex 마켓플레이스를 등록한다.

## 규칙

1. 버전의 단일 기준은 `version.yml`이며 projectops가 관리한다. `package.json`, `.claude-plugin/*.json`, `.codex-plugin/plugin.json`의 version은 `PROJECT-PLUGIN-VERSION-SYNC` 워크플로우(`scripts/sync-version.js`)가 동기화하므로 직접 고치지 않는다. 새 skill이 사용자에게 전달되려면 버전이 올라가야 한다(Claude Code는 플러그인을 버전별로 캐시).
2. skill 추가·수정은 `skills/bean-<이름>/SKILL.md`만 건드린다(설치기 코드 수정 금지). 추가 후 `npm run check` 통과가 필수다.
3. 새 skill은 `npm run new-skill <이름>`으로 만들고, 폴더명 = frontmatter `name` = `bean-` 접두사를 지킨다. `description`에는 트리거 문구를 구체적으로 쓴다.
4. 새 에이전트 지원은 `src/adapters/<id>.js` 추가 + `registry.js` 1줄. 오케스트레이터(`src/commands/`, `src/cli.js`)는 수정하지 않는다.
5. 의존성을 추가하지 않는다(Node 내장 모듈만, Node >= 20.12). 어댑터는 예외를 던지지 않고 `io`(`which/run/home/log`)로만 외부와 통신한다.
6. 민감 정보(토큰, 내부 호스트, 서버 접속 정보)는 이 공개 레포에 넣지 않는다. 필요해지면 별도 private 레포를 만들어 `--marketplace owner/repo`(또는 `src/adapters/marketplaces.js`)로 추가 등록한다.
7. 테스트는 `npm test`(어댑터는 stub `io`). 커밋·push는 사용자가 커밋 컨벤션을 주거나 명시적으로 요청할 때만 한다. 커밋 메시지에 AI 작성 흔적을 남기지 않는다.

## 명령

| 용도 | 명령 |
|------|------|
| 테스트 | `npm test` |
| skill 검증 | `npm run check` |
| skill 생성 | `npm run new-skill <이름>` |
| 설치 흐름 점검 | `node bin/beantal-kit.js --dry-run` |

## 구조

- `skills/` : skill 저장소(Claude Code·Codex 공유)
- `src/adapters/` : 에이전트별 `detect/apply/remove` 구현 + `registry.js`
- `src/commands/`, `src/cli.js` : 어댑터를 순회하는 오케스트레이터
- `scripts/` : `new-skill`, `check-skills`
- `.claude-plugin/`, `.codex-plugin/`, `.agents/` : 마켓플레이스 매니페스트
- `.github/workflows/PROJECT-NODE-NPM-PUBLISH.yaml` : npm 배포 (`NPM_TOKEN` secret)
- `docs/` : 로컬 전용 설계·참고 문서(.gitignore)
