# beantal-kit 규칙

빈털 전용 `bean-*` skill 모음 레포. `npx beantal-kit` 이 Claude Code·Codex 마켓플레이스를 등록한다.

## 규칙

1. 버전의 단일 기준은 `version.yml`이며 projectops가 관리한다. `package.json`, `.claude-plugin/*.json`, `.codex-plugin/plugin.json`의 version은 `PROJECT-PLUGIN-VERSION-SYNC` 워크플로우(`scripts/sync-version.js`)가 동기화하므로 직접 고치지 않는다. 새 skill이 사용자에게 전달되려면 버전이 올라가야 한다(Claude Code는 플러그인을 버전별로 캐시).
2. skill 추가·수정은 `skills/bean-<이름>/SKILL.md`만 건드린다(설치기 코드 수정 금지). 추가 후 `npm run check` 통과가 필수다.
3. 새 skill은 `npm run new-skill <이름>`으로 만들고, 폴더명 = frontmatter `name` = `bean-` 접두사를 지킨다. `description`에는 트리거 문구를 구체적으로 쓴다.
4. 새 에이전트 지원은 `src/adapters/<id>.js` 추가 + `registry.js` 1줄. 오케스트레이터(`src/commands/`, `src/cli.js`)는 수정하지 않는다.
5. 의존성을 추가하지 않는다(Node 내장 모듈만, Node >= 20.12). 어댑터는 예외를 던지지 않고 `io`(`which/run/home/log`)로만 외부와 통신한다.
6. 민감 정보(토큰, 내부 호스트, 서버 접속 정보, 회사 기본 정보, 고객사 제안서·보고서 원본)는 이 공개 레포에 넣지 않는다. 회사 기본 정보는 사용자 PC의 로컬 프로필(`~/.beantal/`)에만 두고, skill은 이를 읽기만 한다. `skills/` 안에 pptx, pdf, zip 등 문서 파일이 있으면 `npm run check`가 실패한다. 필요해지면 별도 private 레포를 만들어 `--marketplace owner/repo`(또는 `src/adapters/marketplaces.js`)로 추가 등록한다.
7. 테스트는 `npm test`(어댑터는 stub `io`). 커밋·push는 사용자가 커밋 컨벤션을 주거나 명시적으로 요청할 때만 한다. 커밋 메시지에 AI 작성 흔적을 남기지 않는다.
8. **skill 설정은 플러그인 폴더 밖 `~/.beantal-kit/` 에만 둔다.** Claude Code 는 플러그인을 버전별 캐시 폴더에 두고 업데이트하면 폴더가 바뀌므로, 플러그인 폴더 안에 두면 설정이 사라진 것처럼 보인다.
   - skill별 설정: `~/.beantal-kit/configs/<skill폴더명>/config.json`, 여러 skill 이 공유하는 정보(회사 기본 정보 등): `~/.beantal-kit/shared/`
   - 레포에는 읽기 전용 템플릿 `skills/<skill>/config.json.example` 만 둔다 (값은 비움, 최상위 키는 skill 이름에서 `bean-` 을 뺀 이름, 칸의 의미는 `_comment_*` 로 설명, 필수 칸은 `_required`). `skills/` 안의 `config.json` 은 `npm run check` 가 실패시킨다.
   - 값 결정 순서: 요청에서 직접 준 값, 환경변수, config.json, example 기본값, (필수인데 없으면) 질문.
   - 설정 생성과 보충은 Claude 가 대화로 한다 (비개발자 사용자 전제): 한 번에 한 질문, 기존 값은 덮어쓰지 않고 빠진 키만 보충, 비밀번호와 토큰은 출력 시 마스킹.
   - `npx beantal-kit uninstall` 은 `~/.beantal-kit/` 를 절대 지우지 않는다 (설치기 코드는 파일 삭제 함수를 쓰지 않는다).
   - 설정이 필요한 skill 은 `npm run new-skill <이름> -- --config` 로 만든다 (규약을 지키는 SKILL.md 설정 섹션과 example 뼈대 생성).
9. **skill 은 macOS 와 Windows 양쪽에서 똑같이 동작해야 한다.** 사용자는 비개발자일 수 있다.
   - 홈 폴더는 `~`, `$HOME`, `%USERPROFILE%` 같은 환경 기준으로만 표기한다. 드라이브 문자나 사용자 이름이 든 OS 고정 절대 경로(`C:...`, `/Users/...`, `/home/...`)는 `npm run check` 가 실패시킨다.
   - 파일 조작은 가능한 한 agent 도구(Read, Write, Edit)로 하고, 셸 명령은 macOS 와 Windows(Git Bash, PowerShell)에서 같게 동작하는 것만 쓴다.
   - 외부 실행 환경(Python, Node 등)이 필요하면 SKILL.md 에 필요 조건, 확인 명령, 없을 때의 안내를 적는다.
   - 파일은 UTF-8, 줄바꿈 LF, 한글 파일명과 공백 경로는 따옴표로 감싼다. `new-skill` 뼈대에 이 규칙이 들어 있다.
   - 설치기와 검증은 GitHub Actions(`BEANTAL-CI-MATRIX`)가 Ubuntu, macOS, Windows 에서 교차 검증한다.

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
