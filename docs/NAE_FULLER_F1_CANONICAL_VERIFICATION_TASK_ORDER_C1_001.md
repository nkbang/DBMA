# Task Order — F1: Fuller Canonical 재검증 + Provenance 한계 확정 (C1)

- 발급: CUE → C1
- 일자: 2026-09-08
- 우산 계획: `NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` F1 (§4)
- HQ 지시: F1 선행 (David 검수 착수 전, 2026-09-08)
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine`, venv `~/envs/dbma311`

---

## 0. 목적

Fuller Vol.01–08 canonical(정제 결과)의 무결성·품질 한계를 확정하고,
`page_count = 1` (page-level citation 불가) 조건에서 쓸 **citation locator
규칙**과 **retrieval/UI disclosure 문구**를 정한다. David 검수·이후
임베딩/색인의 전제.

**읽기 전용.** 재-정제(re-normalize)는 이 Task Order 범위 밖 (F0/Amendment 결정).

---

## 1. 과업

### T1. Canonical 존재·무결성 (8권)
- `NAE/corpus/canonical/Fuller_Complete_Works_Vol01..08/` 각각
  `canonical.json` / `canonical.txt` / `normalize_report.json` 존재
- `canonical.json` JSON 파싱 OK, `normalize_report.json::status == "ok"` (8/8)
- canonical.json 문단 레코드 수 ↔ `normalize_report.json::paragraph_count` 일치

### T2. normalize_report 8권 집계표
컬럼: `pipeline_version`, `source`, `page_count`, `characters_after`,
`paragraph_count`, `heading_count`, `sentence_count`, `verse_paragraph_count`,
`quote_count`, `footnotes_extracted`, `scripture_references_found`,
`headers_footers_removed`, `page_numbers_removed`
- 이상치 표시 (예: Vol.03/Vol.07 `scripture_references_found = 0`,
  Vol.01 `heading_count`가 유독 낮/높은지 등)

### T3. Vol.03 / Vol.07 scripture_references = 0 원인 규명
- 두 권 `canonical.txt` 에서 성구 인용 패턴을 직접 grep/정규식 카운트:
  `[1-3]?\s?(창|출|레|...|마|막|눅|요|롬|고전|...)\s?\d+[:.]\d+`,
  영문 `(Gen|Ex|...|Rom|1 ?Cor|...)\.?\s*[ivxlcdm\d]+[:.]\s*\d+`
- 결과가 유의미(수십+)면 **추출기 누락** / 0에 가까우면 **원문 특성**
- 다른 6권과 비교 (Vol.01=2인데 실제 텍스트엔 몇 개인지도 샘플 확인 —
  추출기 신뢰도 자체 점검)

### T4. Citation locator 규칙 제안
- `page_count = 1` 확정 → page 사용 불가
- 사용 가능 신호: `heading_count`(77~284/권), `paragraph`(TSU 레코드에 존재),
  `canonical.json` heading 경로
- 제안: `work_id + heading_path + paragraph_index` 형태의 locator.
  TSU 레코드의 기존 `page`(전부 1) / `paragraph` / `sentence` 필드와 매핑.
- 재현 가능성(같은 claim → 같은 locator) 확인

### T5. Disclosure 문구 초안
retrieval 결과·citation UI에 붙일 provenance 한계 고지문 (KR + EN):
- OCR 출처, page 번호 없음(heading/문단 기준 locator)
- confidence uncalibrated (모델 self-report)
- 생성 모델 `my-theology-bot-v2:latest`, `authority_class: historical_witness`
- 8개 admission record `rationale` 의 기존 disclosure 문구와 정합

---

## 2. 금지 / STOP

- ❌ canonical 파일 수정, 재-정제 실행
- ❌ `tsu.json`, embedding, Qdrant, promote, ingest
- ❌ ADR / 기존 승인 문서 수정
- ❌ Vol.02–08 TSU 생성 (F2 소관)
- STOP: canonical `status != ok` 발견 / 8권 중 결측 / HEAD 예상과 다름

## 3. 완료 조건

- [ ] T1 8/8 존재·파싱·status ok
- [ ] T2 8권 집계표 (수치 = 파일 원문)
- [ ] T3 Vol.03/07 원인 판정 (추출기 누락 vs 원문 특성) + 근거 grep 카운트
- [ ] T4 citation locator 규칙 (재현성 확인)
- [ ] T5 disclosure 문구 초안 (KR/EN)
- [ ] Mutation 0 — 신규 문서 1개 외 무변경 (`git status --porcelain` 원문)

## 4. 산출물

`docs/NAE_FULLER_CANONICAL_VERIFICATION_001.md`
형식: `git status / T1 / T2 집계표 / T3 판정 / T4 locator 규칙 / T5 disclosure / Next`

## 5. 범위 밖

- 재-정제 필요 여부 최종 결정 = F0 / ADR-030 Amendment
- citation locator 를 코드에 반영 = F5 색인 단계
- disclosure UI 구현 = F6
