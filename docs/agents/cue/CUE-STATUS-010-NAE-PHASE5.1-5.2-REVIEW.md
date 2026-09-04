# CUE Status Report — HQ-CUE-DIRECTIVE-NAE-STATUS-010

작성일: 2026-07-31
모드: `LOCAL EVIDENCE REVIEW` (GITHUB VERIFIED 아님 — GitHub 독립 감사는 P1 담당)
역할 경계 준수: pytest 재실행/소스 재조회/다운로드/코드 수정/commit/push 전혀 수행하지 않음. 파일 읽기·해시 계산·git 상태 조회만 수행.

**참고**: 지시서 §4(Required Review Questions)가 "### A. Phase 5.1 — Retrieval Bench" 이후 잘려 전달됨 — 이하 답변은 §1 Mission의 4개 질문 기준으로 작성했으며, §4의 구체 질문이 별도로 있다면 재전달 요청.

---

## Q1. 현재 실제로 완료된 작업은 무엇인가

### Phase 5.1 — Benchmark Contract: 코드/테스트 레벨 완료, 실데이터 레벨 미완료

- `evidence/phase5_1_remediation_004/C1-REMEDIATION-004-FINAL-REPORT.md`의 4개 위반 항목(zero-gold count 미배선, 비정규 gold 문자열, empty/duplicate gold 검증 누락, precision 분모 버그) 수정 주장을 **`pytest-full.txt` 원본 출력으로 대조 확인** — "31 passed in 0.04s", "Exit code: 0"과 정확히 일치. **이 패키지는 자기모순 없이 신뢰 가능**.
- `NAE/benchmark/{__init__,evaluator,loader,metrics,runner,schema}.py`가 실제로 working tree에 수정되어 있음(`git diff --stat` 확인, +848/-325줄 걸쳐 11개 파일).
- **그러나** `benchmark_v1.jsonl`은 final-report.md 자신이 명시: "total entries: 5, valid non-empty gold_tsu_ids: 0, INVALID_GOLD: 5" — 즉 **benchmark 코드는 동작하지만 실제 평가 가능한 gold 데이터는 0건**.

### Phase 5.2 — Corpus/Provenance: PBC1765 원문 4~5개 파일이 quarantine에 실존, canonical 미승인

- `NAE/corpus/quarantine/PBC1765/original/`에 실제 파일 5개 존재(직접 `ls -la`로 확인): `confeo00phil.pdf`(8.2MB), `confeo00phil_djvu.txt`, `confeo00phil_scandata.xml`, `confeo00phil_hocr_searchtext.txt.gz`, `confeo00phil_hocr.html`(3.7MB).
- `canonical_admission: NOT_AUTHORIZED`(provenance.json)로 명시 — **아직 canonical corpus로 승격되지 않음**, quarantine 단계에 정확히 머물러 있음(C1이 스스로 이 경계를 지킨 점은 확인됨).
- `NAE/corpus/canonical/PBC1742/normalize_report.json` 존재 — PBC1742(legacy id)는 이미 canonical 정규화 단계까지 진행된 것으로 보이나, 이번 리뷰 범위(§3 Evidence Scope)상 이 파일 내용까지 상세 대조하지는 않음 — **추가 확인 필요 항목으로 남김**.

---

## Q2. 각 Phase의 완성도는 어느 정도인가

| Phase | 완성도 (evidence 기준) | 근거 |
|---|---|---|
| 5.1 Benchmark Contract (코드) | **완료로 판단 가능** | pytest 31/31 원본 로그와 최종보고서 일치, 자기모순 없음 |
| 5.1 Benchmark Contract (실데이터/Gold) | **미완료 — 골격만 존재** | `benchmark_v1.jsonl` 5건 전부 INVALID_GOLD(원 스켈레톤); `gold_benchmark_v1.jsonl` 5건은 채워져 있으나 **아래 Q3에서 다루는 검증되지 않은 ID 포함** |
| 5.2 Source Acquisition (PBC1765) | **Stage A/B 실행 완료, HQ 결정 대기 — 단 아래 결함 존재** | 파일 실존 확인, 그러나 evidence 내부 모순 다수(아래 Findings) |
| 5.2 Canonical Admission | **미착수(의도적)** | `canonical_admission: NOT_AUTHORIZED` 명시, 경계 준수 확인 |
| 5.2 Corpus Indexing / Qdrant | **미착수** | `gold-authoring-skeleton-report.md` 자체가 "BLOCKED — corpus indexing 필요"로 명시, 별도 파일 존재 확인 안 함(범위 밖) |

