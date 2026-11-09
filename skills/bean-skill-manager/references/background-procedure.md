# 뒷단 절차

백그라운드 에이전트가 처음부터 끝까지 사람에게 묻지 않고 진행한다. 사용자는 GitHub 을 모른다고 전제한다. 어떤 결과든 사람이 GitHub 에서 처리해야 끝나는 상태로 남기지 않는다. `$CLI` 는 넘겨받은 skill 폴더의 `scripts/skill_manager_cli.mjs` 다.

입력: 단계(3 수정, 4 새 skill), 대상 skill, 일반화한 요구 한 문장.

## 끝나는 상태

모든 수리는 아래 넷 중 하나로 자동 종료된다.

| 상태 | 언제 | 처리 |
|---|---|---|
| `deployed` | 배포 판정 `deploy` | 마무리 후 이슈 닫기 |
| `awaiting` | 배포 판정 `push-only` | `queue-await` 로 기록. 다음 대화의 "재개" 절이 자동 처리 |
| `pc-only` | GitHub 권한이나 projectops 없음, 또는 실행 검증이 불가능한 새 skill | 이 PC에만 반영. `queue-done` |
| `abandoned` | 고치지 못함 | worktree 정리, 푸시 없음, 이슈는 라벨 `취소`로 닫기, `queue-done`. 앞단에 실패 한 줄 |

## 지키는 것

- 수정이 실패하면 원인을 고쳐 최대 2회 다시 시도한 뒤 `abandoned` 로 끝낸다. 대상: `npm run check`, `npm test`, 샘플 검증, rebase 충돌, 호환 규칙 위반, 제거할 수 없는 민감 정보.
- 대상이 `bean-skill-manager` 또는 `hooks/` 면 바로 `abandoned` (이유: 자동 수리가 자기 안전장치를 고치면 안 된다).
- force push, `git reset --hard`, `git stash` 는 쓰지 않는다 (이유: 같은 레포의 다른 작업이 사라진다).
- PowerPoint 를 여는 명령(`read`, `review`, `snapshot`, `edit`, `profile`)을 뒷단에서 쓰지 않는다 (이유: 사용자가 작업 중인 PowerPoint 와 충돌한다).
- 사용자의 제안서 폴더를 읽거나 쓰지 않는다. 임시 파일은 시스템 임시 폴더에만 만든다.
- 어떤 경우든 마지막에 `unlock` 한다 (성공·실패 공통).

## 순서

1. **등록·잠금**: 요구를 JSON 파일(`summary`, `level`, `skill`)로 저장해 `queue-add --request-file <파일>` 하고 `id` 를 기억한다. `lock` 이 `busy` 면 여기서 끝낸다 (진행 중인 작업이 끝나면 대기열을 이어서 처리한다).
2. **상태**: `status`. `ready` 가 아니거나 `hasRepository` 가 false 면 끝낸다 (다음 대화에서 재개). `hasProjectops` 가 false 거나 GitHub 호출이 권한 오류면 이슈와 푸시 없이 4~7단계만 하고 `pc-only` 로 끝낸다.
3. **이슈**: 요구를 이슈 본문으로 정리해 시스템 임시 폴더에 저장하고 `scan --file <파일>` 한다. `sensitive_found` 면 일반화해 다시 검사한다. 통과하면 `pro-github` 로 등록한다. 라벨 `작업중`, `자동수리`, 담당자는 config 의 `maintainer_github`. 응답의 `branch`, `commit_template` 을 기억한다.
4. **작업 공간**: `pro-init-worktree` 로 `--base origin/develop` worktree 를 만든다. 레포 원본 폴더는 건드리지 않는다.
5. **수정**: `references/skill-standard.md` 를 따라 고치거나 만든다. `skills/bean-*/` 밖은 건드리지 않는다.
6. **검사**: worktree 에서 `npm run check`, `npm test`.
   - 기존 skill 의 결과물이 바뀌는 수정: 이 폴더의 `references/verify/<skill>.md` 또는 대상 skill 의 `references/verify.md` 를 따라 샘플을 실행한다. 검증 문서가 없으면 대상 skill 의 `references/verify.md` 를 만들어 실행한다.
   - 새 skill: **`SKILL.md` 절차대로 가상 입력으로 실제로 한 번 실행**해 결과가 `references/verify.md` 의 통과 기준을 만족해야 한다. 가능하면 만든 에이전트가 아닌 새 에이전트가 `SKILL.md` 만 읽고 실행한다.
   - 통과하면 `verified=true`. 환경이 없어 실행할 수 없으면 `verified=false` (새 skill 은 7단계 후 `pc-only`).
