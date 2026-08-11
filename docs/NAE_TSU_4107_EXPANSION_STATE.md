# NAE TSU 4,107건 확장 Human Review — 진행 상태

**최초 작성일:** 2026-08-09
**설계 근거:** `docs/NAE_TSU_4107_EXPANSION_HUMAN_REVIEW_DESIGN_001.md`
(사용자 확정: B안 — 배치 우선순위 + 점진 확장, TSU ID 순차·Dagg부터 시작)

이 문서는 세션이 끊겨도 이어서 진행할 수 있도록 체크포인트와
진행률을 기록한다(CLAUDE.md 상태 관리 규칙).

---

## 배치 구성

- 전체 대상: 4,107건(`review_status="generated"`, Pilot 10건 제외)
- 배치 크기: 100건(`schema.MAX_PENDING_REVIEW` 재사용)
- 총 배치 수: 42개
- 순서: Dagg_Church_Order 전체(TSU ID 오름차순) → Hiscox_Standard_Manual
  전체(TSU ID 오름차순)
- 상태 파일: `NAE/review/human/batch_state.json`(기계 판독용, 이 문서와
  별개로 배치 생성기가 자동 갱신)

## 체크리스트

- [x] 설계 문서 작성 및 사용자 승인
- [x] `decision_gate.py::build_requests_from_records()` 구현
      (Pilot 전용 `build_requests()`는 무수정 — 회귀 없음)
- [x] `batch_manager.py` 구현(정렬/배치 분할/상태 기록)
- [x] Batch 1(TSU-0000006 ~ TSU-0000107, 100건) 요청 생성
      → `NAE/review/human/requests/batch_0001_requests.json`
- [x] Batch 1 Human Review 10건 진행(TSU-0000006~0000015, 10건씩 확인
      방식으로 사용자 확정, 전건 Q1=A/Q2=A/Q3=A/FINAL=APPROVED)
      → `NAE/review/human/decisions/batch_0001_decisions.json`
