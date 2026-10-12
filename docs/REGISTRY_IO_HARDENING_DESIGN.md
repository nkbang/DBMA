# 레지스트리 저장·읽기 보강 설계

- 작성: 2026-10-12 · 기준 코드: `dev/dbma-engine` `be0be6e8`
- 상태: **설계 + 격리 프로토타입 검증 완료, 구현 PR 미생성**
- 관련: `docs/WINDOWS_VERIFICATION_PROCEDURE.md` §1.1, 점검 `08`(`scripts/windows/verify_windows_readiness.py`)

## 1. 한 줄 요약

`save_identity_registry`는 실패를 삼키고 `False`만 돌려주며, `load_identity_registry`는 *어떤* 실패든 빈 레지스트리로 바꿉니다. 둘 다 **실패가 소리 없이 데이터 상실로 이어지는 구조**이고, Windows에서는 `os.replace`가 일시적으로 실패하기 쉬워 이것이 실제로 발현될 가능성이 높습니다. 다음 세 가지를 바꿉니다.

1. **일시적 실패는 재시도**(Windows `PermissionError` 등), **영구 실패는 숨기지 않음**(항상 ERROR 로그, 읽기→수정→저장 호출자에게는 예외).
2. **손상·스키마 비호환 파일은 덮어쓰이기 전에 복사본을 보존**(OS 무관 — macOS에서도 지금 조용히 사라진다).
3. **저장마다 고유한 임시 파일**을 쓴다(잠금 밖 저장끼리의 임시 파일 충돌 제거 — OS 무관).

## 2. 확인된 사실 (코드와 측정)

| # | 사실 | 근거 |
|---|---|---|
| F1 | `save`는 `OSError`(PermissionError 포함)를 삼키고 `False`를 반환한다 | `core/identity_registry.py` `save_identity_registry` |
| F2 | 저장 **실제 호출 18곳**(AST, 테스트 제외) 중 **반환값을 확인하는 곳은 5곳**(`library.py` 3, `dashboard.py` 1, `processing.py:975`), **무시하는 곳은 13곳**(앱 코드 6: `index_orchestrator` 3·`processing` 2·`raw_hygiene` 1 / 스크립트 7) | AST |
| F3 | `load`는 `JSONDecodeError`·`OSError`·**스키마 비호환** 모두를 조용히 `_empty_registry()`로 바꾼다. 백업·격리 로직은 어디에도 없다 | 코드 + `grep` |
| F4 | `load` 호출 26곳 중 `with registry_lock` 안은 5곳, 밖은 21곳 (추정: 상위 함수가 이미 잠금을 쥔 경우는 구분 못 함) | AST |
| F5 | `os.replace`로 파일을 교체하는 모듈이 **6곳**: `identity_registry`, `tsu_builder`(`_atomic_write_text`, 데이터셋), `extraction_failures`, `reading_session`, `research_workspace`, `sermon_artifact` | `grep` |
| F6 | **저장이 항상 같은 임시 파일 이름**(`documents.json.tmp`)을 쓴다. 화면 동작(`library.py`·`dashboard.py`)의 저장은 `registry_lock` **밖**이라 백그라운드 저장과 같은 임시 파일에 동시에 쓸 수 있다 | 코드 (macOS에서도 해당) |
| F7 | 기존 시험 중 임시 파일 이름·"손상 → 빈 레지스트리"를 단언하는 것은 **0건** (레지스트리 관련 18개 파일 169건) | `grep` + 프로토타입 실행 |

### 2.1 위험의 실제 크기 — 앞선 설명의 정정

처음에는 "Windows에서 빈 레지스트리를 읽고 그 위에 저장하면 실제 레지스트리를 덮어쓸 수 있다"고 설명했습니다. 호출부를 직접 읽어 보니 **더 좁게** 말해야 합니다.

