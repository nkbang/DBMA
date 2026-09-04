# C1 — ADR-030 v2.1 / A-2b-2 EXEC ORDER (classification backfill)

> **작성**: CUE (HQ A-2b-2 EXECUTION ORDER 의도 + CUE 점검 F-1~F-5 반영)
> **선행**: A-2b-1 VERIFIED/CLOSED — commit `1fa6fce` (`dev/dbma-engine`)
> **분류 권위**: `docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` — **RATIFIED v1.1** §4.1
> **범위**: M2 Source Registry additive metadata (`content_genre`·`theological_category`·`tradition`) 뿐

---

## 0. 착수 전 — Workspace Verification Gate (`.clinerules/dbma-engineering.md` §3.1)

```bash
pwd
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
python -c "import yaml;d=yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml'));print('records',len(d['sources']),'authority_class',sum(1 for s in d['sources'] if 'authority_class' in s))"
```
**기대**: `--show-toplevel` = `/Users/David/DBMA` (`.claude/worktrees/...` 이면 잘못됨) · `dev/dbma-engine` ·
`1fa6fce` · `records 14 authority_class 14`. 하나라도 불일치 → 편집 금지, 즉시 중단·보고.

무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`) — stage·revert·수정 금지.

---

## 1. MANDATE

RATIFIED v1.1 §4.1 의 `A2B2` dict 를 M2 14 레코드에 적용하고, 그 반영을 validator/test/SSOT 에 갱신한다.
§4.1 은 **유일 분류 권위**다. 어떤 레코드도 재해석·개선·확장·정규화·재분류하지 마라.
**다른 분류가 더 적절해 보인다는 이유로 값을 바꾸지 마라.**

---

## 2. HARD STOP

- **vocab 확장 금지**: `content_genre` / `theological_category` / `tradition` 에 §3 미포함 값(예: `reference`)
  신설 금지.
- **required 승격 금지**: 세 필드는 additive 유지 (`required: false`, WARNING-first).
- **Smith 예외**: `BAP-REF-SMITH-VOL01~04` 에 `tradition` 을 넣지 마라.
- **생략은 생략으로**: `theological_category` 없는 9 레코드에 `theological_category:` 를 빈 값 / `null` /
  `[]` / placeholder 로 넣지 마라. **키 자체를 넣지 않는다.** `A2B2` 의 `None` = 키 미삽입.
- **M2 round-trip 금지**: `yaml.safe_load → yaml.safe_dump` 로 M2 재작성 금지 (folded title reflow). **텍스트 삽입만.**
- **base/A-2b-1 필드 불변**: source_id, author/work/edition identity, `raw_checksum`, `raw_path`,
  `checksum_target`, `authority_class`, 레코드 순서 — 한 글자도 변경 0.
- **무관 mutation 금지**: M1 · M3 · production retrieval · embedding/vector store · TSU dataset ·
  ADR-030 무관 절 · 무관 테스트 · `manifest_writer.py` · `pipeline.py` · 새 schema 파일.
- **`git add` / `git commit` 금지.** CUE 독립검증 후 CUE 가 단일 커밋(§11).

**allowlist (수정 가능 — 4파일):**
`NAE/pipeline/registration/state/source_manifest.yaml` · `scripts/m2_source_registry_validator.py` ·
`tests/test_m2_source_registry_governance.py` · `docs/architecture/NAE-Manifest-Authority-SSOT.md`
(커밋 시 `docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` 도 포함되나 **C1 은 이 파일을 수정하지 않는다** — CUE 가 stage.)

---

## 3. RATIFIED §4.1 — `A2B2` (verbatim)

`None` = 해당 키를 레코드에 넣지 않는다. **이 표를 그대로 소비한다.**

```python
A2B2 = {
 "BAP-CHURCH-DAGG-001":  {"content_genre": ["church_practice"],              "theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
 "BAP-CHURCH-HISCOX":    {"content_genre": ["church_practice", "pastoral"],  "theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL01":{"content_genre": ["theology"],                     "theological_category": ["soteriology"],  "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL02":{"content_genre": ["theology"],                     "theological_category": ["soteriology"],  "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL03":{"content_genre": ["theology"],                     "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL04":{"content_genre": ["theology"],                     "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL05":{"content_genre": ["commentary"],                   "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL06":{"content_genre": ["commentary"],                   "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL07":{"content_genre": ["sermon"],                       "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL08":{"content_genre": ["theology", "sermon", "mission"],"theological_category": ["missions"],     "tradition": "Particular Baptist"},
 "BAP-REF-SMITH-VOL01":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL02":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL03":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL04":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
}
```
읽기 원본은 `CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` §4.1 — 위와 동일해야 한다 (착수 시 대조).

**Ratified vocab (§3 of rule doc):**
- `content_genre` ∈ {`confession`, `theology`, `history`, `commentary`, `sermon`, `mission`, `church_practice`, `pastoral`}
- `theological_category` ∈ {`confession`, `ecclesiology`, `soteriology`, `missions`}
- `tradition` ∈ {`"Particular Baptist"`, `"American Baptist"`, `"Baptist Evangelical"`}

**Record-level 분포 (검증 게이트 기준 — 값별 카운트 아님):**
`content_genre` = **14/14** · `theological_category` = **5/14** · `tradition` = **10/14** ·
삽입 = **+29 lines / −0**.

---

## 4. TASK 1 — M2 backfill

**대상**: `NAE/pipeline/registration/state/source_manifest.yaml`

각 레코드의 **`checksum_target:` 줄 바로 다음**에, `A2B2[sid]` 의 non-`None` 필드를 **이 순서로** 삽입
(들여쓰기 `  ` 2칸):
```yaml
  checksum_target: <기존 값 그대로>
  content_genre: [<v>, ...]          # flow list, 항상
  theological_category: [<v>, ...]   # A2B2 값이 None 이면 이 줄 생략
  tradition: "<value>"               # A2B2 값이 None 이면 이 줄 생략
```
- `content_genre` / `theological_category` = **flow list 한 줄** (`[church_practice, pastoral]`). block style 금지.
- `tradition` = 따옴표 문자열 (`tradition: "Particular Baptist"`).
- `None` 필드는 줄을 만들지 않는다.
- 기존 줄 수정 0. 삭제 0.

**권장 스크립트** (텍스트 삽입, `yaml.safe_dump` 미사용):
```bash
python - <<'PY'
import re
P='NAE/pipeline/registration/state/source_manifest.yaml'
A2B2 = {
 "BAP-CHURCH-DAGG-001":  {"content_genre": ["church_practice"],              "theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
 "BAP-CHURCH-HISCOX":    {"content_genre": ["church_practice", "pastoral"],  "theological_category": ["ecclesiology"], "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL01":{"content_genre": ["theology"],                     "theological_category": ["soteriology"],  "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL02":{"content_genre": ["theology"],                     "theological_category": ["soteriology"],  "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL03":{"content_genre": ["theology"],                     "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL04":{"content_genre": ["theology"],                     "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL05":{"content_genre": ["commentary"],                   "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL06":{"content_genre": ["commentary"],                   "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL07":{"content_genre": ["sermon"],                       "theological_category": None,             "tradition": "Particular Baptist"},
 "BAP-MISS-FULLER-VOL08":{"content_genre": ["theology", "sermon", "mission"],"theological_category": ["missions"],     "tradition": "Particular Baptist"},
 "BAP-REF-SMITH-VOL01":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL02":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL03":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
 "BAP-REF-SMITH-VOL04":  {"content_genre": ["commentary"],                   "theological_category": None,             "tradition": None},
}
lines=open(P).read().split('\n'); out=[]; cur=None
for ln in lines:
    out.append(ln)
    m=re.match(r'- source_id: (\S+)$', ln.strip())
    if m: cur=m.group(1)
    if ln.strip().startswith('checksum_target:') and cur in A2B2:
        e=A2B2[cur]; ind=ln[:len(ln)-len(ln.lstrip())]
        out.append(f"{ind}content_genre: [{', '.join(e['content_genre'])}]")
        if e['theological_category'] is not None:
            out.append(f"{ind}theological_category: [{', '.join(e['theological_category'])}]")
        if e['tradition'] is not None:
            out.append(f'{ind}tradition: "{e["tradition"]}"')
        cur=None
open(P,'w').write('\n'.join(out))
print('inserted')
PY
```

---

## 5. TASK 2 — validator

**대상**: `scripts/m2_source_registry_validator.py`

`check_new_field_definitions` (V6) 를 확장한다. **§4.1 표(레코드별 값)를 validator 에 하드코딩하지 마라** —
vocab + shape + 파일존재만. 레코드별 정확값은 test(§6)에서 검증.

- `content_genre` 존재 시: `list`, 모든 원소가 위 8-vocab 안. 아니면 FAIL.
- `theological_category` 존재 시: `list`, 모든 원소가 4-vocab 안. 아니면 FAIL.
- `tradition` 존재 시: `str`, 3-vocab 안. 아니면 FAIL.
- 기존 V6 shape 검사 + `raw_path`/`checksum_target` 파일존재 검사 **유지**.
- V4 (authority_class enum), V5 (합성 레코드 optionality 실검사), V7 (13→가변 키 whitelist),
  V1~V3, V8 — **약화·우회 금지**. `SCHEMA_PATH` 재도입 금지. synthetic-only 검증 금지 — 실 M2 레코드를 검사.

V7 `check_m2_identity` 의 key-whitelist: `known_keys = M2_BASE_KEYS | ADR030_ADDITIVE_FIELDS` 는 이미
6필드를 포함하므로 그대로 통과. (13키 고정 assert 가 있으면 제거하고 `issubset(known_keys)` 만 유지.)

검증: `python scripts/m2_source_registry_validator.py` → exit 0, 0 FAIL.
`grep -n "SCHEMA_PATH\|source_manifest.schema\|assert len(sources)" scripts/m2_source_registry_validator.py` → 0줄.

---

## 6. TASK 3 — test

**대상**: `tests/test_m2_source_registry_governance.py`

### FLIP (precondition 변경 — weakening 아님, A-2b-1 의 pos_04/05 FLIP 과 동일)
| 현재 | 조치 |
|---|---|
| `test_pos_01_content_genre_optional` (`assert not has_cg`) | **→ `test_pos_01_content_genre_present`**: 14 레코드 전부 `content_genre` 가 non-empty list, 원소 ∈ 8-vocab |
| `test_pos_02_theological_category_optional` (`assert not has_tc`) | **→ `test_pos_02_theological_category_present_where_ratified`**: `theological_category` 가진 레코드는 non-empty list + 4-vocab; **정확히 5 레코드**만 보유 |
| `test_pos_03_tradition_optional` (`assert not has_t`) | **→ `test_pos_03_tradition_present_where_ratified`**: `tradition` 가진 레코드는 3-vocab; **정확히 10 레코드**; `BAP-REF-SMITH-VOL0[1-4]` 는 **미보유** |

### UPDATE
- `test_m2_records_only_known_keys`: `assert keys == expected_13` 류 고정 assert 제거 →
  `assert keys.issubset(base | additive_6)` + `{"authority_class","raw_path","checksum_target","content_genre"}.issubset(keys)` (A-2b-1 3 + A-2b-2 필수 content_genre).

### 신규 (`TestM2KeyGovernance` 에)
```python
    def test_classification_matches_a2b2_v1_1(self):
        """content_genre/theological_category/tradition 이 RATIFIED §4.1 A2B2 와 정확히 일치."""
        A2B2 = {  # CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md §4.1 verbatim
            "BAP-CHURCH-DAGG-001": (["church_practice"], ["ecclesiology"], "Particular Baptist"),
            "BAP-CHURCH-HISCOX": (["church_practice", "pastoral"], ["ecclesiology"], "Particular Baptist"),
            "BAP-MISS-FULLER-VOL01": (["theology"], ["soteriology"], "Particular Baptist"),
            "BAP-MISS-FULLER-VOL02": (["theology"], ["soteriology"], "Particular Baptist"),
            "BAP-MISS-FULLER-VOL03": (["theology"], None, "Particular Baptist"),
            "BAP-MISS-FULLER-VOL04": (["theology"], None, "Particular Baptist"),
            "BAP-MISS-FULLER-VOL05": (["commentary"], None, "Particular Baptist"),
            "BAP-MISS-FULLER-VOL06": (["commentary"], None, "Particular Baptist"),
            "BAP-MISS-FULLER-VOL07": (["sermon"], None, "Particular Baptist"),
            "BAP-MISS-FULLER-VOL08": (["theology", "sermon", "mission"], ["missions"], "Particular Baptist"),
            "BAP-REF-SMITH-VOL01": (["commentary"], None, None),
            "BAP-REF-SMITH-VOL02": (["commentary"], None, None),
            "BAP-REF-SMITH-VOL03": (["commentary"], None, None),
            "BAP-REF-SMITH-VOL04": (["commentary"], None, None),
        }
        S = {s["source_id"]: s for s in _load_yaml(M2_PATH)["sources"]}
        assert set(S) == set(A2B2)
        for sid, (cg, tc, tr) in A2B2.items():
            r = S[sid]
            assert r.get("content_genre") == cg, sid
            assert r.get("theological_category") == tc, sid   # None → 키 부재
            assert r.get("tradition") == tr, sid
        assert sum(1 for s in S.values() if "content_genre" in s) == 14
        assert sum(1 for s in S.values() if "theological_category" in s) == 5
        assert sum(1 for s in S.values() if "tradition" in s) == 10

    def test_no_unratified_classification_vocab(self):
        CG = {"confession","theology","history","commentary","sermon","mission","church_practice","pastoral"}
        TC = {"confession","ecclesiology","soteriology","missions"}
        TR = {"Particular Baptist","American Baptist","Baptist Evangelical"}
        for s in _load_yaml(M2_PATH)["sources"]:
            for v in s.get("content_genre", []): assert v in CG, (s["source_id"], v)
            for v in s.get("theological_category", []): assert v in TC, (s["source_id"], v)
            if "tradition" in s: assert s["tradition"] in TR, (s["source_id"], s["tradition"])
```

### 유지 (그대로 통과해야)
`test_pos_04_raw_path_present` · `test_pos_05_checksum_target_present` · `test_pos_06_*` · `test_pos_07_*` ·
`test_authority_class_matches_adr030_7_3` · `test_raw_path_checksum_target_files_exist` ·
`test_validator_has_no_schema_path` · neg_* · iso_* · int_* · reconcile 15.
**green 얻으려고 기존 assertion 약화 금지.**

검증: `pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py` → FAIL/ERROR 0.

---

## 7. TASK 4 — SSOT

**대상**: `docs/architecture/NAE-Manifest-Authority-SSOT.md` — "Additive metadata" 절만.

- 절 제목: `**A-2b-1 완료 / A-2b-2 PENDING**` → `**A-2b 완료 (A-2b-1 + A-2b-2)**`.
- `content_genre` 행 → `**populated 14/14 (A-2b-2)**` — 값 per RATIFIED v1.1 §4.1.
- `theological_category` 행 → `**populated 5/14 (A-2b-2)**` — ecclesiology×2, soteriology×2, missions×1. 나머지 9 키 생략.
- `tradition` 행 → `**populated 10/14 (A-2b-2)**` — `"Particular Baptist"` ×10. Smith×4 키 생략.
- "M2 레코드 키 = 13" 줄 → "M2 레코드 키 = **14~16** (base 10 + authority_class + raw_path + checksum_target
  + content_genre + [theological_category 5건] + [tradition 10건]). 분류 권위 =
  `docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` (RATIFIED v1.1)."
- **분류표를 SSOT 에 복제하지 마라** — rule doc 이 authority. 참조만.
- 다른 절(§2-1 판정 등) 무변경.

---

## 8. VALIDATION GATE (완료 후 전부 실행, raw 첨부)

```bash
source ~/envs/dbma311/bin/activate
python scripts/m2_source_registry_validator.py ; echo "exit=$?"
grep -n "SCHEMA_PATH\|source_manifest.schema\|assert len(sources)" scripts/m2_source_registry_validator.py ; echo "grep exit=$?"
python -m pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py
grep -c "    def test_" tests/test_m2_source_registry_governance.py
python - <<'PY'
import yaml
S=yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml'))['sources']
print('records', len(S))
print('content_genre', sum(1 for s in S if 'content_genre' in s), '/14  (expect 14)')
print('theological_category', sum(1 for s in S if 'theological_category' in s), '/14  (expect 5)')
print('tradition', sum(1 for s in S if 'tradition' in s), '/14  (expect 10)')
print('smith tradition keys:', [s['source_id'] for s in S if s['source_id'].startswith('BAP-REF-SMITH') and 'tradition' in s], '(expect [])')
PY
git diff --stat -- NAE/pipeline/registration/state/source_manifest.yaml
git diff -- NAE/pipeline/registration/state/source_manifest.yaml | grep -E '^-[^-]' ; echo "removed grep exit=$? (1 = zero removed)"
git diff --stat
git status --short
```

**입증 필수 (record 단위 — 값별 카운트로 판정하지 마라):**
- `content_genre = 14/14` · `theological_category = 5/14` · `tradition = 10/14`
- Smith VOL01~04 `tradition` 키 **부재**
- M2 `git diff --stat` = **`+29`, `-0`** (removed grep exit=1)
- validator exit 0, 0 FAIL. `grep` 0줄.
- pytest FAIL/ERROR 0. governance ≈ 30 (27 + 신규 2 + FLIP/UPDATE 카운트 불변… FLIP 은 rename 이므로 27+2=29~30).
- `test_classification_matches_a2b2_v1_1` PASS (§4.1 verbatim 대조).
- base 10키 + authority_class/raw_path/checksum_target 값 무변경 (removed-line 0).
- M1 / M3 / production / 무관 파일 무변경. staged 없음.

---

## 9. FAILURE POLICY

§4.1 ↔ 구현 ↔ validator ↔ test ↔ 결과 Registry 사이에 불일치 발견 시 → **STOP.** 조용히 화해시키지 마라.
정확한 충돌을 보고하고 HQ/CUE 결정을 기다린다.
무관한 기존 사유로 테스트가 깨지면, green 얻으려고 무관 코드 수정하지 마라.
`test_pos_01/02/03` 의 FLIP 은 **승인된 변경** (precondition 이 바뀜) — 이건 STOP 사유 아님.

---

## 10. COMMIT — C1 은 커밋하지 않는다

`git add` / `git commit` 금지. CUE 가 `1fa6fce` 대비 독립검증 후 **단일 커밋**:
`M2 + validator + tests + SSOT + docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md`.
A-2b-1(`1fa6fce`) 재커밋·amend 없음. `dev/dbma-engine` history rewrite 없음.
커밋 메시지 주제: `A-2b-2: apply RATIFIED v1.1 classification to M2 source registry`.

---

## 11. OUTPUT — `output/ADR-030-Phase1A-A2b2-EXEC-REPORT.md` (author: C1)

1. Workspace gate raw. 2. files changed. 3. exact mutation summary (`+29/-0`, 필드별 라인수 14/5/10).
4. validator result (전체 raw, exit 0). 5. test result (`pytest -q` 전체 raw, `grep -c def test_`).
6. classification distribution (§8 스크립트 raw — 14/5/10, Smith tradition []).
7. scope verification (`git diff --stat`, `git status --short` raw; M1/M3/production 무변경).
8. §4.1 로부터의 deviation = **없음** (있으면 정확히 명시하고 §9 STOP).

speculative commentary·새 분류 제안·ADR-030 재설계 금지. C1 self-PASS 는 승인 아님 — CUE 재검증.

END OF A-2b-2 EXEC ORDER
