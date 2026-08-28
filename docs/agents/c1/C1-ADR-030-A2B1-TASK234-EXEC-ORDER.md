# C1 — ADR-030 v2.1 / A-2b-1 · TASK 2~4 (validator / test / SSOT)

> **작성**: CUE · **선행**: A-2b-1 TASK 1 (M2 backfill) **CUE VERIFIED** — M2 에 14×3 필드가
> 이미 반영돼 있다 (uncommitted). HEAD `44e1a18` (`dev/dbma-engine`).
> 이번 명령은 backfill 을 검증 계층(validator/test/SSOT)에 반영. **M2 는 다시 건드리지 않는다.**

---

## 0. 착수 전 — Workspace Verification Gate (`.clinerules/` §3.1)

```bash
pwd
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
python -c "import yaml;d=yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml'));print('authority_class count =', sum(1 for s in d['sources'] if 'authority_class' in s))"
```
**기대:** `--show-toplevel` = `/Users/David/DBMA` (`.claude/worktrees/...` 이면 잘못됨) · `dev/dbma-engine` ·
`44e1a18` · `authority_class count = 14`.
하나라도 불일치하면 편집하지 말고 즉시 중단·보고.

무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`) — stage·revert·수정 금지.
**`git add` / `git commit` 금지** (Task Order 가 커밋을 요청하지 않음. 검증 후 CUE/사용자가 커밋).

---

## 1. HARD STOP

- **M2 (`NAE/pipeline/registration/state/source_manifest.yaml`) 를 건드리지 마라.** TASK 1 반영분 유지.
- `content_genre` / `theological_category` / `tradition` 관련 로직·테스트를 "구현"하지 마라 (= A-2b-2).
  이 3필드는 M2 에 **없어야** 하고, 관련 테스트는 "부재 확인" 상태 그대로 둔다.
- M1 / M3 / `manifest_writer.py` / `pipeline.py` / 새 schema 파일 금지.
- TSU / Qdrant / retrieval / embedding / `config.yaml` 무접촉.

**allowlist (수정 가능 — 3파일):**
`scripts/m2_source_registry_validator.py` · `tests/test_m2_source_registry_governance.py` ·
`docs/architecture/NAE-Manifest-Authority-SSOT.md`

---

## 2. TASK 2 — validator

**대상**: `scripts/m2_source_registry_validator.py`

### 2-A. V5 (`check_no_required_metadata`) — 아직 no-op PASS (A-2a 잔여 C-4b). 실검사 배선.
`check_authority_class_enum` / `check_new_field_definitions` 는 이미 `sources=None` 파라미터화돼 있다.
```python
def check_no_required_metadata() -> ValidationResult:
    """V5: 6필드 없는 합성 레코드에 per-record 검사 → FAIL 0 (optionality 계약)."""
    result = ValidationResult()
    synthetic = [{k: "x" for k in M2_BASE_KEYS}]
    fails = (check_authority_class_enum(synthetic).failed
             + check_new_field_definitions(synthetic).failed)
    if fails:
        result.add("FAIL", f"V5: 합성 레코드에서 예상외 FAIL: {fails}")
    else:
        result.add("PASS", "V5: 합성 레코드(ADR-030 필드 0) → per-record FAIL 0")
    return result
```

### 2-B. V6 확장 — `raw_path` / `checksum_target` 파일 존재 검사
`check_new_field_definitions` 의 shape 루프 뒤, 마지막 `result.add("PASS", ...)` 앞에 추가:
```python
    missing = []
    for source in sources:
        sid = source.get("source_id", "UNKNOWN")
        for field_name in ("raw_path", "checksum_target"):
            v = source.get(field_name)
            if isinstance(v, str) and not (PROJECT_ROOT / v).exists():
                missing.append(f"{sid}.{field_name}={v}")
    if missing:
        result.add("FAIL", f"V6: raw_path/checksum_target 파일 없음: {missing}")
    else:
        result.add("PASS", f"V6: raw_path/checksum_target 파일 전부 존재")
