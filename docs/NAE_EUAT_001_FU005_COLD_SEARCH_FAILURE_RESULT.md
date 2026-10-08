# FU-005 결과: 콜드 상태 검색 실패 원인

기준일 2026-09-29. 근거: [NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md](NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md) FU-005. 조사는 읽기 전용이었고 앱·설정·코드는 변경하지 않았다. 측정 호출로 Ollama에 bge-m3가 로드됐다(무해, 만료 시 자동 해제).

## 결론

- 공개 패널의 "결과 없음"은 **원인 확정**: 하드 타임아웃 3초 초과가 예외로 삼켜져 빈 결과로 표시됨.
- 채팅의 "검색 중 문제"는 **확정하지 못함**: 앱 로그가 남지 않고, 임베딩 타임아웃은 아님이 확인됨.
- 새 발견: 같은 Ollama에서 두 대형 모델이 서로를 반복 evict하여 EUAT 지연 측정이 환경 경합에 오염됨.

## 1. 공개 패널 "결과 없음" (확정)

**OBSERVED**: 공개 패널이 Dagg·1689·Hiscox·Fuller·EUAT-05·"아브라함" 6회 연속 "결과 없음"을 반환.

**EVIDENCE**
- `NAE/retrieval_adapter.py`: 하드 타임아웃 `_HARD_TIMEOUT_MS = 3_000`. 임베딩과 Qdrant 검색이 3초를 나눠 쓴다. `bridge_query`, `bridge_query_paragraphs` 모두 `except Exception` → `return []`(fail-closed)로 예외를 삼킨다.
- Ollama 로그(`/private/tmp/ollama_serve.log`): 17:00:17~17:01:36 `POST /api/embeddings` 6건이 전부 정확히 3.03초, HTTP 499로 종료. 건수·시각이 6회 시도와 일치.
- 17:03:23 임베딩 호출 36.5초(bge-m3 콜드 로드), 이후 35~60ms. 워밍 후 UI는 10건 반환.
- 어댑터가 예외를 삼키므로 UI의 오류 경고 경로(`_execute_nae_retrieval`의 `st.warning`)는 작동하지 않는다.

**IMPACT**: bge-m3가 상주하지 않은 첫 검색이 3초를 넘기면 조용히 빈 결과가 된다. 사용자는 오류가 아닌 "결과 없음"으로 보고 자료 부재로 오해한다.

**RECOMMENDATION**: 타임아웃과 부재를 UI에서 구분 표시(FU-003에 반영). 콜드 로드를 감안한 타임아웃 정책 또는 bge-m3 사전 로드를 검토. 타임아웃 값(ADR-024 §G) 변경은 ADR Amendment 대상일 수 있다.

## 2. 두 대형 모델의 상호 evict (지연 원인)

**OBSERVED**: Ollama가 오늘 두 대형 모델을 번갈아 evict.

**EVIDENCE**
- `predicted to exceed available memory, evicting` 로그 오늘 18건: 예상 49.6 GiB/ctx 32,768(앱의 `my-theology-bot-v2`) 13건, 20.6 GiB/ctx 131,072(Cline 모델 `qwen3.6:35b-DBMAcode-Cline`) 5건. 16:35, 16:39, 16:42, 16:45 등 3~4분 주기.
- 서버 설정: `KEEP_ALIVE=5m`, `NUM_PARALLEL=1`, `MAX_LOADED_MODELS=0`(자동).
- EUAT 답변 생성 시간과 일치: `/api/generate` EUAT-04 시점 6분 51초, EUAT-05 시점 5분 31초.
- 같은 Ollama에 다른 클라이언트(`/api/chat`, Cline 모델)가 16:30~16:57 사이 수십 회 요청.

**IMPACT**: EUAT 응답 지연(90초~8분)은 상당 부분 동시 사용 경합 때문이다. 답변 내용 판정에는 영향이 없으나 지연 측정은 오염됐다. 요청 주체가 C1인지는 로그로 확정하지 못했다.

## 3. 채팅 "검색 중 문제" (미확정)

- 실패 구간(16:36~16:39)에 `/api/embeddings` 요청이 한 건도 없다 → 임베딩 타임아웃이 원인이 아님.
- 검색 텔레메트리의 채팅 행은 모두 `embedding_time_ms = 0.0`, route `hybrid`. 채팅 검색이 임베딩 없이 어휘 기반으로 도는지는 코드로 확인하지 않았다.
- 4회 연속 실패 후 새로고침 뒤 4회 연속 성공.
- 앱 stdout이 어디에도 저장되지 않아 예외 트레이스가 없다(Streamlit이 `&`로 기동).

## 4. 부수 관찰

- Ollama 로그가 `/private/tmp/ollama_serve.log`에 있고 재부팅 시 사라진다. 표준 `~/.ollama/logs/server.log`는 14줄뿐이다.
- 단독 콜드 재현은 1.1초로 3초 이내였다. 실패 조건은 단순 콜드가 아니라 "대형 모델 상주·evict 진행 중" 경합 상황이다.

## 남은 일

- 채팅 실패는 앱 로그를 확보한 뒤 재현해야 확정 가능. 앱 stdout을 파일로 남기는 것은 설정 변경이라 승인이 필요하다.
- FU-003에 "빈 결과와 오류의 UI 구분" 항목 추가를 권고.
