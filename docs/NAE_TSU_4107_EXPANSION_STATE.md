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
- [ ] Batch 2(TSU-0000108~) 요청 생성 및 진행
- [ ] Batch 3 ~ 42 반복

## 진행률

```
verified: 85 / 4107 (Pilot 10건 제외)
rejected: 15 / 4107
reviewed subtotal: 100 / 4107 (2.44%)
batches_with_requests: 1 / 42 (batch_0001: 100/100건 완료)
```

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

## 다음 조치

Batch 2(TSU-0000108부터, Dagg_Church_Order 계속)의 요청을 생성해
동일한 10건씩 제시 → 사용자 확인 → Promotion 순서로 반복 진행한다.