- [x] 위 10건 Promotion 완료(review_status: generated → verified)
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T225223/`
- [x] Batch 1 다음 10건 진행(TSU-0000016~0000024, 0000026) — TOC 항목
      8건(TSU-0000017~0000024) REJECT, 정상 진술 2건(TSU-0000016/0000026)
      APPROVE → review_status: verified 2건, rejected 8건
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T225804/`
- [x] Batch 1 다음 10건 진행(TSU-0000027~0000037, Pilot 제외 9건) —
      TSU-0000027(claim 오배정 의심)·TSU-0000028(키릴 문자 혼입) REJECT,
      나머지 7건 APPROVE → verified 8건, rejected 2건
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T230308/`
- [x] Batch 1 다음 10건 진행(TSU-0000038~0000047) — 품질 이슈 없음,
      10건 전부 APPROVE → verified 승격
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T231304/`
- [x] Batch 1 다음 10건 진행(TSU-0000048~0000057) — TSU-0000055
      doctrine 미분류, TSU-0000057 한자 혼입("增加","榜樣") 관찰 후
      10건 전부 APPROVE → verified 승격
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T231630/`
- [x] Batch 1 다음 10건 진행(TSU-0000058~0000067) — TSU-0000060
      원문 충실도 의심, TSU-0000066 한자 혼입("決定的") 관찰 후 10건
      전부 APPROVE → verified 승격
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T232148/`
- [x] Batch 1 다음 10건 진행(TSU-0000068~0000077) — TSU-0000070
      claim 오배정(TSU-0000069와 동일) REJECT, 나머지 9건 APPROVE →
      verified 9건, rejected 1건
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T234449/`
- [x] Batch 1 다음 10건 진행(TSU-0000078~0000087) — TSU-0000087
      claim 잘림(truncation) REJECT, 나머지 9건 APPROVE → verified 9건,
      rejected 1건
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T234951/`
- [x] Batch 1 다음 10건 진행(TSU-0000088~0000097) — TSU-0000091
      베트남어 혼입("hướng dẫn") REJECT, 나머지 9건 APPROVE(TSU-0000095
      경미한 의미 이동 관찰 후 승인) → verified 9건, rejected 1건
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260809T235434/`
- [x] Batch 1 마지막 10건 진행(TSU-0000098~0000107) — TSU-0000100
      doctrine 미분류, TSU-0000104 오역("전도서"↔"위임/commission" 혼동)
      REJECT, 나머지 8건 APPROVE → verified 8건, rejected 2건
      → 백업 `NAE/corpus/tsu/_batch0001_promotion_backup_20260810T000503/`
- [x] **Batch 1 완료(100/100건 판정: verified 85건, rejected 15건)**
- [x] Batch 2 요청 생성(TSU-0000209~TSU-0000308, 100건 — TSU-0000108~
      0000208은 이미 generated 아님/다른 상태라 자연히 배치에서 제외됨)
- [x] Batch 2 첫 10건 진행(TSU-0000209~0000218, 헬라어 어원 논증 +
      OCR 손상 구간). 사용자와 협의해 이번 배치는 신규 vocabulary
      도입 없이 기존 Q1-Q3(A/R/C)/FINAL 체계만 사용하기로 확정
      (OCR 원문 보존/정규화/argument_type 태그는 별도 ADR/설계로 분리).
      6건 APPROVE(0000209/0000211/0000214/0000215/0000216/0000218),
      4건 REJECT(0000210/0000212/0000213/0000217)
      → 백업 `NAE/corpus/tsu/_batch0002_promotion_backup_20260810T002209/`
- [ ] Batch 2 나머지 90건(TSU-0000219~TSU-0000308) Human Review
- [ ] Batch 3 ~ 41 반복

## 진행률

```
verified: 91 / 4107 (Pilot 10건 제외)
rejected: 19 / 4107
reviewed subtotal: 110 / 4107 (2.68%)
batches: batch_0001 완료(100/100) / batch_0002 진행 중(10/100)
```

## 참고 — 스키마 확장 논의(Batch 2, 2026-08-10)

Batch 2 첫 10건(헬라어 어원 논증 구간, `Bazzo`/`faxrdo`/`Baxrw` 등
OCR 손상 토큰 다수)에서, 사용자가 OCR 원문 보존(`raw_quote`)/정규화
헬라어 표기(`normalized_quote`)/`argument_type: lexical_semantics`
태그 등 새 vocabulary 도입을 제안했으나, Architecture Freeze Rule에
따라 **이번 배치 처리에서는 도입하지 않기로 사용자와 합의**함
(기존 Q1-Q3 A/R/C + FINAL 체계만 사용). 스키마 확장은 별도 ADR/설계
문서로 분리 예정 — 필요 시 다음 작업으로 제안.

## 참고 — 데이터 품질 관찰(Batch 1, TSU-0000009/0000010/0000011)

리뷰 중 claim 텍스트에 한자가 혼입된 것이 발견됨(예: "来源", "頼赖").
리뷰어가 claim의 신학적 의미 자체는 정확하다고 판단해 원안대로
승인했으나, TSU 생성 파이프라인(LLM 추출) 단계의 표기 결함으로
보이며 별도 확인이 필요할 수 있음. 근거는
`NAE/review/human/decisions/batch_0001_decisions.json`의 comment 필드.

## 참고 — 데이터 품질 관찰(Batch 1, TSU-0000017~0000024)

목차(TOC) 파편이 TSU로 추출된 사례 8건 발견, 전부 REJECT 처리(
`review_status: rejected`). TSU-0000021은 추가로 서로 다른 두 목차
줄이 병합되고 원문에 없는 해석("유아 세례")까지 claim에 삽입된
이중 결함. TSU 생성 파이프라인이 목차/색인 페이지를 신학적 진술과
구분하지 못하는 것으로 보이며, 향후 배치에서 유사 패턴이 반복될
가능성이 높음 — 확인 필요.

## Batch 1 완료 요약 (100건)

```
verified: 85건 (85%)
rejected: 15건 (15%)
```

REJECT 사유 분포:
- 목차(TOC) 파편 추출: 8건(TSU-0000017~0000024)
- claim 오배정(다른 TSU의 claim이 잘못 재사용): 2건(TSU-0000027, 0000070)
- claim 텍스트 언어 혼입(한자/키릴/베트남어): 1건(TSU-0000028)
- claim 텍스트 잘림(truncation): 1건(TSU-0000087)
- doctrine 미분류 + 기타: 2건(TSU-0000100, 0000104 오역)
- 원문에 없는 해석 추가: 1건(TSU-0000021, 목차 결함과 중복 집계)

승인되었으나 특이사항 기록된 건(생성 파이프라인 결함 가능성, 별도
트랙 확인 필요로 코멘트만 남김): TSU-0000009/0000010/0000011(한자
혼입), TSU-0000055(doctrine 미분류), TSU-0000057/0000066(한자 혼입),
TSU-0000060(충실도 의심), TSU-0000095(경미한 의미 이동) — 총 7건.

**관찰**: 15% REJECT + 7% "승인되었으나 특이사항" ≈ 전체의 22%가
생성 파이프라인 품질 이슈를 동반. 목차 오추출·언어 혼입·claim
오배정이 반복 패턴으로 확인됨 — TSU 생성 파이프라인(LLM 추출) 자체의
개선 여지가 있으나, 이는 이 Human Review 트랙의 범위를 벗어나며
별도 확인이 필요하다.

## Exception Queue (2026-08-10 도입)

`NAE/review/human/exception_queue.json` — claim language contamination
또는 forensic 재검증에서 문제가 발견된 TSU를 Production 무수정 원칙
하에 격리 추적하는 파일. 현재 4건:

- TSU-0000230, TSU-0000235: language contamination(일본어/베트남어
  혼입) — Promotion 보류(`review_status: generated` 유지, 판정 없음)
- TSU-0000247: forensic 재검증 결과 claim 범위 확대("their own word"
  →"자기들의 언어") 발견 — **이미 verified 상태**, Production/claim
  무수정, downstream(Embedding) eligibility 문서상 보류(아직 코드
  강제 없음, 수동 확인 필요)
- TSU-0000244: 인용 메타데이터 공백(SCRIPTURE_MISMATCH 패턴) —
  non-blocking QA flag, claim 자체는 문제없음

- [x] TSU-0000247 remediation 완료(claim 교체, verified 유지, exception
      queue RESOLVED)
- [x] TSU-0000249~0000258 forensic disposition 완료(Production+canonical
      독립 검증, Human Decision/Promotion 미실행): 0249/0251/0254/0258
      → NEEDS_CLAIM_REVIEW, 0256/0257 → STRUCTURAL_EXCEPTION(문장
      분할 결함, TSU 생성 파이프라인 이슈, 별도 backlog), 0252 →
      READY_FOR_HUMAN_REVIEW + doctrine QA flag, 0250/0253/0255 →
      READY_FOR_HUMAN_REVIEW. 10건 전부 아직 Human Decision 없음(의도됨)
- [ ] Batch 2 나머지(TSU-0000259~TSU-0000308) Human Review

- [x] TSU-0000259~0000268 forensic disposition 완료(Human Decision/
      Promotion 미실행): 0261(오역)/0263(theological review required)/
      0264(언어 오염)/0268(hedge dropped) → NEEDS_CLAIM_REVIEW,
      0265 → STRUCTURAL_EXCEPTION(0256/0257과 동일 유형, segmentation
      backlog 등록), 0262/0266/0259/0260/0267 → READY_FOR_HUMAN_REVIEW
- [ ] Batch 2 나머지(TSU-0000269~TSU-0000308) Human Review

## Segmentation Defect Backlog

`docs/NAE_TSU_SEGMENTATION_DEFECT_BACKLOG_001.md` 신규 — 각주로 인한
문장 분할 결함(TSU-0000256/0257, TSU-0000265/0266) 기록. 코드 변경
없음, Architecture 영역 후속 검토 대상으로만 등록.

- [x] TSU-0000269~0000308 forensic disposition 완료(Human Decision/
      Promotion 미실행). 상세는 아래 Batch 2 Completion Report 참고.
- [x] **Batch 2(100건) forensic disposition 전체 완료** — 2026-08-10
      부터 운영 방식 변경(사용자 승인): 개별 10건 확인 질문 없이 CUE가
      자동으로 forensic 분류만 계속하고, 실제 Human Decision(APPROVED
      /REJECTED)은 배치 종료 후 일괄 처리하는 방식으로 전환.

- [x] READY_FOR_HUMAN_REVIEW 38건 일괄 승인(Q1=A/Q2=A/Q3=A/FINAL=
      APPROVED) 및 Promotion 완료(review_status: generated → verified)
      → 백업 `NAE/corpus/tsu/_batch0002_promotion_backup_<timestamp>/`

## 진행률 (2026-08-10 기준, 실측)

```
Production 전체: verified 164건 (Pilot 10건 포함) / rejected 22건 / generated 3931건
확장분(Pilot 제외) 기준: verified 154 / 4107, rejected 22 / 4107
Exception Queue 미해결(batch_0002): NEEDS_CLAIM_REVIEW 17건, STRUCTURAL_EXCEPTION 5건, QA_FLAG_NONBLOCKING 1건
```

- [x] Exception 22건(21 TSU) 처리: 15건 claim remediation(언어 오염
      7건 + claim 내용 재작성 8건) → forensic 재검증 통과 → Human
      Decision APPROVED → Promotion 완료. 5건(TSU-0000256/0257/0265/
      0271/0272)은 구조적 결함으로 claim 무수정, `generated` 상태
      보류 유지. TSU-0000263은 fidelity/accuracy 상충으로 사용자
      결정 대기 중.

- [x] TSU-0000263 fidelity/accuracy 결정 확정("구원에 기여한다" 유지)
      → Human Decision APPROVED, claim 무수정, verified 승격
- [x] **Batch 2(100건) 완전 종료** — 남은 것은 구조적 결함으로 의도적
      보류 중인 5건(TSU-0000256/0257/0265/0271/0272)뿐

## Batch 2 최종 현황 (2026-08-10)

```
Production 전체: verified 175건(Pilot 10건 포함) / rejected 22건 / generated 3180건
Exception Queue 잔여(batch_0002): STRUCTURAL_EXCEPTION 5건(0256/0257/0265/0271/0272,
                                   segmentation backlog 해결 전까지 의도적 보류)
                                   QA_FLAG_NONBLOCKING 1건(0244 scripture metadata)
