# Build Report — NAE-TSU-BUILDER-RESUME-001

**작성:** CUE · 2026-09-10
**설계:** `docs/NAE_FULLER_TSU_BUILDER_RESUME_DESIGN_v1.md`
**브랜치:** `claude/tsu-builder-resume-abf035` (base `origin/dev/dbma-engine` @ `daca402`)

---

## STATUS

**IMPLEMENTED — 회귀 PASS. C1 Independent Review + HQ 승인 대기 (TSU Pipeline 변경).**

`build_tsu_for_identifier(..., resume: bool = False)` 추가. `--resume`로 partial
volume을 마지막 checkpoint(`tsu_report.json.candidates_evaluated`)부터 이어서 처리하며,
결과 `tsu.json`은 처음부터 돌린 것과 **byte-identical**. 완료본(`partial: false`)은
skip. `builder_version` `3.0.0` 유지 → ADR-030 Amendment A 무영향.

---

## Changed Files

| 파일 | 변경 |
|---|---|
| `NAE/pipeline/tsu/builder.py` | `resume` 파라미터. 신규 헬퍼 `_atomic_write_json`(temp+`os.replace`), `_load_resume_state`, `_recount_doctrines`, `_resume_next_id`, `_reconcile_resume_point`. `_write_tsu_output`를 원자적 기록 + `tsu.json`→`tsu_report.json` 순서 고정. 루프를 `candidates[resume_from:]`부터. `elapsed_seconds` 누적(`resume_elapsed_base`). `total==0` 중복 기록 블록 제거(최종 기록으로 통합, 파일 내용 동일). `build_tsu_for_all`에 `resume` pass-through. |
| `NAE/pipeline/tsu/runner.py` | `--resume` (store_true). `--identifier` / `--legacy-scan` / gate-wired 분기 전부 pass-through. `_run_gate_wired(..., resume=False)`. 모듈 docstring에 RESUME-001 주기. |
| `scripts/run_fuller_f2.sh` | volume 루프: `tsu_report.json` 존재 & `partial != false` → `--resume` 부여. `partial == false` → skip(기존과 동일). 헤더 주석 갱신("RESTARTS from candidate 0" → resume 설명). gate/commit/push 로직 무변경. |
| `tests/test_nae_tsu_builder.py` | resume 회귀 4건 + 헬퍼(`_setup_multi`, `_claim_for`). |
| `tests/test_tsu_pipeline_wiring.py` | `_run_gate_wired` stub lambda 시그니처에 `resume=False` 추가(1줄). |
| `docs/NAE_FULLER_TSU_BUILDER_RESUME_DESIGN_v1.md` | 신규 설계 문서. |
| `docs/NAE_FULLER_TSU_BUILDER_RESUME_BUILD_REPORT_001.md` | 본 문서. |

**무접촉(제약 준수):** `NAE/pipeline/tsu/claim.py`(추출 프롬프트·모델), `doctrine.py`
분류기, TSU 레코드 필드 집합, `config.BUILDER_VERSION`, `TSU_SCHEMA_VERSION`,
`docs/architecture/ADR-030-AMENDMENT-A-*.md`.

---

## Tests

신규 (`tests/test_nae_tsu_builder.py`, `~/envs/dbma311`):

| 테스트 | 검증 |
|---|---|
| `test_build_tsu_resume_byte_identical` | n=6, `checkpoint_every=2`. mock이 4번째 호출에서 `RuntimeError` → candidate 2 checkpoint 후 중단. `resume=True` 재개 → `tsu.json` **byte-identical** to from-scratch. report 안정 필드(identifier/builder_version/model/candidates_evaluated/candidates_total/claims_extracted/llm_errors/doctrine_breakdown/partial) 동일. `builder_version == "3.0.0"`. |
| `test_build_tsu_resume_noop_when_complete` | 완주 후 `resume=True` → `extract_claim` 0회 호출, `result["skipped"] is True`, `tsu.json` 불변. |
| `test_build_tsu_resume_without_prior_report_starts_fresh` | 깨끗한 tsu_root + `resume=True` → fresh와 동일(ids TSU-0000001..4, `partial: false`). |
| `test_build_tsu_resume_aborts_on_canonical_drift` | partial 후 `canonical.json` paragraph `index` 변경 → `resume=True` → `RuntimeError("... canonical.json changed ...")`, `tsu.json` 미변형(기록 전 abort). |

