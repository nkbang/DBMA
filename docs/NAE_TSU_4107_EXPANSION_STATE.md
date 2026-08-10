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
- [ ] Batch 1 Human Review 진행(사용자)
- [ ] Batch 1 Promotion
- [ ] Batch 2 ~ 42 반복

## 진행률

```
tsu_reviewed_and_completed: 0 / 4107
percent_complete: 0.0%
batches_with_requests: 1 / 42
```

## 다음 조치

Batch 1(100건)의 리뷰 방식은 Pilot 001과 동일한 Q1-Q3(+조건부 Q4)
구조를 그대로 사용한다. 다만 Pilot과 달리 100건 전부를 한 세션에서
서술형으로 리뷰하는 것은 비현실적이므로, 사용자가 원하는 하위 진행
방식(예: 몇 건씩 나눠 확인, 또는 일괄 A/A/A 승인 후 이상 건만 별도
표시 등)을 다음 대화에서 확인 후 진행한다.