```
(부재 필드는 자동 skip — A-2b-1 에선 14×2 전부 존재해야 PASS.)

### 2-C. V4 — 그대로 (enum-generic). 특정 §7.3 배정은 test 에서 pin.

docstring(V5/V6 설명)도 위 변경에 맞게 갱신.

검증: `python scripts/m2_source_registry_validator.py` → exit 0.
`grep -n "SCHEMA_PATH\|assert len(sources)" scripts/m2_source_registry_validator.py` → 0줄 유지.

---

## 3. TASK 3 — test delta

**대상**: `tests/test_m2_source_registry_governance.py` (현재 25 governance; 지금 3건 FAIL 상태)

| 현재 테스트 | 조치 |
|---|---|
| `test_pos_04_raw_path_optional` | **FLIP → `test_pos_04_raw_path_present`**: `for s in M2['sources']: assert isinstance(s.get('raw_path'), str) and s['raw_path']` (14 전부) |
| `test_pos_05_checksum_target_optional` | **FLIP → `test_pos_05_checksum_target_present`**: 동일하게 `checksum_target` |
| `test_m2_records_only_known_keys` | **UPDATE**: `assert keys == base` → `assert keys == base \| {"authority_class","raw_path","checksum_target"}` (14 레코드 전부 정확히 13키). `issubset` 줄은 유지 |
| `test_pos_06_authority_class_vocab_when_present` | **유지** (이제 `found`=14 → 비공허 통과). |
| `test_pos_01/02/03_*_optional` | **유지 그대로** (content_genre/theological_category/tradition 는 A-2b-1 에서 backfill 안 함 → `assert not has_X` 계속 참) |
| `test_pos_07_new_fields_optional_no_fail` | **유지** (합성 레코드 기준 — 무영향) |
| 나머지 (neg_*, iso_*, int_*, TestM2KeyGovernance.test_validator_has_no_schema_path) | **유지** |

**신규 추가 — `TestM2KeyGovernance` 클래스에:**
```python
    def test_authority_class_matches_adr030_7_3(self):
        """authority_class 배정이 ADR-030 v2.1 §7.3 과 일치 (Smith=reference, 나머지=historical_witness)."""
        S = _load_yaml(M2_PATH)["sources"]
        for s in S:
            exp = "reference" if s["source_id"].startswith("BAP-REF-SMITH") else "historical_witness"
            assert s.get("authority_class") == exp, s["source_id"]
        hw = sum(1 for s in S if s.get("authority_class") == "historical_witness")
        rf = sum(1 for s in S if s.get("authority_class") == "reference")
        assert (hw, rf) == (10, 4), f"{hw}/{rf}"

    def test_raw_path_checksum_target_files_exist(self):
        """backfill 된 14×2 경로가 실제 디스크에 존재."""
        S = _load_yaml(M2_PATH)["sources"]
        for s in S:
            for k in ("raw_path", "checksum_target"):
                assert (PROJECT_ROOT / s[k]).exists(), f"{s['source_id']} {k}: {s[k]}"
