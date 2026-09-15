# NAE Fuller Vol.01–08 처리 재개 작업 순서 (v1)

**작성일**: 2026-09-08
**작성자**: CUE
**대상**: Andrew Fuller, *The Works of the Rev. Andrew Fuller, in Eight Volumes* (`author_id: fuller_andrew`, `BAP-MISS-FULLER-VOL01`–`VOL08`)
**Governing Authority**: ADR-030 v2.1 (§4 TSU Track, §11 Human Eligibility Governance, §12 N-9), ADR-029 (Research Corpus Pipeline Lock), ADR-021 (Registration), ADR-024 (Retrieval Segment Gate)
**성격**: 계획 문서 — 이 문서는 어떤 처리도 수행하지 않으며, 각 Phase는 별도 HQ 승인 후 착수한다.

---

## 1. 문서 목적

Fuller Vol.01–08은 2026-08-29 **ADMITTED** (`NAE/governance/corpus_admissions.jsonl` lines 7–14, commit `6b77df6`) 되었으나
**PROCESSING = HOLD** 상태다. 이 문서는 "앱 사용자가 검색·인용으로 Fuller 내용을 받을 수 있는 상태"까지
도달하는 데 필요한 작업을 순서·게이트·산출물·검증 기준으로 정리한다.

---

## 2. 현재 상태 (2026-09-08 점검 결과)

ADR-030 §11.1 4단계 기준:

| 단계 | Vol.01 | Vol.02–08 | 근거 |
|---|---|---|---|
| ACQUIRED (raw + 무결성) | ✅ | ✅ (8/8) | registration `QUALITY_PASSED` (2026-08-15); raw sha256 3-way MATCH (disk = M2 = `raw_checksum_ledger.jsonl`) |
| ADMISSION DECISION | ✅ | ✅ (8/8) | `corpus_admissions.jsonl` lines 7–14, `track: "tsu"`, `authority_class: historical_witness` |
| 추출/정제 (canonical) | ✅ status=ok | ✅ status=ok (8/8) | `NAE/corpus/canonical/Fuller_Complete_Works_Vol0x/normalize_report.json` (2026-08-07 생성, gitignore 대상 · 로컬/NAS 산출물) |
| 청킹 (TSU 생성) | ⚠️ 생성만 3,643 claims | ❌ **미생성** | `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/` 만 존재 (`tsu.json`, `tsu_report.json`) |
| EMBEDDING ELIGIBLE (`review_status == verified`) | ❌ 3,643건 전량 `generated` | ❌ | `tsu.json` 레코드 전수 `review_status: generated`; `NAE/review/human/decisions/`에 Fuller 없음 |
| EMBEDDED | ❌ | ❌ | `NAE/corpus/embeddings/` 비어 있음 |
| INDEXED (`nae_tsu_v1`) | ❌ | ❌ | `review_gate.py` `EMBEDDING_ELIGIBLE_STATUSES = {verified}` — 구조적 차단 |
| RETRIEVAL-ELIGIBLE | ❌ | ❌ | `config.yaml modules.nae_pd.enabled = false` (ADR-024) |

**결론**: 앱 사용자는 현재 Fuller 내용을 검색 결과·인용으로 받을 수 없으며, 받아서도 안 된다.
이는 결함이 아니라 HQ 결정(PROCESSING HOLD, ADR-030 §12 N-9)에 따른 의도된 상태다.

### 2.1 확인된 품질 한계 (canonical `normalize_report.json` 실측, Vol.01 예시)

- `source = ocr`, `page_count = 1` → **page-level citation provenance 없음** (모든 문단이 page 1)
- `footnotes_extracted = 0` (8/8)
- `verse_paragraph_count = 0` (Vol.05만 1)
- `scripture_references_found` 편차: Vol.01 = 2, **Vol.03 / Vol.07 = 0**
- TSU 신뢰도(Vol.01)는 모델 self-report (uncalibrated), 생성 모델 `my-theology-bot-v2:latest`

이 한계는 `authority_class = historical_witness` (claim이 저작에 귀속되며 page-level scholarly
citation certification이 목적이 아님) 범위에서 수용 가능하나, retrieval/citation UI 노출 시 반드시
disclosure 되어야 한다 (8개 admission record `rationale`에 이미 명시됨).