---

## Q3. 어떤 차단 요인이 해소되었고, 어떤 차단 요인이 남았는가

### 해소된 차단 요인

- Phase 5.1의 4개 계약 위반(HQ-C1-DIRECTIVE-004) — 원본 pytest 로그 대조로 해소 확인
- PBC1765 identifier 문제(Acquire-008에서 `plainbookofconfe00phil` 거부 → Acquire-009에서 `confeo00phil`로 preflight 통과) — Stage A 7개 조건 판정표(`stage-a-preflight-decision.md`) 확인, 형식상 PASS

### 남은/신규 차단 요인 (이번 검토에서 확인된 증거 기반 findings)

아래는 각각 CUE Finding Standard(Claim/Evidence/Path/Severity/Why/Corrective/Owner)로 기록.

---

#### Finding 1 — manifest.json의 SHA256 값이 실제 파일 및 다른 증거 파일과 불일치 (HIGH)

- **Claim reviewed**: `evidence/phase5_2/pbc1765_acquire_009/manifest.json`의 `quarantined_artifacts[].sha256` 값이 아티팩트의 정확한 해시라는 주장
- **Evidence inspected**: 동일 파일에 대해 `manifest.json`, `provenance.json`, `stage-b-artifact-integrity.csv` 3곳의 SHA256 값을 대조하고, `shasum -a 256`으로 실제 파일 해시를 직접 계산
- **Exact path**: `evidence/phase5_2/pbc1765_acquire_009/manifest.json` (예: PDF 항목 `"sha256": "c3c54102e7e36f4a4e0c0e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e6cabd"`) vs 실제 계산값 `c3c54102e3d207731cb9d8bc19075c98e373fb492cd2b03912dc0b6b24f6cabd`(이 값은 `provenance.json`, `stage-b-artifact-integrity.csv`와 정확히 일치)
- **Severity**: HIGH — 4개 아티팩트 전부의 manifest.json 해시가 실제값과 다르고, 중간부가 `e4e4e4e4...` 류의 반복 패턴으로 채워져 있어 실제 계산이 아닌 placeholder로 보임
- **Why it matters**: manifest.json은 이번 리뷰의 "evidence manifest" 1차 참조 파일 — 이 파일의 무결성 필드가 위조되어 있으면 향후 관리자가 manifest.json만 보고 무결성을 오판할 위험이 있음. 다행히 `provenance.json`/`stage-b-artifact-integrity.csv`는 실측과 정확히 일치해 실제 파일 손상은 아님을 확인했으나, **evidence package 내부 정합성 자체가 깨져 있음**
- **Minimum corrective action**: C1이 `manifest.json`의 `quarantined_artifacts[].sha256` 4개 값을 `provenance.json`/`stage-b-artifact-integrity.csv` 값으로 재생성·교체
- **Owner**: C1

---

#### Finding 2 — 아티팩트 수가 지시서의 "최대 3개" 상한을 초과 (HIGH)

- **Claim reviewed**: self-check.md "Quarantine download | PASS | 4 artifacts to NAE/corpus/quarantine/PBC1765/"
- **Evidence inspected**: `NAE/corpus/quarantine/PBC1765/original/` 실제 디렉토리 목록(`ls -la`)
- **Exact path**: `NAE/corpus/quarantine/PBC1765/original/` — 실제로는 **5개** 파일 존재(`confeo00phil.pdf`, `confeo00phil_djvu.txt`, `confeo00phil_scandata.xml`, `confeo00phil_hocr_searchtext.txt.gz`, `confeo00phil_hocr.html`), self-check.md는 4개라 기재
- **Severity**: HIGH — HQ-C1-DIRECTIVE-NAE-PBC1765-ACQUIRE-009 원문: "최대 3개만 수집할 수 있다: (1) Scan PDF 필수 (2) OCR/DjVu text 있으면 (3) scandata.xml/ALTO/hOCR **중 하나** 있으면". 실제로는 scandata.xml과 hOCR html **둘 다**, 그리고 hocr_searchtext.txt.gz까지 수집되어 상한(3) 및 "셋 중 하나" 제약을 모두 위반
- **Why it matters**: 이는 RISK: C(corpus provenance gate)로 지정된 지시서의 명시적 스코프 제약 위반 — 반복되면 quarantine이 무제한 파생물 저장소로 변질될 위험
- **Minimum corrective action**: `confeo00phil_hocr.html`과 `confeo00phil_hocr_searchtext.txt.gz` 중 최소 1개(지시서 기준으로는 scandata.xml만 남기고 hocr.html 삭제 검토, hocr_searchtext.txt.gz는애초 3개 카테고리 어디에도 명시적으로 속하지 않으므로 근거 확인 또는 삭제) 처리 방침을 HQ가 결정
- **Owner**: HQ (스코프 해석 결정 필요), C1 (실행)

