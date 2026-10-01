# beantal-kit

빈털 전용 Claude Code·Codex skill 모음(`bean-*`)과 설치기.

## 설치

```bash
npx beantal-kit            # Claude Code, Codex 마켓플레이스 등록/업데이트 (멱등)
npx beantal-kit status     # 상태 확인
npx beantal-kit uninstall  # 제거
```

| 옵션 | 설명 |
|------|------|
| `--only claude,codex` | 지정한 에이전트만 처리 |
| `--marketplace owner/repo[:name]` | 추가 마켓플레이스 등록 (private 레포 등, 반복 가능) |
| `--dry-run` | 실행할 명령만 출력 (조회성 명령만 실제 실행) |

설치 후 업데이트는 각 에이전트의 플러그인 CLI가 처리한다. CLI가 없는 에이전트는 건너뛰고 수동 명령을 안내한다.

수동 설치:

```bash
claude plugin marketplace add Cassiiopeia/beantal-kit
claude plugin install beantal-kit@beantal-kit-marketplace --scope user
codex plugin marketplace add Cassiiopeia/beantal-kit
```

## skill 추가

```bash
npm run new-skill my-tool   # skills/bean-my-tool/SKILL.md 생성
npm run check               # frontmatter, name, 접두사 검증
```

`SKILL.md`만 추가하고 push 하면 된다. 설치기 코드는 수정하지 않는다.

## 에이전트 추가 (antigravity, pi, cursor 등)

1. `src/adapters/<id>.js` 에 `{ id, label, order, strategy, detect, apply, remove, manualHint }` 객체를 만든다 (`src/adapters/adapter.js` 계약 참고).
2. `src/adapters/registry.js` 배열에 1줄 추가한다.

마켓플레이스가 없는 에이전트는 `strategy: "copy"` 어댑터로 skill 폴더를 복사하는 방식으로 붙인다.

## 배포

- `main` push 시 `PROJECT-NODE-NPM-PUBLISH` 워크플로우가 npm 에 배포한다 (이미 배포된 버전은 건너뜀).
- 필요 Secret: `NPM_TOKEN` (npm 토큰, publish 권한).
- **새 skill 이 사용자에게 전달되려면 버전이 올라가야 한다.** Claude Code 플러그인은 버전별로 캐시되므로 version 이 같으면 `plugin update` 가 새 내용을 가져오지 않을 수 있다. push 후 반드시 버전을 올린다.
- 버전은 projectops 가 관리한다. 직접 올려야 하면 `package.json`, `.claude-plugin/*.json`, `.codex-plugin/plugin.json` 의 version 을 함께 맞춘다.

## private skill

회사 비공개 skill 은 이 공개 레포에 넣지 않는다. 별도 private 레포(같은 구조)를 만들고 `npx beantal-kit --marketplace owner/private-repo` 로 함께 등록한다. Claude Code 는 로컬 git 인증을 쓰며 자동 업데이트에는 `GITHUB_TOKEN` 이 필요하다.
