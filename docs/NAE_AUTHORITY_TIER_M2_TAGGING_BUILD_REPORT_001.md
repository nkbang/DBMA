# NAE Authority Tier M2 Tagging — Build Report 001

**Project:** NAE-AUTHORITY-TIER-M2-TAGGING-BUILD-001
**Date:** 2026-09-17
**Nature:** ADR-030 Amendment D §4-B (B1) 구현 — Plan 001 §4/§5 코드 변경만.
Backfill(§6-§8, corpus_admissions.jsonl 태깅)은 별도 HQ 결정 사항으로 이번
구현 범위 밖.
**Branch:** `claude/authority-tier-m2-implementation` (base: `origin/dev/dbma-engine` @ `50728a4b`)
**Git Commit:** 본 문서 작성 직후 수행 (CUE Operating Policy — 완료 조건
충족 시 승인 없이 자동 commit/push)

---

## 1. Executive Summary

Plan 001 §4-§6 설계를 그대로 구현했다. `RegistrationRequest`에 3개
optional 필드(`authority_tier`, `tradition_relation`, `counter_refs`)를
추가하고, `scripts/m2_source_registry_validator.py`에 V9-V12 4개 신규
검사를 추가했다. 기존 M2 15개 레코드는 1바이트도 변경하지 않았다(신규
필드는 어떤 실제 레코드에도 아직 쓰이지 않음 — Amendment D §2.2가 규정한
"부재 = WARNING, fail-closed T4 취급" 원칙 그대로 유지). 신규 pytest
6종 전부 PASS, 관련 회귀 테스트 무회귀 확인.

## 2. Governance Gate 확인 (구현 착수 전)

Amendment D §4-A 기준:
- A1(ADR 초안) ✅, A2(C1 설계 검토 GREEN) ✅ — 기존 완료 상태.
- A3(HQ 설계 승인) — 이번 세션에서 채팅으로 확인. 사용자가 "승인" →
  이어서 "origin/dev/dbma-engine 기준으로 새 브랜치 만들어서 진행해"로
  재확인. Amendment D 문서 A3 행을 이 시점 기준으로 ✅ 완료로 갱신.

구현 착수 전 git 히스토리 확인: 구현 커밋은 A3 확인(본 세션) 이후에만
생성됨 — Architecture Freeze Rule 위반 없음.

## 3. 코드 변경

### 3.1 `NAE/pipeline/registration/pipeline.py`

- `RegistrationRequest` dataclass에 `authority_tier: str | None = None`,
  `tradition_relation: str | None = None`, `counter_refs: list[str] | None
  = None` 3개 필드 추가 — Amendment B 선례와 동일한 optional/additive
  패턴.
- manifest_entry 조립 블록에 3개 조건부 `if request.X is not None` 블록
  추가. 필드 미지정 시 기존과 완전히 동일한 출력.

### 3.2 `scripts/m2_source_registry_validator.py`

