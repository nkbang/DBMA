# FU-003 Build Report: 신뢰 표시 결함 수정

작성일 2026-09-29. 근거: [후속 Task Order](NAE_EUAT_001_FOLLOWUP_TASK_ORDERS.md) FU-003, [EUAT-001 결과](NAE_EUAT_001_RESULT.md) Issue 2·4·5·6·7, [FU-005 결과](NAE_EUAT_001_FU005_COLD_SEARCH_FAILURE_RESULT.md).

## 결론

TO의 4개 결함 중 3개를 수정하고 1개는 진단만 했다. Retrieval Engine(`core/retrieval.py`)은 변경하지 않았다. 신규 테스트 48건 추가, 전체 회귀 3,461 passed / 17 skipped(라이브 Qdrant를 쓰는 통합 테스트 1건 제외).

| 결함 (EUAT Issue) | 조치 | 상태 |
|---|---|---|
| 근거 없는 인용 (4) | 신규 인용 검증기 `core/citation_verifier.py` + 생성 경로·채팅 UI 연결 (경고 전용) | 수정 |
| 출처 고지 오표기 (5) | `get_disclosure()`를 소스별로 분기 | 수정 |
| 표시 품질 (6): 별점 항상 ☆☆☆☆☆, 깨진 청크 제목, 빈 "주장 검증:" 라벨 | `ui/components/display_quality.py` + 카드·채팅 연결 | 수정 |
| 빈 결과와 검색 실패 구분 (2, FU-005 권고) | 어댑터가 실패 사유를 기록, 공개 패널이 "검색 실패/시간 초과"를 별도 표시 | 수정 |
| 한국어 외 문자 혼입 (7) | 진단만 (아래 §5) | 진단 |

## 1. 변경 파일

| 파일 | 변경 |
|---|---|
| `NAE/citation_disclosure.py` | `get_disclosure(authority_class, *, source_id, identifier, author, work)`. Fuller에게만 Amendment A §6 고정 고지문, 그 외 `historical_witness`는 저자·문헌만 밝히는 일반 고지문. 소스 정보를 주지 않으면 종전과 동일(하위 호환) |
| `ui/components/nae_public_section.py` | 고지 호출에 소스 정보 전달. `retrieval_status_text()`, `empty_result_message()` 추가, 검색 실패 시 경고 표시 |
| `NAE/retrieval_adapter.py` | `last_retrieval_failure()`(스레드 로컬) 추가. `bridge_query_paragraphs()`가 fail-closed로 삼킨 사유(timeout/error)만 기록. 반환값·동작 불변, 삭제된 줄은 `except` 절 1줄 |
| `core/citation_verifier.py` (신규) | `verify_citations()`, `issue_messages()` |
| `core/generation.py` | `_run_citation_check()`, `GenerationResult.citation_check`(기본 None) 추가. `to_result()`·`generate()`에서 호출. 삭제된 줄 0 |
| `ui/pages/chat.py` | 인용 경고 렌더링(`_render_citation_warnings`), 대화 기록에 `citation_warnings` 저장, 헤딩 라벨 정리, 빈 라벨 방지 |
| `ui/components/citation_card.py` | 비교 불가한 점수면 별점 줄 생략 |
| `ui/components/display_quality.py` (신규) | 순수 함수: `is_comparable_relevance`, `usable_heading_label`, `claim_guard_message` |

## 2. 설계 결정

### 인용 검증기
- **경고 전용**이다. 답변을 바꾸거나 막지 않는다(chat.py의 기존 방침: 소표본 신호로 동작을 게이팅하지 않는다).
- 한국어 답변과 외국어 근거 사이에서 의미 검증은 불가능하므로, `(출처: …)` 직전 문장의 **3~4자리 숫자**와 **라틴 문자 고유어·인용문**이 인용된 근거 본문(`RankedCandidate.content`, 즉 모델이 실제로 받은 것)에 있는지만 본다. 한국어로 바꿔 쓴 주장은 검증 대상이 아니다.
- 세 가지 이슈 종류: 출처를 검색된 자료 목록에서 찾지 못함 / 인용된 자료에 없음 / 다른 검색 결과에만 있음.
- 오탐을 줄이는 장치: 라틴 고유어는 2개 이상 없을 때만 이슈, 하이픈 단어는 구성 조각 기준, 한국어로 옮긴 출처 라벨은 건너뜀, 출처 라벨 안의 숫자는 주장에서 제외.
- 표현은 "확인하지 못했습니다"로 단정하지 않는다.

