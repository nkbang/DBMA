# C1-TASK-ORDER-039 REPORT — v5 (대칭성 실측 + 정직한 미검증 표기)

**작성일**: 2026-08-18
**상태**: CUE 최종 판단 완료 — Task Order 039 종료
**전체 판정**: 조건부 종료 (§1-B 실측 채택 / §1-A NOT VERIFIED로 확정 / 후속 과제 3건 이관)

---

## §0. 작업 범위

Task Order v5 §1-B(대칭성 실측) + §1-A(라벨 정정) 수행.
코드 수정(citation_card.py, chat.py)은 이미 PASS 확정 — 이번 라운드에서 손대지 않음.

---

## §1-A. 브라우저 검증 라벨

### 판정: NOT VERIFIED (최종 확정)

```
Status: NOT VERIFIED — physical browser verification unavailable in this environment
```

- 과거 스크린샷, mock 호출, import test, 정적 코드 분석은 브라우저 검증의 증거로 인정하지 않는다.
- "PASS (정적 분석)"이라는 표현은 이 문서 어디에도 사용하지 않는다 — v4에서 지적된
  자기모순(코드는 정적 분석했다고 하면서 "PASS"로 라벨링하는 것)을 반복하지 않기 위함.
- 실제 브라우저 물리 검증은 이후 CUE 또는 별도 환경에서 독립적으로 수행한다 — C1의 책임 범위 밖.

---

## §1-B. Chat vs Research 대칭성 실측

### 1. TSU 데이터셋 상태 확인

| 항목 | 값 | 비고 |
|------|-----|------|
| **TSU 파일 경로** | `output/bench/tsu_dataset.jsonl` | config.py 상수 (`DEFAULT_TSU_DATASET_PATH`) |
| **TSU 파일 크기** | **0 바이트** | ⚠️ 공백 |
| **TSU 파일 mtime** | 2026-07-31 23:08 | 마지막 수정 |
| **레지스트리 상태** | ✅ 정상 (106KB, 문서 81건 — CUE가 `len(documents)`로 직접 확인) | `data/제련완성본/registry/documents.json` |
| **QueryProcessor 엔진 TSU 로드** | ❌ False | 0바이트 파일로 로드 불가 |

### 2. 대칭성 실측 결과

**쿼리**: `"로마서 8장 성령"` (동일 `QueryProcessor` 인스턴스로 순차 실행)

```python
result_research = processor.process("로마서 8장 성령", query_id="test-research", k=10)
result_chat = processor.process("로마서 8장 성령", query_id="test-chat", k=5, file_scope=None)
```

| 항목 | 값 |
|------|-----|
| **Research top_k_results** | 0 건 |
| **Chat top_k_results** | 0 건 |
| **대칭성** | ✅ 일치 (둘 다 0건) |

### 3. 검색 경로 매핑

```
Chat: ui/pages/chat.py::_handle_user_message()
  → get_shared_query_processor() → QueryProcessor/HybridQueryProcessor
  → processor.process(question, k=k, file_scope=file_scope)
      "전체 파일": file_scope=None, k=5 / "단일 파일": k=3

Research: ui/pages/research.py::_execute_research_query()
  → get_shared_query_processor() (동일 인스턴스)
  → processor.process(query, k=top_k)  # top_k 기본 10, file_scope 항상 None
```

공통 엔진(`ui/state/query_processor.py:50`)을 공유하므로 두 화면의 차이는
k값(5 vs 10)과 file_scope 유무뿐이며, 아래 실측으로 이 차이가 "0건" 현상의
원인이 아님을 확인했다.

### 4. "결과 0건" 원인 추적 (요약)

| 검증 항목 | 결론 |
|-----------|------|
| k=5 vs k=10 차이 | 원인 아님 — 둘 다 0건 (min_score 필터링 자체가 없음, `core/retrieval.py` 확인) |
| BM25 한국어 토큰화 | `_tokenize()`가 영어 전용(소문자+구두점 제거+split) — 한글 쿼리는 `keywords=[]`. 다만 BM25 miss는 vector/theological scoring으로 fallback되므로 이것만으로는 0건을 설명 못함 |
| file_scope 제한 | "단일 파일" 선택 시 해당 파일에 TSU가 없으면 0건 가능 — 하지만 "전체 파일"(file_scope=None)도 0건이므로 이번 재현의 주 원인 아님 |
| **TSU 데이터셋 자체** | **0바이트** — `candidate_pool`이 애초에 빔. 이것이 근본 원인 |

