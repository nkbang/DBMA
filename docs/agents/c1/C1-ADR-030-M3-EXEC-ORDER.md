# C1 — ADR-030 v2.1 §12 M-3 EXEC ORDER (Corpus Admissions)

> **작성**: CUE (HQ M-3 EXEC COMMAND 반영) · **선행**: A-2b-2 VERIFIED — commit `0931e0c` (`dev/dbma-engine`)
> **판정 권위**: `docs/agents/cue/CUE-ADR-030-M3-CORPUS-ADMISSIONS-DRAFT.md` §4 (소급 6항목) + HQ 비준 M3-1~M3-6
> **범위**: `NAE/governance/corpus_admissions.jsonl` 신설 + admission flow 문서 + governance test 뿐

---

## 0. 착수 전 — Workspace Verification Gate (`.clinerules/dbma-engineering.md` §3.1)

```bash
pwd
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
ls NAE/governance/ 2>/dev/null || echo "NAE/governance ABSENT (expected)"
```
**기대**: `--show-toplevel` = `/Users/David/DBMA` (`.claude/worktrees/...` 이면 잘못됨) · `dev/dbma-engine` ·
`0931e0c` · `NAE/governance ABSENT`. 하나라도 불일치 → 편집 금지, 즉시 중단·보고.

무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`) — stage·revert·수정 금지.

---

## 1. MANDATE

ADR-030 §12 M-3 만 수행한다. HQ 가 아래 6개를 **이미 비준**했다 — 재검토·재판정 금지:

- **M3-1**: Smith Vol.1–4 = **source별 4개** admission record
- **M3-2**: `decided_by` = `"David / HQ"`
- **M3-3**: `date` = `"2026-08-28"`
- **M3-4**: 부재 metadata 는 **키 생략** (`null` / `[]` / placeholder 금지)
- **M3-5**: admission 은 **코드 게이트로 강제하지 않음** (`TSU_ELIGIBLE` = S-4 deferred)
- **M3-6**: **M2 = classification authority / M3 = admission 당시 snapshot**

필드·값의 authority = M-3 DRAFT §4. 그대로 소비한다. 값을 재판단하지 마라.

---

## 2. HARD STOP — 금지

- **Fuller Vol.1–8 admission record 생성 금지.** (verified TSU 미충족/미생성 — DRAFT §3.3.)
- **admission 코드 게이트 구현 금지** (`ProcessingState`/TSU Builder 배선 = S-4).
- **TSU / chunk 재처리 금지.**
- **corpus / Qdrant / state store (`incremental_state.json`, `registration_state.json`, `tsu.json`) 변경 금지.**
- **M2 (`NAE/pipeline/registration/state/source_manifest.yaml`) 변경 금지.**
- **M1 (`NAE/authority/source_manifest.yaml`) · M3-manifest (`NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv`) 변경 금지.**
- **새 vocabulary / classification 생성 금지.**
- **HQ 결정 재해석 금지. 기존 admission 결정 수정 금지.**
- **`manifest_writer.py` / `pipeline.py` / registration 아키텍처 변경 금지.**
- **`git add` / `git commit` 금지.**

**allowlist (신규/수정 가능 — 3):**
`NAE/governance/corpus_admissions.jsonl` (신규) ·
`docs/architecture/NAE-Manifest-Authority-SSOT.md` (절 1개 추가) ·
`tests/test_m2_source_registry_governance.py` (test 추가; 또는 신규 `tests/test_corpus_admissions.py`)

---

## 3. TASK 1 — `NAE/governance/corpus_admissions.jsonl` 생성

`NAE/governance/` 디렉터리 + `corpus_admissions.jsonl` 파일 신설. **append-only JSONL, 1줄 = 1 record.**
아래 **6줄을 verbatim** 으로 쓴다 (DRAFT §4 와 동일). 파일 끝 개행 1개. 그 외 줄 추가 금지.

```jsonl
{"source_id": "BAP-CHURCH-DAGG-001", "decided_by": "David / HQ", "date": "2026-08-28", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["church_practice"], "theological_category": ["ecclesiology"], "tradition": "Particular Baptist", "rationale": "Pre-existing human review (NAE/review/human/decisions/, reviewer David, 2026-08-09..11, APPROVED) retroactively satisfies admission + review; 2958 verified TSU already in nae_tsu_v1. Back-fill record only; no reprocessing.", "evidence_refs": ["NAE/review/human/decisions/", "NAE/corpus/tsu/Dagg_Church_Order/tsu.json", "NAE/pipeline/registration/state/registration_state.json"]}
{"source_id": "BAP-CHURCH-HISCOX", "decided_by": "David / HQ", "date": "2026-08-28", "track": "tsu", "authority_class": "historical_witness", "content_genre": ["church_practice", "pastoral"], "theological_category": ["ecclesiology"], "tradition": "Particular Baptist", "rationale": "Pre-existing human review (NAE/review/human/decisions/, reviewer David, 2026-08-09..11, APPROVED) retroactively satisfies admission + review; 361 verified TSU already in nae_tsu_v1. Back-fill record only; no reprocessing.", "evidence_refs": ["NAE/review/human/decisions/", "NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json", "NAE/pipeline/registration/state/registration_state.json"]}
{"source_id": "BAP-REF-SMITH-VOL01", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
{"source_id": "BAP-REF-SMITH-VOL02", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
{"source_id": "BAP-REF-SMITH-VOL03", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
{"source_id": "BAP-REF-SMITH-VOL04", "decided_by": "David / HQ", "date": "2026-08-28", "track": "reference", "authority_class": "reference", "content_genre": ["commentary"], "reference_quality_confirmed": true, "rationale": "Registration QUALITY_PASSED (ADR-021) + ADR-028 reference layer + already indexed in nae_ref_v1 (Smith Vol1-4 = 34,948 chunks). Back-fill record only; no re-chunk/re-index.", "evidence_refs": ["docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md", "NAE/pipeline/registration/state/source_manifest.yaml"]}
```

**형식 규칙:**
- 각 줄은 **단일 JSON object** (한 줄에 전부). pretty-print 금지.
- 키 순서 위와 동일.
- `theological_category` / `tradition` 이 위에 **없는 줄**(Smith 4건)은 그 키를 **넣지 않는다** — `null`/`[]`/`""` 금지.
- `reference_quality_confirmed` 는 **Smith 4건에만** `true`. Dagg/Hiscox 는 이 키 없음.
- `content_genre` / `theological_category` = JSON array. `tradition` = JSON string.

**착수 시 대조**: 위 6줄이 `docs/agents/cue/CUE-ADR-030-M3-CORPUS-ADMISSIONS-DRAFT.md` §4 와 문자 단위로 동일한지 확인.

**evidence_refs 실존 확인** (편집 전):
```bash
for p in NAE/review/human/decisions NAE/corpus/tsu/Dagg_Church_Order/tsu.json \
         NAE/corpus/tsu/Hiscox_Standard_Manual/tsu.json \
         NAE/pipeline/registration/state/registration_state.json \
         NAE/pipeline/registration/state/source_manifest.yaml \
         docs/NAE_SMITH_BIBLE_DICTIONARY_REGISTRATION_001.md; do
  test -e "$p" && echo "OK  $p" || echo "MISSING  $p"
done
```
하나라도 MISSING 이면 중단·보고.

---

## 4. TASK 2 — governance test

`tests/test_corpus_admissions.py` 신규 (또는 `test_m2_source_registry_governance.py` 에 `TestCorpusAdmissions` 클래스).
아래를 검증:

```python
import json
from pathlib import Path
import yaml
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ADM = PROJECT_ROOT / "NAE" / "governance" / "corpus_admissions.jsonl"
M2  = PROJECT_ROOT / "NAE" / "pipeline" / "registration" / "state" / "source_manifest.yaml"

def _records():
    return [json.loads(l) for l in ADM.read_text(encoding="utf-8").splitlines() if l.strip()]

class TestCorpusAdmissions:
    def test_file_exists_and_valid_jsonl(self):
        assert ADM.exists()
        recs = _records()
        assert len(recs) == 6

    def test_source_ids(self):
        ids = [r["source_id"] for r in _records()]
        assert len(ids) == len(set(ids)) == 6
        assert set(ids) == {
            "BAP-CHURCH-DAGG-001", "BAP-CHURCH-HISCOX",
            "BAP-REF-SMITH-VOL01", "BAP-REF-SMITH-VOL02",
            "BAP-REF-SMITH-VOL03", "BAP-REF-SMITH-VOL04",
        }

    def test_no_fuller_admission(self):
        ids = {r["source_id"] for r in _records()}
        assert not any(i.startswith("BAP-MISS-FULLER") for i in ids)

    def test_required_fields_and_hq_ratifications(self):
        for r in _records():
            for k in ("source_id", "decided_by", "date", "track",
                      "authority_class", "content_genre", "rationale", "evidence_refs"):
                assert k in r, (r["source_id"], k)
            assert r["decided_by"] == "David / HQ"
            assert r["date"] == "2026-08-28"
            assert r["track"] in ("tsu", "reference")
            assert isinstance(r["content_genre"], list) and r["content_genre"]
            assert isinstance(r["evidence_refs"], list) and r["evidence_refs"]

    def test_track_specific(self):
        for r in _records():
            if r["track"] == "reference":
                assert r["reference_quality_confirmed"] is True
                assert r["source_id"].startswith("BAP-REF-SMITH")
            else:
                assert "reference_quality_confirmed" not in r

    def test_absent_metadata_is_key_omission(self):
        for r in _records():
            for k in ("theological_category", "tradition"):
                if k in r:
                    assert r[k] not in (None, [], "")  # 존재하면 실값

    def test_snapshot_matches_m2_classification(self):
        m2 = {s["source_id"]: s for s in yaml.safe_load(M2.read_text(encoding="utf-8"))["sources"]}
        for r in _records():
            s = m2[r["source_id"]]
            assert r["authority_class"] == s["authority_class"]
            assert r["content_genre"] == s["content_genre"]
            assert r.get("theological_category") == s.get("theological_category")
            assert r.get("tradition") == s.get("tradition")

    def test_evidence_refs_exist(self):
        for r in _records():
            for p in r["evidence_refs"]:
                assert (PROJECT_ROOT / p).exists(), (r["source_id"], p)
```

기존 governance / reconcile test 는 **무변경** — 계속 통과해야 한다.

---

## 5. TASK 3 — SSOT 문서 절 추가

`docs/architecture/NAE-Manifest-Authority-SSOT.md` 에 아래 절을 추가 (다른 절 무변경, 분류표/스키마 **복제 금지**):

```markdown
## Corpus Admission (ADR-030 v2.1 §11)

`QUALITY_PASSED` 이후 · TSU 생성 / reference chunking 이전에, HQ 가
`NAE/governance/corpus_admissions.jsonl` 에 admission 결정 1줄을 기록한다
(track / authority_class / classification snapshot / (reference 시) reference_quality_confirmed /
rationale / evidence_refs). 이 기록이 없는 source 는 다음 단계로 진행하지 않는다
(현재 **수기 게이트**; 코드 강제 = ADR-030 S-4, `TSU_ELIGIBLE`).

- M2 = classification authority. admission record 의 classification 은 결정 당시 **snapshot** 이며 M2 와 일치한다.
- 소급: 기존 3,319 verified TSU (Dagg 2,958 + Hiscox 361, `nae_tsu_v1`) + Smith Vol.1–4
  (`nae_ref_v1` 34,948 chunk) 6건은 back-fill record 로 충족 — 재처리·재승인 없음.
- Fuller Vol.1–8: verified TSU 미충족/미생성 → admission 미기록 (처리 재개 시 HQ 결정).
- Flow 상세: ADR-030 v2.1 §11.2.
```

---

## 6. VALIDATION GATE (완료 후 전부 실행, raw 첨부)

```bash
source ~/envs/dbma311/bin/activate
python - <<'PY'
import json
recs=[json.loads(l) for l in open("NAE/governance/corpus_admissions.jsonl") if l.strip()]
print("records:", len(recs))
ids=[r["source_id"] for r in recs]
print("unique:", len(set(ids))==len(ids)==6)
print("ids:", sorted(ids))
print("fuller present:", any(i.startswith("BAP-MISS-FULLER") for i in ids))
print("decided_by ok:", all(r["decided_by"]=="David / HQ" for r in recs))
print("date ok:", all(r["date"]=="2026-08-28" for r in recs))
print("smith rqc:", all(r.get("reference_quality_confirmed") is True for r in recs if r["track"]=="reference"))
print("tsu no rqc:", all("reference_quality_confirmed" not in r for r in recs if r["track"]=="tsu"))
for r in recs:
    for k in ("theological_category","tradition"):
        if k in r: assert r[k] not in (None,[],""), (r["source_id"],k)
print("absent meta = key omission: OK")
PY
python -m pytest -q tests/test_corpus_admissions.py tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py
python scripts/m2_source_registry_validator.py ; echo "validator exit=$?"
git diff --stat
git status --short
git diff --quiet -- NAE/pipeline/registration/state/source_manifest.yaml ; echo "M2 unchanged? exit=$? (0=unchanged)"
```

**입증 필수:**
- JSONL = **6 records**, 전부 unique source_id, {Dagg, Hiscox, Smith Vol.1–4}
- Fuller Vol.1–8 admission **없음**
- `decided_by = "David / HQ"` · `date = "2026-08-28"` (6/6)
- Smith 4건 `reference_quality_confirmed = true`; Dagg/Hiscox 는 그 키 **없음**
- 부재 metadata(Smith `theological_category`/`tradition`) = **키 생략** (null/[]/placeholder 아님)
- `evidence_refs` 경로 6종 전부 실존
- `test_snapshot_matches_m2_classification` PASS — M2 classification authority 침해 없음
- `git diff --stat` : allowlist 3 파일만 (JSONL 신규 +6, SSOT +N, test 신규). **M2 diff 없음.**
- `incremental_state.json` / `registration_state.json` / `tsu.json` / Qdrant 무접촉
- 기존 governance/reconcile test + validator 전부 GREEN
- `git status --short` : 무관 항목 미접촉, staged 없음

---

## 7. FAILURE POLICY

DRAFT §4 ↔ 작성된 JSONL ↔ M2 사이 불일치 발견 시 → **STOP.** 조용히 화해시키지 마라.
정확한 충돌을 보고하고 CUE/HQ 결정을 기다린다.
무관한 기존 사유로 테스트가 깨지면 무관 코드 수정하지 마라.

---

## 8. COMMIT — C1 은 커밋하지 않는다

`git add` / `git commit` 금지. C1 → 실행 → §9 보고 → **STOP.**
CUE 가 `0931e0c` 대비 독립검증 후 **단일 커밋**:
`NAE/governance/corpus_admissions.jsonl` + SSOT 절 + test (+ DRAFT 문서는 CUE 가 stage).
메시지 주제: `M-3: corpus admission records + manual gate (ADR-030 v2.1 §11)`.

---

## 9. OUTPUT — `output/ADR-030-Phase1A-M3-EXEC-REPORT.md` (author: C1)

1. Workspace gate raw.
2. files created/changed (3).
3. `corpus_admissions.jsonl` 6줄 (그대로) + §6 검증 스크립트 raw.
4. test result — `pytest -q` 전체 raw (신규 + 기존 GREEN).
5. validator raw (exit 0).
6. scope — `git diff --stat`, `git status --short` raw; M2/state/Qdrant 무접촉 입증.
7. DRAFT §4 로부터의 deviation = **없음** (있으면 §7 STOP).

speculative commentary · 새 분류 · Fuller record · 코드 게이트 제안 금지.
C1 self-PASS 는 승인 아님 — CUE 재검증.

END OF M-3 EXEC ORDER