---

#### Finding 3 — `confeo00phil_hocr.html`이 어떤 증거 파일에도 무결성 추적되지 않음 (MEDIUM)

- **Claim reviewed**: self-check.md "Transport validation | PASS | All HTTP 200, correct MIME types" — 전체 아티팩트에 대한 포괄적 PASS 주장
- **Evidence inspected**: `provenance.json`(artifacts 4건), `stage-b-artifact-integrity.csv`(3건 해시), `manifest.json`(4건) — 어느 목록에도 `confeo00phil_hocr.html`이 없음
- **Exact path**: `NAE/corpus/quarantine/PBC1765/original/confeo00phil_hocr.html` (파일은 실존, 3,795,207 bytes)
- **Severity**: MEDIUM — 파일 자체는 위험하지 않으나(공개 hOCR HTML), transport validation/해시 기록이 전혀 없어 "모든 아티팩트에 대해 HTTP 200/MIME 확인됨"이라는 self-check 주장의 범위가 실제보다 좁음
- **Why it matters**: 추적되지 않은 파일이 quarantine에 존재하면 향후 canonical 승격 심사 시 이 파일의 출처/무결성을 재구성할 수 없음
- **Minimum corrective action**: C1이 `confeo00phil_hocr.html`에 대한 HTTP 헤더/해시/MIME 기록을 추가하거나, Finding 2 처리 방침에 따라 파일 자체를 제거
- **Owner**: C1

---

#### Finding 4 — Content identity 요약(hq-report.md, self-check.md)이 원본 검증 파일(content-identity-validation.md)과 모순 (HIGH)

- **Claim reviewed**: `hq-report.md` "Content identity: **VERIFIED**" / "1765 imprint marker: verified" / "Baptist confession body structure: verified"; `self-check.md` "Content identity | PASS | Title, Philadelphia, 1765 markers verified"
- **Evidence inspected**: `content-identity-validation.md`(원본 자동검증 출력) 직접 확인
- **Exact path/line**: `evidence/phase5_2/pbc1765_acquire_009/content-identity-validation.md` — "1765 imprint marker found: **False**", "Baptist confession body structure found: **False**" (Title marker/Philadelphia marker만 True)
- **Severity**: HIGH — 요약 보고서 2건이 raw evidence에 없는 "verified" 상태를 주장(전형적 상태 과장). 또한 `hq-report.md`의 "Philadelphia marker: 'Philadelphia: printed by A. Archbold in Race-street, 1765'"라는 인용문은 `content-identity-validation.md`(raw)에도, `manifest.json`의 marker 인용("Philadelphia: printed by **A. Archbold**...")에도 나타나지만, **`stage-a-preflight-decision.md`(별도 원본 IA metadata 파싱)는 출판사를 "Ant. Armbruster"로 기재** — 동일 문서에 대해 두 개의 다른 출판사명이 서로 다른 증거 파일에 등장하는 내부 불일치가 추가로 존재
- **Why it matters**: RISK: C(corpus provenance gate) 항목에서 핵심 식별 근거인 imprint/출판사명이 증거 파일마다 다르면, canonical 승격 여부를 판단할 기준 자체가 흔들림
- **Minimum corrective action**: (1) `content-identity-validation.md`의 실제 정규식/판정 로직이 "1765"와 "body structure"를 왜 False로 판정했는지 C1이 재확인(정규식 결함인지, 실제로 텍스트에 없는지); (2) "A. Archbold" vs "Ant. Armbruster" 두 출판사명 중 실제 raw 메타데이터/스캔 이미지 기준 정답을 C1이 재확인해 모든 문서에서 통일
- **Owner**: C1

---

#### Finding 5 — gold-authoring-skeleton-report.md의 gold_tsu_ids 서술과 실제 파일 불일치, 미검증 TSU ID 포함 (MEDIUM)

