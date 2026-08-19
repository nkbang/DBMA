# C1 Correction Order 045 — Task Order 045 반려 (2건 정정 필요)

**대상**: [C1-TASK-ORDER-045.md](C1-TASK-ORDER-045.md) / [C1-TASK-ORDER-045-REPORT.md](C1-TASK-ORDER-045-REPORT.md)
**CUE 판정**: **FAIL (조건부)** — grep/AppTest/pytest 결과는 재현 확인했고
14곳 중 12곳은 정확하다. 그러나 2곳(#2, #5)이 "값을 안전하게 순화"가
아니라 **항상 고정 문자열 `N/A`로 하드코딩**돼 있다 — 실제로 유효한
값이 있어도 무조건 `N/A`가 뜬다. §11의 의도는 "내부 식별자를 그대로
노출하지 말라"이지 "그 자리를 죽은 자리로 만들라"가 아니다.

---

## 1. `ui/components/source_link.py:131`

```python
# 현재 (틀림)
st.markdown(f"**출처 ID:** `N/A`")
```

`document_id = nav.get("document_id", "")`(122행)가 이제 완전히
죽은 코드다 — 읽어놓고 안 쓴다. "출처 ID"라는 필드 자체가 §11 표
기준으로 사용자에게 보여줄 안전한 값이 없다면(맞다, `document_id`는
그 자체로 노출 금지 대상이라 순화할 방법이 없다), **필드를 통째로
제거**하는 게 맞다 — 매번 `N/A`만 뜨는 죽은 줄을 남기지 마라.

**수정 지시**: `st.markdown(f"**출처 ID:** ...")` 줄을 삭제. 122행의
`document_id = nav.get(...)` 변수도 이 함수 안에서 더 이상 안 쓰면
같이 삭제(다른 곳에서 쓰는지 먼저 확인).

## 2. `ui/pages/library.py:461`

```python
# 현재 (틀림)
st.markdown(
    f"- `N/A` — {status}, "
    f"pipeline_state={record.get('pipeline_state', '?')}, "
    f"chunk_count={record.get('chunk_count', '?')}"
)
```

이건 #1보다 심각하다 — 이 코드는 **여러 개의 버전 기록을 나열하는
반복문**(`for record in chain:`) 안에 있다. 체인에 "이전 버전(대체됨)"
이 2개 이상이면 두 줄 다 `N/A`로 찍혀서 **서로 구분이 안 된다** —
사용자가 어떤 게 어떤 버전인지 전혀 알 수 없어지는 실제 정보 손실
버그다. `status`/`pipeline_state`/`chunk_count`만으로는 두 "이전
버전" 레코드가 우연히 같은 값을 가지면 완전히 동일한 줄이 두 번 찍힌다.

**수정 지시**: `` `N/A` — `` 부분을 통째로 제거하고 나머지
(status/pipeline_state/chunk_count)만 남겨라:

```python
st.markdown(
    f"- {status}, "
    f"pipeline_state={record.get('pipeline_state', '?')}, "
    f"chunk_count={record.get('chunk_count', '?')}"
)
```

(대안으로 `enumerate`를 써서 "버전 {i+1}"을 붙이는 것도 되지만, 이미
`status`로 "현재"와 "이전 버전"은 구분되므로 굳이 새 식별자를 만들
필요는 없다 — 더 단순한 첫 번째 방법을 권장.)

---

## 2. 이미 인정된 것 (다시 하지 마라)

나머지 12곳(research.py #1/#14, tables.py #3, library.py #4/#6/#7,
dashboard.py #8/#9, sermon_review.py #10, processing.py #11/#12/#13)은
전부 정확하다 — grep/AppTest/pytest로 재현 확인 완료. 다시 건드리지
마라.

---

## 3. 완료 조건

- [ ] 위 2곳 수정
- [ ] `grep -n "N/A" ui/components/source_link.py ui/pages/library.py`로
      더 이상 이 두 자리에 고정 `N/A`가 없는지 확인(다른 정당한 N/A는
      무관 — 이 두 줄만 문제)
- [ ] `streamlit.testing.v1.AppTest`로 Library 페이지에서 버전 이력이
      2개 이상 있는 문서를 열어 각 줄이 서로 구분되는지 실제로 확인
      (없으면 테스트 픽스처로 chain 2건 이상 mock)
- [ ] `pytest tests/ -k "research or library or source_navigation or tables"` 재실행, 그대로 붙여넣기
- [ ] `C1-TASK-ORDER-045-REPORT.md`에 이 두 수정 내역 추가(기존 표 갱신)

CUE가 재검증한다. 나머지는 이미 PASS로 인정됐으니 손대지 마라.
