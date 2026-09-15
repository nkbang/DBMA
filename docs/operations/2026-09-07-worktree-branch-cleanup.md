# Worktree / 브랜치 정리 기록 — 2026-09-07

## 목표

방치된 고아 git worktree와 이미 병합된 로컬 브랜치를 정리해 저장소 상태를
읽기 쉽게 만든다. 진행 중인 작업은 손실 없이 보존한다.

## 실행 환경

- 실행 위치: worktree `session-not-ending-778b6e` (브랜치 `claude/session-not-ending-778b6e`)
- 원격(`origin`)은 전 과정에서 **변경하지 않음** (로컬 ref만 조작)

---

## 1. 고아 worktree 제거 (6개)

활성 세션이 붙어 있지 않은 worktree. 작업 트리에 미커밋 변경이 있던 것은
해당 브랜치에 WIP 스냅샷 커밋을 만든 뒤 worktree만 제거했다.

| worktree | 처리 | 비고 |
|---|---|---|
| adr-030-nae-corpus-authority-400037 | 제거 | clean, 이미 병합됨 |
| adr-030-post-forensic-reassessment-777899 | 제거 | clean, 미병합 커밋 `72b8357` 존재 |
| ai-question-search-scope-debug-48b43e | WIP 커밋 후 제거 | `.claude/launch.json` 변경 |
| beta-test-start-af0766 | WIP 커밋 후 제거 | STATE/TODO/ADR-009 doc + shadow script |
| nae-dbma-design-styling-491b53 | WIP 커밋 후 제거 | `ui/app.py` 변경 |
| personal-data-reset-debug-609121 | WIP 커밋 후 제거 | `ui/pages/dashboard.py` + `core/reset.py` |

**제외:** `smith-gate-cross-validation-4b511c` 는 활성 세션이 붙어 있어 유지.

정리 후 남은 worktree (4개, 전부 활성):
`~/DBMA` (main), `adr-030-nae-corpus-authority-212938`,
`json-decode-orphan-cleanup-abf035`, `session-not-ending-778b6e`.

---

## 2. 병합 완료 로컬 브랜치 삭제 (33개)

`origin/dev/dbma-engine` **및** `origin/main` 양쪽에 완전 병합(ahead 0)되고
어떤 worktree에도 체크아웃되지 않은 `claude/*` 로컬 브랜치. 전부
`git branch -d` (safe delete) 로 삭제 — 32개는 tip `a526e8d`,
`claude/nice-engelbart-aef967` 은 `af62b2a`.

<details>
<summary>삭제된 33개 브랜치</summary>

```
claude/adr-030-nae-corpus-authority-212938
claude/adr-030-nae-corpus-authority-400037
claude/adr-030-phase-1a-a2a-03c944
claude/adr-030-phase1-verification-dbfe55
claude/adr-030-priority-assessment-d33bf3
claude/ai-question-search-scope-debug-48b43e
claude/baptist-bible-dictionary-embed-0aac56
claude/baptist-materials-download-status-513932
claude/ch1-complex-task-feasibility-3d01b1
claude/ch1-usage-model-d0abd9
claude/citation-button-key-duplicate-ec553f
claude/confident-thompson-65c785
claude/context-window-clear-602b37
claude/cue-c1-loop-live-verification-5b03f4
claude/cue-c1-overnight-loop-b1-363b10
claude/cue-independent-verification-phase1-dc1641
claude/dagg-index-gate-discrepancy-54e189
claude/field-appropriateness-check-c1cb7e
claude/funny-diffie-87d831
claude/human-runtime-debugging-2ae823
claude/m4-final-state-validation-994478
claude/nae-baptist-forensic-verification-b01c90
claude/nae-dbma-llm-model-46fc78
claude/nae-landing-page-link-35cc38
claude/nae-phase1-candidate-discovery-cb6f51
claude/nae-theology-resume-point-35944a
claude/nice-engelbart-aef967
claude/reissue-work-order-e8eef0
claude/smith-gate-completion-check-2e214f
claude/smith-gate-cross-validation-4b511c
claude/sprint34-smith-phaseb-verify-a2d516
claude/verify-ch1-role-f0d8e2
claude/vscode-claude-integration-35a3cd
```
</details>

**origin 원격 브랜치:** 위 33개 중 `origin` 에 존재하는 것은 0개였다
(커밋은 이미 `origin/dev/dbma-engine`·`origin/main` 에 병합됨). 삭제할
원격 브랜치 없음. stale 추적 참조는 `git remote prune origin` 으로 정리.

---

## 3. 잔여 worktree 브랜치 삭제 (5개)

1번에서 worktree만 제거하고 남겨둔 브랜치. 미병합 작업(WIP 스냅샷 및
`72b8357`)을 담고 있어 `git branch -D` 전에 복구 앵커로 `attic/` 태그를
만들었다가, 이후 사용자 지시로 태그도 삭제했다.

| 삭제된 브랜치 | tip SHA | 담긴 내용 |
|---|---|---|
| claude/adr-030-post-forensic-reassessment-777899 | `72b8357` | ADR-030 NAE Sermon Corpus Governance v2.1 문서 (origin 어디에도 없음) |
| claude/library-auto-organize-check-430c5a | `87a82dd` | WIP(`.claude/launch.json`). 선행 커밋 `5a0d432` 는 `origin/claude/library-auto-organize-check-430c5a` 에 존재 |
| claude/beta-test-start-af0766 | `5ac06e9` | WIP — STATE/TODO/ADR-009 doc + `scripts/shadow_subdefect_b_frequency.py` |
| claude/nae-dbma-design-styling-491b53 | `e230f11` | WIP — `ui/app.py` |
| claude/personal-data-reset-debug-609121 | `0ffcbdb` | WIP — `ui/pages/dashboard.py` + `core/reset.py` |

`attic/*` 복구 태그 5개는 생성 후 **삭제됨**. 위 SHA 는 현재 어떤 ref 로도
참조되지 않으며, `git gc` 실행 전까지만 `git reflog` / `git fsck --lost-found`
로 복구 가능하다. 되살리려면: `git branch <name> <SHA>`.

---

## 최종 상태

- 로컬 `claude/*` 브랜치: 정리 전 다수 → **5개** (전부 활성 worktree
  또는 진행 중 작업):
  `adr-030-s9-s71-doc-correction`, `fuller-c1-token-execution-ad889f`,
  `json-decode-orphan-cleanup-abf035`, `project-data-reset-c10afd`,
  `session-not-ending-778b6e`
- `attic/*` 태그: 0
- git worktree: 4개 (전부 활성)
- `origin` 원격: 변경 없음

## 후속 조치

- 복구가 필요한 커밋이 있으면 `git gc` 전에 위 SHA 로 브랜치 재생성.
- 활성 세션이 종료되면 남은 worktree 4개 중 해당 항목도 동일 절차로 정리 가능.