- **화면 동작은 안전합니다.** `library.py` 551·598·611, `dashboard.py` 815는 저장 전에 *문서가 레지스트리에 있는지* 확인하므로(`target is None`, `doc_id in documents`), 빈 레지스트리를 읽어도 "저장 실패/없음"으로 끝나고 빈 것을 저장하지 않습니다. 저장 반환값도 5곳이 확인합니다(사용자에게 오류 표시).
- **위험한 곳은 새 문서를 등록하는 잠금 안 경로**입니다 (`processing.py`, `index_orchestrator.reconcile`, `raw_hygiene`). 여기서 읽기가 일시 실패해 빈 레지스트리를 받고 새 문서를 등록·저장하면 실제 레지스트리가 덮어써집니다. 잠금 안에서는 다른 *잠금 보유* 저장자와 충돌하지 않으므로 일시 실패 확률은 낮지만(백신 검사 등), **발생하면 결과가 치명적**입니다.
- **조용한 저장 실패**(F1·F2)는 현실적입니다. 잠금 밖의 읽기가 파일을 열어 둔 순간 잠금 안의 저장이 실패하고, 백그라운드 `reconcile`·`processing.py:987/1038`·`raw_hygiene`는 반환값을 무시합니다. 인덱스가 이미 바뀐 *뒤에* 저장하므로 레지스트리와 인덱스가 어긋납니다(`reconcile`은 다음 5초 틱에 다시 시도해 자가 회복하는 편).
- **macOS에서도 이미 존재하는 문제**: 손상(F3)과 비호환(F3)이 조용히 빈 레지스트리가 되어 *다음 저장이 원본을 지웁니다.* 임시 파일 충돌(F6)도 OS 무관합니다.

## 3. 설계

### 3.1 `core/atomic_io.py` (신규) — 일시적 실패 재시도

```python
def is_transient_os_error(exc) -> bool        # Windows: PermissionError / winerror ∈ {5, 32, 33}; POSIX: errno ∈ {EBUSY, EAGAIN, EINTR}
def retry_io(fn, *, what, total_timeout=2.0, first_delay=0.01, max_delay=0.25)   # 지수 백오프, 상한 2초
def replace_with_retry(src, dst, **kw)        # os.replace 를 retry_io 로 감싼 것
```

- 일시적 오류만 재시도한다. POSIX의 `PermissionError`(진짜 권한 문제)는 재시도하지 않아 2초를 낭비하지 않는다.
- **최종 실패는 삼키지 않고 예외로 올린다.** 삼킬지 말지는 호출자가 정한다.
- 정상 경로(실패 없음)는 `os.replace` 한 번 — 동작·성능 변화 없음.

### 3.2 `save_identity_registry(registry, path, *, strict=False)`

- 저장마다 `tempfile.mkstemp(dir=..., prefix=...)`로 **고유한 임시 파일**에 쓰고 `replace_with_retry`로 교체 (F6 해소).
- 실패 시: 임시 파일 정리, **항상 ERROR 로그**, 비엄격(기본)은 예전처럼 `False`, `strict=True`는 `RegistrySaveError`.
- 기본값이 호환이므로 18개 호출부는 코드 변경 없이 동작한다.

### 3.3 `load_identity_registry(path, *, strict=False)`

| 상황 | 비엄격(기본, 호환) | `strict=True` (읽기→수정→저장 호출자용) |
|---|---|---|
| 파일 없음 | 빈 레지스트리 | 빈 레지스트리 (정상: 처음 시작) |
| 일시적 I/O 오류 | **재시도**(≤2초) | 재시도 |
| 재시도 후에도 읽기 실패 | 빈 레지스트리 + **ERROR 로그** | `RegistryReadError` |
| JSON 손상 | 빈 레지스트리 + **원본 복사본 보존** + ERROR 로그 | `RegistryCorruptError` |
| 스키마 비호환(미래 버전 등) | 빈 레지스트리 + **원본 복사본 보존** + ERROR 로그 | `RegistrySchemaError` |

- **복사본 보존**: `documents.json.corrupt-<sha256 앞 10자>` / `.schema-<버전>-<해시>`. 해시가 이름에 들어가 같은 내용은 한 번만 만든다(멱등). 원본은 **이름을 바꾸지 않고 복사**한다 — 읽는 쪽이 이름을 바꾸면 쓰는 쪽과 경합하기 때문이다.
- 예외들은 `OSError`의 하위 클래스라 기존 `except OSError`가 있는 곳은 의미가 유지된다.

### 3.4 호출자 변경 (구현 2단계)

1. **잠금 안 읽기→수정→저장 경로를 `strict=True`로**: `processing.py`, `index_orchestrator.py`(3곳), `raw_hygiene.py`, 레지스트리를 수정하는 `scripts/*`. 실패하면 *빈 레지스트리 위에 등록*하는 대신 해당 문서/틱을 실패로 처리한다.
2. **저장 반환값을 무시하는 곳**(앱 코드 6곳: `index_orchestrator` 3, `processing.py:987/1038`, `raw_hygiene`; 스크립트 7곳)이 결과를 확인하고 실패를 기록·전파한다.
3. **화면의 수정 동작**(`library.py` 3, `dashboard.py` 1)을 `with registry_lock(path):` 안으로 옮긴다. 지금은 잠금 밖의 읽기→수정→저장이라 백그라운드 저장과의 **lost update**(2026-08-23 유형)가 남아 있다.
4. (선택) 같은 헬퍼를 다른 `os.replace` 사용처에 적용: `tsu_builder._atomic_write_text`(데이터셋, 2026-09-07 사고), `extraction_failures`, `reading_session`, `research_workspace`, `sermon_artifact`.

