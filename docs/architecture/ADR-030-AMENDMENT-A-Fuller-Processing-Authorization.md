# ADR-030 Amendment A — Fuller Vol.01–08 Processing Authorization

| | |
|---|---|
| **Status** | **PROPOSED** (2026-09-08) — Evidence Before Promotion Rule 적용: 구현·회귀·C1 독립검토·HQ 승인 4조건 충족 전까지 Proposed |
| **Amends** | `ADR-030-NAE-Sermon-Corpus-Governance.md` (IMPLEMENTED, 2026-08-27) — §11 Human Eligibility Governance, §12 N-9 |
| **Trigger** | HQ 결정 B (2026-09-08, Vol.01 파일럿) + `NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` §3 P-2 |
| **Deciders** | Rev. Bang / HQ = Final Authority · CUE = Architecture · C1 = Independent Review |
| **Adoption mutation** | 이 Amendment 채택 = Code 0 / Corpus 0 / TSU 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Config 0 |
| **CLEAN baseline (변경 금지)** | `nae_tsu_v1` = 3,319 · `nae_ref_v1` = 34,948 |

---

## 1. 목적

ADR-030 §12 N-9 는 Fuller Vol.01–08 을 "ADMITTED … TSU/review/embedding 후속
승인 대기(HQ HOLD)" 로 둔다. 본 Amendment 는 그 HOLD 를 **명시된 조건 하에서
해제**하고, 처리에 필요한 provenance 한계 수용·citation disclosure·인용
locator 규칙을 고정한다.

본 Amendment 는 ADR-030 의 다른 조항을 바꾸지 않는다 (§4 TSU Track 순서,
§11 human-review 요구, §13 Migration, §14 Production Safety, §16 Scale
Protection, ADR-013 Qdrant isolation, ADR-024 retrieval gate 전부 그대로).

---

## 2. 처리 대상

`BAP-MISS-FULLER-VOL01` … `BAP-MISS-FULLER-VOL08` (Andrew Fuller,
*The Works …*, 공개 도메인 OCR, archive.org). ADMITTED 2026-08-29
(`corpus_admissions.jsonl` lines 7–14, `track: tsu`,
`authority_class: historical_witness`).

---

## 3. 인가되는 처리 (RESUMPTION_PLAN F0–F6)

| Phase | 대상 | 인가 근거 | 게이트 |
|---|---|---|---|
| F0 거버넌스 | 8권 | 본 Amendment | HQ 승인 + C1 Review + 4조건 |
| F1 canonical 재검증 | 8권 | 완료 (`NAE_FULLER_CANONICAL_VERIFICATION_001.md`, 🟢) | — |
| **B-1/B-2** scripture 추출기 수정 + 재-정제 | 8권 | 완료 (`e9cb72c`, `0a9c8d1`, 0→1000 refs, 구조 불변) | — |
| **F2 TSU 생성** | Vol.02–08 (7권) | 본 Amendment | 권별 `tsu_report.json` 정상 + doctrine 분포 이상치 없음 |
| **F3 인간 검수** | Vol.01–08 (8권) | HQ 결정 B (Vol.01) + 본 Amendment (Vol.02–08). 검토자 David. 절차 = `NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md` (Q2-light) | 권별 전량 disposition + audit trail |
| **F4 임베딩** | `review_status == verified` TSU only | 본 Amendment | verified 건수 = 임베딩 건수, `bge-m3:latest`, 차원 1024 |
| **F5 색인** | `nae_tsu_v1` **additive upsert** | 본 Amendment | 3,319 baseline point 무접촉, `work_id`/`source_id` 격리, upsert 후 count = 3,319 + Fuller verified |
| **F6 retrieval** | `config.yaml modules.nae_pd` | 본 Amendment + HQ | `nae_corpus_reconcile.py` drift 0, 벤치 회귀 없음, 앱 실검색 정상, disclosure 노출 확인 |

각 Phase 는 완료 게이트 통과 후에만 다음으로 진행. Phase 간 자동 진행 없음.

---

## 4. Provenance 한계 — `historical_witness` 범위로 수용

| 한계 | 내용 | 처리 |
|---|---|---|
| Page-level provenance 없음 | `page_count = 1` (OCR, 8/8) | 인용 locator = `work_id + heading_path + paragraph_index` (§5) |
| 신뢰도 미교정 | `confidence` = 모델 self-report 2값(0.8/0.9) | retrieval triage 가중에 사용 금지, disclosure 명시 |
| 생성 모델 | `my-theology-bot-v2:latest` | disclosure 명시 |
| 성구 추출 잔여 오차 | B-1/B-2 로 0→1,000 refs 정상화. OCR 노이즈로 개별 ref 누락 가능 | disclosure 에 "일부 누락 가능" 유지 |
| OCR 노이즈 | 1820s 스캔 원문 | F3 검수 Q1(추출 충실도)에서 걸러냄 |

