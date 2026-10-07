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
4. **버전 파일은 만든 뒤 고치지 않는다.** v01 은 `outline.md` 에서 `render` 로 만들고, v02 부터는 **최신 pptx 가 기준**이다. 고칠 때는 `version-new` 로 최신본을 다음 번호로 복사한 뒤 그 복사본만 고친다. 사람이 PowerPoint 에서 직접 고친 파일이 이미 있으면 그것이 기준이니 `outline.md` 로 덮어 다시 만들지 않는다. PowerPoint 가 파일을 잠가도 새 번호로 만들면 충돌이 없다.
5. **승인 게이트를 지킨다.** G1 요건 목록, G2 방향·구성안, G3 초안, G4 점검, G5 제출 — 사용자 승인 전에는 다음 단계로 가지 않는다. 방향이 틀린 채 버전만 쌓이는 것을 막는다.
6. **한 번에 한 질문.** 선택지가 있으면 추천안을 첫 번째에 두고 이유를 붙인다.

## 사내 DRM 환경에서 일하는 법

문서 보안(DRM)이 깔린 PC 에서는 아래처럼 동작한다 (실측). 우회하지 않고 이 동작에 맞춰 일한다.

| 파일 | 동작 | 이 skill 의 대응 |
|---|---|---|
| `.pptx` `.docx` `.xlsx` (`.pdf` 일부) | 저장·복사·이동 즉시 암호화 (파일 앞부분이 `BMS` 등으로 바뀜) | 결과 pptx 가 암호화되는 것은 정상. 다시 읽을 때는 PowerPoint 경유 |
| `.md` `.json` `.csv` `.png` 등 텍스트·이미지 | 평문 유지 | 작업 상태(요건 · 구성안 · 점검 결과)는 전부 md/json 으로 둔다 |
| DRM pptx 읽기 | python 라이브러리로는 불가 | `read` · `profile` · `review` 가 자동으로 PowerPoint 를 읽기 전용으로 열어 메모리에서만 구조를 뽑는다 (Windows) |
| DRM docx · xlsx · doc · xls 읽기 | 그 문서를 여는 앱(Word·Excel)은 읽을 수 있다 | `read` 가 앱을 읽기 전용·숨김으로 열어 메모리에서만 읽고 저장 없이 닫는다 (Windows) |

### 파일은 "못 읽는다"고 하지 않고 읽는다

어떤 파일이든 먼저 `read <파일> --lines` 를 실행한다. `read` 는 확장자만 보지 않고 **파일 앞부분(DRM·PDF·zip 안 이름·옛 Office)** 과 **이 PC 에 설치된 앱**으로 읽는 방법을 정해 차례로 시도하고, 하나가 실패하면 다음 방법으로 넘어간다. 결과의 `via` 가 실제로 읽은 방법이고 `tried` 가 실패한 시도다.

| 형식 | 평문일 때 | DRM·옛 형식일 때 |
|---|---|---|
| pptx · docx · xlsx · pdf · hwpx · txt · csv | python 으로 바로 (빠르고 토큰이 적다) | PowerPoint · Word · Excel 로 읽기 전용 |
| doc · xls · ppt (옛 Office) | — | Word · Excel · PowerPoint |
| hwp | — | 한컴오피스(한글)가 설치된 PC 만 |
| DRM pdf | — | Word 로 시도 (변환 안내창에 걸리면 시간 초과) |
| 확장자 없음·모르는 확장자 | 글자 파일이면 text | 앱을 차례로 시도 |

자동 순서는 기본값일 뿐이고 **판단은 에이전트가 한다.** 확장자가 낯설거나 이상하면 먼저 `probe <파일>` 로 사실(파일 생김새, 이 PC 에 설치된 앱, 읽는 방법 후보)만 받아 보고, 후보 중에서 직접 골라 `--via` 로 읽는다. 확장자와 생김새가 다르면 생김새를 믿는다.

실패해도 멈추지 않는다. 실패하면 `code`=`unreadable` 과 함께 **`tried`(무엇을 시도했나)·`hints`(다음에 해 볼 일)** 가 온다. 그것을 보고 에이전트가 스스로 이어간다.

