# C1 Task Order 071 — ADR-035 초안 독립 리뷰

- 발주자: CUE
- 일자: 2026-09-23
- 유형: **C1 독립 리뷰(Review) — 구현 아님, PLAN MODE로만 진행**
- 근거: `docs/architecture/ADR-035-NAE-Pastoral-Library-Automation.md`(신규,
  PR #76, Status: Proposed), `docs/NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md` §6

---

## 배경

C1이 작성한 `NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md` §6에서 제안한
자동화 6건을 CUE가 코드 실측으로 대조 검증해 ADR-035 초안을 작성했다
(PR #76, 아직 미병합·미구현). CLAUDE.md CUE Operating Policy상 새 ADR은
"구현 완료 + 회귀 테스트 통과 + **C1 독립 리뷰** + 사용자 승인" 4개를
모두 충족해야 Approved로 승격된다 — 이 Task Order는 그중 C1 리뷰
단계를 요청한다.

## 요청 사항 (RQ)

1. **RQ1 — 재분류 검증**: ADR-035 §2 표에서 "이미 구현됨"으로 분류한
   2건(휴지통 30일 자동 삭제, 세션 자동 저장/복원)이 실제로 코드에
   존재하는지 직접 파일을 열어 확인하라(인용된 경로:
   `core/raw_hygiene.py::maybe_purge_expired_trash`,
   `ui/pages/library.py:856`, `core/config.py:326`,
   `core/research_workspace.py`, `research.py:169`). CUE의 인용이
   틀렸다면 구체적으로 지적하라.
2. **RQ2 — 기각 근거 검증**: §2/§3.2에서 "중복/오리판 주간 자동 정리"를
   기각한 근거로 인용한 `ui/pages/library.py:685-707`의 2026-09-07 사고
   기록(오리판 50건 중 37건이 실제로는 사용자가 원한 파일)이 실제
   주석 내용과 일치하는지 확인하라.
3. **RQ3 — 위험도 판단에 대한 의견**: §3.1에서 "RAW 폴더 워처"와
   "인덱스 자동 갱신"을 additive(생성/갱신만)라는 이유로 채택 가능
   위험군으로 분류했다. 이 판단에 동의하는지, 동의하지 않는다면
   구체적으로 어떤 실패 시나리오를 놓쳤는지 밝혀라.
4. **RQ4 — 누락 확인**: ADR-035 §1 "절대 변경 금지" 목록(Retrieval
   Engine/TSU Pipeline/Embedding Engine/RAW 원본/Production Registry)과
   ADR-022/023과의 도메인 분리 서술에 오류나 누락이 있는지 확인하라.

## 하지 말아야 할 것

- ADR-035를 대신 구현하지 말 것(§3.1 코드 작성 금지 — 이 Task Order는
  리뷰만 요청한다).
- ACT MODE로 파일을 수정하지 말 것 — **PLAN MODE로만** 조사·의견 제출.
- RQ 범위를 벗어난 새로운 자동화 항목을 제안하지 말 것(별도 Task Order로
  요청할 것).

## 제출 형식

RQ1~RQ4 각각에 대해 "동의/불일치 + 근거(파일:줄번호)"로 답하라. 새 파일
`docs/agents/c1/C1-TASK-ORDER-071-COMPLETE.md`에 결과를 작성해 제출.
