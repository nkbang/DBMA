# C1 — ADR-030 v2.1 / A-2b-1 · TASK 1 ONLY (M2 backfill)

> **작성**: CUE · **선행**: A-2a VERIFIED, HEAD `44e1a18` (`dev/dbma-engine`)
> C1 이전 3회 시도 전부 **아무것도 기록 못 함** (출력 한도 / 잘못된 워크트리 / 중단).
> 이번 명령은 **TASK 1(M2 backfill) 단독**. TASK 2~4(validator/test/SSOT)는 이게 반영된 뒤 별도 발부.

---

## 0. 착수 전 필수 — Workspace Verification Gate (`.clinerules/dbma-engineering.md` §3.1)

**아래를 실행하고 원본 출력을 보고서에 그대로 붙여라:**
```bash
pwd
git rev-parse --show-toplevel
git rev-parse --abbrev-ref HEAD
git rev-parse --short HEAD
test -f NAE/pipeline/registration/state/source_manifest.yaml && echo "M2 EXISTS" || echo "M2 MISSING"
```
**기대값:** `--show-toplevel` = `/Users/David/DBMA` (`.claude/worktrees/...` 이면 잘못됨) ·
브랜치 = `dev/dbma-engine` · HEAD = `44e1a18` · `M2 EXISTS`.

**하나라도 불일치하면 편집하지 말고 즉시 중단·보고.**

무관 미커밋 항목(`NAE/smith_activation.py`, `ui/pages/chat.py`, `docs/STATE.md`, `test_seal_*`)이 트리에
남아 있다 — **stage·revert·수정 금지.**

---

## 1. OBJECTIVE

`NAE/pipeline/registration/state/source_manifest.yaml` (M2) 의 **14개 레코드 전부**에
`authority_class` · `raw_path` · `checksum_target` 3개 키를 추가한다. 그 외 아무것도 하지 않는다.

---

## 2. HARD STOP

- `content_genre` / `theological_category` / `tradition` **추가 금지** (= A-2b-2).
- M2 기존 10키(`source_id title author author_id work_id edition_id year license archive_source raw_checksum`)
  및 값·레코드 순서 **한 글자도 변경 금지**.
- 값 **추측 금지** — §3 표 verbatim 복사.
- **`yaml.safe_dump` 로 M2 를 재작성하지 마라** (folded title 문자열 reflow). **텍스트 삽입만.**
- M1 / M3 / `manifest_writer.py` / `pipeline.py` / 새 schema / `NAE/corpus/governance/` 금지.
- TSU / Qdrant / retrieval / embedding / `config.yaml` 무접촉.
- **`git add` / `git commit` 금지** (Task Order 가 커밋을 요청하지 않음).

---

## 3. BACKFILL TABLE (verbatim)

경로 = repo-relative. `raw_path` ≠ `checksum_target` (Fuller·Smith 12건) 은 **정상**.

| source_id | authority_class | raw_path | checksum_target |
|---|---|---|---|
| `BAP-CHURCH-DAGG-001` | `historical_witness` | `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html` | `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html` |
| `BAP-CHURCH-HISCOX` | `historical_witness` | `NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html` | `NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html` |
| `BAP-MISS-FULLER-VOL01` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/original.pdf` |
| `BAP-MISS-FULLER-VOL02` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/original.pdf` |
| `BAP-MISS-FULLER-VOL03` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/original.pdf` |
| `BAP-MISS-FULLER-VOL04` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/original.pdf` |
| `BAP-MISS-FULLER-VOL05` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/original.pdf` |
| `BAP-MISS-FULLER-VOL06` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/original.pdf` |
| `BAP-MISS-FULLER-VOL07` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/original.pdf` |
| `BAP-MISS-FULLER-VOL08` | `historical_witness` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/original.pdf` |
| `BAP-REF-SMITH-VOL01` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/original.pdf` |
| `BAP-REF-SMITH-VOL02` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/original.pdf` |
| `BAP-REF-SMITH-VOL03` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/original.pdf` |
| `BAP-REF-SMITH-VOL04` | `reference` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/original.pdf` |

Smith 디렉터리 = `Vol1..Vol4` (zero-pad 없음), Fuller = `Vol01..Vol08` (zero-pad). **표기 그대로.**

---

## 4. 삽입 방법

각 레코드의 **`raw_checksum:` 줄 바로 다음**에 3줄 삽입 (들여쓰기 `  ` 2칸, 기존 필드와 동일):
```yaml
  raw_checksum: <기존 값 그대로>
  authority_class: <표>
  raw_path: <표>
  checksum_target: <표>
```
- 값은 전부 plain scalar (따옴표 불필요).
- 14 레코드 전부. 누락·중복 금지. 기존 줄 수정 0.

