# C1 — ADR-030 v2.1 Phase 1-A / A-2b-1 EXEC ORDER

> **작성**: CUE · **승인 대기**: 사용자(HQ) · **선행**: A-2a VERIFIED, commit `44e1a18` (`dev/dbma-engine`)
> **HQ 결정 반영**: `authority_class` = ADR-030 v2.1 §7.3 값을 비준으로 간주하여 A-2b-1 에 포함.

---

## 0. 작업 환경

| 항목 | 값 |
|---|---|
| 작업 디렉터리 | `/Users/David/DBMA` (메인 체크아웃, worktree 아님) |
| 브랜치 / baseline | `dev/dbma-engine` @ **`44e1a18`** |
| venv | `source ~/envs/dbma311/bin/activate` |
| 검증 diff | `git diff -- <allowlist 4경로>` 만. bare `git diff`/`git status` 로 판단 금지 |

착수 전 확인:
```bash
pwd && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD
# → /Users/David/DBMA · dev/dbma-engine · 44e1a18
```

무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`)이 작업 트리에
남아 있다. **stage·revert 하지 마라.**

---

## 1. OBJECTIVE — A-2b-1: M2 3필드 backfill (14 레코드)

`NAE/pipeline/registration/state/source_manifest.yaml` (M2) 의 **14개 레코드 전부**에 아래 3개 키를 추가한다.

| 필드 | 타입 | 값 출처 |
|---|---|---|
| `authority_class` | str (enum) | ADR-030 v2.1 §7.3 (§3 표) |
| `raw_path` | str (repo-relative) | `docs/agents/cue/CUE-ADR030-M2-RAWPATH-CHECKSUM-TARGET-DETERMINATION.md` §3 (§3 표) |
| `checksum_target` | str (repo-relative) | 동 문서 §3 (§3 표) |

이어서 A-2a 산출물(validator / test / SSOT)을 backfill 반영 상태로 갱신한다.

---

## 2. HARD STOP — 금지

- **`content_genre` / `theological_category` / `tradition` 를 추가하지 마라.** = A-2b-2 (별도 명령, HQ 값 비준 대기).
  §7.5 WARNING-first: 미결정 필드는 **키 자체를 생략**한다.
- M2 기존 10개 base 키(`source_id title author author_id work_id edition_id year license archive_source raw_checksum`)
  및 그 값을 **한 글자도 바꾸지 마라.** 레코드 순서·identity 불변.
- `authority_class` / `raw_path` / `checksum_target` **값을 추측·재판단하지 마라.** §3 표에서 **verbatim 복사**.
- **M2 를 `yaml.safe_load → yaml.safe_dump` 로 round-trip 하지 마라.** folded 다중행 title 문자열이 reflow 되어
  거대·불명확 diff 가 된다. **텍스트 레벨 삽입**(레코드당 3줄)만 한다.
- M1 (`NAE/authority/source_manifest.yaml`) 을 건드리지 마라. backfill 후 M1↔M2 prefix 불일치는 **예상된 것**
  (M1 = derived 미러, archival 은 별도 S-3 task). M1 동기화 금지.
- M3 · `manifest_writer.py` · `pipeline.py` · registration 아키텍처 · 새 schema 파일 · `NAE/corpus/governance/` 금지.
- TSU / `nae_tsu_v1`(3,319) / `nae_ref_v1`(34,948) / `incremental_state` / `registration_state` / retrieval /
  embedding cache / `config.yaml` / Qdrant / n8n 무접촉.

---

## 3. BACKFILL TABLE (verbatim — §3 표에서 그대로 복사)

경로는 **repo-relative**. `raw_path` 와 `checksum_target` 은 12건(Fuller·Smith)에서 서로 다르다 — **정상**
(`checksum_target` = 무결성 대상 `original.pdf`, `raw_path` = canonical 이 실제 읽은 파생 텍스트).

| # | source_id | authority_class | raw_path | checksum_target |
|---|---|---|---|---|
| 1 | `BAP-CHURCH-DAGG-001` | `historical_witness` | `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html` | `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html` |
| 2 | `BAP-CHURCH-HISCOX` | `historical_witness` | `NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html` | `NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html` |
| 3 | `BAP-MISS-FULLER-VOL01` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/original.pdf` |
| 4 | `BAP-MISS-FULLER-VOL02` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/original.pdf` |
| 5 | `BAP-MISS-FULLER-VOL03` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/original.pdf` |
| 6 | `BAP-MISS-FULLER-VOL04` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/original.pdf` |
| 7 | `BAP-MISS-FULLER-VOL05` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/original.pdf` |
| 8 | `BAP-MISS-FULLER-VOL06` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/original.pdf` |
| 9 | `BAP-MISS-FULLER-VOL07` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/original.pdf` |
| 10 | `BAP-MISS-FULLER-VOL08` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/original.pdf` |
| 11 | `BAP-REF-SMITH-VOL01` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/original.pdf` |
| 12 | `BAP-REF-SMITH-VOL02` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/original.pdf` |
| 13 | `BAP-REF-SMITH-VOL03` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/original.pdf` |
| 14 | `BAP-REF-SMITH-VOL04` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/original.pdf` |

**분포**: `authority_class` = `historical_witness` ×10 (Dagg, Hiscox, Fuller Vol01–08) + `reference` ×4 (Smith Vol01–04).
Smith 디렉터리는 `Vol1..Vol4` (zero-pad 없음), Fuller 는 `Vol01..Vol08` (zero-pad) — **표기 그대로**.

---

## 4. TASK 1 — M2 backfill

**대상**: `NAE/pipeline/registration/state/source_manifest.yaml`

각 레코드의 **`raw_checksum:` 줄 바로 다음**에 3줄을 삽입한다 (들여쓰기 = 기존 필드와 동일, `  ` 2칸):
```yaml
  raw_checksum: <기존 값 그대로>
  authority_class: <표>
  raw_path: <표>
  checksum_target: <표>
