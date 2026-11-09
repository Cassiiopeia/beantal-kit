# bean-proposal 샘플 검증

결과물이 바뀌는 수정(`scripts/`, `references/page-types.md`, 렌더링 관련 절차)일 때 실행한다. 고객 자료는 쓰지 않고 레포의 가상 샘플만 쓴다.

## 준비

- Python 3.10+. 확인: `python3 --version` (Windows: `python --version`)
- worktree 에서 `skills/bean-proposal/scripts/proposal_cli.py doctor` 실행. `missing_libs` 면 시스템 임시 폴더의 가상환경에 `install` 값의 라이브러리와 `python-pptx` 를 설치해 쓴다. 사용자 Python 환경은 바꾸지 않는다.
- 준비할 수 없으면 `verified=false` 로 끝낸다.

## 실행

결과 파일은 시스템 임시 폴더에만 만들고 검증 후 지운다.

1. 입력: `skills/bean-skill-manager/fixtures/bean-proposal-sample-outline.md`. 고친 동작이 샘플에 없으면 임시 폴더의 복사본에 그 경우를 재현하는 장을 추가한다.
2. `outline-check <outline>`
3. `render <outline> --out <임시 폴더>/sample_v01.pptx`
4. `review <임시 폴더>/sample_v01.pptx --md <임시 폴더>/review.md`
5. `snapshot <임시 폴더>/sample_v01.pptx --slides <고친 장>` 을 실행할 수 있으면 이미지를 Read 로 보고 요구가 해결됐는지 확인한다.

## 통과 기준 (모두 만족)

- `outline-check`: `ok` true, 오류 0 (메시지 길이 경고 `O09` 는 샘플 특성이라 무시)
- `render`: `ok` true, `code` 가 `rendered`, `slides` 가 outline 장 수와 같음
- `review`: `ok` true, `counts.red` 가 0
- 고친 요구를 재현한 장에서 요구가 해결됨. 이미지로 확인할 수 없으면 `review` 코드와 렌더 결과의 구조로 확인하고, 그것도 안 되면 `verified=false`
