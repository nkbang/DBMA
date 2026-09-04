# NAE Pilot TSU Review Preparation 001

**Project:** NAE-PILOT-TSU-REVIEW-PREP-001
**작성일:** 2026-08-08
**성격:** Human Review 준비 + 검증 패키지 작성만 수행. **모든 실행 금지 항목 미실행.**
**Authority:** `docs/NAE_VECTOR_PAYLOAD_CONTRACT_INDEPENDENT_REVIEW_001.md`(C1, APPROVED)
**Git Commit/Push:** 미수행.

---

## A. Candidate Selection

```
총 후보 수: 10
Dagg_Church_Order 후보: 5
Hiscox_Standard_Manual 후보: 5
```

### 선정 기준(적용 순서)

1. `review_status = generated`(4,117건 전부 해당 — 필터 아님, 전제 조건)
2. `claim` 존재 + 20자 이상(공허한 재진술 배제)
3. `doctrine` classification 존재(`None` 배제)
4. 각 책에서 **레코드 수가 많은 상위 5개 doctrine 카테고리**를 우선해
   서로 다른 신학적 claim 유형을 포함하도록 구성(편중 방지, 기준9)
5. 동일 doctrine 그룹 내에서는 `citations`/`scriptures`가 존재하는
   레코드를 우선 선택(기준4 "가능한 한 존재" — Dagg 전체 3,377건 중
   `scriptures` 비어있지 않은 레코드는 0건임을 실측 확인, 코퍼스
   전반의 특성이므로 이 기준으로 후보를 배제하지 않고 `citations`
   존재 여부로 대체 우선순위 적용)
6. Metadata Schema 1.1.0 필드 + `metadata_provenance` 정상 존재
   여부는 §B Integrity Audit에서 별도 검증(선정 자체를 좌우하지 않음
   — 4,117건 전체가 이미 Migration 완료 상태이므로 사실상 전건 충족)

### 편중 방지 확인

| Book | 선정 건수 | 선정 doctrine(중복 없음) |
|---|---|---|
| Dagg_Church_Order | 5 | Ecclesiology, Baptism, Lord's Supper, Soteriology, Sanctification |
| Hiscox_Standard_Manual | 5 | Ecclesiology, Baptism, Church Discipline, Lord's Supper, Soteriology |

각 책 내에서 5개 서로 다른 doctrine을 선택했고, 두 책 사이에서도
Ecclesiology/Baptism/Lord's Supper/Soteriology가 겹치되(같은 교리를
서로 다른 저자가 어떻게 다루는지 비교 가능) Church Discipline/
Sanctification은 책마다 다른 항목을 포함시켜 특정 section 편중을
피했다.

---

## B. Candidate Integrity(Read-only, 임의값 생성 없음)

검증 필드 19개: `id, source_id, author_id, work_id, edition_id,
volume_id, publication_year, source_type, copyright_status,
usage_permission, access_control, tsu_access, metadata_schema_version,
metadata_provenance, claim, doctrine, scriptures, citations,
review_status`

| TSU ID | Book | Doctrine | 전체 판정 | Warning 필드 |
|---|---|---|---|---|
| TSU-0000713 | Dagg | Ecclesiology | PASS(1 WARNING) | scriptures(빈 배열) |
| TSU-0000199 | Dagg | Baptism | PASS(1 WARNING) | scriptures(빈 배열) |
| TSU-0000330 | Dagg | Lord's Supper | PASS(2 WARNING) | scriptures, citations(둘 다 빈 배열) |
| TSU-0000033 | Dagg | Soteriology | PASS(2 WARNING) | scriptures, citations(둘 다 빈 배열) |
| TSU-0000025 | Dagg | Sanctification | PASS(2 WARNING) | scriptures, citations(둘 다 빈 배열) |
| TSU-0003524 | Hiscox | Ecclesiology | PASS(1 WARNING) | scriptures(빈 배열) |
| TSU-0003661 | Hiscox | Baptism | PASS(1 WARNING) | scriptures(빈 배열) |
| TSU-0003525 | Hiscox | Church Discipline | PASS(1 WARNING) | scriptures(빈 배열) |
| TSU-0003893 | Hiscox | Lord's Supper | PASS(1 WARNING) | scriptures(빈 배열) |
| TSU-0003647 | Hiscox | Soteriology | PASS(1 WARNING) | scriptures(빈 배열) |