---

## 3. 선행 조건 (Phase 착수 전 필수)

| # | 조건 | 근거 | 현재 |
|---|---|---|---|
| P-1 | **HQ의 PROCESSING HOLD 해제 결정** — Vol 단위 또는 전 8권 일괄, 명시적 지시 | ADR-030 §12 N-9 ("TSU/review/embedding 후속 승인 대기") | 미승인 |
| P-2 | **ADR-030 Amendment 또는 처리 지시서** — HOLD 해제 범위, provenance 한계 수용 명문화, citation disclosure 정책 확정 | ADR-030 §11.2 신규 자료 flow; Architecture Freeze Rule | 미작성 |
| P-3 | **ADR-029 Pipeline Lock 정합 확인** — Fuller 처리가 현재 PHASE(‑1 Korean Terminology 진행 중)와 리소스·순서 충돌하지 않는지 | ADR-029 (Research Corpus Pipeline Lock) | 확인 필요 |
| P-4 | **C1 Review 요청** — TSU pipeline 재진입은 ADR-030 "TSU Pipeline 진입 직전" C1 Review 트리거에 해당 | CLAUDE.md CUE Operating Policy "C1 Review 요청 시점" | 미요청 |
| P-5 | **3,319 production baseline 동결 확인** — Fuller 처리가 `nae_tsu_v1` 기존 3,319 point를 건드리지 않음(별도 collection 아님, additive only) | ADR-030 §3.3 CLEAN 영역 동결 | 설계 시 보장 |

P-1 ~ P-4가 모두 충족되기 전에는 Phase F1 이하를 착수하지 않는다.

---

## 4. 작업 순서

```
F0  HOLD 해제 + 거버넌스 정비        (HQ / CUE / C1)
 │
F1  Canonical 재검증 + provenance 한계 확정   (Vol.01–08)
 │
F2  TSU 생성                          (Vol.02–08, 7권)
 │
F3  인간 검수 → review_status=verified 승격   (Vol.01–08, 8권)
 │
F4  임베딩                            (verified TSU only)
 │
F5  Qdrant 인덱싱                     (nae_tsu_v1, additive)
 │
F6  Retrieval 활성화 + 벤치 + reconciliation
```

각 Phase는 **완료 게이트를 통과해야** 다음 Phase로 넘어간다. Phase 간 자동 진행 없음.

---

### F0 — HOLD 해제 + 거버넌스 정비

| 항목 | 내용 |
|---|---|
| 입력 | 본 문서, `CUE-FULLER-ADMISSION-READINESS-PACKAGE.md`, ADR-030 v2.1 |
| 작업 | ① HQ가 PROCESSING HOLD 해제 범위 결정 (P-1) ② ADR-030 Amendment/처리 지시서 작성 — provenance 한계 수용, citation disclosure 규칙, 처리 순서 고정 (P-2) ③ ADR-029 정합 확인 (P-3) ④ C1 Review 요청·완료 (P-4) |
| 산출물 | ADR-030 Amendment 문서 (Proposed → 4조건 충족 시 Approved), C1 Review 결과 |
| 완료 게이트 | HQ 승인 + C1 Review GREEN + ADR Amendment 승인 |
| Mutation | Corpus 0 / TSU 0 / Embedding 0 / Qdrant 0 (문서만) |

---

### F1 — Canonical 재검증 + provenance 한계 확정