- 상수 추가: `VALID_AUTHORITY_TIERS`(4-enum), `VALID_TRADITION_RELATIONS`
  (5-enum). `ADR030_ADDITIVE_FIELDS`에 3개 신규 필드 추가(V7의 "known
  keys" 검사가 자동으로 이 신규 필드를 허용하도록).
- 신규 함수 `check_authority_tier_fields()` — V9(tier/tradition_relation
  vocab), V10(T3 → counter_refs 필수), V11(a: orphan 참조 금지, b: 참조
  대상 authority_tier ∈ {T1,T2} 강제), V12(T1/T2/T4 → counter_refs 금지)
  를 한 함수에서 순차 검사. 어떤 레코드도 신규 필드를 갖지 않으면 전부
  skip(PASS)하는 기존 V6 패턴을 그대로 따름.
- `validate()` 파이프라인 목록에 `("V9-V12", check_authority_tier_fields)`
  추가.
- V5(self-check) 합성 레코드 검사에도 `check_authority_tier_fields`
  결과를 포함 — 필드 0개 합성 레코드는 여전히 FAIL 0.

### 3.3 `tests/test_m2_source_registry_governance.py`

- `VALID_AUTHORITY_TIERS`/`VALID_TRADITION_RELATIONS` 상수, `ADR030_ADDITIVE_FIELDS`에
  신규 3필드 추가.
- 신규 `TestAuthorityTierGovernance` 클래스, 6개 테스트:
  - `test_pos_08_authority_tier_vocab_when_present` — 실제 M2 대상,
    백필 이전이므로 공허 통과.
  - `test_neg_09_t3_without_counter_refs_fails` — V10.
  - `test_neg_10_orphan_counter_ref_fails` — V11(a).
  - `test_neg_11_counter_ref_target_not_t1_t2_fails` — V11(b).
  - `test_neg_12_t1_t2_t4_with_counter_refs_fails` — V12 (3개 tier 모두
    파라미터화).
  - `test_pos_09_t3_with_valid_t1_t2_counter_ref_passes` — 정상 케이스
    (순환 불가능함을 보이는 최소 예).
- `test_m2_records_only_known_keys`의 로컬 `additive` 리터럴을 모듈
  상수 참조로 교체(드리프트 방지).

## 4. 검증 결과 (실제 실행, 추론 아님)

```
$ python -m pytest tests/test_m2_source_registry_governance.py -v
33 passed, 2 skipped (skip 사유: NAE/corpus/raw 부재, 본 구현과 무관)

$ python -m pytest tests/test_m2_source_registry_governance.py \
    tests/nae/registration/test_phase_d_coverage.py \
    tests/nae/registration/test_pipeline_smoke.py \
    tests/test_authority_validator.py \
    tests/test_authority_validator_canonical.py -q
101 passed, 2 skipped

$ python scripts/m2_source_registry_validator.py
PASS: 15  FAIL: 2  WARN: 0
  [FAIL] V6 raw_path/checksum_target 파일 없음 — 이 worktree에 NAE/corpus/raw
         트리 없음(사전 존재, 변경 전 동일 FAIL 확인됨)
  [FAIL] V8 canonical dirs = 3 (baseline=17) — 상동, 환경 문제
  [PASS] V9-V12: no authority_tier fields in M2 (not yet tagged, all skip)
```

**변경 전/후 대조**(`git stash`로 구현 전 상태 재현 후 동일 명령 실행):
변경 전에도 동일하게 PASS 14 / FAIL 2(V6, V8 동일 사유) — 이 2건은
구현과 무관한 환경 데이터 갭임을 확인. 구현 후 PASS가 14→15로 늘어난
1건은 신규 V9-V12 검사 자체의 PASS 항목.

**전체 스위트 회귀**(`python -m pytest tests/ -q`): 3076 passed, 17
skipped, 2 failed. 실패 2건(`test_indexer_review_gate_wiring.py`,
`test_nae_pilot_human_review_intake.py`)은 프로덕션 TSU 인덱스 카운트
하드코딩 baseline(3319) vs 실제 디스크 상태(8936) 불일치 — 본 구현이
건드리지 않는 `NAE/pipeline/index/indexer.py` 및 TSU 데이터 자체에
관한 것이며, `git diff`로 무관함을 확인(본 구현은 `pipeline.py`
(registration)/validator/test 3개 파일만 수정). 별도 이슈로 분리 —
이 Build Report의 완료 판정에 영향 없음.

## 5. 변경 범위 확인 (Freeze 준수)

- M2 기존 15개 레코드 값 — 무변경 (git diff 확인, YAML 파일 자체를
  건드리지 않음).
- Retrieval Engine(`core/retrieval.py`) — 무접촉.
- RAW 코퍼스, TSU Pipeline, Production Registry — 무접촉.
- `authority_class` 4-enum, §7.3 관계 선언 — 무변경.

## 6. 다음 단계

1. B3 — 구현 코드에 대한 C1 독립 검토 요청 (`docs/agents/c1/` 관례에
   따라 Review Request 문서 작성, Amendment B 선례와 동일한 사후검증형).
2. B3 GREEN 이후 B4 — HQ 최종 승인 → Amendment D APPROVED 승격.
3. Amendment D APPROVED 이후에만 Plan 001 §6-§8(실제 M2 backfill,
   `corpus_admissions.jsonl` 태깅)을 별도 작업으로 진행 — 이번
   구현에는 포함되지 않음.

---

**End of Build Report 001.**