```

- [x] Batch 3(TSU-0000402~TSU-0000501, 100건) forensic 자동 스캔
      완료(언어오염/중복/doctrine공백 정규식 + 플래그 20건 canonical
      개별 대조, 나머지 80건은 자동 스캔만 — 전수 수동검증 아님을
      명시). SCREENING_CLEAR 80건 사용자 일괄 승인(Q1=A/Q2=A/Q3=A/
      FINAL=APPROVED, reviewer=David) 및 Promotion 완료.
      → 백업 `NAE/corpus/tsu/_batch0003_promotion_backup_<timestamp>/`

## Batch 3 현황 (2026-08-10)

```
Production 전체: verified 255건(Pilot 10건 포함) / rejected 22건 / generated 3100건
Exception Queue(batch_0003): NEEDS_CLAIM_REVIEW 15건(언어오염 14 + claim오류 2, 1건 중복)
                              QA_FLAG_NONBLOCKING 7건(doctrine 공백)
Validator: PASS(DRIFT=0) / Regression: 실행 중
```

- [x] Batch 3 Promotion 사후 재검증 PASS 확정(80건, 무결성 위반 0건,
      Exception 15건과 중복 없음). Exception 15건은 remediation 없이
      현재 상태(generated) 그대로 보류.
- [x] Batch 4(TSU-0000582~TSU-0000681, 100건) forensic screening
      완료(자동 스캔: 언어오염/중복/doctrine공백). Human Decision/
      Promotion 미실행(사용자 지시).

## Batch 4 Screening 결과 (2026-08-10)

```
SCREENING_CLEAR: 91건
Exception(언어오염, 전부 중국어 한자): 9건
  TSU-0000593(洗足) 0595(洗足) 0597(行) 0628(洗礼) 0645(世俗)
  0675(良心) 0676(力的) 0678(原始) 0679(章)
