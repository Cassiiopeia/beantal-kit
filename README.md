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

## skill 목록

| skill | 하는 일 | 이렇게 말하면 자동으로 쓰인다 |
|---|---|---|
| `bean-proposal` | 제안서 PPT 컨설턴트: RFP 분석, 구성 조언, PPT 초안 제작, 제출 전 점검·비판 | "RFP 왔어", "제안서 만들어줘", "목차 잡아줘", "이 제안서 검토해줘", "제출 전에 점검해줘" |
| `bean-issue-first` | 작업을 GitHub 이슈로 시작하고 완료 증거를 댓글로 남긴다 | "이슈 먼저", "이슈화해서 진행", "이슈 완료 처리" |

자연어로 말하면 Claude 가 skill 설명을 보고 알아서 고른다. 확실하게 부르고 싶으면 슬래시 명령을 쓴다: `/beantal-kit:bean-proposal 이 RFP로 제안서 구성 잡아줘`

## bean-proposal 사용법

### 이렇게 말하면 된다

| 하고 싶은 것 | 예시 |
|---|---|
| RFP 로 제안서 시작 | "RFP 받았어. 이걸로 제안서 만들어줘" + 파일 경로 또는 첨부 |
| 방향만 조언 | "이 RFP 어떻게 구성하면 좋을지 조언해줘" |
| 구성안까지만 | "목차랑 장별 메시지까지만 잡아줘" |
| 일부 페이지만 | "운영 프로세스 섹션만 만들어줘", "11~12페이지만 다시 만들어줘" |
| 기존 제안서 비판 | "이 제안서 객관적으로 비판해줘" + pptx 경로 |
| 제출 전 점검 | "제출 전에 점검해줘" — 메모 잔존, 수치 불일치, 목차 번호, 빠진 요건, 오타 |
| 예시처럼 만들기 | "이 PPT 스타일로 다른 고객사 제안서 만들어줘" |
| 자료 없이 시작 | "RFP 는 없고 미팅만 했어. 제안서 만들어줘" → 질문 몇 개로 시작 |

### 처음 한 번 하는 일

1. 필요 환경을 확인한다: Python 3.10+, (Windows) PowerPoint. 부족한 라이브러리는 Claude 가 설치 명령을 보여 주고 동의를 받는다.
2. **작업 루트 폴더를 고른다.** Claude 가 이 PC 에서 제안서가 모여 있는 폴더를 찾아 추천한다 (다운로드 · 클라우드 동기화 폴더는 비추천). 새 폴더를 만들어도 된다.
3. 기존 정리 규칙(고객사별 폴더 등)을 확인한다. 이후 프로젝트는 같은 규칙으로 만들어진다: `<루트>/<고객사>/<YYMMDD>_<건명>/`
4. 기존 제안서가 있으면 그 덱에서 하우스 스타일(크기 · 글꼴 · 색 · 헤더 위치)을 뽑아 저장한다.
5. 회사 수치(센터 수, 면적, 매출 등)를 기준일과 함께 확정한다. 확정 전에는 제안서에 `[확인 필요]` 로 남는다.

### 진행 방식

```text
접수 → 분석(요건 목록) → [승인] → 질의 · 부서 확인(선택) → 설계(방향 · 목차 · 장별 메시지) → [승인]
     → 제작(pptx) → [승인] → 점검(자동 점검 + 화면 확인 + 6축 채점) → [승인] → 제출 체크리스트
```

- 승인 단계마다 Claude 가 결과를 보여 주고 확인을 받는다. 방향이 틀린 채 버전만 쌓이지 않게 한다.
- 덱의 원본은 `02_설계/outline.md` 다. 수정은 여기서 하고 다시 만든다. 버전은 `v01`, `v02` … 로만 쌓인다.
- 모르는 값은 지어내지 않고 `[확인 필요: …]` 로 남긴다. 점검에서 치명으로 잡히므로 제출 전에 반드시 채운다.

### 프로젝트 폴더

```text
<프로젝트>/
├── project.json   00_입력/   01_분석/requirements.md   02_설계/outline.md
└── 04_제작/<건명>_v01.pptx   05_점검/review_v01.md   06_제출/checklist.md
```

### 사내 DRM(문서 보안)이 있는 PC

- pptx · docx · xlsx 는 저장하면 자동으로 암호화된다. **정상이다.** 이 skill 은 DRM pptx 를 PowerPoint 를 통해 읽기 전용으로 열어 읽고, 복호화 사본을 만들지 않는다.
- 작업 상태(요건, 구성안, 점검 결과)는 암호화되지 않는 md/json 으로 남는다.
- DRM 이 걸린 docx · xlsx · pdf 는 아직 직접 읽지 않는다. 필요한 부분을 대화로 붙여 주거나 승인된 평문본을 지정한다.
- DRM 파일 읽기는 Windows + PowerPoint 에서만 된다. macOS 에서는 평문 파일만 다룬다.

### 저장 위치 (공개 레포에 올라가지 않음)

```text
~/.beantal-kit/shared/company/company.json        회사 프로필 (수치마다 기준일 · 출처)
~/.beantal-kit/shared/company/documents.json      공통 제출 서류 경로 (사업자등록증 등)
~/.beantal-kit/configs/bean-proposal/config.json  작업 루트, 정리 규칙, 하우스 스타일
~/.beantal-kit/configs/bean-proposal/references.json  참고 제안서 목록
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
## 최신 버전 : v0.5.0 (2026-10-06)

[전체 버전 기록 보기](CHANGELOG.md)
