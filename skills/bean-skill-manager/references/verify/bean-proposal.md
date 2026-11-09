# bean-proposal 샘플 검증

결과물이 바뀌는 수정(`scripts/`, `references/page-types.md`, 렌더링 관련 절차)일 때 실행한다. 고객 자료는 쓰지 않고 레포의 가상 샘플만 쓴다.

`render-check` 는 PPT 를 메모리에서만 만들고 점검한다. 디스크에 pptx 를 쓰지 않으므로 문서 보안(DRM) 암호화가 걸리지 않고 PowerPoint 도 열지 않는다. 사용자의 작업과 충돌하지 않게 뒷단에서는 이 명령만 쓴다.

## 준비

- Python 3.10+. 확인: `python3 --version` (Windows: `python --version`)
- worktree 에서 `skills/bean-proposal/scripts/proposal_cli.py doctor` 실행. `missing_libs` 면 시스템 임시 폴더의 가상환경에 `install` 값의 라이브러리와 `python-pptx` 를 설치해 쓴다. 사용자 Python 환경은 바꾸지 않는다.
- 준비할 수 없으면 `verified=false` 로 끝낸다.

## 실행

입력: `skills/bean-skill-manager/fixtures/bean-proposal-sample-outline.md`. 고친 동작이 샘플에 없으면 시스템 임시 폴더의 복사본에 그 경우를 재현하는 장을 추가한다.

1. `outline-check <outline>`
2. `render-check <outline>`

## 통과 기준 (모두 만족)

- `outline-check`: `ok` true, 오류 0 (메시지 길이 경고 `O09` 는 샘플 특성이라 무시)
- `render-check`: `ok` true, `slides` 가 outline 장 수와 같음, `counts.red` 가 0
- 고친 요구가 재현한 장의 `findings` 와 `deck.slides` 구조(도형 위치·크기·글자)에서 해결됨. 구조로 판단할 수 없으면 `verified=false`