**권장**: 아래 스크립트를 그대로 실행 (텍스트 삽입 방식, `yaml.safe_dump` 미사용):
```bash
python - <<'PY'
import re
P='NAE/pipeline/registration/state/source_manifest.yaml'
def fuller(n): b=f'NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol{n:02d}'; return ('historical_witness',f'{b}/ocr.txt',f'{b}/original.pdf')
def smith(n):  b=f'NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{n}'; return ('reference',f'{b}/djvu.xml',f'{b}/original.pdf')
T={
 'BAP-CHURCH-DAGG-001':('historical_witness','NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html','NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html'),
 'BAP-CHURCH-HISCOX':('historical_witness','NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html','NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html'),
 **{f'BAP-MISS-FULLER-VOL{i:02d}':fuller(i) for i in range(1,9)},
 **{f'BAP-REF-SMITH-VOL{i:02d}':smith(i) for i in range(1,5)},
}
lines=open(P).read().split('\n')
out=[]; cur=None
for ln in lines:
    out.append(ln)
    m=re.match(r'- source_id: (\S+)$', ln.strip())
    if m: cur=m.group(1)
    if ln.strip().startswith('raw_checksum:') and cur in T:
        a,r,c=T[cur]
        ind=ln[:len(ln)-len(ln.lstrip())]
        out += [f'{ind}authority_class: {a}', f'{ind}raw_path: {r}', f'{ind}checksum_target: {c}']
        cur=None
open(P,'w').write('\n'.join(out))
print('inserted')
PY
```

---

## 5. 필수 검증 (완료 후 전부 실행, raw 출력 첨부)

```bash
source ~/envs/dbma311/bin/activate

python - <<'PY'
import yaml, os
d=yaml.safe_load(open('NAE/pipeline/registration/state/source_manifest.yaml'))
S=d['sources']
def fuller(n): b=f'NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol{n:02d}'; return ('historical_witness',f'{b}/ocr.txt',f'{b}/original.pdf')
def smith(n):  b=f'NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol{n}'; return ('reference',f'{b}/djvu.xml',f'{b}/original.pdf')
E={
 'BAP-CHURCH-DAGG-001':('historical_witness','NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html','NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html'),
 'BAP-CHURCH-HISCOX':('historical_witness','NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html','NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html'),
 **{f'BAP-MISS-FULLER-VOL{i:02d}':fuller(i) for i in range(1,9)},
 **{f'BAP-REF-SMITH-VOL{i:02d}':smith(i) for i in range(1,5)},
}
BASE={'source_id','title','author','author_id','work_id','edition_id','year','license','archive_source','raw_checksum'}
ADD={'authority_class','raw_path','checksum_target'}
assert len(S)==14, len(S)
bad=0
for s in S:
    sid=s['source_id']; got=(s.get('authority_class'),s.get('raw_path'),s.get('checksum_target'))
    if got!=E[sid]: print('VALUE MISMATCH',sid,got,'!=',E[sid]); bad+=1
    if set(s)!=BASE|ADD: print('KEY MISMATCH',sid,sorted(set(s))); bad+=1
    for k in ('raw_path','checksum_target'):
        if not os.path.exists(s[k]): print('FILE MISSING',sid,k,s[k]); bad+=1
for f in ('content_genre','theological_category','tradition'):
    if any(f in s for s in S): print('FORBIDDEN',f,'present'); bad+=1
hw=sum(1 for s in S if s.get('authority_class')=='historical_witness')
rf=sum(1 for s in S if s.get('authority_class')=='reference')
print('distribution historical_witness/reference =',hw,'/',rf,'(expect 10/4)')
print('RESULT:', 'ALL 14 OK' if bad==0 else f'{bad} PROBLEM(S)')
PY

git diff --stat -- NAE/pipeline/registration/state/source_manifest.yaml
git diff -- NAE/pipeline/registration/state/source_manifest.yaml | grep -E '^-[^-]' ; echo "removed-line grep exit=$? (1 = zero removed = OK)"
python scripts/m2_source_registry_validator.py ; echo "validator exit=$?"
python -m pytest -q tests/test_m2_source_registry_governance.py tests/test_nae_corpus_reconcile.py 2>&1 | tail -8
git status --short
```

**입증 필수:**
- 검증 스크립트: `RESULT: ALL 14 OK`, distribution `10 / 4`.
- `git diff --stat` M2 = **`+42`, `-0`** (removed-line grep exit=1).
- validator exit 0. (V4 = "14 M2 records with authority_class — all valid", V6 는 shape 검사 수행.)
- pytest: **`test_pos_04_raw_path_optional` / `test_pos_05_checksum_target_optional` /
  `test_m2_records_only_known_keys` 3건 FAIL 예상** — TASK 3 에서 flip 하므로 **정상**.
  그 3건 외 FAIL/ERROR 는 0 이어야 한다. (FAIL 목록을 raw 로 첨부.)
- `git status --short` : M2 외 allowlist 파일 무변경, 무관 항목 미접촉, staged 없음.

---

## 6. FINAL REPORT

`output/ADR-030-Phase1A-A2b1-TASK1-REPORT.md` (author: C1):
1. **Workspace gate** — §0 명령 raw 출력.
2. **Backfill** — 삽입 방식, 검증 스크립트 raw (`ALL 14 OK`, `10/4`).
3. **Git evidence** — `git diff --stat` M2 raw (`+42/-0`), `git status --short` raw.
4. **Validator** — `python … validator.py` 전체 raw (exit 0).
5. **Pytest** — 전체 raw. 예상 FAIL 3건(pos_04/pos_05/known_keys)만 나왔는지 명시.
6. **Deferred** — TASK 2~4 (validator V5·V6, test flip+신규, SSOT), A-2b-2 (분류 3필드), M1 archival.
7. **Verdict** — `A-2b-1 TASK 1 COMPLETE — READY FOR CUE REVIEW` / `... INCOMPLETE — RETURN`.

C1 self-PASS 는 승인 아님. CUE 가 `44e1a18` 대비 §3 표 대조 재검증한다.

END OF A-2b-1 TASK 1 ORDER
