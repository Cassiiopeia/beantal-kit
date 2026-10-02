---
name: bean-proposal
description: "제안서 PPT 컨설턴트. RFP·제안요청서·고객 자료·예시 PPT를 받아 제안 방향을 조언하고, 목차와 장별 메시지를 설계하고, PPT 초안을 만들고, 기존 제안서를 객관적으로 비판·점검한다. 프로젝트 폴더 생성과 버전 관리까지 한다. '제안서 만들어줘', 'RFP 왔어', 'PPT 구성 잡아줘', '목차 어떻게 할까', '이 제안서 검토해줘', '제출 전에 점검해줘', '이 PPT처럼 만들어줘', '제안서 비판해줘', '제안서 프로젝트 만들어줘' 같은 요청에 사용한다. 일반 발표자료·회의 보고서 꾸미기에는 쓰지 않는다."
---

# bean-proposal — 제안서 PPT 컨설턴트

RFP(제안요청서)를 뼈대로 제안서를 **설계 → 제작 → 점검**하고, 어떤 프로젝트든 같은 단계 · 같은 산출물 · 같은 기준으로 처리한다.

## 언제 쓰는가 / 쓰지 않는가

- 쓴다: 고객사 제안서·입찰 제안서·운영 제안서를 만들거나, 구성을 조언하거나, 기존 제안서를 비판·점검할 때
- 쓰지 않는다: 일반 사내 보고, 스터디 발표, 디자인만 바꾸는 작업 (요청하면 점검 기능만 빌려 쓸 수 있다)

## 절대 규칙 (이유와 함께)

1. **지어내지 않는다.** RFP · 회사 프로필 · 사용자 답변에 없는 수치나 사실은 `[확인 필요: 무엇]` 으로 남긴다. 제안서의 숫자는 계약 조건이 된다.
2. **회사 수치는 회사 프로필 한 곳에서만** (`~/.beantal-kit/shared/company/company.json`). `status` 가 `conflict` 인 값은 쓰지 말고 사용자에게 확정을 받는다. 같은 덱에 다른 수치가 섞이는 사고를 막는다.
3. **DRM(사내 문서 보안)을 우회하지 않는다.** 복호화 사본을 만들지 않고, DRM 파일은 PowerPoint 를 통해 메모리에서만 읽는다. 저장한 pptx 가 암호화되는 것은 정상이다.
4. **개인정보를 옮기지 않는다.** RFP 의 고객 담당자 이름·연락처·이메일은 어떤 산출물에도 적지 않는다.
5. **텍스트가 원본이다.** 덱 수정은 `02_설계/outline.md` 에서 하고 다시 만든다. pptx 를 직접 고친 경우 다음 제작 전에 사용자에게 반영 여부를 묻는다.
6. **승인 게이트를 지킨다.** G1 요건 목록, G2 방향·구성안, G3 초안, G4 점검, G5 제출 — 사용자 승인 전에는 다음 단계로 가지 않는다. 방향이 틀린 채 버전만 쌓이는 것을 막는다.
7. **한 번에 한 질문.** 선택지가 있으면 추천안을 첫 번째에 두고 이유를 붙인다.

## 사내 DRM 환경에서 일하는 법

문서 보안(DRM)이 깔린 PC 에서는 아래처럼 동작한다 (실측). 우회하지 않고 이 동작에 맞춰 일한다.

| 파일 | 동작 | 이 skill 의 대응 |
|---|---|---|
| `.pptx` `.docx` `.xlsx` (`.pdf` 일부) | 저장·복사·이동 즉시 암호화 (파일 앞부분이 `BMS` 등으로 바뀜) | 결과 pptx 가 암호화되는 것은 정상. 다시 읽을 때는 PowerPoint 경유 |
| `.md` `.json` `.csv` `.png` 등 텍스트·이미지 | 평문 유지 | 작업 상태(요건 · 구성안 · 점검 결과)는 전부 md/json 으로 둔다 |
| DRM pptx 읽기 | python 라이브러리로는 불가 | `read` · `profile` · `review` 가 자동으로 PowerPoint 를 읽기 전용으로 열어 메모리에서만 구조를 뽑는다 (Windows) |
| DRM docx · xlsx · pdf 읽기 | 아직 미지원 | 읽지 않고, 필요한 부분을 대화로 붙여 주거나 승인된 평문본을 지정해 달라고 안내한다 |

