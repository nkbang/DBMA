# C1 Task Order 004 — 설교문 작성 워크플로(Phase 1) 아키텍처 설계 검토

발급: CUE (2026-07-21)
대상: C1 (Cline 작업창 #1, **모델: `qwen3.6:35b-DBMAcode`** — 사용자
지정. 코드 작업용으로 도입된 모델이지만 이번 작업은 설계 문서 작성이며,
아래 §4/§7의 "코드 변경 절대 금지" 제약은 모델 선택과 무관하게 그대로
유지된다)
성격: **설계 검토 문서 작성 — 코드 변경 절대 금지.** 이 작업의 산출물은
마크다운 설계 문서 하나뿐이며, `.py` 파일을 단 한 줄도 만들거나 고치지
않는다. [[feedback_c1_routing_criteria]]의 "코드는 CUE 전담" 원칙을
그대로 유지하는 작업 — Task Order 003(TDD 게이팅 코드 예외)과는 다른
카테고리다.

---

## 1. 배경 (사용자 요청, PM 분석 결과)

사용자가 RAG Chat 답변이 "다이제스트하다"(빈약하다)고 지적했고, 향후
**설교문(sermon manuscript) 작성 기능**이 필요하다는 요구가 있었다. CUE가
PM 관점에서 분석한 결과:

- 현재 Chat은 "질문 하나 → 답 하나"의 단발 Q&A 구조 (`core/generation.py::
  GenerationService.generate()`/`generate_stream()`, `ui/pages/chat.py`).
- 설교문 작성은 이것과 다른 워크플로가 필요: 본문(성경 구절)+주제 입력 →
  넓은 범위 자료 검색 → 설교 개요(서론/대지/결론) 1차 생성 → **사용자
  검토·수정** → 승인된 개요를 대지별로 확장 생성 → 출처 인용 포함 최종본.
- 이건 신규 기능(Phase 1)이며, 규모가 커서 코드를 바로 쓰기 전에
  아키텍처 설계 검토가 먼저 필요하다고 판단했다.

## 2. 목표

`docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-Review.md` 파일 하나를
작성하라 (새 파일 생성만 허용, 기존 파일은 건드리지 않는다). 이 문서는
"어떻게 구현할지"의 설계 검토이며, 실제 구현 코드는 포함하지 않는다
(의사코드/인터페이스 시그니처 수준까지는 가능, 완전한 함수 본문은 불가).

## 3. 검토해야 할 질문 (문서에 반드시 답할 것)

1. **검색 전략**: 지금 `RetrievalEngine.retrieve(k_output, file_scope)`는
   질문 하나당 k=3~10개 짧은 청크를 반환하도록 설계돼 있다(`core/
   retrieval.py`). 설교 한 편을 쓰려면 훨씬 넓은 범위(여러 챕터/여러
   문헌)의 자료가 필요한데, 기존 `retrieve()`를 그대로 여러 번 호출하는
   방식과, `k_output`/`candidate_k` 자체를 확장하는 방식 중 어느 쪽이
   기존 아키텍처(One Retrieval Engine 원칙, `docs/architecture/ADR-001-
   Retrieval-Engine-Authority.md` 참고)를 덜 깨는가?
2. **개요 생성 → 확장 생성의 2단계 구조**: 이걸 하나의 새 UI 페이지
   (`ui/pages/sermon_draft.py` 같은)로 만들 때, 세션 상태를 어떻게
   모델링해야 하는가 (예: `st.session_state`에 "현재 개요", "승인 여부",
   "대지별 확장 결과"를 어떤 키 구조로 둘지)? 기존 `ui/state/
   query_processor.py`, `ui/pages/research.py`의 세션 상태 패턴을 참고해
   일관성 있는 설계를 제안하라.
3. **문체 학습(Phase 2 대비)**: 코퍼스에 이미 사용자 본인의 과거 설교문
   (.rtf 파일들, `source_file`로 식별 가능)이 섞여 있다. 이걸 "내용
   검색 대상"과 "문체 참고 예시"로 구분해서 다루려면 TSU 데이터 모델이나
   `file_scope` 필터링에 어떤 최소 변경이 필요한가 (Phase 1에서는 설계만,
   구현은 하지 않음)?
4. **GenerationService 재사용 가능성**: 기존 `GenerationService.generate()`
   /`generate_stream()`을 그대로 재사용할 수 있는가, 아니면 개요 생성용과
   확장 생성용으로 별도 메서드가 필요한가? 재사용 시 어떤 부분이 걸리는가
   (예: 현재 프롬프트는 단발 질문·답변 형태로 고정돼 있음).
5. **리스크**: 이 워크플로가 기존 Retrieval/Generation 아키텍처의 어떤
   전제를 깨뜨릴 위험이 있는가? (예: One Execution State 원칙과 다단계
   세션 상태의 충돌 가능성 등)

## 4. 반드시 지킬 것 (Scope — 위반 시 반려)

- **`.py` 파일을 만들거나 수정하지 마라.** 산출물은 §2에 명시한 마크다운
  파일 하나뿐이다.
- **기존 파일(`core/retrieval.py`, `core/generation.py`, `ui/pages/*.py`
  등)을 절대 수정하지 마라.** 읽기/참고만 하라.
- 완전한 함수 구현체를 쓰지 마라. 인터페이스 시그니처·의사코드·설계
  다이어그램(텍스트 트리 형태)까지만 허용.
