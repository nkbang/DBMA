# C1 Task Order 067 — RQ-1 재답변 요청 (source_provenance 필드 누락)

- 발주: CUE · 일자: 2026-09-17
- 모드: **PLAN MODE 전용 — ACT MODE 금지. 구현하지 않는다**
- 사용 모델: `dbma-planner-r1-q6:70b`(분석용)
- 성격: 범위 고정 검증형 Q&A — 아래 파일만 근거로 삼을 것
- 대상: `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_002.md`의 RQ-1 답변

## CUE 대조검증 결과

`docs/DBMA_SIDECAR_METADATA_C1_REVIEW_VERIFICATION_002.md`를 먼저 읽어라.
**RQ-2는 정확했다 — 재검토 불필요.** RQ-1에 근거 누락이 있다.

RQ-1 답변(002 문서 62, 71, 80행)이 "`source` 필드는 존재하지 않는다"고
세 번 단정했는데, `core/document_context.py:76`에
`source_provenance: Optional[dict] = None` 필드가 이미 존재하고
(`core/claim_guard.py:284`, `core/retrieval.py:1098,1113,2070`,
`core/generation.py:556-589`, `core/tsu_builder.py:458-471`에서 실제로
쓰인다 — 죽은 필드 아님, 인용 라벨링에 관여). 이 필드가 답변에 전혀
등장하지 않았다.

## 재답변 요청

**RQ-1을 다시 답하라.** 이번에는 `source_provenance` 필드를 반드시
검토 대상에 포함해라. 다음 두 질문에 답하라:

1. D-2의 사이드카 `source` 키(예: `"archive.org original.pdf docinfo"`)가
   `source_provenance`(dict)에 담기도록 설계하는 것이 타당한가, 아니면
   `source_provenance`는 이미 다른 용도(외부 소스 청크 판정, TSU record
   전파)로 쓰이고 있어 같은 필드를 공유하면 의미 충돌이 생기는가?
   `core/generation.py` 556~589행, `core/tsu_builder.py` 458~471행을
   읽고 `source_provenance`의 현재 스키마(어떤 키를 담는지)와 D-2의
   `source` 문자열이 같은 성격인지 판단하라.
2. 위 판단에 따라 RQ-1의 최종 결론("D-2 스키마는 기존 Model 변경 아님")이
   그대로 유지되는가, 아니면 수정이 필요한가?

**RQ-2는 다시 답하지 말 것 — 확정됨.**

## 요청 형식

- 파일·행 번호 근거 필수. 추정치 금지, 확인 못 한 것은 "확인 불가"
- 판정: GREEN / YELLOW / RED
- 산출물: `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_003.md`
- 결과 문서 상단에 `git rev-parse HEAD`, `git remote -v`,
  `git rev-parse --show-toplevel` 출력 먼저 붙일 것

## 게이트

RQ-1 재답변 → CUE 대조 검증 → 두 질문 모두 확정 시 설계 확정 → HQ 승인 →
구현 착수. Evidence Before Promotion Rule에 따라 그 전까지 선행 구현 금지.