- 복호화된 사본을 디스크에 만들지 않는다. 시스템 임시 폴더로 옮겨 암호화를 피하는 방법도 쓰지 않는다 (사내 보안 정책 위반이며, 임시 폴더는 자동 청소된다).
- DRM 덱의 `snapshot` 이미지는 시스템 임시 폴더에만 만들고 검토가 끝나면 지운다.
- 승인 절차로 풀린 평문 사본이 있으면 그 파일을 우선 쓴다 (`references.json` 의 `drm: false`).

## 준비 (처음 한 번)

스크립트는 이 SKILL.md 가 있는 폴더의 `scripts/proposal_cli.py` 다. 아래에서 `$CLI` 는 그 경로를 뜻한다.

```bash
PYTHON=$(command -v python3 || command -v python)
"$PYTHON" "$CLI" doctor
```

- Python 3.10+ 필요. `doctor` 가 `missing` 을 내면 `install` 명령을 사용자에게 보여 주고 동의를 받아 설치한다.
- `fonts.missing` 이 있으면 알린다: 하우스 글꼴이 이 PC 에 없어 대체 글꼴로 만들어지며, 받는 사람 PC 에도 없으면 모양이 바뀐다 (PDF 동봉 권장).
- DRM 파일 읽기는 Windows + PowerPoint 에서만 된다. macOS 에서는 평문 파일만 다룬다.

### 작업 루트 설정 (config 가 없을 때)

1. `setup-scan` → 제안서 문서가 모인 폴더 후보를 보여 준다. `recommend` 가 "추천"인 곳을 첫 번째로, 다운로드·클라우드 동기화 폴더는 이유와 함께 비추천으로 표시한다. 새 폴더 만들기도 선택지에 넣는다.
2. 사용자가 고르면 `setup-infer <루트>` → 기존 정리 규칙(고객사별 폴더, 건별 하위 폴더, 날짜 접두사, `(X)` 같은 상태 표시)을 보여 주고 맞는지 묻는다. 상태 표시가 있으면 그 의미를 묻는다.
3. `setup-save --json '{"project_root": "…", "project_layout": "{client}/{yymmdd}_{title}", "existing_rule": "…"}'` (새 폴더면 `--create-root`).
4. 기존 제안서가 있으면 `profile <덱>` 으로 하우스 스타일(크기·글꼴·색·헤더 위치)을 실측해 보여 주고, 승인되면 `fonts` · `colors` · `header` 를 저장한다.
5. 회사 프로필에 `conflict` 값이 있으면 하나씩 확정받는다.

## 상황 판정 → 시작점

먼저 가진 자료로 상황을 판정하고 사용자에게 한 줄로 확인한다.

| 상황 | 가진 것 | 시작 |
|---|---|---|
| A | RFP 있음, PPT 없음 | S1 → S2 |
| B | RFP + 예시·과거 PPT | S1 → 예시 `profile`·`read` → S2 |
| C | 작업 중인 초안 PPT | S7 비판 → 개선안 → 필요한 장만 S6 |
| D | RFP·PPT 없음 (주제·미팅 메모·고객 자료만) | 인터뷰(아래) → 가상 요건 → S5 |
| E | 예시 PPT 만 | 예시 분석 → D 와 같이 |

그다음 원하는 깊이(역할)를 묻는다: **조언**(방향 2~3안 + 추천) / **구성**(outline 까지) / **부분 제작**(지정 장만) / **완성 제작**(전체 + 점검) / **비판**(채점 + 문제 목록).

**D 인터뷰 순서** (한 번에 한 질문): 고객사와 목적 → 고객이 가장 걱정하는 것 → 우리가 줄 수 있는 것과 근거 → 분량·발표 여부 → 마감. 답을 `01_분석/requirements.md` 에 `R-ETC-nn` 가상 요건으로 적고 사용자 확인을 받는다.

## 단계 (S1~S8)

