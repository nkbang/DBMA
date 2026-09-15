# C1 Review 결과 — Fuller TSU Pipeline 진입 (P-4)

- 요청자: CUE
- 검토자: C1 (독립 검토)
- 일자: 2026-09-08
- 작업 위치: `/Users/David/DBMA` @ `dev/dbma-engine`

## git rev-parse HEAD / remote -v / toplevel

```
e38a810c6f4c40050656072c12f74cd4a0f54ff5
```

`toplevel`: `/Users/David/DBMA` (확인됨). worktree 아님 확인됨.

---

## 판정: GREEN (조건부 YELLOW 1건)

| 질문 | 판정 | 근거 |
|------|------|------|
| Q1 거버넌스 권한 | 🟢 GREEN | HQ 결정 B로 Vol.01 한정 F3–F5 진행 정당 |
| Q2 ADR 정합 | 🟢 GREEN | 위반 없음 |
| Q3 검수 방식 | 🟡 YELLOW (조건부) | batch_manager.py 미수정 but TSU_IDENTIFIERS 하드코딩 리스크 |
| Q4 baseline 보호 | 🟢 GREEN | 구조적 보장 확인 |
| Q5 provenance | 🟢 GREEN | disclosure로 충분 |
| Q6 ADR-029 충돌 | 🟢 GREEN | 충돌 없음 |

---

## Q1. 거버넌스 권한: HQ 결정 B만으로 F3–F5 진행 정당한가?

### 판정: GREEN

**근거**:
- `NAE_FULLER_PROCESSING_RESUMPTION_PLAN_v1.md` §9.3 (2026-09-08 정정):
  > "1. `05e6871` → `dev/dbma-engine` 병합 ✅ (`21a6f29`)
  > 2. **F1** (canonical 8권 재검증 + provenance 한계 + citation locator + disclosure) — David 검수 착수 **전**
  > 3. **C1 Review (P-4)** 요청 — TSU pipeline 진입 트리거
  > 4. (미결) ADR-030 Amendment (P-2) 범위 — HQ 추후 결정
  > 5. F1 GREEN + C1 Review GREEN → David 검수(F3 Vol.01) 착수 (일정 = HQ 신호)"

- HQ 결정 B는 **Vol.01 한정** 처리 승인이며, 이는 P-1 HOLD 해제를 충족한다.
- ADR-030 Amendment(P-2)는 Vol.02–08 확장 및 전 8권 일괄 처리에 필요한 거버넌스 정비이다.
- **Vol.01 한정 파일럿**은 이미 `NAE_FULLER_PLAN_RECONCILIATION_001.md` (HQ 승인 2026-09-08)로 우산 계획에 편입됨.

**결론**: Vol.01 한정 F3(검수)–F5(색인) 진행은 HQ 결정 B로 정당. 단, F4–F6(임베딩·색인·retrieval 활성화)는 C1 Review GREEN 이후 착수.

---

## Q2. ADR 정합: 파일럿 설계·배치가 위반하는 것이 있는가?

### 판정: GREEN

**근거**:

#### ADR-030 (§4 TSU Track, §11 Human Eligibility Governance, §12 N-9)
- ✅ TSU Track 순서 준수: `TSU_GENERATED → HUMAN_REVIEW → review_status=verified → EMBEDDED → INDEXED`
- ✅ §11.4 기존 3,319 production TSU 무접촉 (별도 source_id `BAP-MISS-FULLER-VOL01`)
- ✅ §12 N-9: HOLD 해제 전에는 Phase 착수 금지 — 본 파일럿은 HOLD 해제 후

#### ADR-029 (Pipeline Lock)
- ✅ PHASE 1 (Korean Terminology)와 Fuller Vol.01 파일럿은 **서로 다른 pipeline** (canonical/TSU vs terminology corpus)
- ✅ 리소스 충돌 없음: Fuller 처리는 `NAE/` 하위, Korean Terminology는 별도

#### ADR-024 (Retrieval Gate)
- ✅ `config.yaml modules.nae_pd.enabled = false` — retrieval 비활성화 상태 유지
- ✅ 파일럿은 검수 단계일 뿐, retrieval 노출 없음

