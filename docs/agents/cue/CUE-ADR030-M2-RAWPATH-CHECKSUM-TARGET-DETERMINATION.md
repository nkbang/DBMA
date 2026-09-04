# CUE — ADR-030 M2 `raw_path` / `checksum_target` Forensic Determination

**작업명**: ADR-030 v2.1 Phase 1-A / A-2b — 실제 M2 14 레코드의 `raw_path` · `checksum_target` 확정
**작성자**: CUE (Independent Forensic Determination — 원본 artifact 직접 대조, 추측 없음)
**작성일**: 2026-08-27
**Mode**: FORENSIC · READ-ONLY · MEASURE → CROSS-CHECK → DETERMINE
**Mutation Budget**: Code 0 / Corpus 0 / RAW 0 / Canonical 0 / TSU 0 / Review 0 / Embedding 0 / Qdrant 0 / Manifest 0 / Registry 0 / Cache 0 / Git add·commit 0
**Baseline 문서**: `docs/agents/cue/CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md` (2026-08-27)

---

## 1. Executive Summary

ADR-030 v2.1 §12 M-2는 실제 M2(`NAE/pipeline/registration/state/source_manifest.yaml`, 14 레코드)에
`raw_path` · `checksum_target` 를 backfill하도록 요구한다. 이 두 값은 분류(classification)가 아니라
파일시스템 사실이므로 CUE가 forensic으로 확정한다.

**판정 결과 — 14/14 확정, BLOCK 0:**

| 항목 | 결과 |
|---|---|
| `checksum_target` 근거 | `NAE/pipeline/registration/state/raw_checksum_ledger.jsonl` — 14 레코드 전부 `preserve` + `reverify` 기록 |
| 원장 checksum ↔ M2 `raw_checksum` | **14/14 완전 일치** |
| `raw_path` 근거 | `NAE/corpus/canonical/<work>/canonical.json::source` + `normalize_report.json::source` — 14/14 확인 |
| 파일 존재 | `raw_path` 14개 파일 + `checksum_target` 14개 파일 전부 디스크에 존재 |
| **`raw_path` ≠ `checksum_target`** | **12 / 14** (Fuller Vol01–08, Smith Vol01–04) — **정상**, §5 참조 |
| ADR-030 v2.1 §8.4 텍스트 | 괄호 예시 **오류 발견** — §6, 별도 정정안 참조 |

---

## 2. Method & Evidence Sources

READ-ONLY 조사. 실측 소스 3종:

1. **`NAE/pipeline/registration/state/raw_checksum_ledger.jsonl`**
   — ADR-021 registration pipeline이 `preserve` / `reverify` 시 기록. 필드: `source_id`, `raw_path`(절대경로),
   `checksum`(sha256), `event`, `recorded_at`. 14 source 전부 다중 `reverify` 이벤트 존재, 전부 동일 해시
   → 무결성 안정. **이 원장의 `raw_path` = `checksum_target`** (해시가 계산된 파일).

2. **`NAE/corpus/canonical/<work>/canonical.json` + `normalize_report.json`**
   — 정규화 파이프라인(v2.0.0) 산출물. 최상위 `source` 필드 = canonical 생성에 실제 소비된 입력 종류
   (`hocr` / `ocr` / `djvu_xml`). **이 값 = ADR §8.4가 정의한 `raw_path`** ("canonical 생성에 실제 사용된 파일").
   canonical dir는 17개(= M2 14 + PBC1742 / PBC1765 / SLBC1689, 후자 3건은 M2 미등록).

3. **`NAE/pipeline/registration/state/source_manifest.yaml`** (실제 M2) — 기존 `raw_checksum` 대조용.

`source` → 파일명 매핑: `hocr` → `hocr.html` · `ocr` → `ocr.txt` · `djvu_xml` → `djvu.xml`.

---

## 3. Determination Table (14 records)

경로는 repo-relative. `checksum` = M2 `raw_checksum` = 원장 checksum (일치 확인됨).

