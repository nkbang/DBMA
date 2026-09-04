// deno-fmt-ignore-file
# C1 Task Order 011 — DBMA-SEQ(Sermon Evaluation & Quality) 착수 안내

발급: CUE (2026-07-24)
대상: C1 (Cline 작업창 #1) — **반드시 새 Task/새 세션으로 시작**
성격: **신규 프로젝트 소개 + Phase 1 최소 착수.** 큰 계획을 한 번에
구현하지 않는다 — 이 Task Order는 골든셋 라벨링 담당·일정을 먼저
HQ에게 확인받는 것까지만 다룬다.

---

## 1. 배경

`docs/architecture/ADR-012-DBMA-SEQ-Sermon-Evaluation-Quality.md`를
먼저 읽어라. 요약:

- `DBMA-SIL`(ADR-009)은 설교 개요/확장 **생성** 기능
- `DBMA-SEQ`(ADR-012, 신규)는 생성된 결과물의 **품질 검증** 계층 —
  `DBMA-REQ`(ADR-010, RAG groundedness 평가)와 같은 명명·설계
  패턴을 설교 생성물에 적용한 것
- `core/evaluation/rag_judge.py`가 이미 이 패턴의 실제 구현
  예시다 — 새로 설계하지 말고 이 파일 구조를 그대로 참고해서
  변형하라.

## 2. 이번 Task Order의 범위 — Phase 1 준비만

ADR-012의 Next Steps를 그대로 따른다:

1. **지금 하지 말 것**: `sermon_judge.py` 실제 구현, few-shot 예시
   뱅크 큐레이션, eval harness 골든셋 작성 — 전부 아직 착수 금지.
2. **지금 할 것**: ADR-012와 ADR-010(특히 §Decision-미확정 §1 골든셋
   라벨링 절차)을 읽고, `DBMA-SEQ` Phase 1을 위한 골든셋(설교 개요
   실제 사례 5~10개, "이 대지가 검색 자료에 근거했는가"를 사람이
   0~5점으로 채점)을 만들려면:
   - 실제 설교 개요 생성을 몇 건 실행해서 사례를 뽑을 준비(코드
     실행 계획만 — 실제 채점은 사용자 몫)
   - `core/evaluation/rag_judge.py`와 `core/generation.py`의
     `SermonOutline`/개요 생성 함수 시그니처를 읽고, 어떤 필드
     (검색된 자료 리스트, 생성된 대지 텍스트)를 judge에 넘겨야
     하는지 정리한 짧은 설계 메모 작성.
3. 설계 메모를 문서(`docs/agents/c1/DBMA-SEQ-Phase1-Design-Note.md`
   같은 이름)로 남기고, **코드 구현 전에 CUE 검토를 받는다.**

## 3. 원칙 재확인

- 이번에도 "이미 존재합니다"라고 주장하기 전에 실제 파일을 열어
  확인하라(Diagnosis rule 적용 대상).
- 큰 스코프(파인튜닝, LDA, KoBERT 등)는 이 프로젝트와 무관 —
  sermon_corpus 쪽 별도 논의였고 DBMA-SEQ와 섞지 마라.
- 새 세션으로 시작하는 이유: Session-scope rule에 따라 이전 대화
  맥락을 "기억하는 척" 하지 않기 위함 — 이 Task Order 파일과 ADR
  문서가 유일한 근거다.
