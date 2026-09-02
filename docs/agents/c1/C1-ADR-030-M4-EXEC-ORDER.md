# C1 — ADR-030 v2.1 §12 M-4 EXEC ORDER (Corpus Reconciliation Tool)

> **작성**: CUE · **선행**: M-3 VERIFIED — commit `ad1464d` (`dev/dbma-engine`)
> **설계 권위**: `docs/agents/cue/CUE-ADR-030-M4-RECONCILE.md` — **RATIFIED v1.1** (HQ 비준 2026-08-28)
> **범위**: `scripts/nae_corpus_reconcile.py` 재작성 + `tests/test_nae_corpus_reconcile.py` 재작성 뿐
> **loop**: C1 구현 → CUE 독립검증 → (필요 시 CUE 정정 지시) → GREEN → CUE 단일 커밋. C1 은 커밋하지 않는다.

---

## 0. 착수 전 — Workspace Verification Gate (`.clinerules/dbma-engineering.md` §3.1)

```bash
pwd
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
test -f scripts/nae_corpus_reconcile.py && echo "skeleton EXISTS" || echo "skeleton MISSING"
```
**기대**: `--show-toplevel` = `/Users/David/DBMA` (`.claude/worktrees/...` 이면 잘못됨) · `dev/dbma-engine` ·
`ad1464d` · `skeleton EXISTS`. 하나라도 불일치 → 편집 금지, 즉시 중단·보고.