```
- 텍스트 삽입만. 기존 줄 수정 0.
- 값에 특수문자 없음 → 따옴표 불필요(경로·enum 전부 plain scalar 가능). 기존 파일 스타일 유지.
- 14 레코드 전부. 누락·중복 금지.

**권장 실행 방식** (택1, 둘 다 결과 동일해야):
- (a) 스크립트: §3 표를 dict 로 하드코딩 → M2 를 **줄 단위**로 읽어 `raw_checksum:` 매칭 시 3줄 append →
  파일 재작성. `yaml.safe_dump` 사용 금지.
- (b) 수동 삽입 후 아래 검증 스크립트로 전수 대조.

**삽입 후 필수 검증**:
```bash
python -c "
import yaml
d = yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml'))
print('records:', len(d['sources']))
exp = {  # §3 표
 'BAP-CHURCH-DAGG-001': ('historical_witness','NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html','NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html'),
 # ... 14행 전부 채워서 대조 ...
}
import os
for s in d['sources']:
    sid = s['source_id']
    a, r, c = s.get('authority_class'), s.get('raw_path'), s.get('checksum_target')
    assert (a, r, c) == exp[sid], f'{sid} MISMATCH: {(a,r,c)} != {exp[sid]}'
    assert os.path.exists(r), f'{sid} raw_path MISSING: {r}'
    assert os.path.exists(c), f'{sid} checksum_target MISSING: {c}'
    assert set(s) == {'source_id','title','author','author_id','work_id','edition_id','year','license','archive_source','raw_checksum','authority_class','raw_path','checksum_target'}, f'{sid} keys={set(s)}'