1. `--via word|excel|powerpoint|hangul|pdf|docx|xlsx|hwpx|text` 로 읽는 방법을 직접 지정해 다시 시도한다 (확장자가 틀린 파일도 이렇게 푼다).
2. 긴 문서는 `--lines` 가 한 번에 약 15000자까지만 내고 `next_offset` 을 준다. `--offset <next_offset>` 으로 이어 읽는다 (도구가 큰 결과를 평문 파일로 저장해 DRM 문서가 디스크에 남는 것을 막는다).
3. 스캔 이미지 PDF·한글이 없는 PC 의 hwp 처럼 정말 안 열리면, 그때만 사용자에게 붙여 달라고 하거나 PDF·DOCX 로 저장해 달라고 부탁한다. 처음부터 "못 읽는다"고 말하지 않는다.
4. 새 형식이 필요하면 `scripts/proposal_lib/deckio.py` 의 `READERS` 에 함수 하나, `guess_routes()` 에 한 줄을 더한다.

### 글자만 읽고 끝내지 않는다 (그림·도형 확인)

`read` 가 글자를 다 뽑았어도 **그림·표·흐름도로 들어간 내용은 글자로 안 나온다.** RFP 의 센터별 작업 공정, 흐름도, 납품처 현황이 흔히 그림이다. 이걸 놓친 채 요건 목록을 쓰면 요건이 빠진다.

- `read` 결과에 `visual_pages` / `must_view` 가 있거나 `--lines` 에서 `[pN] ⚠ 그림 있음` 이 보이면, **요건 목록·요약을 쓰기 전에** `pdf-view <파일> --pages <쪽,쪽>` 로 그 쪽을 이미지로 만들어 `Read` 로 직접 본다 (시스템 임시 폴더에만 만든다. 다 본 뒤 지운다).
- 본 내용은 `requirements.md` 맨 아래 `## 그림 확인` 절에 쪽별로 적는다 (쪽, 그림 종류, 읽은 내용, 불확실한 부분). `visual_pages` 에 있는 쪽이 이 절에 하나라도 빠지면 G1 을 요청하지 않는다.
- 보고할 때 "글자는 다 읽었다"로 끝내지 않는다. 어느 쪽을 이미지로 확인했고 어느 쪽을 못 봤는지 말한다. 이미지로도 판독이 안 되는 부분만 사용자에게 묻는다.
- 같은 폴더의 첨부 자료(zip·엑셀 등)도 S2 에서 목록을 먼저 확인한다. 못 읽는 형식이면 그 사실과 대안(압축 해제 승인 요청 등)을 처음 보고에 포함한다.

### 자료 집계 (출고 데이터·엑셀·zip)

자료마다 열 이름·단위·시트 구조가 달라 하나의 집계 도구로 다 풀 수 없다. 대신 **싼 것부터 차례로** 쓴다. 매번 스크립트를 만들고 지우지 않는다.

1. **구조 보기**: `archive <zip>` 로 파일 목록, 시트별 행 수·열 이름을 본다 (압축은 풀지 않고 메모리에서 읽는다). `--member 이름 --rows 3` 으로 한 파일의 앞부분만 본다.
2. **단순 집계는 명령으로**: `archive <zip> --member 센터A --sheet 출고내역 --group 납품월 --sum "납품수량(PLT)"` 처럼 월별·채널별 합계는 스크립트 없이 낸다. 날짜 열은 `--bucket month`.
3. **그 밖의 집계는 레시피로**: 명령으로 안 되는 집계(여러 시트 합치기, 조건 계산, 단위 환산)만 파이썬을 쓴다. 쓰기 전에 `~/.beantal-kit/configs/bean-proposal/recipes/index.md` 를 먼저 읽어 비슷한 것이 있으면 그것을 인자만 바꿔 다시 쓴다. 없으면 새로 만들고 **지우지 않고** 그 폴더에 저장한다.
   - 레시피는 파일 경로·시트·열 이름을 인자로 받게 쓴다 (특정 고객 값을 코드에 박지 않는다). 파일 맨 위 주석에 용도, 인자, 입력 형태 한 줄씩 적고, `index.md` 에 `파일명 — 한 줄 설명` 을 추가한다.
   - 레시피는 `~/.beantal-kit/` 에만 둔다. 프로젝트 폴더와 이 레포(공개)에는 두지 않는다. 고객 파일을 임시로 풀어야 하면 시스템 임시 폴더에만 풀고 바로 지운다.
