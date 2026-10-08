# CW-05 Corrective WO — search_cache.py SQLite Thread-Safety

- **Status**: `[✓ HQ] CLOSED` (2026-09-29)
- **선행**: [GS-FINAL-RPV-CW04-RUNTIME-INVESTIGATION.md](GS-FINAL-RPV-CW04-RUNTIME-INVESTIGATION.md)
  §3 — CW-04와 무관한 pre-existing infrastructure defect로 확정, 별도
  corrective work로 분리
- **목적**: `core/search_cache.py`의 SQLite thread-safety 결함을 최소
  변경으로 수정한다. AD-01/AD-02, GS, retrieval ranking과 무관한
  독립 수정이다 — CW-04 범위에 섞지 않는다.

---

## 1. 결함 위치 (CUE가 코드로 직접 확인)

`core/search_cache.py::_L2SqliteCache.__init__()` (113-117번째 줄):

```python
def __init__(self, db_path: str | Path) -> None:
    self.db_path = str(db_path)
    self._conn = sqlite3.connect(self.db_path)   # <- 115번째 줄, 원인
    self._conn.executescript(self._SCHEMA)
    self._conn.commit()
```

`sqlite3.connect()`를 `check_same_thread` 인자 없이 호출한다 — Python
`sqlite3` 모듈의 기본값은 `check_same_thread=True`이며, 이 경우 connection
을 생성한 스레드가 아닌 다른 스레드에서 그 connection을 사용하면
예외가 발생한다.

## 2. 재현된 실제 오류 (CUE 실측, Runtime Investigation에서 확보)

```
core/search_cache.py:123
sqlite3.ProgrammingError: SQLite objects created in a thread can only
be used in that same thread. The object was created in thread id
12969013248 and this is thread id 13664940032.
```

`HybridQueryProcessor`(그 안의 `SearchResultCache` → `_L2SqliteCache`)
가 Streamlit `st.session_state`에 캐시되어 세션 전체에서 재사용되는데
(`ui/state/query_processor.py::get_shared_query_processor()`),
Streamlit의 스크립트 재실행 모델에서 이후 요청이 다른 스레드에서
처리되면 이 connection을 그대로 재사용하려다 예외가 발생한다. 두
번째 질문(RPV-06b) 처리 중 실측 재현됨.

## 3. 목표

L2 SQLite 캐시가 여러 스레드에서 안전하게 호출 가능해야 한다. 기존
L1(메모리)/L2(SQLite) 2-tier 캐시 구조, TTL 의미, cache key 구성
(`make_cache_key()`), invalidation 방식(dataset fingerprint 포함)은
전혀 변경하지 않는다 — 오직 SQLite connection의 스레드 안전성만
고친다.

## 4. 허용 파일

`core/search_cache.py`만. **다른 파일은 건드리지 않는다**
(`ui/pages/chat.py`, `ui/state/query_processor.py`,
`core/hybrid_candidate_pipeline.py`, `core/evidence_adapters/tsu_adapter.py`,
`core/identity_registry.py`, `core/retrieval.py`, `core/grounded_*.py`
전부 무변경).

## 5. 구현 방향 (제안, C1이 구체화·CUE가 검증)

최소 변경 원칙에 따라 다음 중 하나 또는 조합을 C1이 제안한다:

1. `sqlite3.connect(self.db_path, check_same_thread=False)` — 가장
   최소 변경. Python의 `sqlite3` 모듈이 기본적으로 링크되는 SQLite
   라이브러리는 보통 "serialized" threading mode로 컴파일되어 있어
   `check_same_thread=False`만으로 안전한 경우가 일반적이나, C1은
   이를 가정하지 말고 실제 동시 접근 시나리오로 검증해야 한다.
2. 방어적으로 `threading.Lock`을 `_L2SqliteCache`의 `get()`/`set()`/
   `clear()`/`purge_expired()` 호출부에 추가해 직렬화 — 1번만으로
   동시성 테스트가 불안정하면 추가한다.
3. (대안, 1·2가 부적절하다고 판단되면) 스레드-로컬 connection 패턴 —
   단, 이는 구조 변경 폭이 커지므로 1·2로 충분한지 먼저 확인 후
   최후 수단으로만 고려한다.

**CUE는 특정 구현을 강제하지 않는다** — C1이 제안하고 CUE가
동시성 시나리오로 직접 검증한다.

## 6. 금지 사항

- `_L1MemoryCache`, `SearchResultCache`(상위 클래스), `make_cache_key()`,
  `normalize_query()` 로직 변경 금지 — 오직 `_L2SqliteCache`의
  connection 생성/스레드 안전성 부분만 수정
- cache key 형식, TTL 의미, invalidation 방식 변경 금지
- 새로운 캐시 계층(L3 등) 추가 금지
- 다른 파일에 대한 "함께 정리" 성격의 리팩토링 금지
- production 데이터(registry, TSU dataset) 접근/수정 금지 — 이 결함
  수정은 코드 레벨 작업이며 데이터에 영향 없어야 한다

## 7. Gate 0 (예외 없음, 승계)

```text
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
```

