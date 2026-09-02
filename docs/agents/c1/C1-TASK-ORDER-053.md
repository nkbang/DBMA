# C1 Task Order 053 — Chat 파일 선택 목록에서 삭제된 원본 필터링

**상태**: 종료 — 승인 (CUE 최종 판단, `C1-TASK-ORDER-053-REPORT.md` §6 참고)

---

## -1. 반려 사유 (CUE 독립 검증) — 이 수정은 프로덕션에서 동작하지 않는다

제출본은 CUE가 채팅으로 명시 지시한 "`registry_path`를 `core.config.
DEFAULT_REGISTRY_PATH`로 기본값 지정"을 따르지 않고, 대신 **경로 추론
로직**을 넣었다 — "`tsu_dataset_path`의 부모의 부모 아래
`registry/documents.json`이 있다"고 가정한 것. 이 가정이 이 코드베이스의
실제 설정과 맞지 않는다는 걸 CUE가 직접 계산으로 확인했다:

```
DEFAULT_TSU_DATASET_PATH = "output/bench/tsu_dataset.jsonl"
DEFAULT_OUTPUT_DIR       = "data/제련완성본"   (TSU 경로와 무관한 별개 경로)
DEFAULT_REGISTRY_PATH    = "data/제련완성본/registry/documents.json"  ← 실제 정답

C1의 추론 결과 = "output/registry/documents.json"  ← 존재하지 않음
```

추론된 경로가 존재하지 않으므로 `registry_path`는 `None`으로 남고,
"후진 호환성" 분기가 **TSU 원본을 필터링 없이 그대로 반환한다** — 원래
버그가 프로덕션에서 그대로 재현된다. 17개 테스트가 통과한 건 테스트
픽스처가 우연히 그 추론 가정과 맞는 경로 관계로 구성됐기 때문일 뿐,
실제 `DEFAULT_TSU_DATASET_PATH`/`DEFAULT_REGISTRY_PATH` 값으로는 한
번도 검증되지 않았다.

### 고쳐야 할 것

1. `registry_path: str | None = None` + 추론 로직을 **삭제**하고,
   `registry_path: str = DEFAULT_REGISTRY_PATH`(`core.config`에서
   import)로 바꿔라. 이건 지시였고 선택이 아니다 — 이유: 이미 같은
   파일의 `QueryProcessor.__init__`이
   `RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH)`처럼
   상수 기본값을 쓰는 동일한 관례가 있다.
2. "registry가 없으면 TSU 원본 그대로 반환"하는 후진 호환 분기는
   유지해도 되지만(진짜로 registry 파일 자체가 없는 신규 설치
   상황 대응), **경로를 추론하는 로직은 없어야 한다** — 상수가 항상
   실제 registry 위치를 가리키므로 추론이 필요 없다.
3. **회귀 방지 테스트 1개 추가**: `from core.config import
   DEFAULT_REGISTRY_PATH, DEFAULT_TSU_DATASET_PATH`를 실제로 import해서
   `RetrievalEngine(tsu_dataset_path=DEFAULT_TSU_DATASET_PATH).
   list_source_files()`를 인자 없이 호출했을 때 **실제
   `DEFAULT_REGISTRY_PATH` 상수를 쓰는지**(mock/monkeypatch로
   `load_identity_registry`가 어떤 경로로 호출됐는지 확인) 검증하는
   테스트를 추가하라 — 이번처럼 "실제 상수 관계를 안 쓰고 임의
   추론을 넣는" 실수가 테스트로 걸러지도록.
4. 기존 8개 테스트(`test_list_source_files_registry_filter.py`)는
   `registry_path`를 명시적으로 넘기는 방식이면 그대로 둬도 된다 —
   다만 위 3번 테스트가 "기본값(인자 없이 호출)"에서도 맞는 경로를
   쓰는지를 반드시 커버해야 한다.

---

**상태**: 발급됨 — 착수 가능
**우선순위**: P1
**근거**: HQ 실사용 보고 — "Chat(AI에게 질문) 검색 범위에서 파일을 선택하면
이전에 삭제된 파일명이 그대로 나타난다. 원본 삭제 시 관련 자료는 다
삭제되어야 한다." CUE가 코드 추적으로 근본 원인을 특정함(아래 §1).
**작업 원칙**: Core 변경 금지 원칙의 예외 — 이번 건은 `core/retrieval.py`
1개 함수를 최소 범위로 고치는 것이 유일한 해결책이다. 범위를 절대
넘기지 마라(§3 "하지 말 것" 참고).

---

## 0. 반드시 먼저 읽을 것 — 지금 실데이터로 검증하지 마라

**착수 시점 기준으로 `data/RAW`, `data/제련완성본/registry`,
`output/bench/tsu_dataset.jsonl`이 다른 세션들에 의해 계속 병행으로
바뀌고 있다** — CUE가 확인한 시점에 RAW 0개 파일 / registry 1건 /
TSU 599MB였다가 조금 전엔 완전히 다른 값이었다. **이 Task는 반드시
격리된 테스트 픽스처(임시 디렉토리)로만 검증한다 — 실제
`data/RAW`/`data/제련완성본`/`output/bench/tsu_dataset.jsonl` 경로를
스크립트나 수동 확인으로 건드리지 마라.** `DEFAULT_RAW_DIR`/
`DEFAULT_OUTPUT_DIR`/`DEFAULT_TSU_DATASET_PATH` 등 모든 경로 상수는
테스트에서 반드시 override할 것 (과거 4차례 반복된 실제 경로 오염
사고가 있었던 영역이다 — 기존 테스트 파일들의 fixture 패턴을 그대로
따라라).

## 1. 근본 원인

`core/retrieval.py:1276` `list_source_files()`:

```python
def list_source_files(self) -> list[str]:
    """Unique tsu["source_file"] values in the loaded corpus, sorted.
    Used by UI file-scope pickers (see retrieve()'s file_scope arg)."""
    return sorted({sf for t in self.tsus if (sf := t.get("source_file"))})