- §3의 5개 질문 각각에 대해 "권장안 + 이유 + 트레이드오프" 형식으로
  답하라 — 질문 하나만 깊이 파고 나머지를 생략하면 반려.
- 문서 마지막에 "CUE가 구현 시작 전 확인해야 할 열린 질문" 목록을
  3~5개 남겨라(불확실한 부분을 지어내지 말고 질문으로 남길 것).

## 5. C1에게 보낼 프롬프트

```text
너는 DBMA 프로젝트의 시스템 아키텍트다(Principal Research Engineer
역할). 이번 작업은 설계 검토 문서 작성이며, 코드는 단 한 줄도 쓰지 않는다
— .py 파일을 만들거나 수정하는 것은 절대 금지다.

배경: RAG Chat이 단발 질문-답변 구조인데, 앞으로 "설교문 작성" 기능을
만들어야 한다. 설교문 작성은 본문(성경 구절)+주제 입력 → 넓은 범위 자료
검색 → 설교 개요(서론/대지/결론) 1차 생성 → 사용자 검토·수정 → 승인된
개요를 대지별로 확장 생성하는 다단계 워크플로가 필요하다.

기존 아키텍처 (반드시 이 파일들을 먼저 읽고 참고할 것, 수정 금지):
- /Users/David/DBMA/core/retrieval.py (RetrievalEngine.retrieve(),
  QueryProcessor.process() — file_scope 파라미터 있음)
- /Users/David/DBMA/core/generation.py (GenerationService.generate(),
  generate_stream())
- /Users/David/DBMA/ui/pages/chat.py, /Users/David/DBMA/ui/pages/
  research.py (기존 페이지의 세션 상태 패턴)
- /Users/David/DBMA/ui/state/query_processor.py (공유 상태 헬퍼)
- /Users/David/DBMA/docs/architecture/ADR-001-Retrieval-Engine-
  Authority.md (One Retrieval Engine 원칙)

작업: /Users/David/DBMA/docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-Design-
Review.md 파일을 새로 작성하라(기존 파일 수정 금지, 새 파일만).

문서에 다음 5개 질문 각각에 "권장안 + 이유 + 트레이드오프" 형식으로
답하라:

1. 검색 전략: retrieve()를 여러 번 호출 vs k_output/candidate_k 확장 —
   어느 쪽이 One Retrieval Engine 원칙을 덜 깨는가?
2. 개요→확장 2단계 워크플로의 세션 상태를 어떻게 모델링할 것인가
   (신규 페이지 ui/pages/sermon_draft.py 가정)?
3. 코퍼스에 섞인 사용자 본인 과거 설교문(.rtf)을 "문체 참고 예시"로
   분리하려면 TSU 데이터 모델/file_scope에 어떤 최소 변경이 필요한가
   (설계만, Phase 1에서는 구현 안 함)?
4. GenerationService를 그대로 재사용 가능한가, 별도 메서드가 필요한가?
5. 이 워크플로가 기존 아키텍처의 어떤 전제를 깨뜨릴 위험이 있는가?

제약:
- .py 파일 생성/수정 절대 금지. 마크다운 문서 1개만 작성.
- 완전한 함수 구현체 금지. 인터페이스 시그니처/의사코드/텍스트
  다이어그램까지만.
- 불확실한 부분은 지어내지 말고 문서 마지막 "열린 질문" 섹션에
  3~5개로 남겨라.

작업 완료 후 작성한 파일의 전체 내용을 보여줘.
```

## 6. 절차

1. 위 §5 프롬프트를 그대로 C1(Cline 창, `dbma-planner-r1-q6:70b`)에
   붙여넣는다.
2. C1이 새 `.md` 파일을 작성하면, **CUE에게 파일 내용을 그대로 전달**
   한다 — C1이 혹시라도 `.py` 파일을 건드렸다면 즉시 중단하고 CUE에게
   알린다.
3. CUE가 §7 검증을 거친 뒤 사용자에게 요약 보고한다.

## 7. CUE 사후 검증 절차

- [ ] `git status`/`git diff`로 `.py` 파일 변경이 **전혀 없는지** 확인
      (하나라도 있으면 즉시 반려, 되돌리기)
- [ ] 새로 생성된 파일이 `docs/agents/c1/DBMA-SERMON-DRAFT-Phase1-
      Design-Review.md` 하나뿐인지 확인
- [ ] §3의 5개 질문에 전부 "권장안+이유+트레이드오프" 형식으로 답했는지
- [ ] 완전한 함수 구현체(실행 가능한 완성 코드)가 섞여있지 않은지
      (의사코드/시그니처 수준은 허용)
- [ ] "열린 질문" 섹션이 있는지
- 위 항목 모두 통과해야 사용자에게 결과를 설계안으로 제시한다. 하나라도
  실패하면 CUE가 무엇이 왜 반려됐는지 기록하고, 필요한 부분만 CUE가
  직접 보완한다.

## 8. 완료 후 CUE가 할 일

1. §7 검증 통과 시 사용자에게 설계 요약 + 전체 문서 링크 보고.
2. 사용자 승인 후에만 Phase 1 실제 구현(코드)에 착수 — 이 작업 자체는
   구현을 포함하지 않는다.
3. 결과를 `feedback_c1_routing_criteria.md`에 새 카테고리(아키텍처
   설계 검토, dbma-planner-r1-q6:70b)로 기록한다.