`authority_class: historical_witness` = 저작에 귀속되는 역사적 증언으로서의
가치. scholarly citation certification 이 아니다 (ADR-030 §7.2).

---

## 5. 인용 Locator 규칙

```
locator = {
  "work_id": "<M2 work_id, 예: fuller_andrew-...vol_1_...>",
  "heading_path": ["<canonical.json heading text …>"],
  "paragraph_index": <canonical.json paragraphs[].index>
}
```

- TSU `page`(전부 1) → 미사용.
- TSU `paragraph` / `sentence` → canonical.json `paragraphs[].index` /
  `sentences[].sentence_index` 매핑.
- 재현 가능(같은 claim → 같은 locator). canonical.json 은 결정론적 출력.
- 근거: `NAE_FULLER_CANONICAL_VERIFICATION_001.md` T4.

---

## 6. Citation Disclosure 정책 (F6 UI 필수 노출)

Fuller 내용이 검색 결과·인용으로 노출될 때 아래를 표시한다:

> **출처 고지 (KR)** — 이 claim 은 Andrew Fuller, *The Works of the Rev.
> Andrew Fuller* (공개 도메인 OCR 원본)에서 자동 추출되었습니다. 페이지
> 번호가 없어 인용 위치는 heading·문단 기준입니다. 신뢰도 값은 교정되지
> 않았습니다. 자동 성구 추출에 일부 누락이 있을 수 있습니다. 권한 등급:
> 역사적 증언(historical_witness).
>
> **Provenance Notice (EN)** — This claim was auto-extracted from Andrew
> Fuller, *The Works of the Rev. Andrew Fuller* (public-domain OCR).
> No page numbers — citations use heading/paragraph locators. Confidence
> values are uncalibrated. Some scripture references may be missing.
> Authority class: historical witness.

(B-1/B-2 완료로 RESUMPTION_PLAN §10 의 "대부분의 성구 참조가 누락됨" 강한
표현은 **철회**한다 — 현재 8권 1,000 refs 정상화됨. "일부 누락 가능" 로 대체.)

admission record rationale (lines 7–14) 의 기존 disclosure 문구와 정합하며
새 주장을 추가하지 않는다.

---

## 7. 변경하지 않는 것 (Freeze)

- **3,319 baseline** (`nae_tsu_v1`) — 재처리·재승인·migration·삭제 금지
  (ADR-030 §3.3, §11.4, §14). F5 는 additive-only.
- ADR-013 Qdrant isolation — Fuller 는 `nae_tsu_v1` 에만, DBMA core
  collection 무접촉.
- ADR-024 retrieval segment gate — F6 전까지 `modules.nae_pd.enabled = false`.
- ADR-030 §4 TSU Track 순서, §11 human-review 요구 (기계가 대체 불가).
- M2 SSOT (`NAE/pipeline/registration/state/source_manifest.yaml`),
  기존 admission records — 무변경.
- Retrieval Engine / Embedding Engine 코드 — 무변경.

---

## 8. Proposed → Approved 승격 조건 (Evidence Before Promotion Rule)

1. F2–F6 파이프라인 단계 **구현** (F5 additive upsert 스크립트 포함)
2. **회귀 통과** — `nae_corpus_reconcile.py` drift 0, 인접 스위트 green,
   3,319 baseline 무결성
3. **C1 독립 검토** 완료 (본 Amendment + F4/F5/F6 구현)
4. **HQ 승인**

4조건 충족 전:
- **F2 (Vol.02–08 TSU 생성) 과 F3 (검수)** 는 production 무접촉이므로 HQ
  지시 하에 선행 가능.
- **F4 / F5 / F6** 는 본 Amendment 가 Approved 된 후에만 착수.

---

## 9. 관련 문서

- `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` §11, §12 N-9
- `docs/NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` (우산 계획, F0–F6, §10 백로그)
- `docs/NAE_FULLER_HOLD_RELEASE_HQ_DECISION_REQUEST_001.md` (HQ 결정 B)
- `docs/NAE_FULLER_CANONICAL_VERIFICATION_001.md` (F1, provenance·locator)
- `docs/NAE_FULLER_B1_SCRIPTURE_EXTRACTOR_REPORT_C1_001.md` ·
  `docs/NAE_FULLER_B2_RENORMALIZE_REPORT_C1_001.md` (추출기 수정·재-정제)
- `docs/NAE_FULLER_TSU_PIPELINE_C1_REVIEW_RESULT_001.md` (P-4 C1 Review, GREEN/YELLOW)
- `docs/NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` ·
  `docs/NAE_FULLER_VOL01_REVIEW_PROCEDURE_v1.md`
