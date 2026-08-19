# C1 Task Order 039 (재발부 v5) — 최종 범위: 대칭성 실측 + 정직한 미검증 표기

**상태**: **종료 (CUE 최종 판단 완료, 2026-08-18)** — 상세: [C1-TASK-ORDER-039-REPORT.md](C1-TASK-ORDER-039-REPORT.md) §2
**우선순위**: P1
**근거 문서**: [DBMA-UX-007-IMPLEMENTATION-SPEC.md](../../DBMA-UX-007-IMPLEMENTATION-SPEC.md)
**작성일:** v1 2026-07-31 / v2 반려 / v3 / v4 REWORK / **v5 2026-07-31 (최종 범위)**

---

## 0. HQ 결정 — 이번이 이 항목의 마지막 경계다

- **코드 수정(citation_card.py, chat.py)은 이미 PASS 확정** — 더 이상 손대지 않는다
- **§1-A(브라우저 물리 검증)는 앞으로 C1에게 다시 요구하지 않는다.** C1의
  환경에 실제 브라우저 접근 도구가 없다는 것을 두 번의 시도로 확인했다.
  이번엔 검증을 시키는 대신 **정직한 라벨링만** 요구한다.
- **§1-B(검색 경로 조사)만 한 가지 실측을 더 하면 끝난다.**

이 Task Order 완료 후 CUE가 최종 판단한다. 더 이상 UI 코드 수정도,
브라우저 검증 시도도 요구하지 않는다.

## 1. 작업 A — §1-B 대칭성 실측 (필수, 이것만 하면 됨)

v4 보고서는 "TSU 데이터셋이 0바이트라 결과가 0건"이라는 근본 원인을
찾았다고 결론 냈다. **그러나 Chat과 Research가 완전히 동일한
`get_shared_query_processor()` → `QueryProcessor()` →
`RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH)` 경로를
쓴다는 것도 v4 스스로 §1-B "1. 검색 경로 매핑"에서 확인했다.** 데이터셋이
정말 비어있다면 Chat뿐 아니라 **Research도 지금 이 순간 0건이어야 앞뒤가
맞는다.** v4는 이 대칭 검증을 하지 않았다.

**지금 이 시점에 실측하라**:

```python
# 동일 세션, 동일 QueryProcessor 인스턴스로:
result_research = processor.process("로마서 8장 성령", query_id="test-research", k=10)
result_chat = processor.process("로마서 8장 성령", query_id="test-chat", k=5, file_scope=None)
print("Research top_k_results:", len(result_research.top_k_results))
print("Chat top_k_results:", len(result_chat.top_k_results))
```

두 가지 경우로 나뉜다:

- **둘 다 0건** → "TSU 데이터셋 공백"이 원인이라는 결론이 성립한다.
  단, 이 경우 CUE가 이전에(오늘 세션 중) Research에서 실제 결과를 받았던
  사실과 시점이 어긋나므로, **TSU 데이터셋이 언제부터 비었는지**
  (`git log`, 파일 mtime, 관련 프로세스 로그 등으로 확인 가능한 범위까지)
  같이 기록하라 — 다른 세션이 재빌드 중이라 일시적으로 빈 상태일
  가능성도 있다는 걸 염두에 두고 적어라.
- **Research는 결과가 나오고 Chat만 0건** → "TSU 공백" 결론은 틀렸다.
  Chat과 Research 사이에 아직 못 찾은 다른 경로 차이가 있다는 뜻이니,
  v4에서 이미 비교한 항목표(§1-B "2. 핵심 차이 비교")를 다시 보고 놓친
  게 무엇인지 찾아라 — 특히 `file_scope=None`이 두 곳에서 정말 동일하게
  처리되는지, `_current_scope()`가 매 호출마다 정확히 `None`을 반환하는지
  실제 세션 상태값을 찍어서 확인하라.

이 실측 결과에 따라 §4 "근본 원인" 결론을 **수정하거나 확정**하라.

## 2. 작업 B — §1-A 라벨 정정 (원칙 변경)

브라우저를 실제로 검증하지 못했다면 **"PASS (정적 분석)"이라는 표현을
완전히 삭제**하고 아래로 명시하라:

```
Status: NOT VERIFIED — physical browser verification unavailable in this environment
```

- 과거 스크린샷, mock 호출, import test, 정적 코드 분석은 브라우저 검증의
  증거로 인정하지 않는다 — "NOT VERIFIED"로 남기는 것 자체가 이번엔
  정답이다. 억지로 PASS를 만들지 마라.
- 실제 브라우저 물리 검증은 이후 CUE 또는 별도 환경에서 독립적으로
  수행한다 — C1의 책임이 아니다.

## 3. 완료 조건

- [ ] 동일 시점 Chat/Research 대칭 실측 결과 기록 (0건/0건 또는 비대칭)
- [ ] 실측 결과에 따라 근본 원인 결론 수정 또는 확정
- [ ] §1-A를 "NOT VERIFIED — physical browser verification unavailable"로 정정, PASS 표현 삭제
- [ ] `citation_card.py`/`chat.py` 코드 수정 없음 확인
- [ ] 범위 밖 파일 수정 없음

## 4. 산출물

`docs/agents/c1/C1-TASK-ORDER-039-REPORT.md` 재작성. 완료 후 CUE
최종 판단에 회부하라 — 이 Task Order로 마지막이다.
