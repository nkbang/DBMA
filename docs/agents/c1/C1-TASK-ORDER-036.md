# C1 Task Order 036 — NAE-CORPUS-FIX-001: source_candidates.csv 데이터 정합성 복구

**상태**: 발급됨 — 구현 착수 가능
**우선순위**: P0 (다음 단계인 NAE-SOURCE-DEDUP-001, RAW Acquisition의 선행 조건)
**대상 파일**: `resources/theological_sources/baptist/source_candidates.csv` (수정 대상)
**참고 파일 (읽기 전용)**: `resources/theological_sources/baptist/source_manifest.yaml`, `scripts/source_validator.py`, `docs/NAE_SOURCE_REGISTRY_REPORT.md`(문제 발견 경위 기록됨)
**모드 제약**: `resources/theological_sources/baptist/source_manifest.yaml`은 절대 수정하지 말 것 — 이번 작업은 CSV만 고친다. manifest의 JS1608 항목(`license: unknown`, `status: verification_pending`)은 CUE가 의도적으로 보수적으로 기록한 값이며, CSV가 고쳐진 뒤에도 manifest 갱신 여부는 별도 CUE 작업(TASK 4에서 "기존 manifest와 비교"만 하고 직접 덮어쓰지 말 것).

---

## 1. 배경

`resources/theological_sources/baptist/source_candidates.csv`는 NAE-SOURCE-003(source_manifest.yaml 생성) 작업의 입력 파일이다. CUE가 `csv.DictReader`로 파싱하며 확인한 결과:

- `SLBC1689`, `NHBC1833` 두 행은 `notes` 컬럼 안에 이스케이프(따옴표 처리)되지 않은 쉼표가 있어 `DictReader` 기준 초과 필드가 발생한다. 내용 손실은 없고 `notes` 텍스트가 여러 필드로 쪼개질 뿐이라 **무해**하지만, CSV 표준을 어긴 상태다.
- **`JS1608` 행은 심각하다.** `language` 컬럼 값(`English`) 뒤에 이스케이프되지 않은 `Dutch`라는 토큰이 추가로 붙어 있어, 그 뒤의 모든 컬럼이 한 칸씩 밀려 파싱된다:
  - 헤더 기준 `license` 위치에 실제로는 `Dutch`가 들어감(잘못됨)
  - 헤더 기준 `availability` 위치에 실제로는 `public_domain_possible`이 들어감(이것이 원래 `license` 값으로 추정됨)
  - `source_location`/`priority`도 각각 한 칸씩 밀려 있음

CUE는 이 문제를 우회하기 위해 `source_manifest.yaml`의 JS1608 항목에 `license: unknown`을 보수적으로 기록하고 `status: verification_pending`으로 등록해두었다. 이번 작업은 **원인(CSV)을 고치는 것**이다.

## 2. 작업 범위

### TASK 1 — CSV quoting 오류 수정

`source_candidates.csv`의 다음 행을 RFC 4180 표준(값에 쉼표가 포함되면 큰따옴표로 감싸기)에 맞게 수정한다:

1. **JS1608 행**: `language` 컬럼 값을 확인·수정. CSV 원문 의도를 다음 두 가지 중 하나로 판단해 정리할 것:
   - (a) `language` 값이 실제로는 "English, Dutch"(두 언어 병기)였고 콤마가 값 안에 있었다면 → `"English, Dutch"`로 큰따옴표 처리
   - (b) `Dutch`가 별도 의미 없는 오기(誤記)라면 → 제거하고 `language`는 `English`만 유지
   - 어느 쪽인지 불확실하면 **추정하지 말고** CUE에게 보고(TASK 4)하여 판단을 넘길 것 — 이 CSV는 침례교 사료 서지정보이므로 임의 수정 금지
   - 수정 후 해당 행의 `license`/`availability`/`source_location`/`priority` 컬럼이 원래 의도한 값(license는 "public_domain_possible"로 추정되나 재확인 필요)으로 올바르게 정렬되는지 확인
2. **SLBC1689, NHBC1833 행**: `notes` 컬럼 값 전체를 큰따옴표로 감싸 쉼표를 이스케이프한다. 텍스트 내용은 한 글자도 변경하지 말 것 — 순수하게 quoting만 추가.
3. 다른 행(PBC1742/BFM2000/TH1612/AF1815)은 이번 조사에서 문제가 발견되지 않았으나, 혹시 유사한 미이스케이프 쉼표가 있는지 전체 파일을 한 번 더 훑어 확인할 것.

### TASK 2 — columns alignment 검증

수정 후 Python `csv.DictReader`로 전체 파일을 다시 파싱하여 각 행이 헤더와 동일한 개수의 필드를 갖는지 확인한다. 예:

```python
import csv
with open("resources/theological_sources/baptist/source_candidates.csv") as f:
    reader = csv.DictReader(f)
    header_len = len(reader.fieldnames)
    for row in reader:
        extra = row.get(None)  # DictReader가 초과 필드를 여기 담는다
        if extra:
            print(f"[FAIL] {row.get('source_id')}: 초과 필드 {len(extra)}개 — {extra}")
        else:
            print(f"[PASS] {row.get('source_id')}: {header_len}개 필드 정상")
```

전체 7행이 `[PASS]`가 될 때까지 반복 수정한다.

### TASK 3 — validator 재실행

`scripts/source_validator.py`(CUE가 이미 구현·커밋한 스크립트, 수정하지 말 것)를 재실행해 기존 `source_manifest.yaml`이 여전히 PASS 상태인지 확인한다:

```bash
python scripts/source_validator.py
```

이번 작업은 CSV만 고치므로 manifest는 그대로 PASS=21/WARNING=0/FAIL=0이 유지되어야 정상이다(참고용 확인, manifest 자체는 건드리지 않으므로 결과가 바뀌면 안 됨 — 바뀐다면 그 자체가 이상 신호이니 보고할 것).

### TASK 4 — 기존 manifest와 비교

CSV 수정 후 JS1608의 올바른 값(특히 `license`)이 무엇으로 밝혀졌는지, 현재 `source_manifest.yaml`의 JS1608 항목(`license: unknown`)과 비교해 **차이가 있으면 명시적으로 보고**한다. **manifest 파일 자체는 수정하지 말 것** — 그 판단과 실행은 CUE가 이 보고를 받은 뒤 별도로 수행한다.

## 3. 완료 보고 형식

다음 형식으로 보고할 것:

```
STATUS: PASS / BLOCKED

수정 전/후 diff:
(git diff 또는 해당 행 전/후 텍스트)

CSV validation 결과:
(TASK 2 스크립트 출력, 7행 전부 PASS 여부)

JS1608 최종 metadata:
- language: ?
- license: ? (CSV에서 실제로 의도했던 값)
- availability: ?
- source_location: ?
- priority: ?
- (TASK 1에서 (a)/(b) 중 어느 쪽으로 판단했는지, 그리고 그 근거)

기존 manifest와의 차이점:
(source_manifest.yaml의 JS1608 license=unknown과 비교해 차이 명시)
```

## 4. 금지 사항

- `resources/theological_sources/baptist/source_manifest.yaml` 수정 금지
- `scripts/source_validator.py` 수정 금지
- CSV의 서지정보 내용(제목/저자/연도/notes 텍스트) 임의 변경 금지 — quoting/정렬만 수정
- git commit 금지 (CUE 검토 후 별도 승인)