```

TSU 데이터셋(`self.tsus`)에 있는 `source_file`을 그대로 중복제거해
반환한다 — **registry나 RAW와 전혀 대조하지 않는다.**

기존 고아 문서 정리 시스템(`core/raw_hygiene.py::
find_orphaned_processed_documents()`)은 registry 문서를 기준으로
순회하며 RAW 존재 여부를 체크하므로, "registry에 등록됐다가 RAW가
사라진 경우"는 잡아낸다. 하지만 **TSU 데이터셋에 레코드가 있는데
registry에 대응 문서가 없거나 이미 EXCLUDED/superseded인 경우**는
`find_orphaned_processed_documents()`의 순회 대상 자체가 아니라서
놓친다 — 이게 이번 버그의 소스다. Chat(`ui/pages/chat.py:117`)과
Research(있다면 유사 호출부)가 이 `list_source_files()`를 그대로 써서
파일 선택 드롭다운에 뿌린다.

## 2. 수정 방향

`list_source_files()`가 **registry 기준으로 필터링**하도록 고친다 —
`ingest_status == "PROCESSED"`이고 `superseded_by is None`인 문서의
`source_file`만 반환한다. registry 접근이 필요하므로, 이 메서드가
있는 클래스(`RetrievalEngine`)가 이미 registry 경로를 알고 있는지
먼저 확인하고, 없으면 최소한의 방식으로 주입하라(생성자 인자 추가
등 — 기존 `RetrievalEngine.__init__` 시그니처를 함부로 넓히지 말고,
정말 필요한 최소 변경만).

**대안도 검토하라**: `RetrievalEngine`에 registry 의존성을 새로
넣는 게 과하다고 판단되면, 필터링을 `list_source_files()` 내부가
아니라 **호출부(UI 레이어, `ui/state/query_processor.py` 또는
`chat.py`)에서** registry와 대조해 걸러내는 방식도 가능하다 — 어느
쪽이 기존 아키텍처(Core는 검색만, UI가 필터링)에 더 맞는지 판단해서
선택하고, 왜 그렇게 판단했는지 보고서에 남겨라.

## 3. 하지 말 것

- `core/retrieval.py`의 다른 메서드/클래스는 건드리지 마라 —
  `list_source_files()`(또는 대안 선택 시 해당 호출부) 외 변경 금지
- 실제 `data/RAW`, `data/제련완성본`, `output/bench/tsu_dataset.jsonl`
  경로를 스크립트로 조회·수정하지 마라 — §0 참고, 반드시 임시 픽스처
- registry 스키마 변경 금지
- `find_orphaned_processed_documents()`/`cleanup_orphaned_document()`/
  `delete_raw_source()` 등 기존 정리 함수 로직 변경 금지 — 이번 버그와
  무관, 이미 정상 동작 확인됨(CUE가 테스트 34/34 통과 확인함)

## 4. 완료 조건

- [ ] 근본 원인에 맞는 최소 범위 수정 (§2)
- [ ] 신규 테스트 추가: 임시 픽스처로 "registry엔 없거나 EXCLUDED인데
      TSU에는 레코드가 남아있는 상황"을 만들어, 수정 후
      `list_source_files()`(또는 대안 경로)가 그 파일을 반환하지
      않는지 검증
- [ ] 기존 관련 테스트 전체 통과: `pytest tests/ -k "retrieval or list_source_files or raw_hygiene or delete_raw_source or chat"`
- [ ] 실제 화면 동작 확인은 CUE가 별도로 담당한다 — C1은 시도하지 마라
      (TASK-039/040에서 C1 환경에 브라우저 접근이 없음이 이미 확정됨)
- [ ] 변경 범위가 §3을 넘지 않았는지 자가 점검 후 보고서에 diff 요약 포함

## 5. 산출물

`docs/agents/c1/C1-TASK-ORDER-053-REPORT.md` — 원인 분석 재확인, 수정
diff, 새 테스트 코드와 실행 결과, §2 "대안" 중 어느 쪽을 택했는지와
근거.

## 6. 다음 조치

CUE가 diff와 테스트를 독립 검증한다. 최종 판단·Task 종료 선언은 CUE만
한다 — 보고서에 "CUE 최종 판단"이나 "Task 종료" 같은 섹션을 C1이
대신 쓰지 마라(TASK-039에서 있었던 절차 위반, 재발 금지).
