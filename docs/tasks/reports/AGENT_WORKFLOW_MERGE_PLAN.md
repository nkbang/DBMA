# AGENT_WORKFLOW Merge Plan

작성일: 2026-07-31

## 현재 두 파일 역할

| 파일 | 역할 | 커밋 상태 |
|---|---|---|
| `docs/AGENT_WORKFLOW.md` | STEP1 초기 지시서(Phase 5) 산출물. HQ/CUE/C1 역할만 정의한 축약본 | 커밋됨 (`f5bd82a`) |
| `docs/tasks/AGENT_WORKFLOW.md` | Task 관리 구조(`docs/tasks/`) 도입 시 작성된 확장본. 역할 정의 + 작업 승인 절차 + 변경 관리 규칙 + 보고서 작성 규칙 포함 | 미커밋 (이번 STEP1 commit 대상) |

두 파일은 겹치는 "역할 정의" 섹션을 공유하지만, `docs/tasks/AGENT_WORKFLOW.md`가 상위 호환(superset)이다. 내용 충돌은 없음 — 후자가 전자를 포함하며 확장한 관계.

## 권장 구조

- `docs/tasks/AGENT_WORKFLOW.md`를 정본(source of truth)으로 확정.
- 루트 `docs/AGENT_WORKFLOW.md`는 정본으로의 리다이렉트 스텁으로 축소(1~2줄, "정본 위치는 docs/tasks/AGENT_WORKFLOW.md 참고")하거나, HQ가 원하면 완전 삭제.
- 근거: `docs/tasks/`가 HQ↔CUE 작업 전달 체계의 실제 운영 디렉토리이므로, 워크플로 문서도 그 안에 두는 것이 구조적으로 일관됨.

## 이동/삭제 예상 절차 (실행은 HQ 승인 후)

1. `docs/tasks/AGENT_WORKFLOW.md` 내용 최종 확인 (현재 버전으로 충분함)
2. 루트 `docs/AGENT_WORKFLOW.md`를 스텁으로 교체 (또는 `git rm`)
3. 루트 파일을 참조하는 곳이 있는지 grep 확인 (`grep -rn "docs/AGENT_WORKFLOW.md"`)
4. 참조 있으면 경로 업데이트, 없으면 그대로 진행
5. 별도 커밋으로 반영 (workspace 초기화 커밋과 분리 권장)

## 영향 범위

- 현재 두 파일을 참조하는 코드/문서 없음 (신규 문서, 아직 다른 곳에서 링크되지 않음 — 이 세션 대화 내 언급만 존재)
- 리스크 낮음. 실제 삭제/이동 시에도 core 코드나 UI 동작에 영향 없음
- 단, 이 계획의 실행(삭제/스텁화)은 본 문서 작성만으로 완료되지 않으며, 별도 HQ 승인 및 별도 작업 지시 필요
