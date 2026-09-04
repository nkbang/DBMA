# C1 — ADR-030 v2.1 Phase 1-A / A-2a CORRECTION ORDER

> **발부**: CUE (독립검증 결과) · **대상 baseline**: `dev/dbma-engine` @ `fcaa380` (`/Users/David/DBMA`)
> **선행**: A-2a EXEC 완료분 위에 이어서 작업. 되돌리지 마라. 아래 punch-list 7건만 처리.

---

## 0. 판정 요약 (CUE 독립검증)

**🟡 A-2a CORE VERIFIED — punch-list RETURN.** 코어(구조/검증/cleanup, M2 무접촉, backfill 0, 범위 누수 0,
production 무접촉)는 통과. 재작업 아님. 아래 7건만 고치고 §9 보고서를 정확히 다시 써라.

**확인 필수 (착수 전):**
```bash
pwd && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD
# → /Users/David/DBMA · dev/dbma-engine · fcaa380
```

---

## 1. PUNCH-LIST (7건)

### C-1 [MEDIUM] `test_validator_has_no_schema_path` 미구현 → 추가

`tests/test_m2_source_registry_governance.py` docstring(L23)과 빈 섹션 헤더
`# ── New: M2 key governance ──` 만 있고 **테스트 본문이 없다.** EXEC §5.3 필수.

그 헤더 아래에 전용 클래스로 추가:
```python
class TestM2KeyGovernance:
    """§2-1 판정 회귀 가드 + M2 키 화이트리스트."""

    def test_validator_has_no_schema_path(self):
        """validator 소스에 schema 파일 참조가 없어야 한다 (§2-1 회귀 가드)."""
        src = (PROJECT_ROOT / "scripts" / "m2_source_registry_validator.py").read_text(encoding="utf-8")
        assert "SCHEMA_PATH" not in src, "validator에 SCHEMA_PATH 재등장"
        assert "source_manifest.schema" not in src, "validator가 schema 파일을 참조"

    def test_m2_records_only_known_keys(self):
        """M2 각 레코드의 키가 {10 base} ∪ {6 ADR-030} 밖으로 나가지 않는다.
        A-2a: 정확히 10 base 키."""
        m2_data = _load_yaml(M2_PATH)
        base = {"source_id", "title", "author", "author_id", "work_id",
                "edition_id", "year", "license", "archive_source", "raw_checksum"}
        additive = {"authority_class", "content_genre", "theological_category",
                    "tradition", "raw_path", "checksum_target"}
        for s in m2_data["sources"]:
            keys = set(s.keys())
            assert keys.issubset(base | additive), f"{s.get('source_id')} unknown keys: {keys - (base | additive)}"
            assert keys == base, f"{s.get('source_id')} A-2a 단계에서 base 10키가 아님: {keys}"
```

### C-2 [MEDIUM] `test_m2_records_only_known_keys` 미구현 → C-1 블록에 포함(위 코드)

### C-3 [MEDIUM] §9 FINAL REPORT 부정확 → 재작성

`output/ADR-030-Phase1A-A2a-EXEC-REPORT.md` 의 test delta 서술이 파일과 불일치한다:
- "3 신규 (test_m2_records_only_known_keys, test_validator_has_no_schema_path, test_pos_07)" →
  앞 2개는 (수정 전) 파일에 없었고, `test_pos_07` 은 rename(신규 아님).
- "10 삭제 / 2 재타깃 / 3 신규" 카운트가 실제와 불일치.

**정확히 다시 써라.** 실제 반영 후 최종 상태 기준:
- **삭제**: `test_neg_02_no_eligible_state_in_schema`, `test_neg_03_no_active_state_in_schema`,
  `test_neg_06_no_forbidden_authority_values_in_schema`, `test_neg_09_no_required_for_eligible_expression` (4)
- **재타깃(rename+본문 교체)**: `test_neg_01_*_in_schema → *_in_m2`,
  `test_pos_01..05_*_defined → *_optional`, `test_pos_06_*_has_4_values → *_vocab_when_present`,
  `test_pos_07_all_new_fields_optional → *_no_fail` (8)
- **신규**: `test_validator_has_no_schema_path`, `test_m2_records_only_known_keys` (2)
- **유지**: 나머지 전부
- 최종 governance test 수: **25** (수정 전 23 + 신규 2). reconcile 15 무변경. 합계 **40**.
- 모든 수치는 **직접 실행한 raw 출력**으로 뒷받침. 추정 금지.

### C-4 [LOW] validator V5 `check_no_required_metadata` — 속 빈 PASS 수정

현재: `synthetic` dict 를 만들고 **쓰지 않은 채** 무조건 `result.add("PASS", ...)`.
→ 실제로 합성 레코드에 per-record 검사를 돌려 FAIL 0 을 확인하도록 고친다.

`check_authority_class_enum` 와 `check_new_field_definitions` 에 주입 파라미터 추가:
```python
def check_authority_class_enum(sources=None) -> ValidationResult:
    result = ValidationResult()
    if sources is None:
        if not M2_PATH.exists():
            return result
        sources = yaml.safe_load(M2_PATH.read_text(encoding="utf-8")).get("sources", [])
    # ... 이하 기존 로직에서 m2_data.get("sources", []) → sources 로 치환 ...
```
`check_new_field_definitions` 도 동일하게 `sources=None` 파라미터화 (내부 `sources` 사용).
`validate()` 의 호출부는 인자 없이 그대로(기본값 = M2 로드).

그다음 V5 를 실제 검사로:
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
검증: `python scripts/m2_source_registry_validator.py` 여전히 exit 0, V5 PASS 문구가 실검사 기반.

### C-5 [LOW] validator V7 bare `assert` 제거