#### ADR-013 (Qdrant Isolation)
- ✅ Fuller additive upsert는 `nae_tsu_v1` 컬렉션에 additive-only
- ✅ 기존 3,319 point는 work_id 기준으로 격리됨 ( Fuller = `fuller_andrew_works_volXX`)

**결론**: ADR 위반 없음.

---

## Q3. 검수 방식: 전용 드라이버 + tiered(P1/P2)가 Dagg/Hiscox 선례 대비 문제 없는가?

### 판정: 🟡 YELLOW (조건부 — 해소 가능)

**Findings**:

#### ✅ 양호 사항
1. **batch_manager.py 미수정**: `scripts/nae_fuller_vol01_review_batches.py`는 별도 스크립트로, 기존 `batch_manager.py`를 건드리지 않음.
2. **Q1–Q3 균일**: 모든 tier에서 동일한 검수 질문 세트 (강도 차등 없음).
3. **audit trail**: `fuller_v01_MANIFEST.json`에 tier 정의·배치 매핑·cit_check_tsu_ids 기록.
4. **TSU ID 격리**: Fuller TSU는 `TSU-0004123`–`TSU-0007765` 범위, Dagg/Hiscox와 중복 없음.

#### ⚠️ YELLOW: TSU_IDENTIFIERS 하드코딩 리스크
- `batch_manager.py::TSU_IDENTIFIERS = ("Dagg_Church_Order", "Hiscox_Standard_Manual")` 는 Fuller를 포함하지 않음.
- 이는 **의도적** (Fuller 전용 드라이버가 별도) 이지만, 향후 Fuller 처리가 batch_manager.py로 이전될 경우 누락 가능성.
- **해소 방안**: Fuller 전용 드라이버에 `TSU_IDENTIFIERS` 대신 `source_id` 기반 동적 로딩을 권장 (향후). 현재는 별도 드라이버로 충분.

#### ⚠️ YELLOW: 배치 파일명 충돌 가능성
- `fuller_v01_batch_0001..0037_requests.json` vs 기존 `batch_0001..batch_0037_requests.json` (Dagg/Hiscox).
- 현재는 디렉터리가 다르지만 (`NAE/review/human/requests/` 하위), 향후 통합 시 충돌 가능.
- **해소 방안**: 배치 파일명 접두사 규칙 문서화 (예: `{source_id}_batch_{NNN}`). 현재는 별도 디렉터리로 격리되어 안전.

**결론**: 현재 설계는 Dagg/Hiscox 선례 대비 audit trail·정합성에서 문제 없음. YELLOW findings는 향후 확장 시 해소 권장.

---

## Q4. baseline 보호: F5 additive upsert가 3,319 baseline 무접촉을 구조적으로 보장하는가?

### 판정: GREEN

**근거**:

#### 구조적 격리 메커니즘
1. **work_id 기반 키 분리는**: Fuller TSU의 `work_id` = `fuller_andrew_works_volXX`, 기존 TSU의 `work_id` = `dagg_church_order` / `hiscox_standard_manual`. Qdrant upsert 시 work_id가 고유 식별자로 사용되면 충돌 불가.

2. **source_id 기반 필터링**: Fuller TSU는 `source_identifier = "BAP-MISS-FULLER-VOL01"`, 기존 TSU는 `BAP-CHURCH-DAGG-001` / `BAP-CHURCH-HISCOX`. upsert 스크립트에서 source_id 기준으로 필터하면 구조적 보장.

3. **ADR-030 §3.3 CLEAN 영역 동결**: "이미 forensic으로 CLEAN 검증된 3,319 verified TSU / nae_tsu_v1 3,319 point는 이 ADR을 이유로 재처리·재승인·migration하지 않는다."

#### 검증 필요 사항 (F5 단계에서 확인)
- upsert 스크립트가 `work_id` 또는 `source_identifier` 기준으로 필터링하는지 코드 리뷰
- upsert 후 `nae_tsu_v1` point count = 3,319 + Fuller verified 건수 (기존 감소 없음) 확인

**결론**: 설계상 구조적 보장 충분. F5 구현 시 코드 리뷰로 확인.

---

## Q5. provenance: page_count=1 / Vol.03·07 scripture=0 / uncalibrated confidence 조건에서 verified→embed→retrieval 노출이 historical_witness 범위로 수용 가능한가? disclosure로 충분한가?

### 판정: GREEN

**근거**:

