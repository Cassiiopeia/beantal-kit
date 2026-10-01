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

## skill 설정 (회사 정보 등)

설정이 필요한 skill 은 `npm run new-skill <이름> -- --config` 로 만든다. 설정은 **플러그인 밖 `~/.beantal-kit/`** 에만 저장된다.

```text
~/.beantal-kit/configs/<skill>/config.json   skill별 설정
~/.beantal-kit/shared/                        여러 skill 이 함께 쓰는 정보 (회사 기본 정보 등)
```

- Claude Code 는 플러그인을 버전별 캐시 폴더에 두고 업데이트하면 폴더가 바뀌므로, 플러그인 안에 두면 설정이 사라진 것처럼 보인다. 밖에 두면 **업데이트, 재설치, 제거 후에도 보존**된다. `npx beantal-kit uninstall` 도 이 폴더는 지우지 않는다.
- 설정이 없으면 Claude 가 질문으로 만들어 준다. 직접 파일을 만들 필요가 없다.
- 레포의 `config.json.example` 은 값이 빈 템플릿이다. 실제 값(회사 정보, 토큰)은 레포에 올라가지 않는다.

## 에이전트 추가 (antigravity, pi, cursor 등)

1. `src/adapters/<id>.js` 에 `{ id, label, order, strategy, detect, apply, remove, manualHint }` 객체를 만든다 (`src/adapters/adapter.js` 계약 참고).
2. `src/adapters/registry.js` 배열에 1줄 추가한다.

마켓플레이스가 없는 에이전트는 `strategy: "copy"` 어댑터로 skill 폴더를 복사하는 방식으로 붙인다.

## 배포

### 브랜치와 릴리스 흐름

```text
작업 → develop (커밋 제목 형식 준수) → develop→main 릴리스 PR → 버전 증가 → 동기화 → npm 배포
```

1. `develop` 에 커밋한다. 제목은 `이슈제목 : feat|fix|docs|... : 설명 이슈URL` 형식이다.
2. 릴리스 PR(develop → main)을 만든다 (`/pro-changelog-deploy`). 머지 시 릴리스 구간 커밋 제목으로 버전이 정해진다.
   - `feat` 포함 → minor, `fix` 등만 → patch, `feat!` 처럼 `!` 표기 → major
3. `PROJECT-PLUGIN-VERSION-SYNC` 가 `package.json`, `.claude-plugin/*.json`, `.codex-plugin/plugin.json` 을 `version.yml` 에 맞춘다.
4. `PROJECT-NODE-NPM-PUBLISH` 가 npm 에 배포한다 (이미 배포된 버전은 건너뜀).

### 알아둘 점

- `develop` 브랜치는 projectops 가 만들어 주지 않는다. 처음에 한 번 `git checkout -b develop && git push -u origin develop` 으로 만든다.
- `main` 에 직접 push 해도 publish 워크플로우는 실행되지만, 새 버전이 아니면 건너뛴다. 릴리스 PR 을 거치지 않은 직접 push 는 안전망(`PROJECT-VERSION-CONTROL`)이 patch 만 올린다. 정식 배포는 릴리스 PR 로 한다.
- projectops 는 `common/` 워크플로우를 조건 없이 설치한다. 이 레포에서 쓰지 않는 `PROJECT-COMMON-PROJECTS-SYNC-MANAGER`(Projects 연동)는 삭제했으며, projectops 를 다시 실행하면 복원될 수 있으니 그때는 다시 지운다.
- 필요 Secret: `NPM_TOKEN` (npm 토큰, publish 권한). projectops 는 Secret 을 등록해 주지 않는다.
- **새 skill 이 사용자에게 전달되려면 버전이 올라가야 한다.** Claude Code 플러그인은 버전별로 캐시되므로 version 이 같으면 `plugin update` 가 새 내용을 가져오지 않을 수 있다.
- 버전의 단일 기준은 `version.yml` (projectops 가 관리). 수동 동기화는 `npm run sync-version`.

## private skill

회사 비공개 skill 은 이 공개 레포에 넣지 않는다. 별도 private 레포(같은 구조)를 만들고 `npx beantal-kit --marketplace owner/private-repo` 로 함께 등록한다. Claude Code 는 로컬 git 인증을 쓰며 자동 업데이트에는 `GITHUB_TOKEN` 이 필요하다.

---

<!-- AUTO-VERSION-SECTION: DO NOT EDIT MANUALLY -->
## 최신 버전 : v0.2.4 (2026-10-01)

[전체 버전 기록 보기](CHANGELOG.md)