| 항목 | 내용 |
|---|---|
| 입력 | `NAE/corpus/canonical/Fuller_Complete_Works_Vol0x/{canonical.json, canonical.txt, normalize_report.json}` (8권, 로컬/NAS) |
| 작업 | ① 8권 canonical 파일 존재·무결성 확인 (git 미추적이므로 로컬/NAS 실체 확인) ② `normalize_report.json` 8권 집계: `paragraph_count`, `scripture_references_found`, `footnotes_extracted`, `verse_paragraph_count` ③ Vol.03 / Vol.07 `scripture_references_found = 0` 재확인 — OCR 품질 문제인지 원문 특성인지 판단 ④ page_count=1 → citation에서 어떤 locator를 쓸지 확정 (예: paragraph index, heading 경로) ⑤ 재-정제(re-normalize) 필요 여부 결정 — 필요 시 pipeline_version 최신으로 재실행 |
| 산출물 | `docs/NAE_FULLER_CANONICAL_VERIFICATION_001.md` (8권 집계 표 + provenance 한계 확정 + citation locator 규칙) |
| 완료 게이트 | 8권 canonical status=ok 확인 + citation locator 규칙 승인 + 재-정제 필요 시 완료 |
| 도구 | `NAE/pipeline/registration/` (재실행 시), 신규 read-only 집계 스크립트 |
| Mutation | canonical 재-정제 시에만 canonical mutation (지시서 명시 범위 내) |

---

### F2 — TSU 생성 (Vol.02–08)

| 항목 | 내용 |
|---|---|
| 입력 | Vol.02–08 canonical (7권) |
| 작업 | ① `NAE/pipeline/tsu/runner.py` 로 Vol.02–08 순차 TSU 생성 (builder v3.0.0 기준) ② Vol.01은 이미 3,643 claims 생성됨 — **재생성하지 않음** (단 builder 버전/모델 불일치 시 재생성 여부 F0 지시서에서 결정) ③ 생성 모델·doctrine 분류기 버전 고정 (Vol.01은 `my-theology-bot-v2:latest`) ④ 각 권 `tsu.json` + `tsu_report.json` 생성, `review_status: generated` ⑤ `NAE/pipeline/ingest/state/incremental_state.json` 에 TSU 단위 `ProcessingState` 기록 |
| 산출물 | `NAE/corpus/tsu/Fuller_Complete_Works_Vol02..08/` (7개 디렉터리), 권별 `tsu_report.json` |
| 완료 게이트 | 7권 `partial: false` + `llm_errors` 허용 임계 이하 + doctrine_breakdown 이상치 없음 + 총 claim 수 리포트 |
| 도구 | `NAE/pipeline/tsu/{runner.py, builder.py, worker/}` |
| Mutation | TSU 생성 (additive, Fuller 신규 디렉터리만) |
| 참고 | Vol.01 소요 실측 ≈ 57,726초(약 16시간) / 5,452 candidates → 3,643 claims. 7권 예상 규모 ≈ 2만~2.5만 claims, 다일(多日) 작업. worker queue 사용 권장 |

---

### F3 — 인간 검수 → `review_status = verified` 승격

| 항목 | 내용 |
|---|---|
| 입력 | Vol.01–08 `tsu.json` (`generated` 상태, 총 ≈ 2.4만~2.9만 claims) |
| 작업 | ① `NAE/review/human/batch_manager.py` 로 배치 생성 (Dagg/Hiscox 선례: batch 0001–0036) ② reviewer(David)가 배치별 검수 → `NAE/review/human/decisions/batch_XXXX_decisions.json` ③ `NAE/pipeline/tsu/review_promotion.py` 로 `generated → verified`(승인) / `rejected`(탈락) 승격 ④ `NAE/pipeline/tsu/review_gate.py` `filter_embedding_eligible()` 통과분만 다음 단계 ⑤ rejected claim 처리 정책(폐기/재생성) 확정 |
| 산출물 | `NAE/review/human/decisions/` Fuller 배치 파일, 승격 후 `tsu.json` (`review_status` 갱신), 검수 요약 리포트 |
| 완료 게이트 | 8권 전량 disposition 완료 (`generated` 잔여 0) + verified 비율 리포트 + audit trail 완비 |
| 도구 | `NAE/review/human/`, `NAE/pipeline/tsu/{review_promotion.py, review_gate.py}` |
| Mutation | `tsu.json::review_status` (disposition 결과 기록), `NAE/review/human/decisions/` (append) |
| 리스크 | **최대 병목.** claim 규모가 크고 검수는 사람 작업. ADR-027 `ReviewStateV2` 활용 여부 F0에서 결정 |

---

### F4 — 임베딩