```
$ ~/envs/dbma311/bin/python -m pytest tests/test_nae_tsu_builder.py -q
........                                                                  [100%]
8 passed in 0.12s        # 기존 4 + 신규 4
```

기존 4건(`..._writes_records_and_report`, `..._id_counter_persists_across_calls`,
`..._skips_non_claim_sentences`, `..._counts_llm_errors_without_crashing`)은
`resume=False` 기본이라 무영향 — 회귀 게이트.

---

## Regression

```
$ ~/envs/dbma311/bin/python -m pytest tests/test_tsu_worker.py tests/test_tsu_pipeline_wiring.py \
      tests/ -k "tsu or crosswalk" -q
498 passed, 1 skipped, 2343 deselected

$ ~/envs/dbma311/bin/python -m pytest tests/ -k "nae or tsu or crosswalk or corpus or fuller" -q
1234 passed, 2 skipped, 1606 deselected in 16.81s
```

- `python -m NAE.pipeline.tsu.runner --help` → `--resume` 노출 확인.
- `bash -n scripts/run_fuller_f2.sh` → syntax OK.
- `import NAE.pipeline.tsu.builder, NAE.pipeline.tsu.runner` → OK.
- `builder_version` 불변 → `run_fuller_f2.sh::gate_ok`, embedding cache hash, F2 gate 회귀 불필요.
- `nae_corpus_reconcile` 스모크 포함 통과 → 3,319 / 34,948 baseline 무접촉.

---

## builder_version 판단 (요구사항 #5)

**`3.0.0` 유지. 승격·ADR-030 Amendment A 갱신 불필요.** 근거: 추출 로직·TSU 레코드
shape 무변경, 동일 입력 → 동일 `tsu.json`(§4 불변식). 선례
`NAE_FULLER_F2_PARALLEL_SPEEDUP_RESULT_001.md` §4(max_workers 배선 변경도 버전 불변).
`run_fuller_f2.sh::gate_ok`의 `builder_version == "3.0.0"` 검사 그대로 통과. 상세는
설계 문서 §6.

---

## 불변식 한계 (정직한 서술)

byte-identical은 **순차(`-np 1`) `claim.extract_claim`가 동일 입력에 결정적**일 때
성립 — from-scratch F2 재현성이 이미 의존하는 것과 동일한 가정. 2026-09-08
parallel-speedup 실측은 **동시성(`-np 2`)에서만** llama.cpp 비결정성을 확인했고
resume는 순차 의미를 유지하므로 그 특성을 물려받지 않는다. 만약 backend가 동일
순차 입력에 다른 토큰을 반환하면 불변식은 **구조적 불변식**(id·건수·순서·doctrine
동일, 재평가 candidate의 `claim` 문자열만 상이)으로 약화되며, `_reconcile_resume_point`
덕분에 **데이터 손실·중복은 어떤 경우에도 없다**.

---

## Git

- **Commit:** `feat(tsu): checkpoint resume for build_tsu_for_identifier` — 완료 조건
  충족(구현·회귀 PASS·claim.py/doctrine 무접촉·Build Report 작성) → 정책상 자동 커밋.
- **Push:** `origin claude/tsu-builder-resume-abf035` → 정책상 자동 push. Force/history
  rewrite 없음. `dev/dbma-engine` 직접 병합 없음(PR/HQ 경유).

---

## Next

1. **C1 Independent Review** (설계 §9): candidate 정합성 3-튜플 키 유일성(Fuller
   실측 Vol.01–03 dup=0 확인 완료, C1 재확인 요청), `next_id` 파생 규칙, 원자적
   기록 순서 + torn-write 폐쇄, 불변식 논증, 회귀 커버리지, `builder_version` 유지 동의.
2. **HQ 승인** → Evidence Before Promotion 4조건 중 3·4.
3. 현재 **F2 실행 중**(`pgrep -f run_fuller_f2` = live). 새 F2 실행(갱신된
   `run_fuller_f2.sh`, `--resume` 경로)은 **F2 완료 후**. builder/runner 수정은
   실행 중 프로세스에 무영향(재로딩 없음), `run_fuller_f2.sh`는 이 worktree 파일이라
   메인 체크아웃 실행본과 별개.
4. 병합 시점 주의: `dev/dbma-engine`에 merge된 뒤 메인 체크아웃이 pull하면 실행 중
   F2가 갱신된 스크립트를 읽을 수 있음 → F2 종료 확인 후 병합 권장.
