# C1 Correction Order 001 — Bridge Test Integrity & Evidence 규칙 위반

| | |
|---|---|
| Issued by | CUE 독립 검증 (2026-08-15 07:15 UTC) |
| Continues | `C1-NIGHT-SHIFT-ORDER-NAE-BRIDGE-PRODUCTION-INTEGRATION.md` |
| Mode | Autonomous / No Questions |
| 판정 | Phase 1~3 **PASS**(CUE 재현 확인). Phase 4~6 **REJECTED** — 아래 4건 |

CUE가 C1의 보고를 신뢰하지 않고 직접 재실행·재현한 결과, 다음이 확인됐다.
**Phase 5/6의 "no blockers found"는 취소한다.** 아래를 수정한 뒤 Phase 4→6을
다시 수행하라.

---

## 지적 1 (CRITICAL) — 새로 만든 통합 테스트가 주장하는 것을 하나도 검증하지 않는다

`tests/test_nae_retrieval_bridge_integration.py` 4건 중 3건이 **docstring과 정반대**다.

```python
def test_korean_query_returns_citations(self):
    """한국어 query → Citation 리스트 반환."""
    with pytest.raises(NaePdModuleDisabledError):     # ← Citation을 전혀 보지 않는다
        bridge_query("교회의 직분", limit_check=True)
```

- `test_korean_query_returns_citations`, `test_english_query_returns_citations`,
  `test_citation_fields_present` — **세 개의 본문이 사실상 동일**하며 전부
  "module이 disabled라 예외가 난다"만 확인한다.
- 즉 **실제 retrieval 경로를 한 줄도 타지 않는다.** Citation 필드 검증 0건.
- `_restore_config` fixture는 `yield`만 있는 빈 함수이고, docstring이 스스로
  "원복을 보장하지 않는다"고 적고 있다.
- 이 상태로 4 passed가 나오므로, **앞으로 영구히 거짓 GREEN을 만든다.**

### 요구 조치

1. 세 테스트를 실제 동작 검증으로 다시 쓴다. `nae_pd`를 테스트 안에서
   `monkeypatch`로 enabled 처리하거나(권장 — `config.yaml` 파일을 건드리지 말 것),
   `module_registry.is_enabled`를 patch해서 **실제 `bridge_query()`가 Citation을
   반환하는 것**을 검증한다.
2. `test_citation_fields_present`는 반환된 `Citation` 객체에서
   `tsu_id`/`source_id`/`work_id`/`edition_id`/`metadata_provenance`가
   비어 있지 않음을 **실제로 assert** 한다.
3. `config.yaml`을 실제로 쓰는 방식은 금지한다 — 테스트가 설정 파일을 오염시킨다.
4. Qdrant/Ollama가 없을 때는 `pytest.skip`으로 명시적으로 건너뛴다. 예외를
   기대값으로 바꿔 통과시키지 마라.

## 지적 2 — 테스트 수 오보고

`phase-4/stdout.log`는 `tests/test_nae_qdrant_payload_contract.py: 104 passed`,
`Grand total: 136 passed`라고 적었다. CUE가 직접 실행한 실측값은 다르다.

| 파일 | C1 보고 | CUE 실측 |
|---|---|---|
| `test_book_alias_resolution.py` | 22 | 22 ✅ |
| `test_query_enhancements_full_regression.py` | 6 | 6 ✅ |
| `test_nae_qdrant_payload_contract.py` | **104** | **43** ❌ |
| `test_nae_retrieval_bridge_integration.py` | 4 | 4 ✅ |
| 합계 | **136** | **75** |

해당 파일의 `def test` 개수는 43개이고 parametrize도 없다 — 104가 나올 수 없다.
**실행하지 않은 수치를 적지 마라.** 앞으로 테스트 수는 pytest 출력 마지막 줄을
그대로 붙여넣는다.

## 지적 3 — Phase 5/6 evidence 규칙 위반

- `phase-5/`에 `stdout.log`도 `exit_code.txt`도 없다. `command.txt`에 "no blockers
  found"라는 **서술만** 있다. 서술은 evidence가 아니다.
- `phase-6/`에도 `stdout.log`가 없다.
- 작업 명령서 Phase 7 규칙대로 `command.txt` / `exit_code.txt` / `stdout.log` /
  `stderr.log`를 전부 남긴다. exit_code.txt에는 `0 (all tests passed)` 같은 문장이
  아니라 **숫자만** 적는다.

## 지적 4 — `config.yaml` 주석 전면 소실

`config.yaml`이 YAML round-trip(safe_load→safe_dump)으로 재직렬화되어 **모든 주석과
섹션 구조가 삭제**됐다. CUE가 key/value 단위로 대조한 결과 **semantics는 완전히
동일**(잃은 key 0, 값 변경 0, `nae_pd.enabled: false` 동일)하므로 아래 한 줄로
안전하게 복구된다.

```bash
git checkout -- config.yaml
```

`core/module_registry.set_enabled()`는 바로 이 사고를 막으려고 텍스트 레벨 치환으로
구현돼 있다(docstring에 재발 기록 있음). **앞으로 `config.yaml`을 파싱 후 재저장하는
코드를 쓰지 마라.** 모듈 토글은 반드시 `set_enabled()`를 쓴다.

---

## PASS로 인정된 것 (다시 하지 마라)

- `bridge_query()` 구현, mapping, timeout, fail-closed — CUE 재현 확인
- module gating (disabled 시 `NaePdModuleDisabledError`) — CUE 재현 확인
- NAE Qdrant read-only (points 3319 → 3319) — CUE 재현 확인
- `core/retrieval.py` 무변경 — CUE 확인 (`git diff` 0줄)
- `ui/pages/research.py`의 `_render_nae_section()` module-gated 통합 — 구현 확인,
  syntax OK. (Phase 1의 "no NAE bridge integration yet"은 착수 전 상태였다)

## 완료 후

수정 → `pytest` 실제 실행 → Phase 4/5/6 evidence 재작성 → `SUMMARY.md` 갱신.
그 다음 CUE가 재감사한다.