**MISSING 필드: 0건**(10건 × 19개 필드 = 190개 항목 전수 검사, 전부
PASS 또는 WARNING — MISSING 없음). `metadata_provenance`는 10건
전부 `crosswalk_id` 존재 확인(Dagg 5건: `f914f6c442983e59`, Hiscox
5건: `260d31b2331a3f8b` — Migration 시 사용된 실제 Crosswalk 레코드와
일치).

**WARNING 사유**: `scriptures`/`citations`가 빈 배열인 것은 코퍼스
전반의 특성(§A §5 실측: Dagg 전체 3,377건 중 `scriptures` 비어있지
않은 레코드 0건)이며, Migration이나 이번 선정 작업의 오류가 아니다.
LLM 추출 단계(`claim.py`)에서 원문에 실제로 성경 인용이 명시적으로
없는 문장은 빈 배열로 남는 것이 정상 동작이다 — 임의로 채우지
않았다.

---

## C. Human Review Package

각 후보의 Review Sheet. **Reviewer Decision은 전부 `PENDING`으로
초기화**되어 있으며, 이번 작업에서 어떤 값도 승격/거부로 사전 결정하지
않았다.

### C.1 TSU-0000713 (Dagg_Church_Order · Ecclesiology)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0000713` |
| 2. Source / Work | `BAP-CHURCH-DAGG-001` / `WORK-DAGG-CHURCH-ORDER-001`(John L. Dagg, *Church Order*, 1871) |
| 3. 원문(evidence) | "No church communicated with me as concerning giving and receiving, but ye only." / "As distinct bodies, they sent and received salutations," |
| 4. Theological claim | 초기 교회들은 서로 다른 교회들과 비교되었으며, 각 교회는 독립된 단체로서 서로 인사와 연락을 주고받았다. |
| 5. Doctrine classification | Ecclesiology |
| 6. Scripture references | (없음 — 원문에 명시적 인용 없음) |
| 7. Citation/evidence | `citations: ["* Rom. xvi. 16; 1 Cor. xvi. 19."]` |
| 8. Metadata provenance | crosswalk_id=`f914f6c442983e59`, mapping=manual-confirmed |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) |

### C.2 TSU-0000199 (Dagg_Church_Order · Baptism)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0000199` |
| 2. Source / Work | `BAP-CHURCH-DAGG-001` / `WORK-DAGG-CHURCH-ORDER-001` |
| 3. 원문(evidence) | "The verb never signifies this process." |
| 4. Theological claim | 동사 'baptō'는 액체를 고체에 적용하는 과정을 의미하지 않는다. |
| 5. Doctrine classification | Baptism |
| 6. Scripture references | (없음) |
| 7. Citation/evidence | `citations: ["2. Barro appears, in some cases, to be used in the secondary"]` |
| 8. Metadata provenance | crosswalk_id=`f914f6c442983e59` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) — 헬라어 원어 논증이므로 언어학적 정확성 확인 필요 |

### C.3 TSU-0000330 (Dagg_Church_Order · Lord's Supper)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0000330` |
| 2. Source / Work | `BAP-CHURCH-DAGG-001` / `WORK-DAGG-CHURCH-ORDER-001` |
| 3. 원문(evidence) | "A well executed picture of the crucifixion... has much more resemblance to the body of Christ, than is furnished..." |
| 4. Theological claim | 성례의 목적을 고려할 때, 성찬에서 빵을 먹음으로써 그리스도의 죽음을 기억하는 것이 더 적절하다. |
| 5. Doctrine classification | Lord's Supper |
| 6. Scripture references | (없음) |
| 7. Citation/evidence | (없음) |
| 8. Metadata provenance | crosswalk_id=`f914f6c442983e59` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) — evidence 없는 레코드, 신학적 논증 근거 재확인 필요 |