무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`) — stage·revert·수정 금지.

---

## 1. MANDATE

ADR-030 §12 M-4 만 수행한다. `CUE-ADR-030-M4-RECONCILE.md` **RATIFIED v1.1** 의 §4(도구)·§5(test)·§6(결정)
을 그대로 구현한다. 설계를 재판단·확장·변경하지 마라. 판단이 필요한 지점이 나오면 §8 에 따라 **중단·보고**.

read-only drift 리포트 도구다. `--apply` 없음. 어떤 파일·state·Qdrant 도 쓰지 않는다.

---

## 2. HARD STOP — 금지

- **쓰기 로직 금지**: `--apply` 플래그, 파일 write, state/Qdrant 변경 — 전부 금지. 모든 `open()` read 모드.
  Qdrant 는 GET / `count` / `scroll` 만.
- **production 코드 수정 금지**: `NAE/pipeline/index/indexer.py::index_all()`, `NAE/pipeline/**`,
  `review_gate.py` 등 — **읽기 import 만**. 한 줄도 고치지 마라.
- **데이터/state 변경 금지**: `incremental_state.json`, `tsu.json`, `source_manifest.yaml`(M2),
  `corpus_admissions.jsonl`, `registration_state.json`, Qdrant — 무접촉.
- **M1 (`NAE/authority/source_manifest.yaml`) · M3-manifest (`NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv`) 변경 금지.**
- **`config.yaml` 수정 금지** (6333 stale 이지만 이번 범위 밖 — Qdrant URL 은 §4 대로 NAE config import).
- **설계 확장 금지**: `NAE_QDRANT_URL` env override (보류), `nae_ref_v1` core 편입 (제외), 새 invariant, 새 CLI 모드.
- **`git add` / `git commit` 금지.**

**allowlist (수정 가능 — 2):**
`scripts/nae_corpus_reconcile.py` (재작성) · `tests/test_nae_corpus_reconcile.py` (재작성)

---

## 3. TASK 1 — `scripts/nae_corpus_reconcile.py` 재작성

RATIFIED §4 그대로. skeleton 결함 D-1~D-8 (§3) 을 전부 해소한다.

### 3.1 함수 (§4.1)
| 함수 | 반환 | 비고 |
|---|---|---|
| `load_incremental_indexed_ids(path=INCREMENTAL_STATE) -> set[str]` | `state == "INDEXED"` 인 tsu_id 집합 | dict key = tsu_id (`TSU-NNNNNNN`) |
| `load_review_status(tsu_dir=TSU_DIR) -> dict[str,str]` | `{tsu_id: review_status}` — non-`_` dir 합산 (pilot/`_*backup*` 제외) | tsu.json record 의 `id` (또는 `tsu_id`) 를 key 로 |
| `tsu_m2_linkage(record) -> str \| None` | record 에서 **`source_id` → `work_id` → `source_file` / `document_id`** 순 추출 | INV-4 authority. **directory name 사용 금지** |
| `build_m2_index(path=M2_PATH) -> dict` | M2 를 `source_id` / `work_id` / `edition_id` 로 역인덱스 | INV-4 대조 |
| `probe_qdrant(url, collection="nae_tsu_v1")` | `("reachable", <ids set 또는 count>)` \| `("unreachable", reason)` \| `("error", detail)` | `url` 기본값 = `from NAE.pipeline.index.config import QDRANT_URL`. connection refused / timeout / DNS = `unreachable`; 그 외(컬렉션 없음·auth 등) = `error`. **bare `except` 로 전부 unreachable 처리 금지 (D-4)** |
| `load_admissions(path=ADMISSIONS) -> list[dict]` | `NAE/governance/corpus_admissions.jsonl` 파싱 | GC용 |
| `reconcile(...) -> ReconcileResult` | INV-1~4 + GC-1~3 | 아래 |

경로 상수는 전부 함수 인자 기본값으로 노출 (test 격리용).

### 3.2 판정 (§4.2) — **ID-level set reconciliation** (count 는 pre-check 로만)

```
CORE (production ↔ production):
  INV-1  verified_ids  ==  indexed_ids
         verified_ids = {tsu_id : review_status == "verified"}
         불일치 시: verified_only = verified_ids - indexed_ids ,  indexed_only = indexed_ids - verified_ids  목록 출력
  INV-2  (Qdrant "reachable" 且 point id 열거 가능 시)  qdrant_ids == verified_ids
         id 열거가 비싸면 count 비교로 fallback + "INV-2: id-level not verified (count only)" 표기
         Qdrant "unreachable"  → INV-2 skip + "INV-2 not checked (Qdrant unreachable)" 표기 (drift 아님)
         Qdrant "error"        → CORE DRIFT ("Qdrant error: <detail>")
  INV-3  ( {tsu_id : review_status in (generated, rejected)} ∪ {review_status 가 verified/generated/rejected 아닌 tsu_id} )
         ∩ ( indexed_ids ∪ qdrant_ids )  ==  ∅
         교집합 있으면: 해당 tsu_id 목록 (= embedded 되면 안 되는데 된 것)
  INV-4  각 non-`_` TSU dir 에 대해: 그 dir 첫 record(또는 전 record)의 tsu_m2_linkage() 가
         build_m2_index() 에 존재해야 한다. 없으면 CORE DRIFT ("<dir>: linkage '<val>' not in M2").
  INV-4b linkage 필드 자체가 없으면 CORE DRIFT ("<dir>: TSU record has no M2-linkage field").

GOVERNANCE (production ↔ M-3 admission log) — CORE 와 분리 리포트:
  GC-1  corpus_admissions.jsonl 의 모든 source_id 가 M2 에 존재. 없으면 GOVERNANCE DRIFT.
  GC-2  admission record 가 없는 source 인데 그 source 의 verified TSU 수 > 0  → GOVERNANCE DRIFT.
        (source→verified 매핑은 INV-4 linkage 로.)
  GC-3  tsu-track admission 인데 그 source 의 TSU dir 자체가 없음  → INFO only (drift 아님).

exit 0  =  core_drift == []  and  governance_drift == []
exit 1  =  그 외
```
- **M2 count(14) 를 TSU/incremental/Qdrant count 와 직접 비교하지 마라 (D-1 제거).**
- tsu_id namespace 가 `incremental_state.json` key 와 `tsu.json` record `id` 사이에서 안 맞으면
  → 그 자체가 INV-1 drift 로 드러난다. **id 포맷을 임의 정규화해서 억지로 맞추지 마라** — 안 맞으면 보고.

### 3.3 출력 (§4.3)
- 사람용 리포트: 4 authority 요약값 + (선택) `nae_ref_v1` points 정보 1줄 + 아래 구획:
  `[CORE DRIFT]` / `[GOVERNANCE DRIFT]` / `[INFO]` / `No drift detected.`
- `--json` : `{"authorities": {...}, "invariants": [{"id","ok","detail"}], "governance": [{"id","ok","detail"}],
  "qdrant": "reachable|unreachable|error", "drift": {"core": [...], "governance": [...]}}`. stdout 로.
- argparse 에 `--json` 만 추가. `--apply` **미등록** (→ `unrecognized arguments`).

### 3.4 도구 불변식
- 실행이 파일·Qdrant·state 를 쓰지 않는다. 모든 `open()` read. Qdrant GET/count/scroll 만.
- docstring 을 재작성 내용에 맞게 갱신 (skeleton 문구 제거).

---

## 4. TASK 2 — `tests/test_nae_corpus_reconcile.py` 재작성

RATIFIED §5 그대로. `probe_qdrant` 를 **주입 가능**(인자 or monkeypatch)하게 만들어 live Qdrant 없이
(b)(c) 를 돌린다. **tmp fixture 로 실제 `NAE/` 파일 무접촉** (memory: Test Fixture Path Overrides — 경로
파라미터 전부 override).

| 구분 | test |
|---|---|
| **(a)** Qdrant 정지 | `probe_qdrant` → `("unreachable", ...)` (또는 `ConnectionError` 던지게) monkeypatch → `reconcile()` 예외 없이 완료, 리포트에 `unreachable`, INV-2 skip |
| **(b)** unit: reachable + 일관 입력 → drift 0 | tmp fixture: verified_ids == indexed_ids == qdrant_ids (전부 주입) → `core_drift == [] and governance_drift == []`, exit 0 |
| **(c1)** INV-1 flag | indexed 에서 1 id 제거 → INV-1 위반 + 그 tsu_id 가 `verified_only` 에 |
| **(c2)** INV-2 flag | `probe_qdrant → ("reachable", <다른 집합>)` → INV-2 위반 |
| **(c3)** INV-3 flag | `generated` tsu_id 를 indexed_ids 에 주입 → INV-3 위반 + 그 id |
| **(c4)** INV-4 flag | tmp tsu record linkage 를 M2 없는 값으로 → INV-4 위반 |
| **(c5)** GC-2 flag | admission 없는 source 에 verified TSU record → GOVERNANCE DRIFT |
| **(d)** mutation 0 | 실행 전/후 `incremental_state.json`·`source_manifest.yaml`·`tsu.json`·`corpus_admissions.jsonl` 의 sha256 동일 assert; `python scripts/nae_corpus_reconcile.py --apply` → stderr 에 `unrecognized arguments` |
| **D-4** | `probe_qdrant` 가 "컬렉션 없음"류 예외를 `("error", ...)` 로 분류(→ core_drift), `unreachable` 로 은폐 안 함 |
| **smoke (판정 아님)** | 실제 파일로 `python scripts/nae_corpus_reconcile.py` 1회 실행 → **stdout + exit code 를 그대로 캡처**. drift 가 나오면 report 에 인용. **데이터를 고쳐 통과시키지 마라** |
| 유지 | 기존 "파일 존재 / list" sanity 는 남겨도 무방 (약화 아님) |

---

## 5. VALIDATION GATE (완료 후 전부 실행, raw 첨부)

```bash
source ~/envs/dbma311/bin/activate

# mutation 0 baseline
for f in NAE/pipeline/ingest/state/incremental_state.json \
        NAE/pipeline/registration/state/source_manifest.yaml \
        NAE/governance/corpus_admissions.jsonl; do shasum -a 256 "$f"; done > /tmp/m4_pre.txt

# smoke run — 결과를 그대로 기록 (drift 유무는 데이터가 결정, 강제 아님)
python scripts/nae_corpus_reconcile.py ; echo "exit=$?"
python scripts/nae_corpus_reconcile.py --json ; echo "exit=$?"
python scripts/nae_corpus_reconcile.py --apply 2>&1 | tail -2 ; echo "apply exit=$?"

# unit tests
python -m pytest -q tests/test_nae_corpus_reconcile.py

# regression (인접)
python -m pytest -q tests/test_m2_source_registry_governance.py tests/test_corpus_admissions.py

# mutation 0 verify
for f in NAE/pipeline/ingest/state/incremental_state.json \
        NAE/pipeline/registration/state/source_manifest.yaml \
        NAE/governance/corpus_admissions.jsonl; do shasum -a 256 "$f"; done > /tmp/m4_post.txt
diff /tmp/m4_pre.txt /tmp/m4_post.txt && echo "MUTATION 0 OK" || echo "MUTATION DETECTED — RED"

git diff --stat
git status --short
grep -n "apply\|\.write\|open(.*['\"]w\|dump(" scripts/nae_corpus_reconcile.py | grep -v "argparse\|# " || echo "no write logic"
grep -n "6333\|QDRANT_PORT" scripts/nae_corpus_reconcile.py ; echo "stale-port grep exit=$? (1=clean)"
grep -n "QDRANT_URL\|NAE.pipeline.index.config" scripts/nae_corpus_reconcile.py
```

**입증 필수:**
- `pytest tests/test_nae_corpus_reconcile.py` — FAIL/ERROR 0. (a)/(b)/(c1..c5)/(d)/D-4 전부 존재·PASS.
- smoke run — stdout + exit code **그대로 기록**. CORE/GOVERNANCE DRIFT 가 나오면 그 목록을 보고에 인용
  (데이터 수정 금지). 안 나오면 "No drift detected", exit 0.
- `--apply` → `unrecognized arguments`.
- **MUTATION 0 OK** (sha256 pre==post). state/Qdrant/manifest/admission 무변경.
- `git diff --stat` — allowlist 2파일만. production 코드 diff 없음.
- stale 포트(`6333`/`QDRANT_PORT`) 0줄. `QDRANT_URL` 은 `NAE.pipeline.index.config` 에서 import.
- `git status --short` — 무관 항목 미접촉, staged 없음.
- 인접 regression (`test_m2_source_registry_governance` / `test_corpus_admissions`) GREEN.

---

## 6. FAILURE POLICY

- 설계 판단이 필요한 지점(RATIFIED §4/§5 에 답이 없는 것) → **중단, CUE 에 보고.** 임의 결정 금지.
- smoke run 이 실제 drift 를 보고하면 → **그대로 보고.** 데이터·state·Qdrant 를 고쳐 통과시키지 마라 (HQ 지적 ③).
- tsu_id namespace 불일치 → id 를 임의 정규화하지 말고 보고.
- 인접 regression 이 무관한 기존 사유로 깨지면 무관 코드 수정 금지 — 보고.
- 범위 초과·2회 이상 반복 실패·설계 변경 필요 → CUE 가 HQ 에 보고 (C1 은 CUE 에만 보고).

---

## 7. COMMIT — C1 은 커밋하지 않는다

`git add` / `git commit` 금지. C1 → 구현 → §5 검증 → §8 보고 → **STOP.**
CUE 가 `ad1464d` 대비 독립검증 (RATIFIED §4/§5 대조, smoke run 재현, mutation 0, ID-level 로직 실측) →
필요 시 CUE 정정 지시(bounded loop) → GREEN → **단일 커밋**
(`scripts/nae_corpus_reconcile.py` + `tests/test_nae_corpus_reconcile.py` + RATIFIED doc + EXEC 명령서;
메시지 `M-4: read-only corpus reconciliation tool (ADR-030 v2.1 §9.4)`).

---

## 8. OUTPUT — `output/ADR-030-Phase1A-M4-EXEC-REPORT.md` (author: C1)

1. Workspace gate raw.
2. `scripts/nae_corpus_reconcile.py` — 함수/판정 요약 (D-1~D-8 해소 대응표).
3. smoke run — `python … reconcile.py` 및 `--json` 전체 stdout + exit code **raw** (해석 없이).
   drift 있으면 CORE/GOVERNANCE 목록 그대로.
4. tests — `pytest -q` 전체 raw. (a)/(b)/(c1-c5)/(d)/D-4 매핑.
5. mutation 0 — pre/post sha256 diff raw ("MUTATION 0 OK").
6. scope — `git diff --stat`, `git status --short`, write-logic grep, stale-port grep raw.
7. 인접 regression raw.
8. RATIFIED §4/§5 로부터의 deviation = **없음** (있으면 §6 STOP).

speculative commentary · 새 invariant · 설계 변경 제안 금지. C1 self-PASS 는 승인 아님 — CUE 재검증.

END OF M-4 EXEC ORDER
