# CUE → C1 BOUNDED CORRECTION ORDER — ADR-030 v2.1 §12 M-4 (F-1 / F-2 / F-3)

> **본문(§0 제외) = HQ 작성.** CUE가 하달. baseline `ad1464d`. 현재 상태: M-4 NOT GREEN.
> 권위 문서: `docs/agents/cue/CUE-ADR-030-M4-RECONCILE.md` — RATIFIED v1.1.
> 대상: `scripts/nae_corpus_reconcile.py` / `tests/test_nae_corpus_reconcile.py`.
> 운영: bounded correction loop. **C1 commit 금지.**

---

## 0. 착수 전 — Workspace Verification Gate (`.clinerules/dbma-engineering.md` §3.1)

```bash
pwd
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
git diff --stat -- scripts/nae_corpus_reconcile.py tests/test_nae_corpus_reconcile.py
```
**기대**: `--show-toplevel` = `/Users/David/DBMA` (`.claude/worktrees/...` 이면 잘못됨) · `dev/dbma-engine` ·
`ad1464d` · 두 파일에 이미 M-4 EXEC 변경분이 존재. 하나라도 불일치 → 편집 금지, 즉시 중단·보고.
무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`) — stage·revert·수정 금지.

---

## 0. MANDATE

CUE 독립검증에서 발견된 **F-1, F-2, F-3 만** 정정한다.
이번 작업은 M-4 설계를 다시 판단하거나 확장하는 작업이 **아니다**.
허용된 수정은 정확히 다음 3건뿐이다.

1. **F-1** Qdrant point integer ID → payload `tsu_id` 비교
2. **F-2** linkage metadata 부재(pre-migration) → `[INFO]`, CORE DRIFT 제외
3. **F-3** JSON `"ok"` 문자열 → JSON boolean `true/false`, skipped 별도 상태

그 외 설계·기능·파일은 변경하지 않는다.

---

## 1. F-1 — INV-2 Qdrant ID 비교 정정

**문제**
현재 Qdrant point 의 numeric `id` (`6, 7, 8, ...`) 를 `TSU-0000006, TSU-0000007, ...` 와 직접 비교 →
false drift 발생.

**정정**
Qdrant `scroll` 시 payload 의 `tsu_id` 를 읽어 TSU authority ID 로 사용한다.

```text
with_payload=["tsu_id"]

qdrant_ids = {
    point.payload["tsu_id"]
    for point in points
    if point.payload contains valid tsu_id
}
```
를 `verified_ids` 와 비교한다.

**금지**
- Qdrant numeric point ID 를 TSU ID 로 임의 변환하지 않는다.
- `"TSU-" + str(point.id)` 같은 정규화 금지.
- payload 에 없는 `tsu_id` 를 추론하지 않는다.
- INV-2 외 invariant 변경 금지.

payload 에 `tsu_id` 가 없거나 malformed 이면 임의 보정하지 말고 명확한 error/drift 로 surface 한다.

---

## 2. F-2 — INV-4b severity 정정

**HQ 결정: Option (b) 승인.**
M2-linkage 필드가 없는 pre-migration TSU record 는 `[INFO]` 로 처리한다. **이는 CORE DRIFT 가 아니다.**

**판정**
다음 4개 linkage 후보가 **모두 없는** 경우 — `source_id` / `work_id` / `source_file` / `document_id` —
pre-migration record 임을 표시한다.
```text
[INFO] Fuller Vol01: TSU record has no machine-verifiable M2 linkage
       (pre-migration metadata)