| # | source_id | `raw_path` | `checksum_target` | `raw_checksum` (sha256) | rp≠ct |
|---|---|---|---|---|---|
| 1 | `BAP-CHURCH-DAGG-001` | `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html` | `NAE/corpus/raw/archive_org/church_order/Dagg_Church_Order/hocr.html` | `f515bb48e57425b95bdd83969e18844666e05ebc5c45389a8986966781c3493b` | — |
| 2 | `BAP-CHURCH-HISCOX` | `NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html` | `NAE/corpus/raw/archive_org/church_order/Hiscox_Standard_Manual/hocr.html` | `83ee409602520d60559edd74ecb935835b2d82722e2c02a2d5052f8a12ad1471` | — |
| 3 | `BAP-MISS-FULLER-VOL01` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol01/original.pdf` | `74416a8f10e1ff21b40876ea018d4a88afbbe55fd2c36ef7cc74af57ca40cb9f` | ✗ |
| 4 | `BAP-MISS-FULLER-VOL02` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol02/original.pdf` | `352d7edff567a4f979579847d56dc2586df17ec432362685394556d1051be408` | ✗ |
| 5 | `BAP-MISS-FULLER-VOL03` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol03/original.pdf` | `787e185cf4c25f1ce45ec2a9177b8e58f42de42b9ff1bc7eab0b2c8b7e2b18a1` | ✗ |
| 6 | `BAP-MISS-FULLER-VOL04` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol04/original.pdf` | `8f4ba47eb6db7f8ee6cccce97b2e4bd8c4e45493f0a7f3b901df0ce9dd4079af` | ✗ |
| 7 | `BAP-MISS-FULLER-VOL05` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol05/original.pdf` | `20da331a39a2f288f5782196fb7590f837178622cf98e606a70fe1558740e074` | ✗ |
| 8 | `BAP-MISS-FULLER-VOL06` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol06/original.pdf` | `95b2fe115f2098f37472d7a563de01ab9ca60eb30b6b0867c5a71eb6b318cef6` | ✗ |
| 9 | `BAP-MISS-FULLER-VOL07` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol07/original.pdf` | `78cd86c9d99f71a4e5ac80690dda4cc06ed63facf0ae11eec76f0da9b83a8fa0` | ✗ |
| 10 | `BAP-MISS-FULLER-VOL08` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/ocr.txt` | `NAE/corpus/raw/archive_org/missions/Fuller_Complete_Works_Vol08/original.pdf` | `bc66c8216ee8a6fa647b1699e033faa1dab398a08d2f7c17136fbe3e17726c8c` | ✗ |
| 11 | `BAP-REF-SMITH-VOL01` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol1/original.pdf` | `31694703c69334f924724f4b000c3b8f4888ba20d670a05edb9cc9d5b5ec83dd` | ✗ |
| 12 | `BAP-REF-SMITH-VOL02` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol2/original.pdf` | `18009c38fc6d1772471d4e79ca1a7ef59a90a05af10e35ae4c8b7806b154204c` | ✗ |
| 13 | `BAP-REF-SMITH-VOL03` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol3/original.pdf` | `fd540747b90caca5f42329abe284795e3bc605afb97d91f50dcdf93199f8f744` | ✗ |
| 14 | `BAP-REF-SMITH-VOL04` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/djvu.xml` | `NAE/corpus/raw/archive_org/reference/Smith_Bible_Dictionary_HackettAbbot_Vol4/original.pdf` | `c6388fe84707f30cddda485406a5684d2acf7c1bdd4a78172d74d269de3b81e5` | ✗ |

**요약**: `raw_path` = Dagg·Hiscox `hocr.html` / Fuller Vol01–08 `ocr.txt` / Smith Vol01–04 `djvu.xml`.
`checksum_target` = Dagg·Hiscox `hocr.html` / Fuller·Smith `original.pdf`.

---

## 4. Evidence Chain / Reproduction

```bash
# (1) checksum_target + M2 raw_checksum 대조 — 14/14 OK
cat NAE/pipeline/registration/state/raw_checksum_ledger.jsonl
python3 - <<'PY'
import re, json
m2 = open('NAE/pipeline/registration/state/source_manifest.yaml').read()
ids = re.findall(r'source_id: (\S+)', m2)
cks = dict(zip(ids, re.findall(r'raw_checksum: (\S+)', m2)))
led = {}
for line in open('NAE/pipeline/registration/state/raw_checksum_ledger.jsonl'):
    d = json.loads(line); led[d['source_id']] = (d['checksum'], d['raw_path'])
for sid in ids:
    lc, lp = led[sid]
    print(('OK  ' if cks[sid] == lc else 'MISMATCH ') + sid, '->', lp.split('archive_org/')[-1])
PY

# (2) raw_path — canonical build가 소비한 입력 종류
for d in NAE/corpus/canonical/*/; do
  python3 -c "import json,sys; p='$d/canonical.json';
d=json.load(open(p)); print('$d'.split('/')[-2], '->', d.get('source'))"
done
```