4. **결과 기록**: `01_분석/data-summary.md` 에 숫자마다 출처(파일, 시트, 열, 사용한 명령이나 레시피)를 적는다. 단위가 다른 값(BOX·EA·PLT)을 합칠 때 쓴 환산 기준은 근거가 RFP·질의 답변에 있을 때만 쓰고, 없으면 `[확인 필요: 환산 기준]` 로 남긴다. 형식이 달라 집계하지 못한 시트는 이름과 이유를 적는다.

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
| S6 제작 | v01 은 outline 대로 pptx, v02~ 는 최신본 복사 후 수정 | `render <outline> --out 04_제작/<건명>_vNN.pptx --project <폴더> --change "…" [--client-mark 고객사]` | vNN.pptx · **G3** |
| S7 점검 | 자동 점검 + 화면 확인 + 6축 채점 | `review <덱> [--requirements …] [--client …] --md 05_점검/review_vNN.md`, `snapshot <덱> [--slides 1,4,9]` | review_vNN.md · **G4** (🟥 0건) |
| S8 제출 | 제출 서류 체크리스트, 최종본 확정 | `status <폴더>` | checklist.md · **G5** |

- **디자인 프리셋**: 참고 제안서의 모양을 이름 붙여 저장해 두고 골라 쓴다 (`~/.beantal-kit/configs/bean-proposal/designs/<이름>.json`).
  - S6 에서 렌더하기 전에 `design-list` 로 목록을 보여 주고 AskUserQuestion 으로 고르게 한다 (기본 config 모양도 선택지에 넣는다).
  - 쓰기: `render … --design <이름> [--color primary=RRGGBB,accent=RRGGBB] [--client-logo <로고.png>] [--cover-image <엠블럼.png>] [--footer-client-logo <고객사 로고.png>]`. 고객사 로고를 주면 하단은 왼쪽 우리 로고 · 오른쪽 고객사 로고 · 가운데 쪽 번호. 프리셋의 `color_policy` 가 `client` 이면 고객사 CI 색을 `--color` 로 넘긴다. CI 색은 고객 자료(RFP 표지 로고 등)에서 뽑고 지어내지 않는다.
  - 저장: 사용자가 "이 디자인 저장해줘"라고 하면 `profile` 실측값과 화면 확인 결과로 `design-save --name <이름> --json '{…}'` (칸: description, source, color_policy, fonts, colors, header, design).
  - `design` 칸: `card: band`(둥근 색 띠 소제목 + 테두리 박스, `▶ ` 로 시작하는 항목은 카드 맨 아래 결론 상자), `divider: light`(흰 간지), `cover: panel`, `toc: list`, `rule: <cm>`(헤더 아래 가로줄), `footer_logo: <이미지 경로>`, `footer_logo_align: right`(기본, 쪽 번호는 왼쪽) · `left`.
  - 고객사 로고는 프로젝트 `00_입력/` 에, 회사 로고는 `~/.beantal-kit/shared/company/` 에 둔다 (레포에 넣지 않는다).
