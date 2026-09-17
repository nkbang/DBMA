# CUE 대조검증 — C1 Review 결과 002 (RQ-1, RQ-2)

- 검증자: CUE · 일자: 2026-09-17
- 대상: `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_002.md`(C1 응답, HEAD `31ada082`)
- 방법: [[feedback_c1_routing_criteria]] 원칙 — C1 산출물을 신뢰하지 않고
  인용된 파일·행 번호를 직접 열어 대조

## 결론 — RQ-2는 확정, RQ-1은 조건부(실제 결함 발견)

| 질문 | C1 판정 | CUE 대조 결과 |
|---|---|---|
| RQ-1 | GREEN | **PLAUSIBLE — 완전하지 않음.** 인용 라인은 정확하나 관련 기존 필드 하나를 놓쳤다(아래) |
| RQ-2 | YELLOW(조건부 GREEN) | **CONFIRMED.** 코드 로직·예시 계산·인용 라인 전부 정확 |

## RQ-2 검증 — 문제없음

`core/extractors.py` 116, 117, 129, 130, 150, 184, 189행 전부 실제 코드와
정확히 일치. `"Untitled".strip() or None` → `"Untitled"`(참으로 평가되어
`None`으로 강등되지 않음) 계산도 정확하다. 블랙리스트+휴리스틱 권고안은
합리적이다. **이 부분은 그대로 수용한다.**

## RQ-1 검증 — 놓친 필드 발견

C1은 "`source` 필드는 존재하지 않는다"고 세 번(62, 71, 80행) 단정했다.
`DocumentContext`(42~58행)에 리터럴 `source`는 없다는 것은 맞다. 그러나
**`core/document_context.py:76`에 `source_provenance: Optional[dict] = None`
필드가 이미 존재하고, 이것이 죽은 필드가 아니라 실제로 널리 쓰이고
있다**:

```
core/claim_guard.py:284      prov = meta.get("source_provenance")
core/retrieval.py:1098,1113  provenance = tsu.get("source_provenance")
core/retrieval.py:2070       prov = md.get("source_provenance")
core/generation.py:556-589   외부 소스 유래 청크 판정 + 인용 라벨(logos_location)
core/tsu_builder.py:458-471  registry → TSU record 전파
```

`source_provenance`는 정확히 "이 청크/문서가 어디서 왔는가"를 담는
필드이고, TSU record까지 전파돼 **인용 라벨링에 실제로 쓰인다**
(`core/generation.py:589` — "Logos location을 라벨에" 반영). 사이드카의
`source: "archive.org original.pdf docinfo"` 키가 의미하는 바(이 메타데이터가
어디서 왔는지)와 개념적으로 정확히 같은 자리다.

**RQ-1 원 질문 "D-2의 3키 스키마가 기존 Model에 필드를 추가하지 않는가"에
대한 답은, `source_provenance`를 고려하지 않고는 완전하지 않다.** 두 가지
가능성이 남는다:

1. 사이드카의 `source`가 `source_provenance`(dict)에 담기도록 설계하면 —
   기존 필드 재사용이라 RQ-1의 GREEN 결론이 오히려 더 강해진다.
2. 반대로 `source_provenance`가 이미 "TSU record 진입"이라는 다른 용도
   (외부 소스 청크 판정)로 쓰이고 있어, D-2의 `source`(사이드카 출처
   문자열)를 거기 넣으면 **의미가 다른 두 개념이 같은 필드를 공유**하게
   돼 오히려 새로운 설계 위험이 생긴다.

어느 쪽이든 **C1이 이 필드의 존재를 언급 없이 "필드가 없다"고만 답한 것은
근거가 불완전하다** — 단순 grep으로 3초 안에 발견 가능한 위치였다.

## 재요청

C1-TASK-ORDER-067로 `source_provenance` 필드를 반영한 재답변을 요청한다.
RQ-2는 재검토 불필요(확정).
