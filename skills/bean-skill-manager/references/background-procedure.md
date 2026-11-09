# 뒷단 절차

백그라운드 에이전트가 처음부터 끝까지 사람에게 묻지 않고 진행한다. `$CLI` 는 넘겨받은 skill 폴더의 `scripts/skill_manager_cli.mjs` 다.

입력: 단계(3 수정, 4 새 skill), 대상 skill, 일반화한 요구 한 문장.

## 멈추는 조건

아래에 걸리면 푸시와 배포를 하지 않는다. 이슈가 있으면 사유를 댓글로 남기고 라벨 `확인필요`를 붙인다. 어떤 경우든 마지막에 `unlock` 한다 (성공·실패 공통).

- `npm run check`, `npm test` 실패
- rebase 충돌을 양쪽 의도를 살려 해소할 수 없음
- 8절 호환 규칙 위반, 민감 정보를 제거할 수 없음
- 대상이 `bean-skill-manager` 또는 `hooks/` (이유: 자동 수리가 자기 안전장치를 고치면 안 된다)

force push, `git reset --hard`, `git stash` 는 쓰지 않는다 (이유: 같은 레포의 다른 작업이 사라진다).

## 순서

1. **잠금**: `node "$CLI" lock`. `busy` 면 요구를 JSON 파일(`summary`, `level`, `skill`)로 저장해 `queue-add --request-file <파일>` 하고 끝낸다.
2. **상태**: `node "$CLI" status`. `ready` 가 아니거나 `hasRepository` 가 false 면 `queue-add` 후 끝낸다. `hasProjectops` 가 false 거나 GitHub 호출이 권한 오류면 이슈 없이 4, 6단계와 7단계까지만 하고 `queue-add` 한다.
3. **이슈**: 요구를 이슈 본문으로 정리해 시스템 임시 폴더에 저장하고 `scan --file <파일>` 한다. `sensitive_found` 면 일반화해 다시 검사한다. 통과하면 `pro-github` 로 등록한다. 라벨 `작업중`, `자동수리`, 담당자는 config 의 `maintainer_github`. 응답의 `branch`, `commit_template` 을 기억한다.
4. **작업 공간**: `pro-init-worktree` 로 `--base origin/develop` worktree 를 만든다. 레포 원본 폴더는 건드리지 않는다.
5. **수정**: `references/skill-standard.md` 를 따라 고치거나 만든다. `skills/bean-*/` 밖은 건드리지 않는다.
6. **검사**: worktree 에서 `npm run check`, `npm test`. 결과물이 바뀌는 수정이면 이 폴더의 `references/verify/<skill>.md` 또는 대상 skill 의 `references/verify.md` 를 따라 샘플을 실행한다. 샘플이 돌았는데 실패하면 고쳐서 다시 돌리고, 끝내 실패하면 멈춘다. 검증 문서가 없거나 환경이 없어 못 돌렸으면 `verified=false` 로 진행한다. 새 skill 은 기존 결과물에 영향이 없으므로 검사와 `skill-standard.md` 점검을 통과하면 `verified=true` 다.
7. **PC 반영**: `node "$CLI" apply-cache --skill <skill> --source "<worktree>/skills/<skill>" --files <skill 폴더 기준 변경 파일을 쉼표로>`. 새 skill 은 `--files` 없이 실행한다.
8. **민감 정보 재검사**: 변경 경로만 명시해 `git add` 한 뒤 `git diff --cached` 출력을 시스템 임시 폴더의 파일로 저장해 `scan` 한다.
9. **커밋**: `pro-commit` 으로 커밋한다. 메시지는 3단계의 `commit_template` 형식을 따른다.
10. **통합·푸시**:
    - `git fetch origin` 후 `git rebase origin/develop`
    - `git log origin/develop..origin/main` 에 내용이 있으면 `git merge origin/main` (이유: 릴리스 버전 커밋이 main 에만 있어 생략하면 다음 배포가 실패한다)
    - `BASE=$(git rev-parse origin/develop)` 를 기록하고 `git push origin HEAD:develop`
    - non-fast-forward 면 fetch, rebase 후 `BASE` 를 다시 기록해 재시도
11. **배포 판정**: `node "$CLI" release-decision --own-commits <git rev-list BASE..HEAD 를 쉼표로> --checks-passed true --verified <true|false>`.
12. **결과 처리**:
    - `deploy`: 레포의 `develop` 기준으로 `pro-changelog-deploy` 를 실행한다. 릴리스 노트는 자동 생성을 고른다. 승인 대기로 멈추면 `pro-github` `create-pr` 로 head `develop`, base `main`, 빈 본문 PR 을 만든다 (워크플로우가 노트를 채우고 automerge 한다). 성공하면 `record-deploy`.
    - `push-only`: 이슈에 `reason` 을 댓글로 남기고 라벨 `확인필요`를 붙인다. 이슈는 열어 둔다.
13. **마무리**: 배포했으면 `pro-report` 로 보고서를 남기고 `pro-github finish-issue` 로 닫은 뒤 worktree 를 제거한다. 대기열에서 온 요구면 `queue-done --id <id>`. `unlock` 후 `queue-list` 에 대기 건이 있으면 1단계부터 이어서 처리한다.

## 호환 규칙

- config 키는 추가만 한다. 이름 변경·삭제 금지. 새 키에는 기본값을 둔다.
- CLI 명령과 인자, `outline.md` 문법, 디자인 프리셋 형식은 기존 입력을 계속 받는다.
- 기존 결과물 모양이 바뀌면 옵션으로 추가하고 기본값을 유지한다. 명백한 버그 수정은 예외다.
- 고객사명, 하드코딩된 수치, 특정 건 분기를 skill 에 넣지 않는다.
- 외부 의존성을 새로 요구하지 않는다. macOS·Windows 양쪽에서 동작해야 한다.

걸리면 배포하지 않는다. 개인 설정으로 처리할 수 있으면 앞단에 그렇게 돌려준다.

## 보고

앞단에 돌려주는 값: `outcome` (`deployed` | `pushed` | `pc-only` | `queued` | `failed`), 이슈 URL, 사유 한 줄. 민감 정보와 토큰은 넣지 않는다.

레포 구조와 업데이트 전달 방식은 `references/repo-guide.md` 를 본다.
