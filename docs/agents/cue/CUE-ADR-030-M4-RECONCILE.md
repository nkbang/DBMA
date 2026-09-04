# CUE — ADR-030 v2.1 §12 M-4 · `nae_corpus_reconcile.py` — RATIFIED v1.1

**작성자**: CUE · **작성일**: 2026-08-28 (v1) · **v1.1**: 2026-08-28 (HQ 보강 지적 ①~④ + 조건부 결정 반영)
**상태**: **RATIFIED v1.1** — HQ 비준 2026-08-28. C1 M-4 EXEC 착수 승인 (bounded impl/verify loop).
**대상**: `scripts/nae_corpus_reconcile.py` (skeleton 존재) 재작성 + test 강화
**baseline**: `dev/dbma-engine` @ `ad1464d` (M-3 완료)
**ADR 근거**: ADR-030 v2.1 §9, §12 MUST M-4, §14.2, §15 Test K

> M-4 는 **실제 production reconciliation 경로**를 건드린다 → M-3 보다 엄격하게.
> 진행: ① 설계 초안(본 문서) → ② HQ 비준 → ③ C1 M-4 EXEC 명령서 → ④ C1 구현/테스트(**commit 금지**)
> → ⑤ CUE 독립검증 → ⑥ GREEN → ⑦ 단일 commit. **본 문서는 도구를 고치지 않는다.**

---

## 1. 이 도구는 무엇이고 무엇이 아닌가

- **read-only drift 리포트.** production state authority 4개 사이의 불일치를 사람이 볼 수 있게 출력. ADR-020
  `index_all()` reconciliation 역할의 명령줄 확장.
- **쓰기 0.** `--apply` 없음. `json.load` / GET / `count` / `scroll` 만. state·corpus·Qdrant·manifest 무접촉.
  자동 수정 없음.
- **stale artifact 재발 방지.** 과거: stale `index_report.json` → Ops Dashboard → C1 오판.

---

## 2. 정합 모델 (Current Production State — ADR §9.2)

### 2.1 네 authority 와 실측값 (2026-08-28, `ad1464d`)

| authority | 무엇 | 실측 |
|---|---|---|
| `NAE/pipeline/ingest/state/incremental_state.json` | per-TSU 처리 단계 (`{tsu_id: {state,...}}`) | dict 3,319, 전부 `state == "INDEXED"` |
| `NAE/corpus/tsu/<work>/tsu.json` `review_status` | per-TSU 검수 결과 | non-`_` dir 합계: verified 3,319 (Dagg 2,958 + Hiscox 361) · rejected 22 · generated 4,419 |
| Qdrant `nae_tsu_v1` | 물리 벡터 (TSU) — points / point IDs | 3,319 (실행 시 GET; 현 환경 `unreachable` 가능) |
| `NAE/pipeline/registration/state/source_manifest.yaml` (M2) | source registry | 14 sources |

> **위 실측값은 "예상"이며, 도구/검증은 실행 결과로 판정한다** (HQ 지적 ③). "drift 없음"을 acceptance 로
> 강제하지 않는다 — 정확히 구현된 도구가 실제 drift 를 찾으면 그건 **surface 할 finding** 이지 test 실패가 아니다.

### 2.2 CORE 불변식 — production state ↔ production state (drift/exit 판정)

**ID-level reconciliation 우선** (HQ 지적 ①). count 는 fast pre-check 로만.

```
INV-1  set( tsu_id : review_status == "verified" )  ==  set( tsu_id : incremental_state.state == "INDEXED" )
       (count 선비교 후 set 차집합 both directions; 불일치 tsu_id 목록 출력)
INV-2  (Qdrant reachable 시)  Qdrant nae_tsu_v1 point id 집합  ==  INV-1 의 verified 집합
       point id 열거가 비싸면(대량 scroll) count 로 fallback + "id-level not verified" 명시
INV-3  set( tsu_id : review_status ∈ {generated, rejected, <verified 아닌 값>} )
       ∩ ( incremental INDEXED 집합  ∪  Qdrant id 집합 )  ==  ∅
       (embedded 되면 안 되는 TSU 가 embedded 됨 → drift). count 항등식은 보조 지표로만.
INV-4  각 tsu.json record 의 M2-linkage (아래) 가 M2 에 등록된 source 를 가리켜야 한다.
```