### 출처 고지
- Amendment A §6이 정의한 것은 Fuller 고정 고지문뿐이다. 다른 소스에 새 정책 문구를 만들지 않도록, 일반 고지문은 **메타데이터(저자·문헌·등급 라벨)만** 사용하고 페이지 번호·신뢰도·성구 추출 상태 같은 소스별 성격은 주장하지 않는다.
- Fuller 판별은 소스 ID 접두사(`BAP-MISS-FULLER`) / identifier 접두사(`Fuller_Complete_Works`) / 저자 전체 이름(`Andrew Fuller`)만 본다. 성만으로 판별하지 않는다(동성이인 Thomas Fuller 오분류 방지).

### 별점
- 하이브리드 검색의 `final_score`는 RRF 값(최대 약 0.049)이라 `round(score*5)`가 항상 0이었다. `RRF_SCORE_CEILING = 0.06` 이하이면 별점 줄을 생략한다. 이 임계값은 "RRF 척도 여부"를 가르는 **휴리스틱**이다(실제 벡터 유사도는 무관 질의도 약 0.37 이상).

## 3. 검증

| 항목 | 결과 |
|---|---|
| 신규 테스트 | 고지 10, 표시 품질 14, 검색 실패 신호 9, 인용 검증기 15 = **48건 통과** |
| 관련 회귀 (39개 파일: 생성·채팅·인용·ClaimGuard·NAE·연구) | 535 passed |
| 전체 회귀 | **3,461 passed, 17 skipped** (85초, `test_nae_retrieval_bridge_integration.py` 제외) |
| 실데이터 검증: EUAT-05의 1689 문장 | Spurgeon Vol41·13·06 전문을 근거로 대조 → **정확히 1건 플래그**(`1689` 미확인) |
| 실데이터 오탐 점검 | EUAT-04의 1689 광고 언급(Vol39·48 기준), Broadus 영문 인용(청크 파일 기준), EUAT-02 Hiscox 언급(NPSP_F 기준) → 모두 이슈 0건 |
| 앱 UI 실행 검증 | **미수행.** 실행 중인 앱은 메인 체크아웃(`~/DBMA`)에서 구동되고 이 변경은 별도 워크트리에 있어 화면에 반영되지 않는다. 화면 확인은 병합 후 필요 |

## 4. 한계와 주의

1. **검증기는 부분 검사다.** 한국어로 바꿔 쓴 주장, 숫자·고유어가 없는 주장은 검증하지 못한다. 이슈가 없다는 것은 인용이 정확하다는 뜻이 아니다.
2. 이웃 문단 확장으로 문맥에 더해진 본문은 후보에 없어, 그 본문에만 있는 내용은 "확인하지 못했다"로 표시될 수 있다.
3. 실데이터 검증은 전문(全文) 파일을 근거로 썼다. 실제 운영에서는 검색된 청크만이 근거라 더 엄격하며, 청크에 없는 사실은 모델이 볼 수 없었던 내용이므로 플래그가 타당하지만 오탐 비율은 측정하지 않았다.
4. 검증기는 채팅 답변에만 연결했다. 연구 탭의 `generate_answer` 경로(튜플 반환)와 설교 생성 경로에는 연결하지 않았다.
5. 연구 탭 결과의 제목("본문 참조 없음 — …")은 손대지 않았다(`tests/test_sermon_research_hub.py`가 의존하는 기존 설계).
6. 공개 패널 실패 신호는 `bridge_query_paragraphs` 경로(문단 근거 활성 시)에서만 동작한다. `NAE_PARAGRAPH_EVIDENCE=0` 폴백의 `bridge_query`는 ADR-024 §D에 따라 무변경이라 신호가 없다.
7. `NAE/retrieval_adapter.py`는 ADR-024(Approved) 소관이다. 변경은 사유 기록용 부가 코드이며 fail-closed 반환값·타임아웃 값은 그대로다. 그래도 Approved ADR의 모듈이므로 C1 검토를 요청한다.
8. 타임아웃 값(3초) 자체와 bge-m3 콜드 로드 대책은 이번 범위 밖이다(ADR-024 §G 관련, 별도 결정 필요).

## 5. 진단: 한국어 외 문자 혼입 (수정 없음)

