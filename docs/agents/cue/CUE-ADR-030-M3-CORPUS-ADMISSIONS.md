# CUE — ADR-030 v2.1 §12 M-3 · `corpus_admissions.jsonl` — RATIFIED

**작성자**: CUE · **작성일**: 2026-08-28 · **상태**: **RATIFIED** — HQ가 M3-1~M3-6 비준 + EXEC 명령 발부 (2026-08-28)
**대상**: `NAE/governance/corpus_admissions.jsonl` 신설 + 소급(back-fill) 항목 + admission flow 문서화
**baseline**: `dev/dbma-engine` @ `0931e0c` (A-2b-2 완료)
**ADR 근거**: ADR-030 v2.1 §11 (Human Eligibility Governance), §12 MUST M-3, §13, §15 Test N

> 진행: ① 규칙·스키마·항목 초안(본 문서) → ② HQ 검토·비준(§7) → ③ M-3 EXEC(파일 생성 + 항목 + flow 문서 + test)
> → ④ CUE 독립검증 → 커밋.

---

## 1. 무엇을 만들고, 무엇을 만들지 않는가

**만든다:**
- `NAE/governance/corpus_admissions.jsonl` — append-only JSONL. **한 줄 = 한 source 의 admission 결정 기록.**
- 이미 admission 이 사실상 성립한 source 6건의 **소급 항목** (Dagg, Hiscox, Smith Vol1–4).
- admission flow 를 SSOT 문서에 짧게 기록 (ADR §11.2 참조 포인터).
- governance test 1개 (파일·스키마·소급항목·M2 정합·무재처리 검증).

**만들지 않는다:**
- **코드 게이트 아님.** "admission 기록 없으면 TSU/chunking 시작 거부" 를 코드로 강제하는 것은
  ADR-019 `TSU_ELIGIBLE` = **S-4 (deferred)**. M-3 의 게이트는 **수기 확인**이다 (ADR §11.3).
- **새 state / enum 아님.** `RegistrationState` / `ProcessingState` 에 값 추가 없음.
- **재처리 아님.** 기존 3,319 verified TSU 재검수·재승인·재임베딩 없음. Smith `nae_ref_v1` 34,948 chunk
  재chunk·재인덱싱 없음. corpus / Qdrant / state store 무접촉 (ADR §11.4, §13).
- Fuller Vol01–08 항목 — **넣지 않는다** (§3.3).

---

## 2. Record 스키마 (ADR §11.3 확정)

JSONL 한 줄 = 아래 객체. 키 순서는 아래 순서 권장.

| 필드 | 타입 | 필수 | 값 |
|---|---|---|---|
| `source_id` | string | ✔ | M2 `source_id` (M2 에 존재해야 함) |
| `decided_by` | string | ✔ | `"David / HQ"` (OPEN-M3-2) |
| `date` | string `YYYY-MM-DD` | ✔ | admission 을 **기록한** 날짜 (OPEN-M3-3) |
| `track` | string | ✔ | `"tsu"` \| `"reference"` |
| `authority_class` | string | ✔ | M2 값과 동일 — `primary_doctrinal`\|`historical_witness`\|`reference`\|`application` |
| `content_genre` | string[] | ✔ | M2 값과 동일 (RATIFIED v1.1 §4.1) |
| `theological_category` | string[] | ✖ | M2 에 있으면 동일. 없으면 **키 생략** (OPEN-M3-4) |
| `tradition` | string | ✖ | M2 에 있으면 동일. 없으면 **키 생략** |
| `reference_quality_confirmed` | bool | reference track만 | `true` (indexed·운영 중). tsu track 은 **키 생략** |
| `rationale` | string | ✔ | 이 admission 이 성립하는 근거 (한 문장) |
| `evidence_refs` | string[] | ✔ | 근거 파일/경로 (실존해야 함 — 추측 금지) |

**정합 규칙**: `authority_class` / `content_genre` / `theological_category` / `tradition` 는 **M2 가 SSOT**이며,
admission 기록의 값은 그 시점 결정의 스냅샷으로서 M2 와 **일치해야 한다**. (test 로 강제.)

---

## 3. 소급(back-fill) 대상 판정