`check_m2_identity` 의 `assert len(sources) == 14, ...` →
```python
    if len(sources) != 14:
        result.add("FAIL", f"V7: expected 14 M2 records, got {len(sources)}")
    else:
        result.add("PASS", "V7: M2 has exactly 14 records")
```
(다른 모든 검사와 동일하게 FAIL 을 result 에 기록. `python -O` 에서 사라지거나 traceback 로 죽지 않도록.)

### C-6 [LOW] `test_pos_01..05` / `test_pos_07` 죽은 코드·불일치 정리

- `test_pos_01..05_*_optional`: 본문 첫 줄 `synthetic = {k: "x" for k in M2_BASE_KEYS}` (미사용) **삭제**.
  docstring 을 본문과 일치시킨다: `"""A-2b backfill 전 <field> 가 M2 에 부재함을 확인 (optional)."""`
- `test_pos_07_new_fields_optional_no_fail`: 현재 단언이 항진명제
  (`set(synthetic).issubset(BASE|ADDITIVE)` 는 구성상 항상 참).
  → 실검사로 교체:
  ```python
  def test_pos_07_new_fields_optional_no_fail(self):
      """6필드 없는 합성 레코드에 validator per-record 검사 → FAIL 0."""
      import scripts.m2_source_registry_validator as v
      synthetic = [{k: "x" for k in M2_BASE_KEYS}]
      fails = (v.check_authority_class_enum(synthetic).failed
               + v.check_new_field_definitions(synthetic).failed)
      assert fails == [], f"합성 레코드에서 예상외 FAIL: {fails}"
  ```
  (C-4 의 파라미터화가 선행되어야 함. `M2_BASE_KEYS` 는 이미 테스트 상수로 존재하거나 validator 에서 import.)

### C-7 [LOW] modern schema 여분 빈 줄 제거

`resources/theological_sources/modern/source_manifest.schema.yaml` — H2 제거 자리에 **빈 줄이 1개 남았다**
(`history_source_ids` description 다음 ~L236, `# manifest.yaml 파일 자체의...` 주석 앞).
그 여분 빈 줄 1개를 지운다. 목표:
```bash
git diff -- resources/theological_sources/modern/source_manifest.schema.yaml
# → hunk 1개(H4, language 따옴표)만 나와야 한다
```

---

## 2. 금지 (A-2a 그대로)

- M2 (`NAE/pipeline/registration/state/source_manifest.yaml`) 수정 금지 — `# ROLE` 포함 현상 유지. backfill 0.
- M1 / M3 수정 금지.
- `manifest_writer.py` / `pipeline.py` / registration 아키텍처 변경 금지.
- 새 schema 파일 금지.
- 무관 미커밋 항목(`test_seal_*`, `smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`) stage·revert 금지.
- TSU / Qdrant / retrieval / embedding / `config.yaml` 무접촉.
- `docs/architecture/NAE-Manifest-Authority-SSOT.md` 는 이미 검증 통과 — **건드리지 마라** (C-3 는 보고서 파일 `output/…` 만).

**수정 가능 경로 (allowlist):**
`scripts/m2_source_registry_validator.py` · `tests/test_m2_source_registry_governance.py` ·
`resources/theological_sources/modern/source_manifest.schema.yaml` · `output/ADR-030-Phase1A-A2a-EXEC-REPORT.md`

---

## 3. 검증 (완료 후 전부 실행, raw 출력 첨부)

```bash
source ~/envs/dbma311/bin/activate
python scripts/m2_source_registry_validator.py ; echo "exit=$?"
python -m pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py
grep -n "SCHEMA_PATH\|source_manifest.schema\|assert len(sources)" scripts/m2_source_registry_validator.py ; echo "grep exit=$?"
grep -c "    def test_" tests/test_m2_source_registry_governance.py
git diff -- resources/theological_sources/modern/source_manifest.schema.yaml
git diff --stat
git diff --cached --stat
git status --short
git diff --quiet -- NAE/pipeline/registration/state/source_manifest.yaml ; echo "M2 unchanged? exit=$? (0=unchanged 무시, 1=기존 ROLE줄만)"
```

**반드시 입증:**
- validator `exit=0`, V5 PASS 가 실검사 기반, V7 에 bare assert 없음
- pytest: FAIL/ERROR 0, governance **25** + reconcile 15 = **40 passed**
- `grep` : `SCHEMA_PATH` 0줄, `assert len(sources)` 0줄
- modern schema `git diff` : **H4 hunk 1개만**
- M2 `git diff` : 기존 `# ROLE` 1줄 외 변화 없음 (backfill 0)
- `git status --short` : 무관 항목 신규 stage 없음, allowlist 4경로만

---

## 4. FINAL REPORT (재작성)

`output/ADR-030-Phase1A-A2a-EXEC-REPORT.md` 를 갱신 (append 아님, 정확한 최신 상태로 교체):
- **Correction applied** 절: C-1~C-7 각 항목의 실제 조치 + 근거 raw 출력.
- **Test delta** 절: §C-3 의 정확한 삭제/재타깃/신규/유지 목록 + `grep -c def test_` = 25 raw.
- **Validator** 절: `python … validator.py` 전체 raw (exit 0, PASS 목록).
- **Pytest** 절: `pytest -q` 전체 raw (40 passed).
- **Scope evidence** 절: `git diff --stat`, `git diff --cached --stat`, `git status --short` raw.
- **Verdict**: `A-2a CORRECTION COMPLETE — READY FOR INDEPENDENT CUE RE-REVIEW`
  (또는 미완/위반 시 `A-2a CORRECTION INCOMPLETE — RETURN`).

**C1 자신의 PASS 는 승인이 아니다.** CUE 가 `fcaa380` 대비 재검증한다.

END OF A-2a CORRECTION ORDER