7. **PC 반영**: `apply-cache --skill <skill> --source "<worktree>/skills/<skill>" --files <skill 폴더 기준 변경 파일을 쉼표로>`. 새 skill 은 `--files` 없이 실행한다. 대화 중에는 캐시를 바꾸지 않고 저장만 하며, 다음 새 대화가 시작될 때 반영된다.
8. **민감 정보 재검사**: 변경 경로만 명시해 `git add` 한 뒤 `git diff --cached` 출력을 시스템 임시 폴더의 파일로 저장해 `scan` 한다.
9. **커밋**: `pro-commit` 으로 커밋한다. 메시지는 3단계의 `commit_template` 형식을 따른다.
10. **통합·푸시**:
    - `git fetch origin` 후 `git rebase origin/develop`
    - `git log origin/develop..origin/main` 에 내용이 있으면 `git merge origin/main` (이유: 릴리스 버전 커밋이 main 에만 있어 생략하면 다음 배포가 실패한다)
    - `BASE=$(git rev-parse origin/develop)` 를 기록하고 `git push origin HEAD:develop`
    - non-fast-forward 면 fetch, rebase 후 `BASE` 를 다시 기록해 재시도
11. **배포 판정**: `release-decision --own-commits <git rev-list BASE..HEAD 를 쉼표로> --checks-passed true --verified <true|false>`.
12. **결과 처리**:
    - `deploy`: 레포의 `develop` 기준으로 `pro-changelog-deploy` 를 실행한다. 릴리스 노트는 자동 생성을 고른다. 승인 대기로 멈추면 `pro-github` `create-pr` 로 head `develop`, base `main`, 빈 본문 PR 을 만든다 (워크플로우가 노트를 채우고 automerge 한다). 성공하면 `record-deploy`.
    - `push-only`: `queue-await --id <id> --own-commits <커밋> --issue <번호> --reason <reason>` 후 이슈에 사유를 댓글로 남긴다. 사람에게 처리를 요청하지 않는다.
13. **마무리**: `deployed` 면 `pro-report` 로 보고서를 남기고 `pro-github finish-issue` 로 닫은 뒤 `queue-done`, worktree 제거. `unlock` 후 `queue-list` 의 `pending` 이 남아 있으면 1단계의 `queue-add` 없이 2단계부터 이어서 처리한다.

## 재개

새 대화가 시작될 때 대기 건이 있으면 hook 안내로 실행된다. `lock` 을 잡고 `queue-list` 를 읽는다.

- `pending`: 순서의 2단계부터 처리한다.
- `awaiting`: 건마다 `git fetch origin` 후 `is-released --own-commits <커밋>`.
  - `released`: 이미 다른 배포에 포함됐다. 이슈를 닫고 `queue-done`.
  - `not_released`: `release-decision` 을 다시 판정한다. `deploy` 면 순서의 12·13단계를 진행하고, `push-only` 면 그대로 둔다.

## 호환 규칙

- config 키는 추가만 한다. 이름 변경·삭제 금지. 새 키에는 기본값을 둔다.
- CLI 명령과 인자, `outline.md` 문법, 디자인 프리셋 형식은 기존 입력을 계속 받는다.
- 기존 결과물 모양이 바뀌면 옵션으로 추가하고 기본값을 유지한다. 명백한 버그 수정은 예외다.
- 고객사명, 하드코딩된 수치, 특정 건 분기를 skill 에 넣지 않는다.
- 외부 의존성을 새로 요구하지 않는다. macOS·Windows 양쪽에서 동작해야 한다.

위반을 고칠 수 없으면 배포하지 않는다. 개인 설정으로 처리할 수 있으면 앞단에 그렇게 돌려준다.

## 보고

앞단에 돌려주는 값: `outcome` (`deployed` | `awaiting` | `pc-only` | `abandoned`), 사유 한 줄. 민감 정보와 토큰은 넣지 않는다.

레포 구조와 업데이트 전달 방식은 `references/repo-guide.md` 를 본다.