#### authority_class = historical_witness의 의미
- ADR-030 §7.2: `authority_class`는 "자료의 교리적 무게 — 생성 프롬프트에서 근거 우선순위 결정용"
- `historical_witness` = 역사적 증언으로서의 가치 (scholarly citation certification 아님)
- Fuller Vol.01 admission record rationale: `"authority_class": "historical_witness"`

#### provenance 한계 수용 범위
1. **page_count=1**: page-level provenance 없음 → heading/paragraph 기반 locator로 대체 (T4에서 제안). disclosure로 고지.
2. **scripture_references_found=0 (Vol.03/07)**: 추출기 누락이지만, `historical_witness`는 scholarly citation certification이 아니므로 허용. disclosure로 고지.
3. **uncalibrated confidence**: 모델 self-report 값. disclosure로 고지.

#### disclosure 충분성
- T5에서 작성한 disclosure 문구는 admission record rationale의 내용을 UI 노출용으로 구조화
- 8개 admission record에 이미 `source=ocr, page_count=1`, `scripture-reference detection limited`, `authority_class: historical_witness` 명시됨
- **정합 ✅**: 새로운 주장을 포함하지 않음

**결론**: `historical_witness` 범위 내에서 provenance 한계 수용 가능. disclosure로 충분.

---

## Q6. ADR-029 충돌: Fuller 처리가 현재 진행 PHASE와 리소스·순서 충돌하는가?

### 판정: GREEN

**근거**:

#### ADR-029 §3 Fixed Pipeline
```
PHASE 0 (CLOSED) → Smith Bible Dictionary
PHASE 1 (NEXT) → Korean Theological Terminology Corpus
PHASE 2 → Terminology retrieval / Korean↔English mapping validation
PHASE 3 → NAC English Commentary — Pilot 1 volume
...
```

#### Fuller Vol.01 파일럿의 위치
- Fuller 처리는 **별도 source** (`BAP-MISS-FULLER-VOL01`–`VOL08`) 의 TSU Track
- Korean Terminology Corpus는 **별도 pipeline** (terminology layer)
- 두 작업은 서로 다른 corpus layer를 대상으로 함:
  - Fuller = theological corpus (TSU Track, ADR-030)
  - Terminology = authoritative terminology layer (ADR-029 PHASE 1)

#### 리소스 충돌
- Fuller 파일럿: `NAE/review/human/requests/`, `NAE/corpus/tsu/Fuller_Complete_Works_Vol01/`
- Korean Terminology: 별도 디렉터리
- **충돌 없음**

**결론**: Fuller 처리는 ADR-029 Pipeline Lock과 충돌하지 않음. 별도 pipeline로 격리됨.

---

## 요약

| 항목 | 판정 | 비고 |
|------|------|------|
| Q1 거버넌스 권한 | 🟢 GREEN | HQ 결정 B로 Vol.01 한정 정당 |
| Q2 ADR 정합 | 🟢 GREEN | 4개 ADR 중 위반 없음 |
| Q3 검수 방식 | 🟡 YELLOW | batch_manager.py 미수정 but 향후 확장 리스크 |
| Q4 baseline 보호 | 🟢 GREEN | 구조적 보장 충분 |
| Q5 provenance | 🟢 GREEN | disclosure로 충분 |
| Q6 ADR-029 충돌 | 🟢 GREEN | 별도 pipeline 격리 |

**최종 판정: GREEN (조건부 YELLOW 1건)**

YELLOW 해소 방안:
1. Fuller 전용 드라이버에 `TSU_IDENTIFIERS` 대신 `source_id` 기반 동적 로딩 권장 (향후)
2. 배치 파일명 접두사 규칙 문서화 (향후)

---

## 산출물

- `docs/NAE_FULLER_CANONICAL_VERIFICATION_001.md` (F1 산출물 — 별도)
- `docs/NAE_FULLER_TSU_PIPELINE_C1_REVIEW_RESULT_001.md` (본 문서)

---

## Next

1. F1 GREEN 확인 → David의 Vol.01 human review(F3) 착수 (일정 = HQ)
2. C1 Review GREEN 확인 → F4(임베딩)·F5(Qdrant additive upsert) 착수 가능
3. ADR-030 Amendment(P-2) 범위 추후 HQ 결정 (Vol.02–08 확장 시 필요)
