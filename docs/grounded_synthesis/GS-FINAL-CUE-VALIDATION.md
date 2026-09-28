# CUE Final Validation — Grounded Synthesis

- 대상 문서: `docs/grounded_synthesis/GS-FINAL-IMPLEMENTATION-REPORT.md`(C1 최종보고, 468줄)
- 절차: `docs/grounded_synthesis/GS-00-JOURNEY-INDEX.md` §5 V0~V9 전체 재적용
- 검증일: 2026-09-28, HEAD `06e5a47b`(feat/peb-v0.1)

## V1/V2 — 환경·범위·스코프 무결성

```
$ git rev-parse HEAD
06e5a47bffba504b258e8cd8f90acdd8fe029796
$ git status --porcelain
(G0 비-GS staged 변경 6건 그대로 격리, GS 산출물 외 추가 변경 없음)
$ git log --oneline 1c0117a7..HEAD | wc -l
11
$ git diff --stat 1c0117a7..HEAD | tail -1
22 files changed, 7172 insertions(+), 1 deletion(-)
```
C1 §11 Scope Integrity와 커밋 수(11)·diffstat(22 files, 7172(+)/1(-))가 정확히
일치. 22개 파일 전부 `core/evidence_*`, `core/grounded_*`, `tests/test_evidence_*`,
`tests/test_grounded_*`, `scripts/grounded_synthesis_integration_demo.py`,
`docs/grounded_synthesis/GS-P{09,10,11}-*.md` 명명 규칙 안에 있음 — 승인 범위
밖 변경 0건 확인.

## V3/V4 — 인용 표본 검증(날조 여부)

C1의 최종보고서는 특정 파일:줄과 테스트명을 대량 인용한다. 표본으로 확인:

- Q1 근거 `tests/test_evidence_pool.py:570,587`(`test_no_retrieval_import_in_evidence_pool`,
  `test_evidence_pool_does_not_call_retrieve`) — **실제 코드와 줄 번호·내용 정확히 일치**
- Q3 근거 `core/evidence_assembly.py:65-83`(AssemblyManifest 클래스 정의) — **일치**
- Q3 근거 `tests/test_evidence_assembly.py:514`(`test_manifest_queries_for_duplicate_evidence`),
  `:631`(`test_manifest_key_matches_pool_evidence_id_when_tsu_id_missing`) — **일치**,
  둘 다 CUE가 P3A 단계에서 직접 만든 재현 케이스를 그대로 테스트화한 것임을 재확인

인용이 정확하고 CUE 자신의 과거 개입(P3A, P7 REWORK) 기록과도 모순이 없다 —
날조 징후 없음.

## V5 — 전체 회귀 독립 재실행 (여정 전체에 대한 마지막 재확인)

```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/ -q
FAILED tests/test_dbma_nae_module_packaging.py::TestA_NaeDisabled::test_retrieval_adapter_refuses_when_disabled
FAILED tests/test_dbma_nae_module_packaging.py::TestJ_DbmaCoreRegressionUnaffected::test_modules_section_added_and_disabled_by_default
FAILED tests/test_m2_source_registry_governance.py::TestM2KeyGovernance::test_raw_path_checksum_target_files_exist
FAILED tests/test_m2_source_registry_governance.py::TestValidatorIntegration::test_int_01_validator_passes
4 failed, 3423 passed, 2 skipped, 16 warnings in 257.62s
```
C1 최종보고 §13("3423 passed / 4 failed")과 정확히 일치. 4개 실패는 P10/P11에서
이미 GS 무관(G0 config.yaml 변경 2건 + NAE/corpus/raw 환경 격차 2건)으로 확인된
바로 그 4건과 동일.

**정확한 수치 표현**(외부 교차검증 지적 반영): "3423개 전부 PASS"라는 압축 표현은
오해 소지가 있다. 정확히는 총 3429개 시도 중 **3423 PASS / 4 FAIL(GS 무관) / 2 SKIP**이다.

### 추가 검증 — G0 완전 격리 후 클린 기준 회귀 (2026-09-28)

인과관계를 최종적으로 확정하기 위해, G0의 6개 파일(`config.yaml`,
`core/candidate_generator.py`, `core/hybrid_candidate_pipeline.py`,
`scripts/merge_nae_corpus.py`, `scripts/process_unprocessed_nae.py`,
`scripts/test_default_corpus_query.py`)을 `git stash push -u`로 완전히
격리한 뒤(고유 태그로 추적, `git stash apply`로 복원 — bare pop 금지 규칙 준수)
전체 스위트를 재실행했다:

```
$ git stash push -u -m "CG-clean-baseline-check-<ts>" -- config.yaml \
    core/candidate_generator.py core/hybrid_candidate_pipeline.py \
    scripts/merge_nae_corpus.py scripts/process_unprocessed_nae.py \
    scripts/test_default_corpus_query.py
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest tests/ -q
2 failed, 3425 passed, 2 skipped, 16 warnings in 267.40s

FAILED tests/test_m2_source_registry_governance.py::TestM2KeyGovernance::test_raw_path_checksum_target_files_exist
FAILED tests/test_m2_source_registry_governance.py::TestValidatorIntegration::test_int_01_validator_passes
```

G0를 제거하니 `config.yaml` 관련 2개 실패가 정확히 사라지고(3423→3425 passed,
4→2 failed), 남은 2개는 `NAE/corpus/raw` 환경 격차로 이미 설명된 것과 동일하다 —
**GS 관련 실패는 0건임을 클린 기준에서 최종 확정**했다. 이후 `git stash apply
<sha>` + `git add`로 G0를 정확히 원상복구했다(`git diff --cached --stat`으로
원래 diffstat과 라인 수까지 일치 확인 후 stash drop).

