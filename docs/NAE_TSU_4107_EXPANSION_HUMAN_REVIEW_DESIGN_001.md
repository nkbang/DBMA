# NAE TSU 4,107건 확장 Human Review — 설계 문서 001

**작성일:** 2026-08-09
**성격:** 설계 제안(구현 전). Pilot 001(10건, 100% 완료)의 Human Review
Gate 아키텍처를 나머지 4,107건 `generated` TSU로 확장하기 위한 설계.
**Authority:** `NAE/review/human/*`(Pilot 001에서 검증된 기존 구조),
`NAE/review/human/schema.py::MAX_PENDING_REVIEW=100`(기존 안전
게이트, 변경하지 않음).

---

## 1. 현재 상태 (실측)

```
Production TSU 총계: 4,117건
  review_status=generated : 4,107건  <- 이번 확장 대상
  review_status=verified  :    10건  (Pilot 001, 완료)
```

### Doctrine × Source 분포 (generated 4,107건)

| Doctrine | Dagg | Hiscox | 합계 |
|---|---|---|---|
| Ecclesiology | 1,758 | 305 | 2,063 |
| Baptism | 718 | 179 | 897 |
| Lord's Supper | 205 | 52 | 257 |
| Soteriology | 152 | 44 | 196 |
| Sanctification | 118 | 21 | 139 |
| Scripture / Authority | 102 | 17 | 119 |
| (doctrine 미분류, None) | 102 | 7 | 109 |
| Church Discipline | 33 | 54 | 87 |
| Election | 54 | 9 | 63 |
| Eschatology | 35 | 14 | 49 |
| Justification | 24 | 12 | 36 |
| Providence | 22 | 7 | 29 |
| Other | 27 | 1 | 28 |
| Trinity | 13 | 6 | 19 |
| Confession | 4 | 5 | 9 |
| Church Covenant | 5 | 2 | 7 |

**Ecclesiology + Baptism 두 항목이 전체의 72%(2,960/4,107)** — Dagg의
교회 정치서·Hiscox의 침례교 매뉴얼이라는 원문 성격상 예상된 분포.

## 2. 현실적 제약 (Pilot 001 실측 기반)

Pilot 001의 10건 Human Review는 각 항목마다 원문·클레임 제시 →
Q1-Q4 신학적 판단(성경 근거 포함 서술형 답변) → FINAL DECISION을
사용자가 직접 작성하는 방식으로, **여러 세션에 걸쳐 진행**되었다.
이 방식을 4,107건에 그대로 1:1 적용하면 완료까지 비현실적으로 긴
시간이 필요하다. 따라서 **전량 동일 강도 리뷰가 아니라, 단계적·
배치 기반 진행**이 필요하다.

기존 안전 게이트 `MAX_PENDING_REVIEW = 100`([schema.py](../NAE/review/human/schema.py))이
이미 "한 번에 PENDING 상태로 둘 수 있는 최대 건수"를 100건으로
제한하고 있어, 이 설계는 이 제약을 그대로 따른다(변경하지 않음).

## 3. 설계 제안

### 3.1 아키텍처 재사용 (변경 없음)

- `decision_gate.py`의 Q1-Q4 + Q4 특별 경고 플래그 + FINAL DECISION
  vocabulary, `HumanDecisionRecord`, `is_promotion_eligible()` 로직은
  Pilot 001에서 검증된 그대로 재사용.
- `review_promotion.py::promote_tsu_to_verified()`(승격 유일 경로)도
  변경 없음.
- `PILOT_REFERENCE`(schema.py, 10건)는 **건드리지 않는다** — Pilot
  001 감사 기록으로 그대로 고정. 확장분은 별도 소스에서 로드.

### 3.2 신규 — 배치 요청 생성기 (제안)

`decision_gate.py`의 `build_requests()`는 현재 `schema.PILOT_REFERENCE`
(하드코딩 10건)만 입력으로 받는다. 확장을 위해 **임의의 TSU 레코드
리스트**를 받는 범용 버전이 필요하다(기존 함수는 그대로 두고 별도
함수 추가 — Pilot 경로 회귀 방지):

