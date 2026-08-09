# NAE Pilot 001 — Remediation Execution Report 001

**작성일:** 2026-08-09
**성격:** CONDITIONAL 5건의 remediation re-review 승인에 따른 실제 claim
교체 + verified 승격 실행.
**Authority:** `NAE/review/human/decisions/pilot_001_remediation_decisions.json`(5건 전부 APPROVED) + 사용자 명시적 승인("진행")
**Git Commit/Push:** 미수행.

---

## 1. 실행 대상(5건)

```
TSU-0000713 (Dagg,   Ecclesiology)   — claim 교체
TSU-0000330 (Dagg,   Lord's Supper)  — claim 교체
TSU-0000033 (Dagg,   Soteriology)    — claim 교체
TSU-0003661 (Hiscox, Baptism)         — claim 교체 + scriptures=["Acts 2:38"] 추가(성경 표기 정정)
TSU-0003893 (Hiscox, Lord's Supper)  — claim 교체 + claim_context_note 신규 필드 추가(메타문)
```

## 2. 실행 절차

```
1. 백업: NAE/corpus/tsu/_remediation_backup_20260809T132448/
2. 각 레코드에 confirmed_claim으로 claim 필드 교체(+ TSU-0003661/0003893 추가 필드)
3. review_promotion.py::promote_tsu_to_verified() 호출(reviewer="David",
   review_date="2026-08-09", review_decision="approved",
   review_notes="[REMEDIATION] "+원 코멘트)
4. 원자적 쓰기(tmp+os.replace)로 Dagg/Hiscox tsu.json 교체
```

---

## 3. 검증 결과

### 3.1 review_status 분포(전체 10건 verified)

```
generated: 4107
verified:  10
total:     4117(불변)
verified IDs: TSU-0000025, TSU-0000033, TSU-0000199, TSU-0000330, TSU-0000713,
              TSU-0003524, TSU-0003525, TSU-0003647, TSU-0003661, TSU-0003893
```

(1차 Promotion 5건 + 이번 Remediation 5건 = 10건)

### 3.2 claim 교체 정확성(5건 전수 확인)

```
TSU-0000713 claim == confirmed_claim: True
TSU-0000330 claim == confirmed_claim: True
TSU-0000033 claim == confirmed_claim: True
TSU-0003661 claim == confirmed_claim: True
TSU-0003893 claim == confirmed_claim: True

TSU-0003661.scriptures == ["Acts 2:38"]: 확인됨(정정 반영)
TSU-0003893.claim_context_note == 확정 메타문: 확인됨(신규 필드 추가)
```

### 3.3 그 외 필드 불변성

```
id/doctrine/source_text/author_id/work_id/edition_id 등 — 전부 무변경(claim/
scriptures[TSU-0003661만]/claim_context_note[TSU-0003893만]/review_status/
review_metadata만 변경 또는 추가)
```

### 3.4 Review Gate 재확인

```
$ indexer.index_all(dry_run=True)
{'processed': 6, 'indexed': 10, 'identifiers': [{'Hiscox_Standard_Manual': 5}, {'Dagg_Church_Order': 5}, ...]}
```

정확히 10건만 통과(1차 5건 + 이번 5건), 나머지 4,107건은 여전히
`generated`로 차단. `dry_run=True`이므로 실제 Embedding/Qdrant 호출은
발생하지 않음.

### 3.5 Regression

```
$ pytest(관련 스위트) 206 passed
$ pytest -q --ignore=output(전체) 2044 passed, 2 failed
```

2건은 기존 무관 baseline(`tests/test_nae_embed.py`, 불변). **신규
regression 0건**(관련 테스트 2건 어서션을 `indexed==5`→`indexed==10`으로
갱신 — 낡은 전제 갱신, 회귀 아님).

### 3.6 Validator

```
source_validator.py    : PASS=89  WARNING=0  FAIL=0  (baseline 일치)
manifest_validator.py  : PASS=138 WARNING=0  FAIL=0  (baseline 일치)
authority_validator.py : PASS=128 WARNING=26 FAIL=0  (baseline 일치)
```

**DRIFT = 0.**

---

## 완료 보고

```
STATUS: PASS

REMEDIATION EXECUTED: YES(5건)
  TSU-0000713, TSU-0000330, TSU-0000033, TSU-0003661, TSU-0003893
  claim 교체 + generated -> verified

BACKUP: NAE/corpus/tsu/_remediation_backup_20260809T132448/ (검증됨)

CUMULATIVE PILOT 001 STATE:
  Total TSU: 4117
  verified: 10(1차 Promotion 5 + Remediation 5)
  generated: 4107

FIELD CHANGES: claim(5건), scriptures(TSU-0003661만, Acts 2:38 추가),
                claim_context_note(TSU-0003893만, 신규 필드), review_status,
                review_metadata — 그 외 전부 무변경

REVIEW GATE: indexed=10(정확히 승격된 10건만 통과), dry_run=True로 실제 Embedding/Qdrant 미실행

REGRESSION: 2044 passed / 2 failed(기존 무관 baseline), 신규 regression 0건

DRIFT: 0

EMBEDDING: NOT EXECUTED
QDRANT: NOT EXECUTED

GIT: NOT PERFORMED

NEXT STEP:
Pilot 001의 10개 TSU 전부 verified 승격 완료 — Pilot 001 Human Review
Gate 전체 사이클 종료. 실제 Embedding/Qdrant 실행은 여전히 별도 작업
명령 및 승인 필요(Vector Index Preflight Design 001 기준). 이후
전체 Corpus(4,107건 generated)의 Human Review 확장 여부는 별도 결정
필요.
```