## 4. 검토한 대안과 기각 사유

| 대안 | 기각 사유 |
|---|---|
| 읽기도 `registry_lock`을 잡게 한다 | `file_lock`은 **재진입이 안 되고** 잠금 안 호출 5곳이 같은 스레드에서 `load`를 부르므로 교착한다. 재진입 구조 도입은 변경 범위가 큼 |
| 읽기 실패 시 "마지막으로 성공한 스냅샷"을 돌려준다 | 대용량 레지스트리의 deepcopy 비용, 그리고 *오래된 스냅샷으로 RMW를 하면 lost update* — 잠금 안 호출자에 위험. 재시도로 일시 오류가 대부분 해소되어 불필요 |
| Windows 전용 API(`ReplaceFile`, `FILE_SHARE_DELETE`로 열기) | `pywin32`/`ctypes` 의존, 플랫폼 분기 증가, macOS에서 시험 불가. 재시도가 더 단순하고 시험 가능 |
| SQLite 등 트랜잭션 저장소로 교체 | 가장 견고하지만 레지스트리 스키마·모든 호출자·마이그레이션을 건드리는 대공사 |
| 손상 파일 이름을 읽는 쪽이 바꾼다(quarantine rename) | 쓰기 쪽과 경합 가능. 복사로 충분 |
| `save`를 무조건 `raise`로 바꾼다 | 18개 호출부 중 13곳이 반환값을 무시하므로 백그라운드·배치가 갑자기 죽을 수 있음. 비엄격 기본 + 호출자 단계 이전이 안전 |

## 5. 검증 (격리 프로토타입, 커밋하지 않음)

`dev` 끝의 `git archive` 복사본에 구현해 측정했습니다.

| 시험 | 수정 전 | 프로토타입 |
|---|---|---|
| 실패 주입 스트레스(`os.replace`에 `PermissionError` 5%, 읽기 `OSError` 3%, 8초, 점검 `08`) | `WARN`: 저장 실패 **9건**(215회 중), 빈 레지스트리 읽기 **220건**(6,841회 중) | **`PASS`: 저장 실패 0, 빈 읽기 0** (저장 206회, 읽기 6,054회) |
| 레지스트리를 쓰는 기존 시험 18개 파일 | — | **169 passed** (수정 없이) |
| 직접 동작 시험 22건 | — | **22/22** (아래) |

직접 동작 시험 22건: 정상 왕복과 임시 파일 잔재 없음 · 손상 JSON(비엄격 빈 레지스트리, 보존 복사본 생성·내용 일치·반복 읽기에 멱등, 원본 불변, strict 예외, ERROR 로그) · 스키마 비호환(동일 항목) · **영구 읽기 실패**(strict 예외, 소요 시간이 상한 2초 준수) · **영구 저장 실패**(False, strict 예외, 원본 불변, 임시 파일 정리, ERROR 로그) · **일시 실패 2회 후 성공**(`replace` 3회 호출) · 저장마다 서로 다른 임시 파일.

대조 실험이 중요합니다. *영구 실패를 재시도가 숨기지 않는다*는 것을 같은 시험 안에서 보였습니다(영구 실패는 2초 안에 예외·`False`로 끝남).

## 6. 구현 계획 (PR 분할)

| PR | 내용 | 위험 |
|---|---|---|
| **PR-1** | `core/atomic_io.py`, `identity_registry`의 load/save(strict 추가, 복사본 보존, 고유 임시 파일, 재시도, 로그), 회귀 시험(프로토타입의 22건을 `tests/`로) | 낮음: 기본값이 호환, 정상 경로 동일 |
| **PR-2** | 호출자 이전(§3.4의 1~3): 잠금 안 경로 strict, 반환값 확인, 화면 수정 동작을 잠금 안으로 | 중간: 앱 동작 변경 — 실패 시 처리 정책 필요, 각 호출부 시험 |
| **PR-3** | 다른 `os.replace` 사용처에 헬퍼 적용, `tsu_builder._atomic_write_text` 포함 | 낮음 |