- 렌더러로 레이아웃을 바꾼 버전은 `version-new` 대신 `render --project` 로 다음 번호를 만든다. 이때 직전 버전에 PowerPoint 직접 수정이 없었는지(outline.md 저장 시각과 pptx 시각) 먼저 확인한다.
- v02 이후 수정: `version-new <프로젝트> --change "5장 SLA 수치 수정"` 로 복사한 뒤 `edit <새 vNN.pptx> --json '[{"slide":5,"find":"…","replace":"…"}]'` 로 글자를 바꾼다 (slide 0 = 전체 장). DRM 덱도 PowerPoint 경유로 고친다. 최신 버전이 아닌 파일은 `edit` 이 거절한다. 장 추가·삭제·배치 변경처럼 글자 교체로 안 되는 수정은 사용자와 함께 PowerPoint 에서 하고 다음 번호로 저장하게 한다.
- 변경 이력은 `project.json` 의 `versions` 에 쌓인다 (버전, 날짜, 기준 파일, 바꾼 이유). 새 대화에서 이어 작업할 때는 `status <프로젝트>` 와 이 이력을 먼저 읽는다.
- `outline-check` 의 커버리지 오류(O12)는 빠진 요건이다. 장을 추가하거나 기존 장 근거에 연결한 뒤 다시 확인한다.
- `snapshot` 이미지를 Read 로 보고 빈 공간 · 넘침 · 줄바꿈을 확인한다. DRM 덱의 이미지는 시스템 임시 폴더에만 만들고 검토 후 지운다.
- 새 버전 번호는 `status` 의 `next_version` 을 쓴다. 파일명에 `_수정`, `_1_1` 같은 꼬리를 붙이지 않는다.

## 레퍼런스 등록 (대화 중 묻기)

사용자가 대화 중에 **과거·완성된 제안서나 예시 PPT, 또는 RFP 와 짝이 되는 자료**를 주면, 작업을 계속하기 전에 한 번 묻는다. 이미 `references.json` 에 있는 파일, 지금 만드는 프로젝트의 중간 산출물(초안 vNN), 사용자가 "참고만 할게"라고 한 파일은 묻지 않는다.

AskUserQuestion 으로 묻는다 (추천을 첫 번째에):

- 질문: "이 파일을 레퍼런스로 등록할까요? (다음 제안서에서 구성·스타일 참고용으로 씁니다)"
- 선택지: **등록(추천)** — 복사해서 보관하고 평문 요약(digest.md)을 만든다 / **등록안함** — 이번 대화에서만 쓰고 보관하지 않는다

"등록"이면 필요한 칸(고객사, 건명, 연도, 품질 gold·reference·wip)을 대화에서 알 수 있는 만큼 채우고, 모르는 것만 한 번에 한 질문으로 묻는다. 그다음:

```bash
"$PYTHON" "$CLI" ref-add --client 고객사 --title 건명 --year 2026 --quality reference --file 최종=<pptx 경로> [--file 입력(RFP)=<docx 경로>]
"$PYTHON" "$CLI" ref-digest <id>
```

- 역할(role)은 `최종` `초안` `입력(RFP)` `질의` `틀` `부서양식` `작업중` 중 하나다. `최종`·`틀`·`작업중` 의 pptx 만 digest 대상이다.
- 원본은 옮기거나 지우지 않고 **복사**만 한다. 고객사 자료라 레포와 skill 폴더에는 절대 넣지 않는다.
- 보관 위치는 `~/.beantal-kit/configs/bean-proposal/references/<id>/` (`원본/` 과 `digest.md`). 설계·스타일 참고가 필요하면 pptx 를 열기 전에 `digest.md` 를 먼저 읽는다 (토큰 절약, DRM 영향 없음).
- 등록 후 `status` 가 `conflict` 인 회사 수치가 이 자료에서 드러나면 사용자에게 알린다.

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
- 같은 폴더에 `references.json`(참고 제안서 목록)과 `references/`(복사본 + digest.md), `library.json`(재사용 장표 색인), `evals/`(테스트 기록)를 둔다. 회사 공통 정보는 `~/.beantal-kit/shared/company/`.
- 템플릿은 이 skill 폴더의 `config.json.example` 이다. 각 칸의 의미는 `_comment_*` 에 적혀 있다.
- **플러그인 폴더(캐시) 안에는 설정을 절대 쓰지 않는다.** 플러그인을 업데이트하면 폴더가 바뀌어 설정이 사라진 것처럼 보인다.
- 설정이 없으면 위 "작업 루트 설정" 절차로 **한 번에 한 질문**씩 물어 만든다. 사용자가 파일을 직접 편집하게 하지 않는다.
- 기존 값은 덮어쓰지 않는다 (`setup-save` 는 넘긴 키만 바꾼다). 새 버전에서 키가 늘었으면 빠진 키만 보충한다.
