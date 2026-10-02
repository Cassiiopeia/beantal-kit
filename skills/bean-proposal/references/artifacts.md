# 프로젝트 폴더와 산출물 규격

## 1. 폴더

`init` 이 config 의 `project_root` + `project_layout` 규칙으로 만든다 (기본 `{client}/{yymmdd}_{title}`).

```
<프로젝트>/
├── project.json        상태 · 단계 · 게이트 · 버전 이력
├── 00_입력/            RFP · 첨부 원본 (DRM 그대로 둔다)
├── 01_분석/            requirements.md · rfp-summary.md · questions.md
├── 02_설계/            strategy.md · outline.md  ← 덱의 원본
├── 03_부서회신/        (대형 RFP) 부서별 확인 요청 · 회신
├── 04_제작/            <건명>_v01.pptx … (버전은 vNN 만)
├── 05_점검/            review_vNN.md · 스냅샷
└── 06_제출/            checklist.md · 최종본 · 제출 서류
```

- **텍스트 산출물(md/json)이 진실이고 pptx 는 결과물이다.** 수정은 outline.md 에서 하고 다시 만든다.
- 사내 DRM 이 있으면 pptx 는 저장 즉시 암호화된다. 정상이다. 이 skill 은 DRM pptx 를 PowerPoint 로 읽는다.
- 고객 담당자 이름 · 연락처 · 이메일 같은 개인정보는 어떤 산출물에도 옮기지 않는다.

## 2. requirements.md

| 열 | 뜻 |
|---|---|
| ID | `R-<분류>-<nn>`: WRT 작성요청 · SOW 업무범위 · SLA · EVL 평가 · SUB 제출물 · PRC 견적 · SCH 일정 · ETC 기타. 지운 번호는 재사용하지 않는다 |
| 출처 | RFP 위치 (장·절·표 번호) |
| 분류 | 작성요청 / 업무범위 / SLA / 평가 / 제출물 / 견적 / 일정 / 기타 |
| 요약 | 원문 요약 한 줄 (원문 통째 복사 금지) |
| 배점 · 대응 · 담당 · 슬라이드 · 메모 | 대응 = 즉시 / 협의 / 확인필요 / 불가 |

작성요청 · 업무범위 · SLA · 평가 요건은 **반드시 슬라이드 하나 이상과 연결**되어야 한다 (`outline-check` 의 커버리지).

## 3. strategy.md (제안 방향 1장)

고객 핵심 요구 3~5 (요건 ID 인용) · 평가 기준 상위 · 우리 강점 3~5 (회사 프로필 인용) · **제안 방향 3대 축** · 리스크와 대응 · 차별 포인트 한 문장.

## 4. outline.md

`page-types.md` 4절 문법. 슬라이드마다 유형 · 섹션 · 제목 · 메시지 · 근거 요건 ID.

## 5. review_vNN.md

`review --md` 가 자동 점검 표를 쓰고, Claude 가 아래 6축 채점을 채운다 (`review-rules.md`).

## 6. checklist.md (제출)

RFP "제출 요청 자료" 항목별: 항목 · 파일 경로 · 준비 상태 · 비고. 회사 공통 서류는 `~/.beantal-kit/shared/company/documents.json` 의 경로를 쓴다 (유효기간 확인).

## 7. project.json

```json
{ "schema": 1, "id": "…", "client": "…", "title": "…", "due": "YYYY-MM-DD",
  "situation": "A", "role": "완성 제작", "stage": "S5",
  "gates": { "G1": "날짜", "G2": null, "G3": null, "G4": null, "G5": null },
  "versions": [ { "v": "v01", "date": "…", "file": "04_제작/…_v01.pptx", "change": "…" } ] }
```