### 3.1 Dagg / Hiscox — TSU track, 기존 human review 로 admission+review 충족
실측:
- `NAE/corpus/tsu/Dagg_Church_Order/tsu.json`: verified **2,958** (+ rejected 22, generated 397)
- `NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json`: verified **361** (+ generated 379)
- 합계 verified **3,319** = `nae_tsu_v1` Qdrant point 수 = `incremental_state.json` INDEXED 수
- `NAE/review/human/decisions/` 40 파일, reviewer `David`, `final_decision: "APPROVED"`, 2026-08-09~11
- 두 source 전부 `registration_state.json` = `QUALITY_PASSED`

→ admission (track 배정 + authority/classification) + review 가 **이미 사실상 성립**. 소급 항목 1건씩 기록.

### 3.2 Smith Vol1–4 — reference track, registration + ADR-028 + 실제 indexing 으로 충족
실측:
- `docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md` — 4권 `QUALITY_PASSED` (ADR-021)
- `nae_ref_v1` Qdrant **34,948 chunk** (Smith Vol1–4, `content_type: reference_dictionary`) — forensic 재확인
- ADR-028 reference layer 대상, `authority_class=reference` (RATIFIED §7.3)
- M2 에 `BAP-REF-SMITH-VOL01~04` 등록

→ reference track admission 충족. `reference_quality_confirmed=true` (이미 indexed·조건부 heuristic 로 사용 중).
**소급 항목 vol별 4건** (admission 은 per-source, M2 에 4개 source_id 로 존재 — 1:1 유지, OPEN-M3-1).

### 3.3 Fuller Vol01–08 — 소급 항목 없음
- `registration_state.json` = `QUALITY_PASSED` 이나:
  - Vol01 TSU 생성됨(3,643) 이지만 **verified 0** (전부 `generated`)
  - Vol02–08 TSU 미생성
- ADR §11.4 소급 범위 = "기존 3,319 + Smith" 에 한함. Fuller = backlog (ADR §12 N-9).
- Fuller 의 admission 은 **Fuller 처리 재개 시 HQ 가 그때 결정**한다. M-3 에서 항목을 만들지 않는다.
- 결과: admission 기록 없는 source(Fuller ×8)는 §5 수기 게이트에 의해 TSU review→embedding 으로 진행 불가 —
  이것이 게이트가 의도대로 동작한다는 증거.

---

## 4. 확정 항목 — `corpus_admissions.jsonl` (verbatim, M-3 EXEC 소비)

6줄. 파일 끝 개행 1개. 각 줄은 위 §2 스키마.

```jsonl
{"source_id": "BAP-CHURCH-DAGG-001", "decided_by": "David / HQ", "date": "2026-08-28", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["church_practice"], "theological_category": ["ecclesiology"], "tradition": "Particular Baptist", "rationale": "Pre-existing human review (NAE/review/human/decisions/, reviewer David, 2026-08-09..11, APPROVED) retroactively satisfies admission + review; 2958 verified TSU already in nae_tsu_v1. Back-fill record only; no reprocessing.", "evidence_refs": ["NAE/review/human/decisions/", "NAE/corpus/tsu/Dagg_Church_Order/tsu.json", "NAE/pipeline/registration/state/registration_state.json"]}
{"source_id": "BAP-CHURCH-HISCOX", "decided_by": "David / HQ", "date": "2026-08-28", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["church_practice", "pastoral"], "theological_category": ["ecclesiology"], "tradition": "Particular Baptist", "rationale": "Pre-existing human review (NAE/review/human/decisions/, reviewer David, 2026-08-09..11, APPROVED) retroactively satisfies admission + review; 361 verified TSU already in nae_tsu_v1. Back-fill record only; no reprocessing.", "evidence_refs": ["NAE/review/human/decisions/", "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json", "NAE/pipeline/registration/state/registration_state.json"]}
{"source_id": "BAP-REF-SMITH-VOL01", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
{"source_id": "BAP-REF-SMITH-VOL02", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
{"source_id": "BAP-REF-SMITH-VOL03", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
{"source_id": "BAP-REF-SMITH-VOL04", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
```

**분포**: 6 항목 — tsu 2 (Dagg, Hiscox), reference 4 (Smith Vol1–4). Fuller 0. 파일 = **+6 lines / −0** (신규 파일).
`NAE/governance/` 디렉터리 신설.

---

## 5. 게이트 메커니즘 (수기 — 코드 게이트는 S-4)

- **규칙**: `corpus_admissions.jsonl` 에 `source_id` 항목이 없는 source 는 TSU 생성(TSU Builder) 또는
  reference chunking 을 **시작하지 않는다.** 현재는 작업 착수 시 **수기 확인** (담당자가 이 파일을 대조).