### C.4 TSU-0000033 (Dagg_Church_Order · Soteriology)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0000033` |
| 2. Source / Work | `BAP-CHURCH-DAGG-001` / `WORK-DAGG-CHURCH-ORDER-001` |
| 3. 원문(evidence) | "A powerful motive, to love and obey Christ, is drawn from the love which he has manifested in dying for us." |
| 4. Theological claim | 그리스도의 사랑과 복종의 강력한 동기는 우리를 위해 죽으신 그분의 사랑에서 비롯됩니다. |
| 5. Doctrine classification | Soteriology |
| 6. Scripture references | (없음) |
| 7. Citation/evidence | (없음) |
| 8. Metadata provenance | crosswalk_id=`f914f6c442983e59` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) |

### C.5 TSU-0000025 (Dagg_Church_Order · Sanctification)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0000025` |
| 2. Source / Work | `BAP-CHURCH-DAGG-001` / `WORK-DAGG-CHURCH-ORDER-001` |
| 3. 원문(evidence) | "To love God with all the heart is the sum of all duty." |
| 4. Theological claim | 하나님을 전심으로 사랑하는 것이 모든 의무의 총합이다. |
| 5. Doctrine classification | Sanctification |
| 6. Scripture references | (없음) |
| 7. Citation/evidence | (없음) |
| 8. Metadata provenance | crosswalk_id=`f914f6c442983e59` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) |

### C.6 TSU-0003524 (Hiscox_Standard_Manual · Ecclesiology)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0003524` |
| 2. Source / Work | `BAP-CHURCH-HISCOX` / `WORK-HISCOX-STANDARD-MANUAL-001`(Edward T. Hiscox, 1890) |
| 3. 원문(evidence) | "The evil passions of even good men may triumph over piety, and partisan strife may destroy the peace and the prosperity of the body of Christ." |
| 4. Theological claim | 선한 사람들의 악한 정서가 경건을 이길 수 있고, 당파적인 분쟁이 그리스도의 몸의 평화와 번영을 파괴할 수 있다. |
| 5. Doctrine classification | Ecclesiology |
| 6. Scripture references | (없음) |
| 7. Citation/evidence | `citations: ["5. Because that a case of discipline undertaken under excitement is almost certain"]` |
| 8. Metadata provenance | crosswalk_id=`260d31b2331a3f8b` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) |

### C.7 TSU-0003661 (Hiscox_Standard_Manual · Baptism)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0003661` |
| 2. Source / Work | `BAP-CHURCH-HISCOX` / `WORK-HISCOX-STANDARD-MANUAL-001` |
| 3. 원문(evidence) | "Then Peter said unto them, Repent, and be baptized every one of you in the name of Jesus Christ for the remission of sins." |
| 4. Theological claim | 예수 그리스도의 이름으로 죄의 사함을 받기 위해 각자가 회개하고 세례를 받아야 한다. |
| 5. Doctrine classification | Baptism |
| 6. Scripture references | (없음 — 본문 자체가 사도행전 2:38 인유이나 `scriptures` 필드에는 파서가 채우지 않음, WARNING 유지) |
| 7. Citation/evidence | `citations: ["18. Then hath God also to the Gentiles granted repentance"]` |
| 8. Metadata provenance | crosswalk_id=`260d31b2331a3f8b` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) — 원문이 사도행전 2:38 인용이므로 `scriptures` 필드 정확성도 함께 검토 권고 |

### C.8 TSU-0003525 (Hiscox_Standard_Manual · Church Discipline)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0003525` |
| 2. Source / Work | `BAP-CHURCH-HISCOX` / `WORK-HISCOX-STANDARD-MANUAL-001` |
| 3. 원문(evidence) | "All this should, if possible, be avoided." |
| 4. Theological claim | 교회에서 일어날 수 있는 악한 정서와 파당적인 분쟁을 가능한 한 피해야 한다. |
| 5. Doctrine classification | Church Discipline |
| 6. Scripture references | (없음) |
| 7. Citation/evidence | `citations: ["5. Because that a case of discipline undertaken under excitement is almost certain"]` |
| 8. Metadata provenance | crosswalk_id=`260d31b2331a3f8b` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) — TSU-0003524와 동일 각주(citation) 인접 문장, 문맥 연속성 확인 권고 |