| 항목 | 내용 |
|---|---|
| 입력 | `review_status == "verified"` Fuller TSU only |
| 작업 | ① `NAE/pipeline/embed/client.py` 로 verified claim 임베딩 (`bge-m3:latest`, ADR 기준 모델 고정) ② `NAE/pipeline/embed/hashing.py` 로 중복/변경 감지 ③ 벡터 차원·정규화 기존 `nae_tsu_v1`(3,319 point)과 동일 확인 ④ `ProcessingState.EMBEDDED` 기록 |
| 산출물 | 임베딩 벡터 (staging), embed 리포트 |
| 완료 게이트 | verified 건수 = 임베딩 건수 + 차원/모델 일치 검증 |
| 도구 | `NAE/pipeline/embed/` |
| Mutation | Embedding (Fuller verified only) |
| 게이트 근거 | ADR-030 §11.1 EMBEDDING ELIGIBLE = TSU track `review_status == "verified"` |

---

### F5 — Qdrant 인덱싱 (`nae_tsu_v1`, additive)

| 항목 | 내용 |
|---|---|
| 입력 | F4 임베딩 벡터 + payload 메타데이터 |
| 작업 | ① `NAE/pipeline/index/qdrant_store.py` + `runner.py` 로 `nae_tsu_v1` 에 **additive upsert** ② 기존 3,319 point 무접촉 확인 (ID 충돌 없음) ③ payload: `source_id`, `authority_class: historical_witness`, `content_genre`, `theological_category`, `tradition: Particular Baptist`, citation locator(F1 규칙), provenance 한계 플래그 ④ ADR-013 Qdrant isolation 준수 (DBMA core collection과 분리) ⑤ `ProcessingState.INDEXED` 기록 |
| 산출물 | `nae_tsu_v1` 갱신 (point 수: 3,319 → 3,319 + Fuller verified), `index_report.json` 갱신 |
| 완료 게이트 | live count = 3,319 + Fuller verified + 3,319 baseline 무결성 확인 |
| 도구 | `NAE/pipeline/index/` |
| Mutation | Qdrant `nae_tsu_v1` (additive only) |
| 예외 처리 | CLAUDE.md 예외 목록: "Retrieval Engine 변경"이 아닌 **데이터 additive ingestion**이므로 자동화 범위 내이나, 규모가 크므로 F0 지시서에서 승인 범위 명시 |

---

### F6 — Retrieval 활성화 + 벤치 + reconciliation

| 항목 | 내용 |
|---|---|
| 입력 | 인덱싱 완료된 `nae_tsu_v1` |
| 작업 | ① `config.yaml modules.nae_pd.enabled` 활성화 여부·범위 결정 (ADR-024 retrieval segment gate) ② `scripts/nae_corpus_reconcile.py` (read-only) 실행 — M2 ↔ `incremental_state.json` ↔ `tsu.json::review_status` ↔ Qdrant count drift 0 확인 ③ 벤치 데이터셋에 Fuller 질의 추가 → precision/recall 회귀 확인 ④ citation UI가 provenance 한계(page 없음)를 올바르게 disclosure 하는지 확인 ⑤ 앱(`dbma_ui.py` → `ui/app.py`) 실검색으로 Fuller claim 반환·인용 표시 확인 |
| 산출물 | `docs/NAE_FULLER_RETRIEVAL_VERIFICATION_001.md`, 벤치 결과, reconciliation "No drift" 로그 |
| 완료 게이트 | drift 0 + 벤치 회귀 없음(3,319 baseline 품질 유지) + 앱 실검색 정상 + citation disclosure 정상 |
| 도구 | `scripts/nae_corpus_reconcile.py`, benchmark suite, `core/retrieval.py` |
| Mutation | `config.yaml` (retrieval gate), 문서 |

---