**INV-4 authority** (HQ 지적 ②): **directory name 이 아니라 `tsu.json` record 의 metadata 를 우선 authority**
로 사용한다.
- record 에서 M2 링크 필드를 이 우선순위로 추출: `source_id` → `work_id` → `source_file` / `document_id`.
- 그 값을 M2 의 `source_id` / `work_id` / `edition_id` 와 대조해 등록 여부 판정.
- directory name (`Dagg_Church_Order` 등) 은 **표시용 라벨**일 뿐, 판정 authority 아님.
- record 에 사용 가능한 링크 필드가 전혀 없으면 → **INV-4b drift**: "`<dir>` TSU record 에 M2-linkage
  metadata 없음".

### 2.3 GOVERNANCE CONSISTENCY (GC) — production ↔ governance log. **CORE 와 분리** (HQ 지적 ④)

INV-1~4 는 "production 이 자기 자신과 맞는가". GC 는 "production 이 M-3 governance 결정과 맞는가" —
성격이 다르므로 **별도 섹션·별도 라벨**로 리포트한다. `corpus_admissions.jsonl` (M-3, `ad1464d` 신설) 대상.

```
GC-1  corpus_admissions.jsonl 의 모든 source_id 가 M2 에 존재            (M-3 test 와 중복이나 재확인)
GC-2  admission 이 없는데 verified TSU > 0 인 source                     → DRIFT (거버넌스 게이트 우회)
GC-3  tsu-track admission 인데 그 source 의 TSU dir 자체가 없음          → INFO (아직 미생성일 수 있음, drift 아님)
```
- **exit code 기여**: GC-1 위반, GC-2 위반 = exit 1. GC-3 = INFO only.
- reference track (`nae_ref_v1`) 은 core 에서 제외되므로 GC 도 tsu-track 만 실질 검사.
- 리포트에서 `[CORE DRIFT]` 와 `[GOVERNANCE DRIFT]` 를 **구분 표기**.

### 2.4 범위 밖
- `nae_ref_v1` (Smith 34,948) — **core reconciliation 에서 제외** (HQ 결정). per-chunk review 없음.
  도구는 `nae_ref_v1` points_count 를 **정보용 1줄**로만 출력(GET 1회, 불변식·exit 기여 없음); 이 정보 출력조차
  선택(구현 부담 시 생략 가능).
- `NAE_QDRANT_URL` env override — **이번 M-4 에서 보류** (HQ 결정). 후속.

---

## 3. skeleton 결함 (실측 — `scripts/nae_corpus_reconcile.py` @ `fcaa380`)

| # | 결함 | 위치 |
|---|---|---|
| **D-1** | `m2_count(14)` 를 `incremental_count(3,319)` · `tsu_count(7,760)` 와 직접 비교 → **항상 discrepancy + 항상 exit 1**. source 단위 vs TSU 단위 | L129–136 |
| **D-2** | `count_tsu_records()` 가 `review_status` 무시, 전체 record 합산(7,760). verified 파티션 없음 | L86–103 |
| **D-3** | Qdrant 포트 `6333` 하드코딩. 실제 NAE = **7333** (`NAE/pipeline/index/config.py:17` `QDRANT_URL`). `config.yaml:52` 6333 은 DBMA legacy | L34 |
| **D-4** | `probe_qdrant()` bare `except` → auth 실패 / 컬렉션 없음 등 실제 error 를 `unreachable` 로 은폐 | L106–114 |
| **D-5** | INV-1~4 전부 미구현. 현재 비교는 D-1 의 틀린 2개뿐 | L128–136 |
| **D-6** | exit code 의미 불명 (D-1 로 항상 1) | L149 |
| **D-7** | test 15개가 "파일 존재 / list / 안 죽음" 수준. §14.2 (a)(b)(c)(d) 미충족 | test 파일 |
| **D-8** | M2 count 14 를 sources 수로만 사용, INV-4(링크 검사) 미활용 | L67–71 |

---

## 4. 재작성 스펙