PR-1만으로도 Windows에서의 일시 실패 흡수, 손상 파일 보존, 임시 파일 충돌 제거가 이뤄집니다. PR-2가 없으면 *영구* 실패가 호출자에서 여전히 무시될 수 있습니다(로그는 남음).

## 7. 인수 기준

1. macOS: 위 22건 + 기존 레지스트리 시험 전체 통과, 정상 경로 성능 불변(저장 1회 `os.replace` 한 번).
2. 점검 `08` 실패 주입 모드에서 저장 실패 0·빈 읽기 0 (프로토타입에서 이미 확인).
3. **Windows 실기: 점검 `08`이 기본 모드(주입 없음)에서도 `PASS`** — 수정 전에 `WARN`이던 환경에서 `PASS`로 바뀌어야 한다. 이것이 설계의 최종 검증이다.
4. 손상 파일을 만들어 앱을 실행했을 때 보존 복사본이 생기고 ERROR 로그가 남는다(수동 확인).

## 8. 한계와 미확인

- **Windows 실기 결과가 없다.** 프로토타입의 재시도 경로는 `DBMA_IO_RETRY_ALL=1`로 macOS에서 *모의*했다. 실제 `winerror` 5/32/33과 `msvcrt`·Defender 동작은 Windows에서 확인해야 한다.
- 재시도 상한(2초)과 백오프는 근거 있는 값이 아니라 **초기값**이다. Windows 측정 후 조정한다. 백신 검사 환경에서는 부족할 수 있다.
- "잠금 안 읽기 일시 실패가 실제로 얼마나 자주 일어나는가"는 측정하지 못했다. 위험은 *확률은 낮고 결과는 치명적*이라는 비대칭으로 판단했다.
- `load` 호출 21곳이 "잠금 밖"이라는 분류는 AST 추정이다.
- PR-2의 정책 결정이 남아 있다: 잠금 안 strict 읽기가 실패할 때 배치를 중단할지, 해당 문서만 실패 처리할지.
- 이 설계는 `schema_version` 마이그레이션 동작(`migrate_registry_schema`가 읽을 때 기본 필드를 채움)은 건드리지 않는다. 다만 이로 인해 "저장한 값 == 읽은 값"이 아닌 점은 수정 전과 같다.

---

## PR-1 구현 시 설계와 달라진 점

- `UnicodeDecodeError`와 최상위가 객체가 아닌 JSON 도 손상으로 취급(복사본 보존, strict 시 `RegistryCorruptError`).
- 저장 시 기존 파일 권한 유지(없으면 POSIX 0644; Windows 는 건드리지 않음). `mkstemp` 기본 0600 으로 권한이 바뀌는 것을 방지.
- 같은 손상은 프로세스당 한 번만 ERROR 로그(`_log_once`). 보존 복사본은 최대 5개(`MAX_PRESERVED_COPIES`).
- 호출부(PR-2)·다른 `os.replace` 지점(PR-3)은 이 PR 범위 밖. 기본값 `strict=False` 라 기존 호출부 동작은 불변.
- 검증: 관련 테스트 25개 파일 207 passed, 신규 12개, `DBMA_IO_RETRY_ALL=1 STRESS_INJECT_FAILURE=1` 스트레스 PASS. Windows 실기 실행은 아직 없음.

## PR-2 구현 메모 (호출부 이전)

- 신규 `mutate_registry(path, mutator)`: 잠금 안에서 strict 읽기 → 수정 → strict 저장. mutator 가 None 이면 저장 생략. 화면 수정 4곳(library 3·dashboard 1)이 사용해 lost update 를 막는다.
- strict 적용: `processing.py`(잠금 안 읽기), `index_orchestrator.delete_raw_source/restore_raw_source`, `raw_hygiene.cleanup_orphaned_document`.
- 정책 결정(미결이던 항목): `reconcile_pending` 은 읽기 영구 실패 시 **그 주기를 건너뛰고** `failed` 에 `*registry*` 항목을 남긴다. 저장 실패 시 `reconciled=0` 으로 보고(다음 주기 재시도). `processing.py` 의 파이프라인 플래그 저장은 반환값으로 `_pipeline_flags_set` 설정.
- UI: registry 오류는 `OSError`로 잡아 `st.error`로 표시(트레이스백 노출 방지). 파일 이동 후 registry 갱신이 실패하는 복구 경로는 그 사실을 사유에 명시.
- 범위 밖(유지): `processing.py` 실패 처리부(예외 삼킴, 저장 실패는 PR-1 로그), scripts/ 7곳(별도).
