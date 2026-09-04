# C1 Correction Order 003 — cli_driver.py: 등록 결과가 전혀 영구 저장되지 않음

| | |
|---|---|
| Issued by | CUE 독립 검증 (2026-08-15 07:45 UTC) |
| Continues | `C1-NIGHT-SHIFT-ORDER-002-NAE-PRODUCTION-INGESTION.md` |
| 대상 | Phase 3/4 (파일럿 1건 + 확대 9건, 전부 "PASS" 보고됨) |
| 판정 | **10건 전부 exit 0/QUALITY_PASSED — 그러나 등록 기록 자체가 남지 않는다.** |

---

## 좋은 소식 먼저 — 정직하게 보고한 부분

`pilot-summary.json`에 C1이 스스로 이렇게 적어놨다:

```json
"registration_state_json": "NOT WRITTEN (cli_driver uses temp path for state_store)"
```

Correction Order 001 때와 달리 이번엔 **문제를 숨기지 않고 직접 evidence에
남겼다.** 좋은 패턴이다, 계속 이렇게 해라. 다만 원인 설명 한 줄
(`"production mutation via manifest_writer.write_entry() to authority files"`)은
**틀렸다** — 아래 §2에서 CUE가 직접 확인한 내용으로 정정한다.

## 무엇이 실제로 영구 저장됐는지 CUE가 직접 확인함

| 항목 | 상태 | 확인 방법 |
|---|---|---|
| `raw_checksum_ledger.jsonl` | ✅ 정상 — 22줄, 10건 전부 preserve+reverify 기록됨 | `wc -l` + `tail` 직접 확인 |
| raw 파일 chmod(0o444) | ✅ 정상 — Dagg의 `hocr.html` 실제로 `-r--r--r--` | `ls -la` 직접 확인 |
| `NAE/authority/*.yaml` | ✅ 무변경(의도대로) | `git status` 무변화 확인 |
| `registration_state.json` | ❌ **미존재** — 10건의 상태 전이 이력이 전부 소실됨 | 파일 자체가 없음 |
| `source_manifest.yaml`(등록 카탈로그) | ❌ **어디에도 존재하지 않음** — temp dir에 썼다가 프로세스 종료와 함께 소실 | `find`로 전체 검색해도 없음 |

## Root cause (CUE가 코드로 확정 — 재조사 불필요)

`cli_driver.py::main()`:

```python
tmp_work = Path(tempfile.mkdtemp(prefix="cli_driver_"))
manifest_path = tmp_work / "source_manifest.yaml"
state_store, exception_queue = _build_state_store_and_queue(tmp_work)
```

`_build_state_store_and_queue()`는 `work_dir / "reg_state.json"`을 쓴다 —
즉 **매 호출마다 새 임시 디렉터리에 state store를 만들고, 프로세스가
끝나면 그 디렉터리가 그대로 버려진다.** `RegistrationStateStore`는
원래 `config.DEFAULT_REGISTRATION_STATE_PATH`를 기본값으로 쓰도록 설계되어
있다(`state.py:46`, `path: Path = config.DEFAULT_REGISTRATION_STATE_PATH`) —
cli_driver.py가 그 기본값을 쓰지 않고 일부러 temp path를 넘긴 것이 버그다.

C1의 원인 설명(`manifest_writer.write_entry()`가 authority 파일에 쓴다)은
**틀렸다.** `manifest_writer.write_entry(manifest_path, entry)`는 호출자가
넘긴 `manifest_path`에만 쓴다 — cli_driver.py가 넘긴 그 경로는 위와 같은
temp path다. Authority 파일(`NAE/authority/*.yaml`)은 `_load_existing_ids()`가
**읽기만** 한다 — 아무도 쓰지 않는다(CUE가 `git status`로 확인, 무변화).

## 수정 지시 (2건 — 위험도가 다르다)

### 수정 1 (안전, 즉시 적용) — `registration_state.json`

`_build_state_store_and_queue()` 또는 `main()`에서 state_store 생성 시
`config.DEFAULT_REGISTRATION_STATE_PATH`를 사용해라(이건 이미 설계된
기본 동작 그대로 쓰는 것뿐이다 — `RegistrationStateStore(config.
DEFAULT_REGISTRATION_STATE_PATH)` 또는 인자 생략). `exception_queue`도
동일하게 `config.DEFAULT_EXCEPTION_QUEUE_PATH`를 쓴다.

### 수정 2 (판단 필요했음 — CUE가 확인 후 방향 확정) — manifest_path

`resources/theological_sources/baptist/source_manifest.yaml`을 열어봤다 —
**이건 다른 목적의 파일이다**: `local_path: null`, `status:
approved_for_acquisition` 같은 필드를 가진, 사람이 수작업으로 큐레이션한
**"확보 예정 후보" 카탈로그**이며, 지금 등록하려는 10건(Dagg/Hiscox/Fuller)은
그 안에 아예 없다. `manifest_writer.write_entry()`가 쓰는 entry 스키마(실제
등록 결과: source_id/checksum/page_count 등)와 다르다 — 여기 잘못 쓰면
사람이 큐레이션한 문서를 오염시킨다. **이 파일에 쓰지 마라.**

대신 `config.py`에 신규 상수를 추가해라(automation 소유 상태 파일들과
같은 위치, 기존 패턴과 일관):

```python
DEFAULT_SOURCE_MANIFEST_PATH = STATE_DIR / "source_manifest.yaml"
```

`cli_driver.py`가 이 경로를 `manifest_path`로 사용하게 한다. 이건 새
아키텍처가 아니라 이미 있는 `DEFAULT_CHECKSUM_LEDGER_PATH`/
`DEFAULT_REGISTRATION_STATE_PATH`와 정확히 같은 패턴을 하나 더 추가하는
것뿐이다.

## 재실행 (안전 확인됨 — CUE가 직접 검증)

10건 전부 **다시 처리해도 안전하다**:

- `raw_preservation.preserve()`의 duplicate 판정은
  `find_duplicate_source_id(checksum, exclude_source_id=source_id)`로 **자기
  자신은 제외**한다 — 같은 source_id로 재실행해도 거짓 duplicate로 잡히지
  않는다(코드로 확인).
- `os.chmod(raw_path, 0o444)`는 이미 0o444인 파일에 다시 걸어도 아무 부작용
  없다(멱등).
- 체크섬 원장은 append-only이므로 재실행해도 기존 줄은 그대로 남고 새
  `reverify` 이벤트만 추가된다 — 데이터 손실 없음.

절차:
1. 위 수정 2건 적용.
2. `pilot-queue-backup/` 대신 방금 처리했던 10건을 **다시** 큐에 넣어(파일이
   `done/`에 있으므로, 원본 queue item JSON을 복사해서 재사용) 처음부터
   다시 실행한다.
3. **이번엔 진짜로** `NAE/pipeline/registration/state/registration_state.json`에
   10개 항목이 `QUALITY_PASSED`로, `NAE/pipeline/registration/state/
   source_manifest.yaml`에 10개 entry가 기록되는지 evidence로 남긴다.
4. `pilot-summary.json`의 틀린 원인 설명(authority 파일 언급)을 정정해서
   다시 쓴다.

## 절대 하지 말 것 (추가)

```
❌ resources/theological_sources/baptist/source_manifest.yaml에 쓰기
❌ resources/theological_sources/ 아래 어떤 파일도 건드리기
❌ NAE/authority/*.yaml에 쓰기 (읽기 전용 유지)
```