**대상**: `scripts/nae_corpus_reconcile.py` **동일 경로 재작성** (HQ 승인) + `tests/test_nae_corpus_reconcile.py`
재작성/확장. `index_all()` 등 production 코드는 **읽기 import 만**, 수정 금지.

### 4.1 함수
| 함수 | 반환 | 비고 |
|---|---|---|
| `load_incremental_indexed_ids() -> set[str]` | `{tsu_id: state=="INDEXED"}` | ID 집합 |
| `load_review_status() -> dict[str, str]` | `{tsu_id: review_status}` (non-`_` dir 합산, INV-5 pilot 제외) | verified/generated/rejected 집합 파생 |
| `tsu_m2_linkage(tsu_record) -> str \| None` | record 에서 `source_id`→`work_id`→`source_file`/`document_id` 순 추출 | INV-4 authority |
| `m2_index() -> dict` | M2 를 `source_id` / `work_id` / `edition_id` 로 역인덱스 | INV-4 대조용 |
| `probe_qdrant(url, collection) -> ("reachable", ids_or_count) \| ("unreachable", reason) \| ("error", detail)` | | URL = `NAE.pipeline.index.config.QDRANT_URL` import (D-3). connection refused/timeout = `unreachable`; 그 외(컬렉션 없음 등) = `error` → drift (D-4) |
| `load_admissions() -> list[dict]` | `corpus_admissions.jsonl` 파싱 | GC용 |
| `reconcile() -> ReconcileResult` | INV-1~4 + GC-1~3 | `[CORE DRIFT]` / `[GOVERNANCE DRIFT]` / `[INFO]` 분리 |

### 4.2 판정
```
core_drift =
  INV-1: verified 집합 != INDEXED 집합   (양방향 차집합 tsu_id 목록)
  INV-2: (reachable) Qdrant id 집합 != verified 집합   | id 열거 불가 시 count 비교 + 표기
  INV-3: (generated∪rejected∪기타) ∩ (INDEXED ∪ Qdrant) != ∅   → 해당 tsu_id 목록
  INV-4: tsu record linkage 가 M2 에 없음   (dir 별, linkage 값 표시)
  INV-4b: tsu record 에 linkage 필드 자체가 없음
  probe_qdrant == "error"
gov_drift =
  GC-1: admission source_id 가 M2 에 없음
  GC-2: admission 없는데 verified TSU > 0
exit 0  = core_drift == [] and gov_drift == []
exit 1  = 그 외
Qdrant "unreachable"  → INV-2 skip, "INV-2 not checked (Qdrant unreachable)" 표기, exit 0 가능
```
- **M2 count(14) 를 TSU count 와 직접 비교하지 않는다** (D-1 제거).

### 4.3 출력
- 사람용 리포트: 4 authority 값 + `nae_ref_v1` 정보 1줄(선택) + `[CORE DRIFT]` / `[GOVERNANCE DRIFT]` /
  `[INFO]` / `No drift detected.`
- `--json` (**HQ 승인**): `{authorities:{...}, invariants:[{id, ok, detail}], governance:[{id, ok, detail}],
  qdrant:"reachable|unreachable|error", drift:{core:[...], governance:[...]}}`.
- `--apply` 플래그 **없음** (argparse 에 미등록 → `unrecognized arguments`).

### 4.4 도구 자체 불변식
- 실행이 어떤 파일·Qdrant·state 도 쓰지 않는다. 모든 `open()` 은 read 모드. Qdrant 는 GET/count/scroll 만.

---

## 5. Test 스펙 (§14.2 (a)(b)(c)(d))

`tests/test_nae_corpus_reconcile.py` 재작성. `probe_qdrant` 를 **주입 가능**하게(인자 or monkeypatch) 만들어
live Qdrant 없이 (b)(c) 검증. **tmp fixture 로 실제 `NAE/` 파일 무접촉** (memory: Test Fixture Path Overrides).