### C.9 TSU-0003893 (Hiscox_Standard_Manual · Lord's Supper)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0003893` |
| 2. Source / Work | `BAP-CHURCH-HISCOX` / `WORK-HISCOX-STANDARD-MANUAL-001` |
| 3. 원문(evidence) | "To them it seems kindly and fraternal to invite all who say they love our common Lord and Saviour to unite in commemorating his death in the Supper." |
| 4. Theological claim | 일부 사람들은 주님의 만찬에서 죽으신 주님을 기념하는 것을 모든 사람들이 함께 할 수 있도록 초청하는 것이 친절하고 형제적인 행동이라고 생각한다. |
| 5. Doctrine classification | Lord's Supper |
| 6. Scripture references | (없음) |
| 7. Citation/evidence | `citations: ["3. They do not invite immersed members"]` |
| 8. Metadata provenance | crosswalk_id=`260d31b2331a3f8b` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) — "일부 사람들은 ~라고 생각한다"는 타 견해 소개 문장, 저자 본인 입장인지 구분 확인 필요 |

### C.10 TSU-0003647 (Hiscox_Standard_Manual · Soteriology)

| 항목 | 값 |
|---|---|
| 1. TSU ID | `TSU-0003647` |
| 2. Source / Work | `BAP-CHURCH-HISCOX` / `WORK-HISCOX-STANDARD-MANUAL-001` |
| 3. 원문(evidence) | "And the times of this ignorance God winked at, but now commandeth all men everywhere to repent." |
| 4. Theological claim | 하나님은 이전에는 무지한 시대를 용납하셨지만 이제는 모든 사람에게 어디서나 회개할 것을 명령하시고 계심 |
| 5. Doctrine classification | Soteriology |
| 6. Scripture references | (없음 — 사도행전 17:30 인유, `scriptures` 필드 미기재) |
| 7. Citation/evidence | `citations: ["18. Then hath God also to the Gentiles granted repentance"]` |
| 8. Metadata provenance | crosswalk_id=`260d31b2331a3f8b` |
| 9. Reviewer decision | `PENDING` |
| 10. Reviewer notes | (검토자 작성 대기) — 원문이 사도행전 17:30 인용, `scriptures` 필드 정확성 검토 권고 |

**Reviewer Decision 값은 `PENDING`/`APPROVE_FOR_VERIFICATION`/`REJECT`
3가지만 허용되며, 이번 단계에서 `verified` 값을 직접 기록하지 않았다.**

---

## D. Payload Preview(Offline, Qdrant/Embedding 미접근)

`qdrant_store.build_point()`를 dummy vector(`[0.0]*1024`, 실제 임베딩
아님)로 호출해 payload 구조만 계산 — Qdrant client 인스턴스 생성이나
`ollama.embeddings()` 호출 없음.

```
검증 필드셋: 기존 23개 + Metadata Schema 1.1.0 16개 + metadata_provenance = 40개
10건 전체: payload 필드 집합이 기대 40개 필드와 정확히 일치 -> OK
10건 전체: category=null, citation_policy=null(AUTHORITATIVE_SOURCE_MISSING 정책 유지) -> OK
10건 전체: 임의값 생성 없음(추가 조회/추측 없이 record.get()만 사용) -> OK
```

| TSU ID | payload 필드 수 | 기존 필드 보존 | Metadata 1.1.0 필드 보존 | provenance 보존 | null 정책 |
|---|---|---|---|---|---|
| TSU-0000713 | 40/40 | OK | OK | OK | OK |
| TSU-0000199 | 40/40 | OK | OK | OK | OK |
| TSU-0000330 | 40/40 | OK | OK | OK | OK |
| TSU-0000033 | 40/40 | OK | OK | OK | OK |
| TSU-0000025 | 40/40 | OK | OK | OK | OK |
| TSU-0003524 | 40/40 | OK | OK | OK | OK |
| TSU-0003661 | 40/40 | OK | OK | OK | OK |
| TSU-0003525 | 40/40 | OK | OK | OK | OK |
| TSU-0003893 | 40/40 | OK | OK | OK | OK |
| TSU-0003647 | 40/40 | OK | OK | OK | OK |