```python
def build_requests_from_records(records: list[dict]) -> list[HumanReviewRequest]:
    """PILOT_REFERENCE 대신 임의의 review_status='generated' TSU
    레코드 리스트를 받아 Q1-Q3(+조건부 Q4) 요청을 생성한다."""
```

### 3.3 배치 분할 전략

- 배치 크기: `MAX_PENDING_REVIEW=100`을 그대로 배치 크기 상한으로 사용.
- 순서: **TSU ID 오름차순, source 단위(Dagg 전체 → Hiscox 전체)** —
  Pilot 001과 동일한 원칙(추적 가능성 우선, 임의 순서 금지).
- 배치 상태 파일 신규: `NAE/review/human/batch_state.json` —
  각 배치의 시작/완료 여부, 리뷰 완료 건수, 마지막 처리 TSU ID를
  기록해 세션이 끊겨도 이어서 진행 가능하게 한다.
- 총 배치 수: 4,107 / 100 ≈ **42개 배치**.

### 3.4 리뷰 강도 — 단계적 접근 (사용자 결정 필요)

Pilot 001과 동일한 서술형 Q1-Q4 전체 리뷰를 42개 배치 전부에
적용할지, 아니면 강도를 낮춘 경량 리뷰(예: 클레임-원문 일치 여부만
A/R 이진 판단 + 이상 징후 있을 때만 서술형 Q4)를 적용할지는 순전히
사용자의 페이스와 신학적 정밀도 요구 수준에 달린 결정이다. AI가
임의로 리뷰 강도를 낮출 수 없다(자동 정답 생성 금지 원칙과 동일한
이유 — 신학적 판단은 항상 인간 소관).

**제안 옵션(사용자 선택 필요):**

| 옵션 | 방식 | 장점 | 단점 |
|---|---|---|---|
| A. 전량 동일 강도 | Pilot과 동일한 Q1-Q4 서술형 × 4,107건 | 최고 정밀도 | 완료까지 매우 오랜 시간 |
| B. 배치 우선순위 + 점진 확장 | Ecclesiology/Baptism처럼 비중 큰 doctrine부터 배치 단위로 진행, 매 배치 후 진행률 보고·중단/계속 판단 | 페이스 조절 가능, 언제든 멈춰도 안전 | 완료 시점 불확정 |
| C. 경량 1차 스크리닝 + 정밀 2차 | 1차는 A/R 이진 판단으로 빠르게 전수 스크리닝, REJECT/애매 건만 Q1-Q4 정밀 재검토 | 속도 개선 | 스키마·vocabulary 신규 설계 필요(범위 확대) |

## 4. 진행 상태 문서화 (CLAUDE.md 규칙 준수)

신규 `docs/NAE_TSU_4107_EXPANSION_STATE.md`를 만들어 체크포인트·
진행률(%)을 기록. 예:

```md
- [x] 설계 완료
- [ ] 배치 요청 생성기 구현
- [ ] Batch 1(TSU-0000001~) 리뷰
- [ ] ...
진행률: 0% (0/4107)
```

## 5. 다음 조치

이 문서는 설계 제안이며, 아직 아무 코드도 변경하지 않았고 어떤
`requests/`도 생성하지 않았다. 사용자 확인이 필요한 항목:

1. **리뷰 강도**: 위 3.4의 A/B/C 중 선택.
2. **배치 크기/순서**: 100건·TSU ID 오름차순·source 단위(3.3안)로
   진행해도 되는지.
3. **시작 지점**: 첫 배치를 Dagg의 TSU-0000001부터 시작할지, 아니면
   비중이 큰 Ecclesiology/Baptism부터 우선할지.

확인되는 대로 `build_requests_from_records()` 구현 + 배치 상태 파일
초기화 + 첫 배치(최대 100건) 요청 생성까지 진행하겠습니다.