- 현상: 2026-09-29 EUAT 5개 답변 중 2건(EUAT-02, EUAT-05)에서 "□" 치환과 경고가 나타났다(예: "성경의 권□는", "성도□은"). 앞서 TO 초안이 적은 "5건 중 3건"은 부정확했고 2건이 맞다.
- 원인 (기존 코드 주석 실측 근거): 모델(`my-theology-bot-v2`)/양자화 자체의 결함으로, 특정 개념 주변에서 토큰이 다른 언어와 얽혀 온도와 무관하게 재현된다(0.0에서도 1자 발생 기록). 예를 들어 "권위"의 한 글자가 한자로 나왔다가 제거되면 "권□"가 된다.
- 기존 방어: 비스트리밍 경로는 오염 감지 시 최대 2회 재시도, 스트리밍은 재시도가 불가능해 청크별 제거 + 마지막 정리(`_sanitize_script_contamination`)만 남는다. 채팅은 스트리밍이라 재시도 없이 글자가 깨진 채 표시된다.
- 개선 방향(미실행, 설계 결정 필요): 스트리밍 종료 후 오염이 감지되면 비스트리밍으로 재생성해 교체하거나, 깨진 단어 위치를 표시하는 방안. 대기 시간이 늘어나는 비용이 있다.

## 6. C1 검토 요청 (새 Validator 추가에 해당)

붙여넣기용 지시 (자기완결형):

```text
너는 NAE 프로젝트의 검증(Audit) 담당 C1이다. 코드·데이터·Git은 수정하지 않는다(READ-ONLY). 파일을 새로 만들지 마라.
이 메시지가 지시의 전부다. 저장소에서 Task Order를 찾지 마라.

[대상] 저장소 /Users/David/DBMA 가 아니라 워크트리 /Users/David/DBMA/.claude/worktrees/sleepy-ellis-ad7a97 의 브랜치
claude/nae-end-user-acceptance-test-bd2fff 의 변경분(FU-003)이다. 먼저 git -C <워크트리> log -1, git -C <워크트리> status -s 를 실행해 보고하라.
[검증 항목] 명령을 직접 실행하고 출력 원문을 붙여라. 확인 못 하면 "미확인".
R1 <워크트리>에서 python -m pytest tests/test_citation_verifier.py tests/test_display_quality.py tests/test_citation_disclosure_source_aware.py tests/test_nae_retrieval_failure_signal.py -q → 48 passed 기대
R2 core/citation_verifier.py를 읽고, 경고 전용인지(답변 텍스트를 바꾸거나 예외를 전파하는 경로가 없는지), 외부 호출·전역 상태가 없는지
R3 core/generation.py diff: 삭제된 줄이 없고 _run_citation_check가 예외를 삼키는지
R4 NAE/retrieval_adapter.py diff: 삭제된 줄이 except 절 1줄뿐이고, 반환값·타임아웃(_HARD_TIMEOUT_MS)·bridge_query() 본문이 불변인지 (ADR-024 §D/§G 위반 여부)
R5 NAE/citation_disclosure.py: 소스 정보 없이 get_disclosure("historical_witness")를 호출하면 종전 Fuller 고정 문구를 반환하는지, Dagg/Hiscox 입력에는 "Fuller"가 나오지 않는지 (Amendment A §6 보존)
R6 core/retrieval.py 가 git diff 에 없는지 (Retrieval Engine 무변경)
R7 오탐 관점 검토: verify_citations의 SOURCE_MATCH_MIN_OVERLAP=0.6, MIN_MISSING_LATIN_TOKENS=2 가 정상 인용을 오탐할 가능성이 큰 사례를 코드 읽기만으로 2건 이상 제시(실행 불필요)
[금지] 수정·패치·새 ADR 금지. 문제는 OBSERVED → EVIDENCE → IMPACT → RECOMMENDATION 형식으로만.
[보고 형식] 15줄 이내: STATUS / R1~R7 각 CONFIRMED·DISPUTED·미확인 + 한 줄 근거 / 발견 사항
```

C1 보고는 CUE가 매번 직접 교차검증한다.

## 7. 후속 결정 필요

1. 스트리밍 답변의 글자 깨짐 개선(§5) 여부.
2. 검증기를 연구 탭·설교 생성 경로로 확장할지.
3. 3초 하드 타임아웃과 bge-m3 콜드 로드 대책(ADR-024 §G Amendment 여부).
4. 병합 후 앱 화면에서 별점·경고·고지 표시를 실제로 확인.