print('ALL 14 OK — values match §3, files exist, exactly 13 keys')
"
git diff --stat -- NAE/pipeline/registration/state/source_manifest.yaml   # +42 (14×3), -0
git diff -- NAE/pipeline/registration/state/source_manifest.yaml | grep -E '^-' | grep -v '^---'   # → 빈 출력 (삭제/수정 0)
```

---

## 5. TASK 2 — validator 갱신

**대상**: `scripts/m2_source_registry_validator.py`

### C-4b (A-2a 잔여) 해소 — V5 실검사 배선
`check_no_required_metadata()` 가 아직 no-op PASS. `check_authority_class_enum` / `check_new_field_definitions`
는 이미 `sources=None` 파라미터화됨. 실검사로 교체:
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

### V6 확장 — raw_path / checksum_target 파일 존재 검사
`check_new_field_definitions` 의 shape 루프 뒤에 추가: `raw_path` / `checksum_target` 이 존재하면
`(PROJECT_ROOT / value).exists()` 를 확인, 없으면 FAIL. (backfill 된 경로가 실파일을 가리키는지 = 실질 무결성.)

### V4 — 그대로 (enum-generic). 특정 배정은 테스트에서 pin (§6).

검증: `python scripts/m2_source_registry_validator.py` → exit 0.
V4 = "14 M2 records with authority_class — all valid",
V6 = "all present ADR-030 fields have correct shape" + "raw_path/checksum_target 14/14 files exist".

---

## 6. TASK 3 — test delta

**대상**: `tests/test_m2_source_registry_governance.py` (현재 25 governance)

| 테스트 | 조치 |
|---|---|
| `test_pos_04_raw_path_optional` | **FLIP → `test_pos_04_raw_path_present`**: 14 레코드 전부 `raw_path` 가 비어있지 않은 str |
| `test_pos_05_checksum_target_optional` | **FLIP → `test_pos_05_checksum_target_present`**: 동일 |
| `test_pos_06_authority_class_vocab_when_present` | 유지 (이제 `found`=14 → 비공허 통과). 원하면 `_all_valid` 로 rename |
| `test_pos_01/02/03_*_optional` | **유지** (content_genre/theological_category/tradition 는 A-2b-1 에서 backfill 안 함 → `assert not has_X` 계속 참) |
| `test_pos_07_new_fields_optional_no_fail` | 유지 (합성 레코드 기준 — 무영향) |
| `test_m2_records_only_known_keys` | **UPDATE**: `assert keys == base` → `assert keys == base \| {"authority_class","raw_path","checksum_target"}` (14 레코드 전부 정확히 13키) |
| `test_int_03_m2_yaml_valid` | 유지 (14 sources) |

**신규 추가:**
```python
    def test_authority_class_matches_adr030_7_3(self):
        """authority_class 배정이 ADR-030 v2.1 §7.3 과 일치."""
        m2 = _load_yaml(M2_PATH)
        expect = {}
        for s in m2["sources"]:
            sid = s["source_id"]
            expect[sid] = "reference" if sid.startswith("BAP-REF-SMITH") else "historical_witness"
        for s in m2["sources"]:
            assert s.get("authority_class") == expect[s["source_id"]], s["source_id"]
        hw = sum(1 for s in m2["sources"] if s.get("authority_class") == "historical_witness")
        rf = sum(1 for s in m2["sources"] if s.get("authority_class") == "reference")
        assert (hw, rf) == (10, 4), f"분포 {hw}/{rf} != 10/4"

    def test_raw_path_checksum_target_files_exist(self):
        """backfill 된 14×2 경로가 실제 디스크에 존재."""
        m2 = _load_yaml(M2_PATH)
        for s in m2["sources"]:
            for k in ("raw_path", "checksum_target"):
                p = PROJECT_ROOT / s[k]
                assert p.exists(), f"{s['source_id']} {k} missing: {p}"