```
**중요**: 이 경우 `core_drift += ...` 하지 않는다. 이것만으로 `exit 1` 이 되어서는 안 된다.

**그러나 다음은 여전히 CORE DRIFT** — linkage 필드가 **존재하지만** 그 값이 M2 에 없는 경우:
```text
[CORE DRIFT]
INV-4: linkage '<value>' not found in M2
```
즉:
```text
필드 없음        → INFO
필드 있음 + M2 불일치  → CORE DRIFT
```

**금지**
- `book == M2.title` 등 title-based fallback linkage 를 추가하지 않는다.
- directory name 을 authority 로 사용하지 않는다.
- 새 invariant 를 추가하지 않는다.

---

## 3. F-3 — `--json` schema 정정

현재 `"ok": "true"` / `"ok": "false"` 처럼 문자열 출력 → **반드시 JSON boolean** (`"ok": true` / `"ok": false`).

**skipped 처리**: `skipped` 를 `ok` 에 문자열로 넣지 않는다. 예:
```json
{ "id": "INV-2", "ok": true, "skipped": true, "detail": "Qdrant unreachable; INV-2 not checked" }
```
또는 기존 RATIFIED schema 를 유지하면서 동등하게 machine-readable 한 별도 상태 필드를 사용한다.
**핵심: `ok` 는 항상 JSON boolean 이다.**

---

## 4. TEST REQUIREMENTS

기존 M-4 test 를 약화시키지 않는다. 최소한 다음을 추가/수정하여 검증한다.

**F-1** — Qdrant fixture: `point.id = 6`, `payload.tsu_id = "TSU-0000006"`, verified = `"TSU-0000006"` 일 때
INV-2 가 **PASS**. numeric point ID ≠ TSU ID 때문에 false drift 가 발생해서는 안 된다.

**F-2** — linkage 없는 pre-migration record fixture 추가. 기대: `CORE DRIFT 없음` / `INFO 존재` / `exit 0 가능`.
그리고 M2 에 없는 linkage 값이 **실제로 존재하는** fixture 에서는: `CORE DRIFT` / `exit 1`.

**F-3** — `--json` 결과를 `json.loads()` 로 읽고 `isinstance(inv["ok"], bool)` 성립 검증.
`"true"` / `"false"` / `"skipped"` 문자열을 `ok` 에 넣는 구현은 FAIL.

---

## 5. VALIDATION GATE

```bash
python -m pytest -q tests/test_nae_corpus_reconcile.py
python -m pytest -q tests/test_m2_source_registry_governance.py tests/test_corpus_admissions.py
```
그리고 실제 smoke:
```bash
python scripts/nae_corpus_reconcile.py
echo "exit=$?"
python scripts/nae_corpus_reconcile.py --json
echo "exit=$?"
```
실제 smoke 결과에 drift 가 나타나면 **데이터를 수정하지 말고 그대로 보고**한다.

---

## 6. MUTATION / SCOPE GATE

수정 전후 SHA-256 비교:
```text
NAE/pipeline/ingest/state/incremental_state.json
NAE/pipeline/registration/state/source_manifest.yaml
NAE/governance/corpus_admissions.jsonl
```
(필요 시 TSU fixture 대상도 확인.) 반드시 `MUTATION 0 OK`.
또한 `git diff --stat` / `git status --short` 로 확인. **허용 파일**:
```text
scripts/nae_corpus_reconcile.py
tests/test_nae_corpus_reconcile.py
```
외의 파일은 수정하지 않는다.

---

## 7. HARD STOP

다음 상황에서는 임의 판단하지 말고 **즉시 CUE 에 보고하고 STOP**:
- RATIFIED v1.1 해석이 추가로 필요함
- F-1/F-2/F-3 외 수정이 필요함
- 기존 test 와 설계가 충돌함
- 실제 production data drift 를 발견함
- Qdrant payload 구조가 예상과 다름
- 다른 production 파일 수정이 필요함
- 2회 이상 correction 실패
- 새로운 invariant 가 필요함

**데이터를 변경하여 테스트를 통과시키지 않는다.**

---

## 8. COMMIT 금지

C1 은 `git add` / `git commit` 을 실행하지 않는다.
수정 → 테스트 → validation → report 작성 후 STOP.

최종 보고: `output/ADR-030-Phase1A-M4-CORRECTION-REPORT.md`
1. F-1 수정 내용 및 test 결과
2. F-2 수정 내용 및 test 결과
3. F-3 수정 내용 및 test 결과
4. 전체 M-4 test raw 결과
5. 인접 regression raw 결과
6. smoke stdout + exit code raw
7. mutation 0 결과
8. git diff/status
9. 수정 범위
10. deviation 유무

C1 self-PASS 는 승인으로 간주하지 않는다. 완료 후 CUE 독립 재검증으로 반환한다.

---

## 9. SUCCESS CONDITION

```text
F-1 corrected
F-2 corrected
F-3 corrected
M-4 tests = PASS
adjacent regression = PASS
MUTATION = 0
scope = allowlist only
commit = 0
```
그 후: C1 → CUE independent verification → GREEN → CUE single commit.

END OF BOUNDED CORRECTION ORDER