Human Decision: 0건 (전부 대기)
Production: 무변경
```

- [x] Batch 4 SCREENING_CLEAR 91건 승인·Promotion 완료(reviewer=David,
      diff 91건 only review_status/review_metadata, protected fields
      불변, validator PASS/DRIFT=0).
- [x] Batch 5(TSU-0000774~TSU-0000873, 100건) forensic screening
      완료. Human Decision/Promotion 미실행.

## Batch 5 Screening 결과 (2026-08-10)

```
SCREENING_CLEAR: 90건
Exception(언어오염 9 + fidelity 1건 중복): 9건 TSU
  0802(如此) 0803(尊重) 0818(榜樣+오역:apostle→대제사장) 0823(利)
  0827(真正) 0842(紀律) 0864(щед,러시아어) 0869(учрежд,러시아어) 0871(頼)
QA_FLAG_NONBLOCKING(doctrine 공백): 1건 (TSU-0000798)
```

- [x] Batch 5 SCREENING_CLEAR 90건 승인·Promotion 완료(TSU-0000818
      fidelity 이슈 포함 10건 정상 제외 확인).
- [x] Batch 6(TSU-0000964~TSU-0001063, 100건) forensic screening 완료.

## Batch 6 Screening 결과 (2026-08-10)

```
SCREENING_CLEAR: 88건
Exception(언어오염): 3건 — TSU-0000977(上的上的) 1023(渐進的な) 1027(們)
QA_FLAG_NONBLOCKING(doctrine 공백): 9건
```

- [x] Batch 6 SCREENING_CLEAR 88건 + QA_FLAG_NONBLOCKING 9건 = 97건
      승인·Promotion 완료(Exception 3건 정상 제외 확인).
- [x] Batch 7(TSU-0001161~TSU-0001260, 100건) forensic screening 완료.

## Batch 7 Screening 결과 (2026-08-10)

```
SCREENING_CLEAR: 85건
Exception(언어오염, fidelity 이슈 없음): 15건
  0001161 0001171 0001181 0001191 0001198 0001210 0001213 0001216
  0001217 0001218 0001219 0001226 0001227 0001236 0001248
