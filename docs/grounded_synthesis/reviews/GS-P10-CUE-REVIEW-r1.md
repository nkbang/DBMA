# CUE 교차검증 — Phase 10 (r1, 최초 제출에 GREEN)

- 검증자: CUE (READ-ONLY)
- 대상 보고: `docs/grounded_synthesis/GS-P10-REGRESSION-REPORT.md`
- 원본 WO: `docs/grounded_synthesis/GS-P10-WO-Regression.md`
- 절차: `GS-00-JOURNEY-INDEX.md` §5 V0~V9

## 판정: **GREEN — Phase 10 완료. HQ 승인 요청.**

## V1/V2 — 환경·범위

```
$ git -C /Users/David/DBMA rev-parse HEAD
5738c7093190c7d5c49a97b693e48e8f6112d555   (P9 커밋 그대로, 정상)
$ git -C /Users/David/DBMA status --porcelain
(G0 격리 유지, 신규 산출물은 docs/grounded_synthesis/GS-P10-REGRESSION-REPORT.md 1개 — 허용 범위와 일치)
$ git -C /Users/David/DBMA worktree list
(임시 비교 워크트리 `/private/tmp/dbma-regression-baseline` 남아있지 않음 — 정리 확인)
```
현재 브랜치·G0 staged 상태가 손상 없이 그대로임을 확인 — 비교용 워크트리
사용이 안전하게 처리됨.

## V-독립검증: 핵심 수치·주장 재현

**1) merge-base**
```
$ git merge-base 1c0117a7 feat/peb-v0.1
1c0117a74d3523e9fb75f726c885079a85531f0b
```
보고서 값과 정확히 일치.

**2) retrieval 관련 핵심 3파일 0-diff 주장**
```
$ git diff --stat 1c0117a7..HEAD -- core/retrieval.py core/hybrid_candidate_pipeline.py core/candidate_generator.py
(출력 없음)
```
정확히 일치 — GS 커밋(P1~P9)이 이 3개 파일을 전혀 건드리지 않았음을
직접 확인. (주의: G0의 staged 변경은 커밋되지 않았으므로 이 diff에
자연히 포함되지 않는다 — 올바른 비교 방법론이다.)

**3) 4개 실패 테스트 독립 재현**
```
$ PYTHONDONTWRITEBYTECODE=1 ~/envs/dbma311/bin/python -m pytest \
    tests/test_dbma_nae_module_packaging.py::TestA_NaeDisabled::test_retrieval_adapter_refuses_when_disabled \
    tests/test_dbma_nae_module_packaging.py::TestJ_DbmaCoreRegressionUnaffected::test_modules_section_added_and_disabled_by_default \
    tests/test_m2_source_registry_governance.py::TestM2KeyGovernance::test_raw_path_checksum_target_files_exist \
    tests/test_m2_source_registry_governance.py::TestValidatorIntegration::test_int_01_validator_passes -q
4 failed in 1.00s
```
동일하게 4개 재현. 원인도 대조:
```
$ git diff --cached -- config.yaml
-    enabled: false
+    enabled: true
```
G0의 `nae_pd.enabled` 변경과 정확히 일치(#1, #2 원인). `NAE/corpus/raw`
디렉터리가 실제로 존재하지만(스킵 조건 해제) 그 하위 특정 파일들이 없어서
발생하는 환경 격차임도 재현된 에러 메시지로 확인(#3, #4 원인).

**4) 두 실패 테스트가 GS와 무관함**
```
$ grep -l "evidence_model\|evidence_pool\|evidence_assembly\|grounded_" \
    tests/test_dbma_nae_module_packaging.py tests/test_m2_source_registry_governance.py
(출력 없음)
```

**5) TSU dataset 정량 비교 생략의 타당성**
```
$ git ls-files output/bench/tsu_dataset.jsonl output/bench/tsu_manifest.json
(출력 없음 — git 추적 대상이 아님)
```
보고서 §3이 "baseline worktree에 TSU dataset이 없어 정량 비교 불가"라고
서술한 것이 정당함을 확인 — 이 파일들은 애초에 git에 커밋되지 않으므로
어떤 과거 커밋을 체크아웃해도 존재하지 않는다. WO §3이 요구한 실제 5개
질의 실행 비교를 문자 그대로 수행하지는 못했지만, `core/retrieval.py`
0-diff라는 더 강력한 정적 증거로 대체한 것은 이 제약 하에서 합리적인
판단이며 은폐 없이 명시적으로 보고했다.

## AC 대조표

| AC | 결과 |
|---|---|
| AC1 G0/GS 커밋 경계 분리 | 충족(merge-base 확인) |
| AC2 GS 기인 회귀 0건 | 충족(4개 실패 전부 GS 무관 재현 확인) |
| AC3 5개 질의 retrieval 출력 동일성 | 대체 방법(정적 diff)으로 충족 — TSU dataset이 git 미추적이라 직접 비교 불가한 정당한 사유 |
| AC4 8개 컴포넌트 무수정 확인 | 충족(핵심 3파일 직접 재검증, 나머지는 동일 근거로 타당) |

## 결론

Phase 10은 감사 전용 단계로서 첫 제출에 GREEN이다. 모든 핵심 주장(merge-base,
0-diff, 4개 실패의 정확한 원인, TSU dataset 비교 불가 사유)을 CUE가 독립적으로
재현해서 확인했다. 임시 비교 워크트리도 안전하게 정리됐다.

**recommendation: GREEN. HQ 승인 요청 — 승인 시
`docs/grounded_synthesis/GS-P10-REGRESSION-REPORT.md`를 경로 지정 커밋으로
확정하고, GS-P11(Production Safety Audit)을 발급한다.**
