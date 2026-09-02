# CUE → C1 EXEC ORDER — ADR-030 v2.1 §12 M-5 (문서 한정 status 갱신)

> **baseline**: `dev/dbma-engine` @ `5b0a867` (M-4 GREEN/CLOSED).
> **권위**: 본 명령서 §2 (교체 문구 CUE 확정). RATIFIED 설계 = `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` (v2.1).
> **대상**: `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` — **1파일뿐.**
> **운영**: single EXEC. **C1 commit 금지.**
> **선행**: M-1/M-2 read-only 종결 감사 = CUE GREEN (2026-08-28). M-5 문구 = HQ APPROVED.
> **작성**: CUE · 2026-08-28

---

## 0. Workspace Verification Gate (`.clinerules/dbma-engineering.md` §3.1)

```bash
pwd
git rev-parse --show-toplevel        # 기대: /Users/David/DBMA  (.claude/worktrees/… 이면 STOP)
git rev-parse --abbrev-ref HEAD      # 기대: dev/dbma-engine
git rev-parse --short HEAD           # 기대: 5b0a867
git diff --stat -- docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md   # 기대: 변경 없음
```

하나라도 불일치 → 편집 금지, 즉시 중단·보고.
무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`, 다수 untracked `docs/agents/cue/*.md`) — stage·revert·수정 금지.

---

## 1. MANDATE

`docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` 에 **정확히 3개 문자열 치환**만 수행한다.
설계·본문 재해석·다른 파일 수정 금지. 아래 OLD 블록을 파일에서 **정확히** 찾아 NEW 블록으로 교체한다.
OLD 가 정확히 일치하지 않으면 임의 조정하지 말고 STOP·보고.

허용 수정: 이 1파일. 그 외 전부 금지 (§3).

---

## 2. 치환 (verbatim)

### 치환 1 — §1 Status 행

OLD:
```
| **Status** | **ACCEPTED (2026-08-27, v2.1 consolidated)** |
```
NEW:
```
| **Status** | **IMPLEMENTED / §12 MUST COMPLETE (2026-08-28)** — 채택: ACCEPTED 2026-08-27 (v2.1 consolidated). §12 MUST M-1~M-5 전량 완료, 각 단계 CUE 독립검증 GREEN (§12 표 · Appendix C) |
```

### 치환 2 — §12 MUST HAVE 표 (`종결` 열 추가)

OLD:
```
| # | 항목 | 산출물 | mutation |
|---|---|---|---|
| M-1 | M2 = Source Registry SSOT, M3 = Acquisition Backlog Tracker, M1 = `derived` mirror — 각 파일 헤더 주석 + 1페이지 "NAE Manifest & Authority SSOT" 문서 | 문서 + 주석 | 코드 0 |
| M-2 | M2 schema에 `content_genre[]` / `theological_category[]` / `tradition` / `authority_class` / `raw_path` / `checksum_target` 추가 (`required: false`), 14 레코드 backfill | schema + M2 YAML | manifest만 |
| M-3 | `NAE/governance/corpus_admissions.jsonl` 신설 + Dagg / Hiscox / Smith back-fill 항목(기존 증거 인용) + admission flow 문서화 | 신규 governance 파일 (append-only) | governance 기록만 |
| M-4 | read-only reconciliation 명령 (`scripts/nae_corpus_reconcile.py`) — M2 ↔ `incremental_state.json` ↔ `tsu.json::review_status` ↔ Qdrant count drift 출력, `--apply` 없음 | 신규 script (read-only) | 0 |
| M-5 | ADR-030 status 갱신 (본 문서 = 완료) | ADR 상태 변경 | — |
```
NEW:
```
| # | 항목 | 산출물 | mutation | 종결 (2026-08-28) |
|---|---|---|---|---|
| M-1 | M2 = Source Registry SSOT, M3 = Acquisition Backlog Tracker, M1 = `derived` mirror — 각 파일 헤더 주석 + 1페이지 "NAE Manifest & Authority SSOT" 문서 | 문서 + 주석 | 코드 0 | ✅ `470a1b5` (헤더 주석) + `NAE-Manifest-Authority-SSOT.md` (`fcaa380`~`0931e0c`) · CUE 검증 |
| M-2 | M2 schema에 `content_genre[]` / `theological_category[]` / `tradition` / `authority_class` / `raw_path` / `checksum_target` 추가 (`required: false`), 14 레코드 backfill | schema + M2 YAML | manifest만 | ✅ `5f4e300` (A-2a) → `1fa6fce` (A-2b-1) → `0931e0c` (A-2b-2) · CUE 독립검증 ×3 · 분류 권위 `CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` RATIFIED v1.1 |
| M-3 | `NAE/governance/corpus_admissions.jsonl` 신설 + Dagg / Hiscox / Smith back-fill 항목(기존 증거 인용) + admission flow 문서화 | 신규 governance 파일 (append-only) | governance 기록만 | ✅ `ad1464d` · HQ CLOSED |
| M-4 | read-only reconciliation 명령 (`scripts/nae_corpus_reconcile.py`) — M2 ↔ `incremental_state.json` ↔ `tsu.json::review_status` ↔ Qdrant count drift 출력, `--apply` 없음 | 신규 script (read-only) | 0 | ✅ `5b0a867` · HQ GREEN/CLOSED (F-1/F-2/F-3 correction 포함) |
| M-5 | ADR-030 status 갱신 (본 문서 = 완료) | ADR 상태 변경 | — | ✅ 본 커밋 · CUE |
```

### 치환 3 — Appendix B 말미 + STATUS 푸터 (Appendix C 삽입 + STATUS 재작성)

OLD:
```
- [x] ADR-001/013/019/020/021/024/027/028/029 충돌 없음 (§4, §5, §6.3, §8.5, §10, §12 N-1)

---

**STATUS: ACCEPTED (2026-08-27, v2.1 consolidated). Supersedes ADR-030 v1. 채택 시점 mutation 0 —
구현 항목은 §12 MUST. Production Contact NO. Migration NO.**
```
NEW:
```
- [x] ADR-001/013/019/020/021/024/027/028/029 충돌 없음 (§4, §5, §6.3, §8.5, §10, §12 N-1)

---

## Appendix C — §12 MUST 종결 기록 (2026-08-28)

ADR-030 v2.1 §12 MUST 5개 항목 전량 완료. 각 항목 CUE 독립검증 → 단일 커밋 landing. Production mutation 0.

| 항목 | 종결 커밋 | 검증 | 핵심 산출물 |
|---|---|---|---|
| M-1 | `470a1b5` + `fcaa380`~`0931e0c` (SSOT 문서) | CUE | M1/M2/M3 역할 주석 + `docs/architecture/NAE-Manifest-Authority-SSOT.md` |
| M-2 | `5f4e300` (A-2a) → `1fa6fce` (A-2b-1) → `0931e0c` (A-2b-2) | CUE 독립검증 ×3 | M2 additive 6필드 (`required: false`): authority_class·raw_path·checksum_target·content_genre 14/14, theological_category 5/14, tradition 10/14 (RATIFIED v1.1). validator 16/0, governance test 29 passed |
| M-3 | `ad1464d` | HQ CLOSED | `NAE/governance/corpus_admissions.jsonl` (append-only) + Dagg/Hiscox/Smith 소급 + flow 문서 |
| M-4 | `5b0a867` | HQ GREEN/CLOSED | `scripts/nae_corpus_reconcile.py` (read-only, `--apply` 없음). test 20 passed · 인접 regression 49 passed · 실데이터 smoke "No drift detected" exit 0. F-1/F-2/F-3 bounded correction 포함 |
| M-5 | 본 커밋 | CUE | 본 문서 status = IMPLEMENTED / §12 MUST COMPLETE |

- 분류 권위: `docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` (RATIFIED v1.1, HQ 2026-08-28).
- M-4 설계 권위: `docs/agents/cue/CUE-ADR-030-M4-RECONCILE.md` (RATIFIED v1.1).
- M-1/M-2 종결 감사: CUE read-only audit 2026-08-28 = GREEN.
- SHOULD (S-1~S-9) / NOT-YET (N-1~N-10)는 자동 착수 안 함 — 별도 HQ 우선순위 결정 대상.

---

**STATUS: IMPLEMENTED / §12 MUST COMPLETE (2026-08-28). 채택 ACCEPTED 2026-08-27 (v2.1 consolidated),
supersedes ADR-030 v1. §12 MUST M-1~M-5 전량 완료 — 각 단계 CUE 독립검증 GREEN, production mutation 0
(TSU 3,319 / nae_tsu_v1 3,319 / nae_ref_v1 34,948 / Qdrant / incremental_state / config 무변경).
SHOULD (S-1~S-9) / NOT-YET (N-1~N-10)는 별도 HQ 우선순위 대상. Production Contact NO. Migration NO.**
```

---

## 3. 금지

- `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` 외 어떤 파일도 수정 금지.
- 코드·데이터·YAML·JSONL·state·Qdrant·manifest 무접촉.
- §12 SHOULD/NOT-YET 표, §1~§11 본문, Change Log, Appendix A/B 내용 변경 금지.
  (치환 2 = §12 MUST 표만. 치환 3 = Appendix B 직후 Appendix C 삽입 + STATUS 푸터 재작성만.)
- `git add` / `git commit` / `git stash` 금지.
- 새 섹션·문구 창작 금지 — §2 NEW 블록 그대로만.
- OLD 정규화·공백 조정·줄바꿈 변경 금지 (STATUS 푸터는 2줄로 줄바꿈된 상태 그대로 매치).

---

## 4. VALIDATION GATE

```bash
git diff --stat
# 기대: docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md 1파일, 그 외 0

git status --short
# 기대: ' M docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md' + 기존 무관 항목만

grep -n "IMPLEMENTED / §12 MUST COMPLETE" docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
# 기대: 2건 (§1 Status 행 + STATUS 푸터)

grep -n "Appendix C — §12 MUST 종결 기록" docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
# 기대: 1건

grep -c "^| M-[1-5] " docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
# 기대: §12 MUST 표 5행 유지 (M-1~M-5)

grep -n "ACCEPTED (2026-08-27, v2.1 consolidated)\*\* |$" docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md
# 기대: 0건 (§1 Status 행의 옛 문구 완전 제거 확인)
```

수동 확인:
- markdown 표 렌더 정상 — §12 MUST 표 5열, Appendix C 표 4열.
- Appendix C 가 Appendix B 다음 · STATUS 푸터 앞에 위치.
- Change Log 표(2026-08-27 행들)의 "ACCEPTED" 문구는 **변경 없음** (치환 대상 아님).

---

## 5. MUTATION / SCOPE GATE

수정 전후 SHA-256 동일 (무변경 확인):
```
NAE/pipeline/registration/state/source_manifest.yaml
NAE/governance/corpus_admissions.jsonl
NAE/pipeline/ingest/state/incremental_state.json
scripts/nae_corpus_reconcile.py
scripts/m2_source_registry_validator.py
```
허용 수정 파일: `docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md` **1개뿐.**
반드시 `MUTATION 0 OK` (문서 외 전부).

---

## 6. HARD STOP

임의 판단하지 말고 **즉시 CUE 보고·STOP**:
- OLD 블록이 파일과 정확히 일치하지 않음
- §12 표 행 수가 5가 아님 / 예상 밖 열 수
- 치환 3 OLD 가 2건 이상 매치 (STATUS 문자열 중복)
- 문서 외 파일에 diff 발생
- 3개 치환 외 수정이 필요해 보임
- 2회 이상 실패
- RATIFIED 해석이 추가로 필요함

---

## 7. COMMIT 금지

C1 은 `git add` / `git commit` 을 실행하지 않는다.
치환 → §4 validation → §5 mutation gate → report 작성 → STOP.

최종 보고: `output/ADR-030-Phase1A-M5-EXEC-REPORT.md`
1. 치환 1 / 2 / 3 각 적용 결과 (before/after 인용)
2. `git diff` 전문 (1파일)
3. `git status --short`
4. §4 VALIDATION GATE 명령 raw 출력
5. §5 MUTATION 0 결과 (sha256 표: pre / post)
6. 수정 범위 (허용 1파일만)
7. deviation 유무

C1 self-PASS 는 승인으로 간주하지 않는다. 완료 후 CUE 독립 재검증으로 반환한다.

---

## 8. SUCCESS CONDITION

```
치환 3건 정확 적용
문서 외 mutation 0
git diff = ADR-030 문서 1파일
commit 0
```
이후: C1 → CUE 독립 재검증 → GREEN → CUE 단일 commit (`M-5: ADR-030 v2.1 §12 MUST COMPLETE — status update`) → HQ 최종 판정.

END OF M-5 EXEC ORDER
