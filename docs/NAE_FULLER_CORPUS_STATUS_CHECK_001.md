# NAE Fuller Corpus 처리 현황 점검 (2026-09-07)

- 점검자: CUE
- 점검 대상 체크아웃: `/Users/David/DBMA` @ `dev/dbma-engine` `478a2de` (엔진 정본 브랜치)
- 방식: read-only 파일 점검 (Qdrant 무접촉)

---

## 0. 결론

**8권 중 프로덕션 벡터스토어(`nae_tsu_v1`)에 색인된 Fuller 자료는 0권이다.**
Vol.01만 청킹(TSU 생성) 단계까지 진행됐고 그마저 **미검수(generated)**
상태다. Vol.02–08은 정제(canonical)까지만 되어 있다. 이 정지 상태는
사고가 아니라 **의도된 HOLD** — `CUE-FULLER-ADMISSION-READINESS-PACKAGE.md`
가 "ADMITTED ≠ PROCESSED"를 명시하고 Processing을 HOLD로 못박았다.

> 사용자 인식("8개 중 1번만 처리") 정정: Vol.01은 *청킹까지만*,
> *색인은 0권*. "처리 완료"된 권은 없다.

---

## 1. 파이프라인 단계별 매트릭스

파이프라인: 원본 → 추출 → 정제(canonical) → 청킹(TSU) → 검수 → 임베딩 → 색인

| 권 | RAW | 등록(QUALITY) | Admission | 추출·정제 | 청킹(TSU) | 검수 | 임베딩·색인 |
|---|---|---|---|---|---|---|---|
| Vol.01 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ⚠️ 3,643건 생성 | ❌ 전량 `generated` | ❌ 미색인 |
| Vol.02 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ❌ 없음 | ❌ | ❌ |
| Vol.03 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ❌ 없음 | ❌ | ❌ |
| Vol.04 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ❌ 없음 | ❌ | ❌ |
| Vol.05 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ❌ 없음 | ❌ | ❌ |
| Vol.06 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ❌ 없음 | ❌ | ❌ |
| Vol.07 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ❌ 없음 | ❌ | ❌ |
| Vol.08 | ✅ MATCH | ✅ PASSED | ✅ ADMITTED | ✅ canonical.json | ❌ 없음 | ❌ | ❌ |

---

## 2. 근거 (실측)

### 2.1 RAW·등록·Admission
- `NAE/pipeline/registration/state/registration_state.json`: `BAP-MISS-FULLER-VOL01`–`VOL08` 전부 `state: QUALITY_PASSED` (2026-08-15)
- `NAE/governance/corpus_admissions.jsonl` 7–14행: 8권 전부 `track: tsu`, `date: 2026-08-29`, rationale = **"ADMIT for future ADR-030 TSU-track processing"**
- `CUE-FULLER-ADMISSION-READINESS-PACKAGE.md` §0: Processing = **HOLD**, Mutation Budget `TSU 0 / Embedding 0 / Qdrant 0`, 3-way checksum MATCH 8/8, 정본 커밋 `6b77df6`

### 2.2 추출·정제
- `NAE/corpus/canonical/Fuller_Complete_Works_Vol01`–`Vol08` 8개 디렉터리 모두 `canonical.json` + `canonical.txt` + `normalize_report.json` 존재 (2026-08-07)

### 2.3 청킹(TSU)
- `NAE/corpus/tsu/` 하위 실제 소스 디렉터리: **`Dagg_Church_Order`, `Fuller_Complete_Works_Vol01`, `Hiscox_Standard_Manual`** 3개뿐 (나머지는 `_batch*_backup`)
- `Fuller_Complete_Works_Vol01/tsu.json`: list 3,643건, id 범위 `TSU-0004123`–`TSU-0007765`, **`review_status` 전량 `generated`** (검수 0건)
- Vol.02–08: `NAE/corpus/tsu/Fuller_Complete_Works_Vol0X` 디렉터리 자체가 없음 → TSU 미생성

### 2.4 임베딩·색인
- `NAE/pipeline/ingest/state/incremental_state.json`: 총 **3,319건 전부 `INDEXED`**
- 이 3,319 = Dagg 2,958 + Hiscox 361 (admission rationale의 수치와 정확히 일치)
- Fuller Vol.01의 3,643개 tsu_id ↔ `incremental_state` INDEXED 집합 **교집합 0건**
- ⇒ `nae_tsu_v1`에 Fuller 벡터 0

---

## 3. 남은 작업량 (참고)

| 단계 | Vol.01 | Vol.02–08 |
|---|---|---|
| 추출·정제 | 완료 | 완료 |
| 청킹(TSU) | 완료(재생성 불요) | **7권 신규 생성 필요** |
| 검수 | 3,643건 신규 검수 | 각 권 신규 검수 |
| 임베딩·색인 | 신규 | 신규 |

- 처리 재개는 **ADR-030 TSU track** 규정을 따라야 하며, 현재 HOLD 해제는
  HQ 결정 사항 (`CUE-FULLER-ADMISSION-READINESS-PACKAGE.md` 기준).
- `3,319 production baseline`은 FROZEN — Fuller 처리 중 건드리지 말 것.

---

## 4. 다음 조치 (제안)

1. HQ에 HOLD 해제 여부 확인 — 해제 시 ADR-030 TSU track 재개 Task Order 발급
2. Vol.01 검수 착수(이미 생성된 3,643 TSU) vs 8권 일괄 TSU 재생성 후 검수 — 순서 결정
3. 검수 리소스(사람) 일정 확인 — 8권 × 수천 TSU 규모