## R6 grep 전체 재실행(Evidence boundary 재확인)

```
$ grep -rln "QueryProcessor\|HybridQueryProcessor\|RetrievalEngine\|HybridRetriever\|CandidateGenerator\|import ollama\|import qdrant_client\|import tantivy\|import requests\|import httpx\|import urllib\|import subprocess\|import socket" \
    core/evidence_*.py core/evidence_adapters/*.py core/grounded_*.py
core/evidence_assembly.py
core/evidence_pool.py
```
매칭 확인 결과 전부 docstring/주석("이것들을 호출/import하지 않는다"는
자기선언문)일 뿐, 실제 import/호출 코드가 아님을 확인.

## P8 6케이스 재실행

18개 테스트 전부 PASS 재확인(Case A~F, 통합, 경계 케이스 포함).

---

## 7문항 최종 판정

| # | 질문 | C1 근거(요약) | CUE 검증 방법 | 판정 |
|---|---|---|---|---|
| 1 | Retrieval authority 유지 | `core/evidence_assembly.py:16-30` 등 docstring, P10 0-diff | `core/retrieval.py` 1c0117a7..HEAD diff=0 독립 재확인 | **PASS** |
| 2 | Evidence boundary 유지 | `tsu_adapter.py:210`, `evidence_model.py:17-19`, P11 항목7 | R6 grep 전체 재실행(위) — 실제 import 0건 | **PASS** |
| 3 | Multi-query integrity | `evidence_assembly.py:67-83`, test:514/631 | 코드+테스트 정독, CUE 원 재현 케이스와 일치 확인 | **PASS** |
| 4 | Deduplication integrity | `evidence_pool.py:42-53`, test:147/173/186/363 | 테스트명·줄번호 대조, P2/P3A REWORK 이력과 정합 | **PASS** |
| 5 | Claim grounding 추적 가능 | `grounded_citation.py:43-56/120`, P7 short-circuit | P7 REWORK(id_exists=False 자동 False) CUE 원검증 사실과 일치 | **PASS**(한계: span 판정이 한국어/영어 간 exact substring이라 관대하지 않음 — §12(c)에 정직하게 기록됨) |
| 6 | Insufficient evidence 정상 표현 | `grounded_answer.py:53-59`, P8 6케이스 | P8 18개 테스트 독립 재실행 전부 PASS | **PASS** |
| 7 | Existing system integrity | P10 회귀표, P11 9항목 | 전체 회귀 재실행 3423 passed/4 failed(무관) 정확히 재현 | **PASS** |

## AC3(§18 요구) 확인

```
$ grep -in "GREEN\|APPROVED\|승인함\|검증 완료" docs/grounded_synthesis/GS-FINAL-IMPLEMENTATION-REPORT.md
(판정 선언 문구 없음 — "완료"라는 상태 서술만 있고 GREEN/APPROVED 미사용)
$ tail -3 docs/grounded_synthesis/GS-FINAL-IMPLEMENTATION-REPORT.md
CUE READ-ONLY FINAL VALIDATION REQUESTED
```
정확히 요구된 마지막 문장으로 끝남.

## CUE 최종 판정

- [x] **GREEN — HQ 최종 승인 상신**

## Remaining Limitations 8건에 대한 CUE 코멘트

C1이 §12에 기록한 8개 한계(D2 미통합, 자동충돌탐지 부재, span 판정 한계,
Claim ID 범위, overwrite 정보손실, max_evidence 절단 시 provenance 단절
경계사례, P9 GPU 의존, TSU git 미추적)는 이 여정 전체에서 CUE가 직접
발견·기록한 것들과 정확히 일치하며 숨긴 것이 없다. 특히 (f)는 P7 REWORK로
해소된 케이스(id_exists=False 단락)와 별개로 "id_exists=True인데 실제로는
max_evidence로 잘렸어야 하는" 이론적 경계까지 스스로 지적한 것으로, 정직한
자기평가로 판단한다.

## HQ 보고 (15줄 이내)

Grounded Synthesis 여정(P1~P12) 최종 검증 완료 — **GREEN**.
11개 커밋, 22개 파일(전부 GS 명명 규칙 내, 범위 이탈 0건), 신규 테스트
220개 + 기존 3203개 = 3423개 PASS, 4개 FAIL(GS 무관, 클린 기준(G0 제외)
재실행으로 0건 확정), 2개 SKIP.
핵심 불변식 7개(retrieval authority 유지, evidence boundary, multi-query
provenance, dedup 정책, claim grounding, insufficient-evidence 정상 처리,
기존 시스템 무손상) 전부 CUE가 코드·테스트를 직접 재확인해서 PASS 판정.
여정 중 8개 Phase에서 REWORK가 있었고(P3A×2, P7×1, P8×2, P9×2, P11×1),
전부 CUE 적대적 프로브 또는 동어반복 검증으로 발견·해소됨 — C1의 자체
GREEN 선언은 한 번도 그대로 수용되지 않았다. 실제 Ollama 모델로 A1/B1
질의가 grounded 도달함을 실증(P9). 남은 한계 8건은 §12에 정직하게 기록됨
(핵심: 아직 운영 UI 미통합, 자동 충돌탐지 없음, 한국어/영어 span 판정 한계).
HQ 최종 승인을 요청합니다.