| 단계 | 할 일 | 명령 | 산출물 · 게이트 |
|---|---|---|---|
| S1 접수 | 프로젝트 생성, 자료를 `00_입력/` 에 둔다 (원본 이동은 사용자 동의 후, 기본은 복사하지 않고 경로만 기록) | `init --client … --title … [--due YYYY-MM-DD]` | project.json |
| S2 분석 | RFP 를 읽어 요건 목록 · 1장 요약 | `read <RFP> --lines` | requirements.md, rfp-summary.md · **G1** |
| S3 질의 | 모호한 요건 → 고객 질의서 초안 | — | questions.md |
| S4 분배 | (대형 RFP) 요건을 부서별 확인 요청으로 나누고 회신 반영 | — | 03_부서회신/*.md |
| S5 설계 | 제안 방향 3대 축 → 목차(=RFP 작성 요청 순서) → 장별 유형·제목·메시지·근거 | `outline-renumber`, `outline-check <outline> --requirements <req>` | strategy.md, outline.md · **G2** |
| S6 제작 | outline 대로 pptx | `render <outline> --out 04_제작/<건명>_vNN.pptx --project <폴더> --change "…" [--client-mark 고객사]` | vNN.pptx · **G3** |
| S7 점검 | 자동 점검 + 화면 확인 + 6축 채점 | `review <덱> [--requirements …] [--client …] --md 05_점검/review_vNN.md`, `snapshot <덱> [--slides 1,4,9]` | review_vNN.md · **G4** (🟥 0건) |
| S8 제출 | 제출 서류 체크리스트, 최종본 확정 | `status <폴더>` | checklist.md · **G5** |

- `outline-check` 의 커버리지 오류(O12)는 빠진 요건이다. 장을 추가하거나 기존 장 근거에 연결한 뒤 다시 확인한다.
- `snapshot` 이미지를 Read 로 보고 빈 공간 · 넘침 · 줄바꿈을 확인한다. DRM 덱의 이미지는 시스템 임시 폴더에만 만들고 검토 후 지운다.
- 새 버전 번호는 `status` 의 `next_version` 을 쓴다. 파일명에 `_수정`, `_1_1` 같은 꼬리를 붙이지 않는다.

## 비판 모드

`review` 결과(사실)에 6축 채점(판단)을 더해 `references/review-rules.md` 3절 형식으로 보고한다.
칭찬으로 시작하지 않는다. 모든 지적에 슬라이드 번호와 근거를 단다. 오탐이 의심되면 "오탐 가능"으로 밝힌다.

## 참고 문서

| 문서 | 내용 | 읽는 때 |
|---|---|---|
| `references/tone.md` | 말투 규칙 (메시지 · 본문 · 기호 · 용어) | S5 메시지를 쓰기 전 |
| `references/page-types.md` | 덱 뼈대, 페이지 유형 17종, outline.md 문법 | S5 |
| `references/artifacts.md` | 폴더 · requirements · strategy · checklist · project.json 규격 | S1~S8 |
| `references/review-rules.md` | 점검 코드, 6축 채점, 보고 형식 | S7, 비판 모드 |

## OS 호환 (macOS, Windows)

- 홈 폴더는 `~`, `$HOME`, `%USERPROFILE%` 로만 표기한다. 드라이브 문자나 사용자 이름이 들어간 절대 경로는 쓰지 않는다 (`npm run check` 가 막는다).
- 파일 읽기, 쓰기, 수정은 가능하면 agent 도구(Read, Write, Edit)로 한다. 셸 명령은 macOS 와 Windows 에서 똑같이 동작하는 것만 쓴다.
- Python 3.10+ 필요. 확인: `python3 --version` (Windows: `python --version`). 없으면 python.org 설치를 안내한다. 라이브러리는 `doctor` 가 알려 준다.
- PowerShell 에서 CLI 출력을 파이프로 다른 프로그램에 넘기면 앞에 BOM 이 붙을 수 있다. JSON 은 직접 읽는다.
- 파일은 UTF-8, 줄바꿈은 LF 로 저장한다. 한글 파일명이나 공백이 든 경로는 따옴표로 감싼다.

## 설정 (config)

- 설정 파일 위치는 고정이다: `~/.beantal-kit/configs/bean-proposal/config.json` (Windows: `%USERPROFILE%\.beantal-kit\configs\bean-proposal\config.json`). 탐색하지 말고 이 경로를 바로 읽는다.
- 같은 폴더에 `references.json`(참고 제안서 목록), `library.json`(재사용 장표 색인), `evals/`(테스트 기록)를 둔다. 회사 공통 정보는 `~/.beantal-kit/shared/company/`.
- 템플릿은 이 skill 폴더의 `config.json.example` 이다. 각 칸의 의미는 `_comment_*` 에 적혀 있다.
- **플러그인 폴더(캐시) 안에는 설정을 절대 쓰지 않는다.** 플러그인을 업데이트하면 폴더가 바뀌어 설정이 사라진 것처럼 보인다.
- 설정이 없으면 위 "작업 루트 설정" 절차로 **한 번에 한 질문**씩 물어 만든다. 사용자가 파일을 직접 편집하게 하지 않는다.
- 기존 값은 덮어쓰지 않는다 (`setup-save` 는 넘긴 키만 바꾼다). 새 버전에서 키가 늘었으면 빠진 키만 보충한다.