| 구분 | test |
|---|---|
| **(a)** Qdrant 정지 | `probe_qdrant` 가 `ConnectionError` → `reconcile()` 예외 없이 완료, 리포트 `unreachable`, INV-2 skip |
| **(b)** unit: reachable + 일관 입력 → drift 0 | fixture: verified 집합 == INDEXED 집합 == Qdrant id 집합 (모두 monkeypatch/tmp) → `core_drift == []`, exit 0 |
| **(c)** unit: 인위적 mismatch → 정확히 flag | fixture 조작 — (c1) INDEXED 집합에서 1개 제거 → INV-1 위반 + 그 tsu_id 목록; (c2) Qdrant id 집합 다르게 → INV-2; (c3) generated tsu_id 를 INDEXED 에 넣음 → INV-3; (c4) tsu record linkage 를 M2 없는 값으로 → INV-4; (c5) admission 없는 source 에 verified TSU → GC-2 |
| **(d)** mutation 0 | 실행 전/후 `incremental_state.json`·`source_manifest.yaml`·`tsu.json`·`corpus_admissions.jsonl` 의 mtime+sha256 동일 assert; `--apply` → `unrecognized arguments` |
| D-4 | `probe_qdrant` 가 "컬렉션 없음"류를 `("error", …)` 로 분류(→ core_drift), `unreachable` 로 은폐 안 함 |
| smoke (판정 아님) | 실제 파일로 `python scripts/nae_corpus_reconcile.py` 1회 실행 → **출력·exit code 를 그대로 기록**. drift 가 나오면 report 에 인용(데이터를 고쳐 통과시키지 않는다 — HQ 지적 ③) |
| 유지 | 기존 "파일 존재 / list" sanity 는 남겨도 무방(약화 아님) |

---

## 6. HQ 결정 — RESOLVED (2026-08-28)

| # | 결정 |
|---|---|
| 지적 ① | INV-1/2/3 = **ID-level set reconciliation** (count 는 pre-check). 불일치 `tsu_id` 목록 출력. §2.2 |
| 지적 ② | INV-4 authority = **`tsu.json` record metadata** (`source_id`→`work_id`→`source_file`/`document_id`). directory name = 표시용. linkage 필드 부재 = INV-4b drift. §2.2 |
| 지적 ③ | "현 상태 drift 없음" 을 acceptance 로 **강제하지 않음**. 도구/검증은 **실제 실행 결과로 판정**. smoke run 은 기록만. §2.1, §5 |
| 지적 ④ | admission reconciliation = **별도 GOVERNANCE CONSISTENCY (GC) 섹션**. CORE (INV) 와 라벨·리포트 분리. GC-1/GC-2 만 exit 1 기여. §2.3 |
| `--json` | **승인** — §4.3 |
| Qdrant URL | `NAE.pipeline.index.config.QDRANT_URL` single source — **승인** |
| `NAE_QDRANT_URL` override | **보류** (이번 M-4 제외, 후속) |
| `nae_ref_v1` | core reconciliation **제외**. 정보용 1줄 출력만(선택) |
| skeleton 동일 경로 재작성 | **승인** |

---

## 7. M-4 EXEC 이 할 일 (참고 — 비준 후, 별도 명령서)

1. `scripts/nae_corpus_reconcile.py` 재작성 — §4 (D-1~D-8 해소; INV-1~4 ID-level; GC-1~3 분리; `--json`;
   Qdrant URL import).
2. `tests/test_nae_corpus_reconcile.py` 재작성 — §5 ((a)(b)(c)(d) + D-4 분류 + mutation 0; tmp fixture 격리).
3. 검증: `python scripts/nae_corpus_reconcile.py` **실행 결과를 그대로 기록** (drift 유무는 데이터가 결정).
   `pytest -q tests/test_nae_corpus_reconcile.py` → FAIL 0. 실행 전/후 state 파일 sha256 동일.
4. **금지**: `--apply`/쓰기 로직, state/corpus/Qdrant/manifest/admission 파일 변경, `index_all()` 등 production
   코드 수정, M2/M1/M3(manifest) 변경, `git add`/`git commit`.
5. CUE 독립검증 → 단일 커밋 (`M-4: read-only corpus reconciliation tool`).

---

## 8. 이번 문서가 하지 않는 것

- 도구/테스트 재작성 — 하지 않음 (M-4 EXEC).
- state/corpus/Qdrant/manifest 접촉 — 하지 않음.
- C1 EXEC 명령 발부 — **하지 않음. HQ 비준이 선행.**

**Mutation: 0. 산출물: 본 DRAFT v1.1.**

END OF M-4 RECONCILE DRAFT v1.1