```

모듈 docstring 의 테스트 목록도 갱신.

검증: `pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py` →
**FAIL/ERROR 0.** governance ≈ 27 (25 + 신규 2; FLIP·UPDATE 는 카운트 불변).

---

## 4. TASK 4 — SSOT 문서

**대상**: `docs/architecture/NAE-Manifest-Authority-SSOT.md` — "## Additive metadata … A-2b PENDING" 절만 수정.
다른 절(M2 governance §2-1 판정 등) 건드리지 마라.

- 절 제목: `status: **A-2b PENDING**` → `status: **A-2b-1 완료 / A-2b-2 PENDING**`.
- 표 갱신:
  - `authority_class` 행 확정 상태 → `**populated 14/14 (A-2b-1)** — 값 per ADR-030 v2.1 §7.3 (historical_witness ×10 / reference ×4)`
  - `raw_path` 행 → `**populated 14/14 (A-2b-1)** — CUE-ADR030-M2-RAWPATH-…md §3`
  - `checksum_target` 행 → `**populated 14/14 (A-2b-1)** — 동 §3`
  - `content_genre` / `theological_category` / `tradition` 행 → `**A-2b-2 PENDING** — per-record 값 CUE 판정 + HQ 비준 필요`
- 한 줄 추가: "현재 M2 레코드 키 = **13** (base 10 + authority_class + raw_path + checksum_target).
  나머지 3필드는 A-2b-2 까지 키 생략 (WARNING-first §7.5). M1 은 backfill 미적용 — derived 미러, M1↔M2 prefix
  불일치는 예상된 것 (archival = S-3)."

---

## 5. 검증 & EVIDENCE (완료 후 전부 실행, raw 첨부)

```bash
source ~/envs/dbma311/bin/activate
python scripts/m2_source_registry_validator.py ; echo "exit=$?"
grep -n "SCHEMA_PATH\|source_manifest.schema\|assert len(sources)" scripts/m2_source_registry_validator.py ; echo "grep exit=$?"
python -m pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py
grep -c "    def test_" tests/test_m2_source_registry_governance.py
git diff --stat
git diff -- scripts/m2_source_registry_validator.py
git diff -- tests/test_m2_source_registry_governance.py
git diff -- docs/architecture/NAE-Manifest-Authority-SSOT.md
git diff --quiet -- NAE/pipeline/registration/state/source_manifest.yaml ; echo "M2 re-touched? exit=$? (1 = only TASK1 backfill, C1 이번에 M2 미변경)"
git status --short
```

**입증 필수:**
- validator exit 0 (V5 실검사 문구, V6 "파일 전부 존재", V4 "14 records — all valid").
- `grep` : `SCHEMA_PATH` 0줄, `assert len(sources)` 0줄.
- pytest: **FAIL/ERROR 0** (현재 3 FAIL 이 전부 해소). governance ≈ 27.
- `git diff --stat` : allowlist 3파일 + M2(TASK1분) 만. M1/M3/기타 무변경. staged 없음.
- M2 는 이번 명령에서 **추가 변경 0** (TASK 1 diff 그대로).

---

## 6. SCOPE AUDIT

```
TASK 2~4 변경만 (validator / governance test / SSOT)
M2 추가 변경 없음 (TASK 1 backfill 유지)
content_genre / theological_category / tradition 구현 없음 (A-2b-2)
M1 / M3 / writer / pipeline / 새 schema 없음
TSU / Qdrant / retrieval / embedding / config 무접촉
무관 미커밋 항목 미접촉, git add/commit 없음
```
위반 시 중단, **RED** 보고.

---

## 7. FINAL REPORT

`output/ADR-030-Phase1A-A2b1-TASK234-REPORT.md` (author: C1):
1. Workspace gate — §0 raw.
2. Validator — 변경 요약(V5 배선 / V6 파일존재), `python … validator.py` 전체 raw (exit 0).
3. Test delta — FLIP 2 / UPDATE 1 / 신규 2 목록, `grep -c def test_` raw, `pytest -q` 전체 raw (FAIL 0).
4. SSOT — 변경 절 `git diff` raw.
5. Git evidence — `git diff --stat`, `git status --short` raw, M2 재변경 없음 입증.
6. Deferred — A-2b-2 (content_genre/theological_category/tradition, HQ 값 비준), M1 archival (S-3),
   ADR-030 v2.1 §8.4 괄호 예시 정정 (RAWPATH 문서 §6).
7. Verdict — `A-2b-1 TASK 2~4 COMPLETE — READY FOR CUE REVIEW` / `... INCOMPLETE — RETURN`.

없는 테스트를 있다고 쓰지 마라 (A-2a 때 지적). 모든 수치는 raw 로 뒷받침. C1 self-PASS 는 승인 아님 —
CUE 가 `44e1a18` + TASK1 대비 재검증한다.

END OF A-2b-1 TASK 2~4 ORDER