```

검증: `pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py` →
FAIL/ERROR 0. governance ≈ 27 (25 + 신규 2, FLIP 은 카운트 불변).

---

## 7. TASK 4 — SSOT 문서 갱신

**대상**: `docs/architecture/NAE-Manifest-Authority-SSOT.md` — "Additive metadata … A-2b PENDING" 절만 수정.

- `authority_class` / `raw_path` / `checksum_target` 행 → **status `populated 14/14 (A-2b-1)`**.
  근거: authority_class = ADR-030 v2.1 §7.3, raw_path·checksum_target = `CUE-ADR030-M2-RAWPATH-…md` §3.
- `content_genre` / `theological_category` / `tradition` 행 → **status `A-2b-2 PENDING — per-record 값 CUE 판정 + HQ 비준 필요`**.
- 절 제목 `status: **A-2b PENDING**` → `status: **A-2b-1 완료 / A-2b-2 PENDING**`.
- 한 줄 추가: "M2 레코드 키 = 13 (base 10 + authority_class + raw_path + checksum_target). 나머지 3필드는
  A-2b-2 까지 생략 (WARNING-first, §7.5). M1 은 backfill 미적용 — derived 미러, archival 은 S-3."

다른 절(§2-1 판정 등)은 건드리지 마라.

---

## 8. IN / OUT SCOPE

**allowlist (수정 가능 — 4경로):**
`NAE/pipeline/registration/state/source_manifest.yaml` ·
`scripts/m2_source_registry_validator.py` ·
`tests/test_m2_source_registry_governance.py` ·
`docs/architecture/NAE-Manifest-Authority-SSOT.md`

**READ-ONLY 참조:** `docs/agents/cue/CUE-ADR030-M2-RAWPATH-CHECKSUM-TARGET-DETERMINATION.md`,
`docs/architecture/ADR-030-NAE-Sermon-Corpus-Governance.md`

**금지:** §2 HARD STOP 전부. 특히 content_genre/theological_category/tradition, M1/M3, writer/pipeline,
무관 미커밋 항목, TSU/Qdrant/retrieval/config.

---

## 9. TESTING & EVIDENCE (완료 후 전부 실행, raw 첨부)

```bash
source ~/envs/dbma311/bin/activate
python scripts/m2_source_registry_validator.py ; echo "exit=$?"
python -m pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py
python -c "import yaml,os; d=yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml')); \
print('records',len(d['sources'])); \
[print(s['source_id'], s['authority_class'], os.path.exists(s['raw_path']), os.path.exists(s['checksum_target'])) for s in d['sources']]"
git diff --stat -- NAE/pipeline/registration/state/source_manifest.yaml
git diff -- NAE/pipeline/registration/state/source_manifest.yaml | grep -E '^-[^-]' ; echo "removed-line count exit=$? (1 = none)"
git diff --stat
git status --short
```

**반드시 입증:**
- M2: `+42 / -0`. 14 레코드 전부 정확히 13키. `authority_class`/`raw_path`/`checksum_target` 값이 §3 표와 **완전 일치**.
- `raw_path` 14 + `checksum_target` 14 = 28 파일 전부 `os.path.exists() == True`.
- base 10키·값·레코드 순서·identity 불변 (removed-line 0).
- validator exit 0 (V4 14/14 valid, V5 실검사, V6 파일존재 14/14, V7 13키 whitelist).
- pytest FAIL/ERROR 0.
- content_genre/theological_category/tradition = M2 어디에도 없음.
- M1/M3 무변경. 무관 항목 미접촉.

---

## 10. SCOPE AUDIT

```
A-2b-1 변경만 (allowlist 4경로)
authority_class / raw_path / checksum_target = 14/14, 값 §3 일치
content_genre / theological_category / tradition = 0 (A-2b-2)
base 10키 무변경, 레코드 순서·identity 불변
M1 / M3 / writer / pipeline 무변경
TSU / Qdrant / retrieval / embedding / config 무접촉
무관 미커밋 항목 미접촉
```
하나라도 위반 → 중단, **RED** 보고.

---

## 11. REPORTING INTEGRITY

- raw command 출력 없는 PASS 주장 금지.
- backfill 값은 §3 표 verbatim — "대략" / "추정" 금지.
- 없는 테스트를 있다고 쓰지 마라 (A-2a 정정 때 지적된 패턴 재발 금지). 보고서 수치는 `grep -c`·`pytest` raw 로 뒷받침.
- CUE / C1 역할 혼동 금지. **보고서 author = C1.**
- **C1 self-PASS 는 승인 아님.** CUE 가 `44e1a18` 대비 독립 검증한다.

---

## 12. FINAL REPORT 구조

`output/ADR-030-Phase1A-A2b1-EXEC-REPORT.md` (author: C1)

1. Scope — A-2b-1 (authority_class + raw_path + checksum_target), 3필드만. content_genre/theological_category/tradition = 0.
2. M2 backfill — 14×3 삽입, `git diff --stat` raw (+42/-0), 값 대조 스크립트 raw (14 OK).
3. File existence — 28 파일 `os.path.exists` raw.
4. Validator — `python … validator.py` 전체 raw (exit 0), V4/V5/V6 문구.
5. Test delta — FLIP 2 + 신규 2 목록, `grep -c "def test_"` raw, `pytest -q` 전체 raw.
6. SSOT — 변경 절 diff raw.
7. Git evidence — `git diff --stat`, `git status --short` raw.
8. Production safety — TSU/Qdrant/Retrieval/embedding/config mutation = 없음.
9. Deferred — A-2b-2 (content_genre/theological_category/tradition, HQ 값 비준 대기), M1 archival (S-3),
   ADR-030 v2.1 §8.4 괄호 예시 정정 (RAWPATH 문서 §6).
10. Verdict — `A-2b-1 COMPLETE — READY FOR INDEPENDENT CUE REVIEW` / `A-2b-1 INCOMPLETE — RETURN`.

---

## 13. FINAL COMMAND

A-2b-1 = 3필드 backfill (§3 표 verbatim) + validator/test/SSOT 반영. 그 외 아무것도 안 함.
content_genre/theological_category/tradition 금지. M2 base 키 불변. M1/M3/writer/pipeline 불변.
구현 → §9 검증 → raw evidence → §12 FINAL REPORT. 완료 후 CUE 독립 검증.

END OF A-2b-1 EXEC ORDER