## 5. 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 검수(F3) 병목 — 수만 claim | 재개 전체 지연 | 권 단위 부분 릴리스 허용(F0에서 결정), ADR-027 ReviewStateV2 활용 검토 |
| page-level provenance 부재 | citation 신뢰도·학술 인용 한계 | `historical_witness` 범위 수용 + UI disclosure 필수 (P-2) |
| Vol.03 / Vol.07 scripture ref = 0 | scripture 기반 retrieval 커버리지 낮음 | F1에서 원인 규명, 필요 시 재-정제 |
| OCR 노이즈가 TSU claim 품질 저하 | 잘못된 claim이 verified로 통과 | F3 검수 기준에 OCR 아티팩트 탈락 규칙 추가 |
| 3,319 baseline 오염 | production 회귀 | F5 additive-only 강제, F6 reconciliation + 벤치 회귀 게이트 |
| builder/모델 버전 불일치 (Vol.01 vs Vol.02–08) | claim 일관성 저하 | F0에서 Vol.01 재생성 여부 확정 |
| ADR-029 Pipeline Lock 충돌 | 거버넌스 위반 | P-3 정합 확인 필수 |

---

## 6. 예상 규모 (참고, 미확정)

| 항목 | 근거 | 추정 |
|---|---|---|
| TSU 생성 (Vol.02–08) | Vol.01 = 3,643 claims / 5,452 candidates / ≈16h | 7권 ≈ 2.0만~2.5만 claims, 다일 배치 |
| 인간 검수 총량 | Vol.01–08 합산 | ≈ 2.4만~2.9만 claims |
| 임베딩 | verified only (검수 통과율 가정 필요) | 검수 결과에 종속 |
| `nae_tsu_v1` 최종 | 3,319 + Fuller verified | 검수 결과에 종속 |

---

## 7. 체크리스트

```md
### 선행 조건
- [ ] P-1 HQ PROCESSING HOLD 해제 결정
- [ ] P-2 ADR-030 Amendment / 처리 지시서 승인
- [ ] P-3 ADR-029 Pipeline Lock 정합 확인
- [ ] P-4 C1 Review 완료 (TSU pipeline 진입)
- [ ] P-5 3,319 baseline 동결 보장 설계 확인

### Phase
- [ ] F0 HOLD 해제 + 거버넌스 정비
- [ ] F1 Canonical 재검증 + provenance 한계 확정 (Vol.01–08)
- [ ] F2 TSU 생성 (Vol.02–08)
- [ ] F3 인간 검수 → review_status=verified (Vol.01–08)
- [ ] F4 임베딩 (verified only)
- [ ] F5 Qdrant 인덱싱 (nae_tsu_v1, additive)
- [ ] F6 Retrieval 활성화 + 벤치 + reconciliation

진행률: 0% (선행 조건 미충족 — 착수 불가)
```

---

## 8. 관련 문서

- `NAE/governance/corpus_admissions.jsonl` (lines 7–14) — Fuller admission 기록
- `docs/agents/cue/CUE-FULLER-ADMISSION-READINESS-PACKAGE.md` — admission readiness (2026-08-29)
- `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` — §4 TSU Track, §11 Human Eligibility Governance, §12 N-9
- `docs/architecture/ADR-029-NAE-Research-Corpus-Expansion-Pipeline-Lock.md`
- `docs/architecture/ADR-024` — Retrieval Segment Gate (`modules.nae_pd.enabled`)
- `docs/architecture/ADR-013` — Qdrant isolation
- `NAE/pipeline/tsu/review_gate.py` — `EMBEDDING_ELIGIBLE_STATUSES = {verified}`

---

## 9. 정합 갱신 — Vol.01 파일럿 편입 (2026-09-08, HQ 승인)

본 문서는 **우산(umbrella) 계획**으로 채택됨. 별도로 진행된 **Vol.01
파일럿 트랙**(`dev/dbma-engine` `177e981`)을 그 하위 인스턴스로 편입한다.
근거: `docs/NAE_FULLER_PLAN_RECONCILIATION_001.md` (HQ 승인 2026-09-08).

### 9.1 §2·§3 상태 재기술 (Vol.01 한정)

