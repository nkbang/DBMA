// deno-fmt-ignore-file
# C1 Task Order 012 — DBMA-SEQ Phase 1: sermon_judge.py 구현

발급: CUE (2026-07-24)
대상: C1 (Cline 작업창 #1) — **반드시 새 Task/새 세션으로 시작**
성격: **구현 Task.** `docs/agents/c1/DBMA-SEQ-Phase1-Design-Note.md`
(C1 작성, CUE 승인 완료)를 그대로 코드로 옮긴다. 설계를 다시 바꾸지 않는다.

---

## 1. 배경

`docs/agents/c1/DBMA-SEQ-Phase1-Design-Note.md`를 먼저 읽어라.
CUE 검토 결과는 다음과 같다:

1. 프롬프트 설계(§3.2) 승인 — 그대로 구현.
2. text_type 분리 불필요 — outline/expansion을 위한 별도 프롬프트를
   만들지 말 것. 프롬프트 문구 안에 `{text_type}` 값만 끼워 넣는다
   (설계 메모 §3.2 그대로).
3. `_judge_common.py` 분리 **금지** — 아직 중복 코드가 실제로
   존재하지 않는 상태에서 미리 공통 모듈을 만드는 것은 추측성
   리팩터링이다(CLAUDE.md 금지 사항). `core/evaluation/rag_judge.py`
   파일은 **건드리지 않는다.**
4. 골든셋 라벨링 담당/일정은 아직 미정 — 이번 Task Order는 라벨링을
   요구하지 않는다.

## 2. 이번 Task Order의 범위

1. **새 파일**: `core/evaluation/sermon_judge.py`
   - 설계 메모 §3.1의 `judge_sermon_groundedness()` 시그니처 그대로
     구현
   - `_parse_judge_json()`, ollama 호출 패턴은 `rag_judge.py`에서
     복붙 후 이 파일 안에서 독립적으로 유지한다 (import로 공유하지
     않는다 — §1.3 참고)
   - 프롬프트는 설계 메모 §3.2 그대로, `_format_sermon_context()`는
     `core/generation.py`에 있는 기존 함수를 import해서 재사용
     (이건 이미 존재하는 포맷터라 복붙 대상 아님 — 새로 만들지 말 것)

2. **schemas 추가**: `core/evaluation/schemas.py`에 `RagEvalScore`
   옆에 `SermonQualityScore` dataclass 추가 (설계 메모 §3.3 그대로)

3. **테스트**: `tests/test_sermon_judge.py` 신규 작성
   - ollama 호출은 mock 처리
   - 정상 JSON 파싱, JSON 파싱 실패 시 score=0.0 fallback 두 케이스
     최소 확인 (rag_judge.py 기존 테스트 있으면 그 패턴 그대로 따라할 것)

4. **하지 말 것**
   - `rag_judge.py` 수정 금지
   - `_judge_common.py` 생성 금지
   - few-shot 예시, eval harness, 골든셋 라벨링 — 전부 Phase 2

## 3. 완료 후

- 변경 파일 목록과 테스트 실행 결과를 짧은 md로 남겨라
  (`docs/agents/c1/` 아래, 파일명은 자유)
- CUE 검토 요청

## 4. 원칙 재확인

- "이미 존재합니다"라고 주장하기 전에 실제 파일을 열어 확인
  (Diagnosis rule)
- 새 세션으로 시작 — 이 Task Order와 설계 메모가 유일한 근거