Expected: `/Users/David/DBMA-cw04-nae-app`, branch
`feat/cw04-ad01-ad02-nae-app`, HEAD `d202238d6b9fa9d8326425f55c453805999a07d2`
(CW-04 구현이 이미 커밋된 상태 위에서 작업). `/Users/David/DBMA`(main
checkout)는 이번에도 접근/수정하지 않는다. 불일치 시 예외 없이 STOP.

## 8. 테스트 요구사항

1. **동시성 재현 테스트(신규)**: 별도 스레드에서 동일
   `_L2SqliteCache`/`SearchResultCache` 인스턴스에 `get()`/`set()`을
   호출해 `sqlite3.ProgrammingError`가 더 이상 발생하지 않음을 확인
   (수정 전 코드로 먼저 재현되는지 확인한 뒤, 수정 후 통과하는 것을
   보여주는 것이 이상적)
2. **기존 캐시 동작 regression**: L1 hit, L2 hit(L1 backfill 포함),
   TTL 만료, `clear()`, `purge_expired()`, cache key 구성 — 기존
   동작 전부 그대로 유지되는지 확인
3. **격리 환경에서 RPV-06b 재실행**: `/Users/David/DBMA-cw04-nae-app`
   의 G5 격리 환경(이미 구성됨 — `output/bench`, `data/제련완성본/registry`)
   에서 실제 Streamlit runtime으로 RPV-06b 정본 질문을 재실행해
   예외 없이 응답이 생성되는지 확인. RPV-06a도 회귀 확인(정상
   응답이었던 것이 계속 정상인지)

## 9. Production Safety (재확인)

```text
production registry path: /Users/David/DBMA/data/제련완성본/registry/documents.json
```
작업 전/후 mtime·SHA-256을 반드시 측정해 보고한다(불변이어야 함 —
이번 수정은 코드 레벨이므로 registry에 영향을 줄 이유가 없다).

## 10. C1 보고 형식

```text
## 1. Execution Environment
pwd: / branch: / HEAD: / git status:

## 2. Root Cause Confirmation
reproduced before fix: YES/NO
error message:

## 3. Fix
file changed: core/search_cache.py
approach: (§5의 어느 방식을 택했는지 + 이유)
diff:

## 4. Concurrency Test
test added: YES/NO
result:

## 5. Regression
existing search_cache tests: passed/failed
other affected tests: passed/failed

## 6. RPV-06b Runtime Re-verification
worktree: (격리 환경)
query: (정본 그대로)
result: (raw 응답 텍스트)

## 7. RPV-06a Regression Check
result:

## 8. Production Safety
registry mtime before/after:
registry SHA-256 before/after:
mutation: NO/YES

## 9. Changed Files
...

## 10. Commit
...

## 11. C1 Disposition
IMPLEMENTATION COMPLETE / HOLD
```

GREEN/HQ APPROVED/CUE VERIFIED 같은 표현 사용 금지 — C1은
Implementation Complete까지만 보고한다.

## 11. 진행 순서

```text
CW-05 Scope (본 문서)
    ↓
Gate 0 확인
    ↓
C1 구현(§5 제안 + §6 금지사항 준수)
    ↓
C1 동시성 테스트 + regression + RPV-06b 재검증(§8)
    ↓
C1 보고(§10)
    ↓
CUE 독립 검증(코드 diff, 동시성 재현, RPV-06a/06b 라이브 재실행,
              production registry 불변 확인)
    ↓
HQ 최종 결정
    ↓
[승인 시] CW-04 Gate 2B 최종 판정으로 복귀
```

## 12. HQ 최종 판정 (2026-09-29, CLOSED)

```text
search_cache.py 결함 원인                [✓] 확인
허용 파일 범위                           [✓] 단일 파일
check_same_thread=False                 [✓]
threading.Lock                          [✓] 적용 및 검증
cache key/TTL/invalidation 변경 없음      [✓]
동시성 + 기존 테스트                      [✓] 23/23 PASS
RPV-06b 실제 격리 Streamlit runtime       [✓] CUE 직접 검증
RPV-06a 회귀                            [✓]
Production registry                     [✓] mtime/hash 불변
Production mutation                     0
CUE 독립 검증                            [✓] GREEN

CW-05                                   [✓ HQ] CLOSED
```

**C1 보고 형식 문제 — 기술 결함과 분리 기록**: C1이 WO §10이 요구한
실제 Streamlit runtime RPV-06b 재검증과 production registry mtime/
hash 증거를 보고하지 않았다. CUE가 baseline/격리 환경에서 직접
검증해 완료 조건 충족을 증명했으므로 CW-05 자체를 HOLD할 이유는
없으나, **"WO의 완료 조건을 실제 수행하지 않고 단위 테스트만으로
Implementation Complete를 보고하는 패턴"이 CW-04 Gate 2B 때도
반복됐다**(§Gate 2B Independent Audit 최초 시도, §Runtime
Investigation 참고) — C1의 향후 "Implementation Complete" 보고
신뢰도는 이 패턴을 감안해 별도 관리하고, CUE는 매번 WO에 명시된
전체 완료 조건이 실제로 수행됐는지 독립적으로 재확인한다.

## 13. 현재 상태

```text
CW-05                 [✓ HQ] CLOSED
CW-04 Gate 2B         [✓ HQ] CLOSED (아래 별도 기록 참고)
```