| 항목 | 본문 §2/§3 기재 | Vol.01 파일럿 실제 |
|---|---|---|
| P-1 HOLD 해제 | "미승인" | **HQ 결정 B (2026-09-08)** — Vol.01 한정 처리 승인, Vol.02–08 HOLD 유지 (`NAE_FULLER_HOLD_RELEASE_HQ_DECISION_REQUEST_001.md` §7) |
| P-4 C1 Review | "미요청" | **요청 예정** — `NAE_FULLER_TSU_PIPELINE_C1_REVIEW_REQUEST_001.md` (2026-09-08 발행) |
| F3 검수 방식 | `batch_manager.py` + 균일 | **전용 드라이버 + tiered(P1/P2)** — `scripts/nae_fuller_vol01_review_batches.py`, `batch_manager.py::TSU_IDENTIFIERS` 하드코딩 회피. 설계: `NAE_FULLER_VOL01_TIERED_REVIEW_DESIGN_v1.md` (APPROVED) |
| Vol.01 배치 | 미생성 전제 | **생성·커밋됨** — `NAE/review/human/requests/fuller_v01_batch_0001..0037_requests.json` + `fuller_v01_MANIFEST.json` (3,643 claims, Q1–Q3, P1 176 / P2 3,467) |
| 검수 질문 | — | **Q1–Q3 표준** + flag 시 Q4 + citations 26건 CIT 확인 (HQ 승인) |

### 9.2 Phase 매핑

| 우산 Phase | Vol.01 파일럿 대응 | 상태 |
|---|---|---|
| F0 | Preflight + HQ 결정 B + tiered 설계 승인 | ✅ 완료 (C1 Review P-4는 미이행) |
| F1 | — (파일럿이 건너뜀) | ⏳ **선행 실행 중** (본 갱신으로 지시) |
| F2 (Vol.01) | 이미 생성된 3,643 claims | ✅ (재생성 안 함) |
| F2 (Vol.02–08) | 범위 밖 (HOLD) | ⛔ |
| F3 (Vol.01) | tiered 검수 배치 준비 완료, David 착수 대기 | 🔜 F1 완료 후 |
| F4–F6 | 파일럿 Phase 3 | ⛔ |

### 9.3 확정된 선행 순서 (HQ 2026-09-08)

1. `05e6871` → `dev/dbma-engine` 병합 ✅ (`21a6f29`)
2. **F1** (canonical 8권 재검증 + provenance 한계 + citation locator + disclosure) — David 검수 착수 **전**
3. **C1 Review (P-4)** 요청 — TSU pipeline 진입 트리거
4. (미결) ADR-030 Amendment (P-2) 범위 — HQ 추후 결정
5. F1 GREEN + C1 Review GREEN → David 검수(F3 Vol.01) 착수 (일정 = HQ 신호)

---

## 10. F0 백로그 (2026-09-08 등록)

| # | 항목 | 근거 | 상태 | 조건 |
|---|---|---|---|---|
| B-1 | **Scripture 추출기 수정** — `NAE/pipeline/canonical/annotate.py`: `_ROMAN_MAP` 확장(≥ clxxx), 한글 성서명 지원, OCR 노이즈 내성 (`_LEGACY_REF`/`_ARABIC_REF`) | F1 T3 (`NAE_FULLER_CANONICAL_VERIFICATION_001.md`) — 전 8권 체계적 추출 실패 (Vol.01 리포트 2 vs 실제 수백) | OPEN | **Vol.02–08 확장(F2) 착수 전 완료 필수.** Vol.01 파일럿은 옵션 (b)로 선진행 |
| B-2 | B-1 완료 후 Fuller canonical **재-정제(re-normalize)** — 8권, `pipeline_version` 최신 | B-1 | BLOCKED (B-1) | 재-정제 시 canonical mutation 지시서 명시 범위 |

### 결정 기록 (HQ 2026-09-08)

- Vol.01 파일럿 = **옵션 (b)** 진행: 현 canonical 그대로 F3–F5, scripture
  메타데이터 불완전을 **강한 disclosure**로 명시, 추출기 수정(B-1)은 별도 트랙.
- **강한 disclosure 문구** (F1 T5 갱신, F6 UI 반영):
  > 자동 성구 추출의 한계로 **이 저작의 성구 참조 대부분이 색인에서 누락**되어
  > 있습니다. 성구 기반 검색·교차참조는 Fuller 자료에 대해 불완전합니다.
  > (EN) Due to automated scripture-extraction limits, **most scripture
  > references in this work are missing from the index**; scripture-based
  > search and cross-referencing are incomplete for Fuller material.
- Vol.02–08 확장은 B-1 완료를 조건으로 한다.