QA_FLAG_NONBLOCKING: 0건
```

- [x] Batch 7 SCREENING_CLEAR 85건 승인·Promotion 완료.
- [x] Batch 8(TSU-0001346~TSU-0001445, 100건) forensic screening 완료.

## Batch 8 Screening 결과 (2026-08-10)

```
SCREENING_CLEAR(QA_FLAG 2건 포함 승인 가능): 83건
Exception: 17건 — 언어오염 16건(TSU-0001352는 claim 전체가 일본어로
  작성된 심각 사례) + claim 중복 1건(TSU-0001390, 0001389와 동일)
QA_FLAG_NONBLOCKING(doctrine 공백, 승인 대상 포함): 2건
```

- [x] Batch 8 승인 가능 83건 승인·Promotion 완료.
- [x] Batch 9(TSU-0001529~TSU-0001628, 100건) forensic screening 완료.

## Batch 9 Screening 결과 (2026-08-10)

```
승인 가능(QA_FLAG 9건 포함): 85건
Exception(언어오염, TSU-0001609는 claim 전체가 중국어): 15건
QA_FLAG_NONBLOCKING(doctrine 공백, 승인 대상 포함): 9건
```

- [x] Batch 9 승인 가능 85건 승인·Promotion 완료(TSU-0001609 전체
      중국어 claim 포함 15건 정상 제외 확인). **성능 참고**: 누적
      백업 디렉터리(29개, 157MB)로 `indexer.index_all()` dry_run이
      느려짐(1회 타임아웃 발생, 재시도로 해결) — 배치가 늘어날수록
      악화될 수 있음, 추후 정리 방법 논의 필요.
- [x] Batch 10(TSU-0001714~TSU-0001813, 100건) forensic screening 완료.

## Batch 10 Screening 결과 (2026-08-10)

```
승인 가능(QA_FLAG 4건 포함): 86건
Exception(언어오염): 14건
```

- [x] Batch 10 승인 가능 86건 승인·Promotion 완료(sed 오염으로 인한
      무관 synthetic 테스트 2건 오염 발견·정정, PERFORMANCE_BACKLOG
      정식 등록 — `docs/NAE_TSU_INDEXER_PERFORMANCE_BACKLOG_001.md`,
      백업 디렉터리는 보존, indexer 코드는 무수정).
- [x] Batch 11(TSU-0001900~TSU-0001999, 100건) forensic screening 완료.

## Batch 11 Screening 결과 (2026-08-10)

```
승인 가능(QA_FLAG 4건 포함): 89건
Exception(언어오염): 11건
```

- [x] Batch 11 승인 가능 89건 승인·Promotion 완료.
- [x] Batch 12(TSU-0002089~TSU-0002188, 100건) forensic screening 완료.

## Batch 12 Screening 결과 (2026-08-10)

```
승인 가능: 93건
Exception(언어오염): 7건
```

- [x] Batch 12 승인 가능 93건 승인·Promotion 완료.
- [x] Batch 13(TSU-0002282~TSU-0002381, 100건) forensic screening 완료.

## Batch 13 Screening 결과 (2026-08-10)

```
승인 가능: 95건
Exception(언어오염 4 + claim 중복 1): 5건
```

- [x] Batch 13 승인 가능 95건 승인·Promotion 완료(TSU-0002299는
      CLAIM_DUPLICATE / ADJACENT_CONTEXT_LOSS 유형으로 기록, 정상 제외).
- [x] Batch 14(TSU-0002477~TSU-0002576, 100건) forensic screening 완료.

## Batch 14 Screening 결과 (2026-08-10)

```
승인 가능(QA_FLAG 3건 포함): 81건
Exception(언어오염, TSU-0002501은 claim 전체가 중국어): 19건
QA_FLAG_NONBLOCKING(doctrine 공백): 3건
```

- [x] Batch 14 승인 가능 81건 승인·Promotion 완료(TSU-0002501 CRITICAL
      전체-중국어 claim 정상 제외 확인).
- [x] Batch 15(TSU-0002658~TSU-0002757, 100건) forensic screening 완료.

## Batch 15 Screening 결과 (2026-08-10)

```
승인 가능: 92건
Exception(언어오염): 8건
```

- [x] Batch 15 승인 가능 92건 승인·Promotion 완료.
- [x] **Batch 15 완료 후 작업 중지**(사용자 지시) — Batch 16 시작하지 않음.

## 다음 조치

Batch 16(TSU 범위는 Promotion 시점 기준 재계산 필요, 잔여 2,768건
중 첫 100건) 진행 여부는 사용자 지시 대기.