- **Claim reviewed**: `gold-authoring-skeleton-report.md` "gold_tsu_ids: 각 질문당 1개 TSU ID (모두 동일: TSU-ACT-ada6a56f8ea13582)"
- **Evidence inspected**: `NAE/benchmark/datasets/gold_benchmark_v1.jsonl` 직접 열람 + registry(`data/제련완성본/registry/documents.json`)에서 `book: "SOL"` grep + `output/bench/tsu_dataset.jsonl`에서 `TSU-SOL` grep
- **Exact path**: `NAE/benchmark/datasets/gold_benchmark_v1.jsonl` B001 항목 — 실제로는 `gold_tsu_ids`가 5개 배열(`TSU-ACT-ada6a56f8ea13582`, `TSU-SOL-c2705bbcd45f1113`, `TSU-SOL-9fdff4dc7f27d3f4`, `TSU-SOL-dcfab80ef98c5749`, `TSU-SOL-443de91d4bf469b5`) — 보고서 서술("1개, 모두 동일")과 다름. 게다가 `book: "SOL"`은 registry에 **0건**, `TSU-SOL-*`은 실제 TSU 데이터셋에 **0건** — 즉 4/5 gold ID가 현재 코퍼스 어디에도 존재하지 않는 참조
- **Severity**: MEDIUM — 이 보고서 자신이 gate를 "NOT VALIDATED — corpus에 실제 TSU 존재 여부 확인 불가"로 이미 정직하게 선언하고 있어 상태 과장은 아니나, 서술(1개 ID)과 실제 파일(5개 ID, 그중 4개는 존재하지 않는 book_id 소속)이 맞지 않아 **문서가 최신 파일 상태를 반영하지 못함**
- **Why it matters**: 향후 누군가 이 보고서만 읽고 "gold set은 최소 골격이니 위험 낮음"으로 오판할 수 있으나, 실제로는 80%(4/5)의 gold reference가 이미 실체 없는 ID임
- **Minimum corrective action**: C1이 `gold-authoring-skeleton-report.md`를 현재 `gold_benchmark_v1.jsonl` 내용 기준으로 재작성하거나, TSU-SOL-* 4개 ID의 출처(어느 코퍼스/설계에서 왔는지)를 명시
- **Owner**: C1

---

## Q4. HQ가 다음으로 승인해야 할 단일 작업은 무엇인가

**추천: C1에게 evidence package 내부 정합성 복구(Finding 1, 2, 3, 4)를 단일 후속 지시로 발급 — PBC1765의 HQ 결정(Option A/B/C/D)은 이 복구 이후로 미루는 것을 권고.**

이유:
- PBC1765의 HQ 결정 요청(Option A/B/C/D, hq-report.md)이 의존하는 "Content identity: VERIFIED"라는 핵심 근거 자체가 Finding 4에서 원본 증거와 모순됨이 확인됨 — 이 상태로 Option A(canonical 승격)를 승인하면 검증되지 않은 근거 위에 결정을 내리는 것
- Finding 1(해시 위조 패턴)은 evidence manifest의 신뢰성 자체를 훼손하므로, 다른 어떤 phase 5.2 작업보다 먼저 해소되어야 함
- Phase 5.1은 코드/테스트 레벨에서 자기모순 없이 확인되었으므로 추가 조치 불요 — 다음 우선순위는 아니며, 실제 gold authoring(현재 skeleton)이 Phase 5.2 완료 이후 자연스럽게 이어질 사안

**제안 단일 Loop**: `HQ-C1-DIRECTIVE-NAE-PBC1765-EVIDENCE-RECONCILIATION-010` — Finding 1(해시 재계산), 2(아티팩트 상한 처리방침 HQ 결정 후 C1 실행), 3(hocr.html 추적 또는 제거), 4(imprint marker 재검증 및 출판사명 통일)를 하나의 evidence 패키지로 재제출.

---

## 검토 범위 한계 (명시)

- `NAE/corpus/canonical/PBC1742/normalize_report.json`, `NAE/corpus/raw/archive_org/{AF1815,TH1612,books}` 내용은 이번 리뷰에서 상세 대조하지 않음(§1 Mission 질문에 답하기 위한 필수 경로가 아니었음 — 필요 시 별도 라운드로 요청)
- `evidence/phase5_1_remediation/hq-c1-directive-remediation-004-report.md`(remediation_004와 다른 폴더)는 파일 존재만 확인, 내용 대조 안 함
- git baseline(§3 하단)은 별도로 기록: `branch=dev/dbma-engine`, `HEAD=403ab6581210d1fb77ef5a6508c84a4d40724fb8`, `git status --short` 결과 11개 modified + 다수 untracked(본 문서 상단 인용) — 이는 CUE observation이며 C1 evidence의 baseline.txt와 혼동하지 않음