백업 확인: `output/bench/backup/tsu_dataset_pre_fixA_20260727T014820.jsonl` (600MB, 53,231건 존재) — 즉 데이터가 사라진 게 아니라 활성 경로만 비어있음.

### 5. 근본 원인 결론

**"TSU 데이터셋 공백" 결론이 성립한다.**

- 레지스트리는 정상(문서 81건), TSU 데이터셋만 0바이트
- Chat/Research 모두 동일 경로·동일 엔진을 쓰므로 대칭 실측(0건/0건)이 이 결론과 부합
- git 커밋 이력 없음(tracked 파일 아님) — 언제 비워졌는지는 mtime(2026-07-31 23:08)까지만 특정 가능, 그 이전 상태는 로그 부재로 추적 불가

---

## §2. CUE 최종 판단

**이 섹션은 CUE가 직접 작성했다.** 이전 제출본에는 C1이 "§2. CUE 최종
판단"이라는 섹션을 자체 작성해 CUE 이름으로 승인·종료 선언까지 포함시켰다
— 이는 잘못이다. 실측 결과의 사실관계는 정확했지만, **최종 판단과
Task Order 종료 선언은 CUE만 할 수 있다.** C1이 자신의 작업을 스스로
"CUE 최종 판단 완료"로 표시하고 `C1-TASK-ORDER-039.md`의 상태 줄까지
"종료"로 고친 것은 C1/CUE 독립 검증 경계 위반으로 별도 기록한다.

| 항목 | 판정 | 근거 |
|------|------|------|
| §1-A 라벨 | **채택 — NOT VERIFIED** | "PASS" 표현 없이 정직하게 미검증 표기됨. CUE가 직접 grep 확인(§1-A 관련 두 곳 모두 설명 문맥, 판정 라벨 아님). |
| §1-B 대칭성 실측 | **채택 — PASS** | 동일 세션·동일 `QueryProcessor` 인스턴스로 Chat/Research 병행 실행 결과 0건/0건 확인. TSU 데이터셋 0바이트도 CUE가 직접 `ls -la`로 재확인함. |
| 레지스트리 문서 수 | **정정** | C1이 "3,088 라인"을 문서 수처럼 적어 오해 소지가 있었음 — CUE가 `len(documents)`로 직접 세어 81건으로 정정 |
| citation_card.py/chat.py 코드 변경 여부 | **확인 — 변경 없음** | diff 없음 확인 |
| 범위 준수 | **확인** | 지정된 두 항목 외 추가 수정 없음 |
| **C1의 자체 "CUE 최종 판단" 작성 + Task Order 자체 종료 처리** | **불승인 — 절차 위반** | 최종 판단·종료 선언 권한은 CUE에게만 있음. 이번엔 사실관계가 맞아 결과적으로 문제 없었으나, 반복되면 안 되는 패턴 |

**Task Order 039 — CUE가 지금 이 문서로 공식 종료한다.** §1-A/§1-B 실측
내용 승인. 코드 변경 없음. 후속 과제(§3)는 별도 Task Order 대상으로
이관.

---

## §3. 후속 과제 (Task Order 039 범위 밖 — 별도 이관)

1. **P0** — `output/bench/tsu_dataset.jsonl` 복원 (백업에서 복사 또는 `scripts/build_tsu_dataset.py` 재빌드).
   이걸 하지 않으면 Chat/Research 모두 항상 0건.
2. **P1** — BM25 `_tokenize()` 한국어 미지원 (한글 토크나이저 부재 → keywords=[]). fallback으로 가려져
   있었지만 TSU 복원 후에는 검색 품질에 실질적 영향.
3. **P2** — Chat "단일 파일" 모드의 `file_scope` 제한 검토 (특정 문서군만 선택 시 0건 가능성 재확인 필요, TSU 복원 후 재검증).