- **코드 강제 = 별도 S-4**: ADR-019 `processing_status=TSU_ELIGIBLE` 게이트를 `ProcessingState` /
  TSU Builder 에 배선하는 작업. M-3 범위 아님. 구현 시 이 파일이 그 게이트의 입력이 된다.
- **현 상태 검증** (M-3 test): admission 기록 있는 source(Dagg, Hiscox, Smith×4) 는 이미 처리 완료 상태와
  일치하고, 기록 없는 source(Fuller×8) 는 verified TSU / reference index 가 없음 — 게이트가 사실상 지켜짐.

---

## 6. Admission flow 문서화 (최소)

`docs/architecture/NAE-Manifest-Authority-SSOT.md` 에 짧은 절 추가 (분류표처럼 **복제 금지**, ADR §11.2 참조):

> ## Corpus Admission (ADR-030 v2.1 §11)
> `QUALITY_PASSED` 이후 · TSU 생성 / reference chunking 이전에, HQ 가
> `NAE/governance/corpus_admissions.jsonl` 에 admission 결정 1줄을 기록한다 (track / authority_class /
> classification / (reference 시) reference_quality_confirmed / rationale / evidence_refs).
> 이 기록이 없는 source 는 다음 단계로 진행하지 않는다 (현재 수기 게이트; 코드 강제 = ADR-030 S-4).
> 기존 3,319 verified TSU (Dagg·Hiscox) + Smith Vol1–4 는 소급 항목으로 충족 — 재처리 없음.
> Flow 상세: ADR-030 v2.1 §11.2.

새 파일을 만들지 않는다 (ADR §11 이 authority, SSOT 는 포인터).

---

## 7. M3-1 ~ M3-6 — RESOLVED (HQ 2026-08-28, 전부 CUE 권고안대로)

| # | 결정 |
|---|---|
| **M3-1** | Smith 소급 항목 = **vol별 4건** (per-source, M2 4 source_id 와 1:1). |
| **M3-2** | `decided_by` = `"David / HQ"`. |
| **M3-3** | `date` = **기록일 `"2026-08-28"`**. 근거일(review 2026-08-09~11 / Smith reg 2026-08-25)은 `rationale`/`evidence_refs` 에 인용. |
| **M3-4** | 부재 필드(Smith `theological_category`/`tradition`) = **키 생략** (`null`/`[]`/placeholder 금지). |
| **M3-5** | M-3 에 코드 게이트 **불포함**. ADR-019 `TSU_ELIGIBLE` = S-4 (deferred). M-3 = 파일 + 항목 + flow 문서 + test. |
| **M3-6** | **M2 = classification authority, M3 = admission 당시 snapshot.** test 로 admission↔M2 일치 강제. |

---

## 8. M-3 EXEC 이 할 일 (참고 — 본 문서 범위 아님, 비준 후)

1. `NAE/governance/corpus_admissions.jsonl` 생성 — §4 6줄 verbatim.
2. `docs/architecture/NAE-Manifest-Authority-SSOT.md` 에 §6 절 추가 (다른 절 무변경).
3. governance test 추가 (`tests/test_m2_source_registry_governance.py` 또는 신규):
   - 파일 존재 + 각 줄 valid JSON
   - 항목 source_id 집합 = {Dagg, Hiscox, Smith Vol1–4}, 전부 M2 에 존재
   - 각 레코드 §2 스키마 준수 (필수 필드, `track` enum, reference track 만 `reference_quality_confirmed`)
   - `authority_class`/`content_genre`/`theological_category`/`tradition` 이 M2 값과 **일치**
   - `evidence_refs` 경로 전부 실존
   - Fuller Vol01–08 은 admission 기록 없음 (게이트 확인)
4. **금지**: 코드 게이트(S-4), TSU/Qdrant/state 접촉, M1/M2/M3(manifest), 무관 파일. C1 커밋 안 함.
5. CUE 독립검증 → 커밋 (`M-3: corpus admission records + manual gate`).

---

## 9. 이번 문서가 하지 않는 것

- `corpus_admissions.jsonl` 생성 — **하지 않음** (M-3 EXEC 몫).
- 코드 게이트 / state machine / enum — 하지 않음 (S-4).
- TSU / Qdrant / corpus / state store 접촉 — 하지 않음.
- Fuller admission 결정 — 하지 않음 (처리 재개 시 HQ).

**Mutation: 0. 산출물: 본 DRAFT 1건.**

END OF M-3 CORPUS ADMISSIONS DRAFT