- 실행 결과: (1) 14행 전부 `OK`. (2) Dagg/Hiscox = `hocr`, Fuller01–08 = `ocr`, Smith01–04 = `djvu_xml`
  (PBC1742/PBC1765/SLBC1689은 M2 외).
- 파일 존재: `raw_path` 14 + `checksum_target` 14 전부 `os.path.exists() == True`.
- 참고 quirk: `Fuller_Complete_Works_Vol01..08/normalize_report.json` 의 `page_count` = 1
  (`ocr.txt`가 페이지 구분 없는 단일 연속 텍스트라서 — 결함 아님, 입력 형식 특성). Dagg/Hiscox/Smith는
  실제 페이지 수 기록됨.

---

## 5. `raw_path` ≠ `checksum_target` — 의도된 분리

14 레코드 중 12건(Fuller·Smith)에서 두 필드가 다르다. **정상이며, 두 필드를 신설한 이유가 바로 이것이다.**

- **`checksum_target`** = 무결성 검증 대상 = 아카이브 마스터 `original.pdf`. `raw_checksum`은 이 파일에 대해
  계산·재검증된다.
- **`raw_path`** = canonical 파이프라인이 실제로 읽은 파일 = archive.org가 PDF와 함께 배포하는 파생 텍스트
  (`ocr.txt` = archive.org OCR 평문, `djvu.xml` = 페이지 구조 OCR).
- Dagg·Hiscox는 canonical이 `hocr.html`을 소비했고 원장도 `hocr.html`을 해싱해 **두 필드가 우연히 동일**.

이 분리가 명시되지 않아, checksum(=PDF 기준)과 canonical 입력(=텍스트 파일)을 같은 파일로 착각한 것이
C1 "checksum mismatch" 오판의 원인이다 (Baseline forensic §3.2 — 결함 아님, hygiene).

---

## 6. ADR-030 v2.1 §8.4 텍스트 정정 필요

현재 §8.4 (commit `72b8357`, 276–277행):

> - `raw_path` : canonical 생성에 실제 사용된 파일 (Dagg/Hiscox = `hocr.html`, **Fuller/Smith = `original.pdf`**).
>   부재가 C1 "checksum mismatch" 오판 원인 (forensic §3.2 — 결함 아님, hygiene).
> - `checksum_target` : `raw_checksum`이 가리키는 파일.

**오류**: 괄호의 "Fuller/Smith = `original.pdf`"는 `raw_path`가 아니라 `checksum_target` 값이다.
canonical build provenance상 Fuller `raw_path` = `ocr.txt`, Smith `raw_path` = `djvu.xml`.
정의문("canonical 생성에 실제 사용된 파일")은 옳고, 괄호 예시만 틀렸다.

정정안 별도 제출됨 — §8.4 괄호를 본 문서 §3 판정표로 교체, `checksum_target`에 `original.pdf` 예시 추가,
"raw_path ≠ checksum_target은 정상" 명문화, §2.3 Decision History에 `v2.1a` 행 추가. 문서 전용, 코드·데이터 영향 0.

---

## 7. A-2b 투입

- 본 문서 §3 표의 `raw_path` · `checksum_target` 2열 = **CUE 확정값**. A-2b backfill 시 이 표에서 그대로 복사.
- 나머지 4필드(`authority_class`, `content_genre`, `theological_category`, `tradition`)는 **B-1 · B-2 HQ 비준 대기**.
  A-2b는 6필드 전체 확정 후 착수.
- 표기: repo-relative 권고. 원장은 절대경로 사용 — M2 writer(`manifest_writer.write_entry`)가 `yaml.safe_dump`으로
  문자열을 그대로 보존하므로 어느 쪽이든 내구성 문제 없음.
- 보존 불변식: 기존 10개 M2 필드(`source_id` `title` `author` `author_id` `work_id` `edition_id` `year`
  `license` `archive_source` `raw_checksum`) 및 14 레코드 identity 변경·삭제 금지.

---

## 8. Mutation Attestation

이 조사 및 문서 작성 과정에서 수행한 write: 본 파일 1건(`docs/agents/cue/` 신규, governance 기록).
그 외 Code / Corpus / RAW / Canonical / TSU / Embedding / Qdrant / Manifest(M1·M2·M3) / Registry / State store /
Git commit — **전부 0**. 조사 전후 `git status` 해시 불변 확인.