**실제 vector 생성/Qdrant 접근 없음** — `build_point()`는 순수 함수이며
네트워크 I/O를 수행하지 않는다(기존 코드 특성, 이번 작업에서 재확인만).

---

## E. Safety

```
Production TSU 변경 = 0
```
```
$ shasum -a 256(작업 전/후) Dagg/Hiscox tsu.json
변경 없음(작업 시작 시점과 동일한 sha256 유지 확인)
```

```
Review Promotion = 0    (review_promotion.py 호출 없음)
Embedding = 0            (embed_client.embed_text() 호출 없음)
Qdrant = 0                (QdrantClient 인스턴스 생성/get_collections 등 일체 미호출)
Metadata 변경 = 0        (Migration 재실행 없음, 필드 값 전부 읽기만)
Core Retrieval 변경 = 0  (core/retrieval.py 미접근)
ADR 변경 = 0
Git commit/push = 0
```

---

## F. Regression

```
Target tests: tests/test_nae_qdrant_payload_contract.py, test_nae_index_indexer.py,
              test_indexer_review_gate_wiring.py, test_tsu_review_gate.py -> 104 passed

Validators:
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)

new regression = 0
DRIFT = 0
```

이번 작업은 코드를 전혀 수정하지 않았으므로(읽기 전용 선정/검증만),
직전 작업(`NAE-VECTOR-PAYLOAD-CONTRACT-IMPLEMENTATION-001`)에서 이미
확인된 전체 스위트 1,967 passed / 2 failed(기존 무관 baseline,
`tests/test_nae_embed.py`) 상태가 그대로 유지된다.

---

## G. Final Status

```
READY_FOR_HUMAN_REVIEW
```

`READY_FOR_EMBEDDING`으로 판정하지 않는다 — 사람의 Review Sheet 검토
및 `APPROVE_FOR_VERIFICATION`/`REJECT` 결정이 아직 이루어지지 않았다.

---

## 완료 Gate 체크리스트

```
[x] Pilot 후보 ≤ 10건 (정확히 10건)
[x] Dagg/Hiscox 후보 포함 (각 5건)
[x] 후보 integrity PASS (MISSING 0건, WARNING만 존재 — 코퍼스 특성)
[x] Human Review Sheet 생성 (10건 전체)
[x] review_status 변경 없음 (generated=4117 유지)
[x] verified = 0 유지
[x] eligible = 0 유지
[x] indexed = 0 유지
[x] Payload offline preview PASS (10/10, 40필드 구조 확인)
[x] Qdrant 미접근
[x] Embedding 미실행
[x] Production TSU 무변경 (sha256 checksum 동일)
[x] Regression 신규 0
[x] DRIFT = 0
[x] Final report 작성 (본 문서)
```

---

## 완료 보고

```
STATUS: READY_FOR_HUMAN_REVIEW

FILES CREATED:
docs/NAE_PILOT_TSU_REVIEW_PREPARATION_001.md

FILES MODIFIED:
(없음)

CANDIDATES:
total: 10 (Dagg 5, Hiscox 5)
integrity: MISSING 0, WARNING만 존재(scriptures/citations 코퍼스 특성)

REVIEW GATE:
generated: 4117
verified: 0
eligible: 0
indexed: 0

PAYLOAD PREVIEW:
10/10 PASS (40 필드 구조, null 정책, 임의값 생성 없음)

REGRESSION:
target: 104 passed
new_regressions: 0
DRIFT: 0

SAFETY:
Production TSU 변경 0 / Review Promotion 0 / Embedding 0 / Qdrant 0 / Metadata 변경 0 / Core Retrieval 변경 0 / ADR 변경 0

GIT:
NOT PERFORMED

NEXT STEP:
사람이 10건의 Human Review Sheet(§C)를 검토해 각 TSU에
APPROVE_FOR_VERIFICATION 또는 REJECT를 기록. 승인 후에만 다음 Gate인
Pilot Verification(review_promotion.py를 통한 실제 verified 승급) ->
Pilot Embedding으로 진행.
```
