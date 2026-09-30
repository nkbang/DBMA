# FU-001 방안 B Build Report: 공개 자료 근거 답변

작성일 2026-09-29. 근거: [ADR-037](architecture/ADR-037-NAE-Public-Evidence-in-Answer-Generation.md)(Proposed) 방안 B, 사용자 결정(2026-09-29 "B로 진행"). 트리거는 ADR 권고대로 **명시적 버튼**.

## 결론

"내서재 공개 자료(Beta)" 패널에서 사용자가 **버튼을 눌렀을 때만**, 그 패널이 가져온 문단 근거로 **별도 답변**을 생성한다. 내 서재 답변과 병합하지 않는다. Retrieval Engine, 인덱스, 채팅 답변 경로(`chat.py`)는 변경하지 않았다. 신규 테스트 29건, 전체 회귀 3,490 passed / 17 skipped(라이브 Qdrant 통합 1건 제외). ADR-037은 **Proposed 상태 그대로**다(승격은 C1 리뷰 + 사용자 승인 필요).

## 1. 변경 파일

| 파일 | 변경 |
|---|---|
| `NAE/public_answer.py` (신규) | 근거 선택(고유 문단, 상한 5), `ResponsePackage` 조립, 소스별 고지, 색인 범위 요약(읽기 전용 scroll, 10분 캐시), 보류 문구 |
| `ui/components/nae_public_section.py` | "공개 자료 근거 답변" 섹션(버튼, 스트리밍 생성, 저장된 답변 재표시, 인용 경고·주장 검증·소스별 고지·검색 범위 표시). 새 검색 시 이전 답변 폐기 |
| `core/citation_verifier.py` | 실제 생성에서 드러난 두 결함 수정(§4) |
| `tests/test_nae_public_answer.py` (신규), `tests/test_citation_verifier.py` | 신규 29건(공개 답변 23 + 검증기 6) |

`ui/pages/chat.py`, `core/retrieval.py`, `NAE/retrieval_adapter.py`, 인덱스는 이번 변경에서 수정하지 않았다.

## 2. 설계 준수 (ADR-037 수용 기준)

| AC | 내용 | 결과 |
|---|---|---|
| AC-1 | EUAT-01·02: Dagg/Hiscox 인용이 있는 답변 | 실제 모델 시험 통과(§3) |
| AC-2 | EUAT-03·04: 일반 지식으로 채우지 않고 검색 범위 문구 표시 | 통과: 03은 유보, 04는 1689 부재를 밝히고 실제 Hiscox 문장만 인용. 범위 문구는 화면 시험에서 표시 확인 |
| AC-3 | 근거 0건·검색 실패 시 생성 안 함 | 통과: 근거가 없으면 버튼 자체가 나오지 않고, 패키지 조립도 None. 검색 실패는 FU-003의 실패 신호로 별도 표시(생성 호출 없음) |
| AC-4 | 내 서재 경로와 미병합, `TestNoMergeIntoGeneration` 무변경 통과 | 통과: `chat.py` 무변경, 가드 테스트 9건 통과, `generate_answer`·`_handle_user_message`가 `public_answer`/브리지를 참조하지 않음을 테스트로 고정 |
| AC-5 | 소스별 고지, Dagg/Hiscox에 Fuller 고지 없음 | 통과(화면 시험: 고지에 Fuller 미포함) |
| AC-6 | 저장 계층 무변경 | 통과: 모듈 코드(독스트링·주석 제외)에 `6333`, `dbma_qdrant`, upsert/delete/create_collection 없음(AST 테스트, 변이로 검출 가능성 확인). 인덱스 읽기 전용 scroll 1회뿐 |
| AC-7 | 모듈 비활성 시 no-op | 통과(테스트) |
| AC-8 | 새 스위치 없음, 전체 회귀 통과 | 통과 |

## 3. 실제 모델 시험 (UI 밖, 저장소 쓰기 없음, `my-theology-bot-v2`)

각 질문마다 실제 어댑터로 검색한 뒤 `GenerationService.generate()`로 답변을 만들었다(소요 9~51초, GPU 경합 없는 시간대).

| 질문 | 결과 | 평가 |
|---|---|---|
| EUAT-01 (Dagg 권징) | Dagg p.296 §1520, p.99 §541의 문단을 위치와 함께 인용. "구체적 내용은 언급되어 있지 않다"고 먼저 밝힘 | 근거 기반, 정직. 질문에 직접 답하지는 못함 |
| EUAT-02 (Hiscox) | Hiscox p.36 "교정적 규율의 행정" 문단을 인용. 규칙 자체는 나열하지 못함 | 근거 기반이나 내용이 빈약 |
| EUAT-03 (Fuller) | "Fuller 관련 내용이 언급되지 않았다"고 유보 | 정직. UI가 검색 범위 문구로 이유를 덧붙임 |
| EUAT-04 (1689) | 1689 신앙고백에 대한 언급은 없다고 밝히고, Hiscox p.167의 실제 문장("They held the Bible to be the only rule and authority…")만 인용 | 정직하고 유용 |
| EUAT-05 (복수 자료 종합) | 일반론 위주. Dagg의 말이라며 **한국어 직접 인용문**을 붙였는데 근거 문단의 의역일 가능성이 큼. "Eward T. Hiscox" 오타 | **약함**(아래 한계) |

## 4. 실제 생성에서 드러나 고친 검증기 결함 2건

1. **인용 형식 미인식**: 모델이 `(출처: …)` 대신 `(Church Order — John L. Dagg, p.296, 문단 1520)` 형식으로 인용하자 FU-003 검증기가 인용을 0건으로 보고 통과시켰다. 줄표와 쪽/문단 표지가 함께 있는 괄호도 인용으로 인식하도록 확장했다.
2. **오탐**: 문장 속 책 제목·저자 이름이 근거 본문이 아니라 서지 정보에 있어서 정상 문장이 "확인하지 못했다"로 표시됐다(EUAT-04). 지지 근거에 후보의 제목·저자를 포함하도록 고쳤다. 오탐 회귀 테스트와, 같은 조건에서 잘못된 인용문은 여전히 플래그되는 테스트를 함께 추가했다.

## 5. 화면 흐름 검증 (Streamlit 자체 테스트 하네스, 가짜 검색·생성)

검색 → "공개 자료 근거 답변" 섹션과 버튼 표시 → 클릭 → 스트리밍 답변 출력 → 컨텍스트에 공개 근거만 포함 → 인용 경고·소스별 고지(Fuller 미포함)·검색 범위 문구 표시 → 재실행 후에도 저장 답변 유지 → 새 검색 시 이전 답변 폐기. 전부 확인했다. 실제 앱 화면(브라우저)에서의 확인은 하지 못했다(§7).

## 6. 한계 (정직한 기록)

1. **한국어 직접 인용문은 검증하지 못한다.** 근거는 영어이고 답변은 한국어라 따옴표 안의 한국어가 원문을 옮긴 것인지 의역인지 기계적으로 가릴 수 없다. EUAT-05의 Dagg 인용문이 그 사례다. 개선 방향(미실행): 직접 인용은 원문 그대로만 쓰라는 지시문 추가는 생성 계층 정책 변경이라 별도 결정이 필요하다.
2. **종합(EUAT-05)은 해결하지 못한다.** 방안 B의 알려진 한계다. 내 서재 답변과 공개 자료 답변이 나란히 놓일 뿐 종합은 사용자 몫이다.
3. Fuller·1689는 인덱스에 없어 답변에 반영되지 않는다(FU-004). 범위 문구로 이유는 밝힌다.
4. 인용 형식이 `(…)` 괄호가 아닌 서술 속 표기("p.36에 기록")는 인용으로 인식되지 않는다.
5. 답변 품질은 소수의 실제 시험(5문항)에 근거한 관찰이며 통계적 평가가 아니다.
6. 생성 지연은 GPU 경합에 좌우된다(FU-005). 이번 시험은 경합이 없는 시간대였다.

## 7. 반영·확인이 남은 것

- **사용자가 보는 앱에는 반영되지 않았다.** 앱은 `~/DBMA`(`feat/peb-v0.1`)에서 구동 중이고 이 변경은 `main` 기준 브랜치에 있다. 릴리스 라인 통합은 [FU-007](NAE_EUAT_001_FU007_BASELINE_DIVERGENCE_RESULT.md) 결정이 선행되어야 한다. FU-007의 병합 충돌 예측에 이번 변경 파일(`NAE/public_answer.py`, `nae_public_section.py`)은 포함되지 않는다.
- ADR-037 승격 조건: 구현 완료(이 문서) / 회귀 통과(3,490) / **C1 독립 리뷰(대기)** / **사용자 승인(대기)**.

## 8. C1 검토 요청 (자기완결형 지시)

```text
너는 NAE 프로젝트의 검증(Audit) 담당 C1이다. 코드·데이터·Git은 수정하지 않는다(READ-ONLY). 파일을 새로 만들지 마라.
이 메시지가 지시의 전부다. 저장소에서 Task Order를 찾지 마라.

[대상] 워크트리 /Users/David/DBMA/.claude/worktrees/sleepy-ellis-ad7a97 (브랜치 claude/nae-end-user-acceptance-test-bd2fff)의 FU-001 방안 B 변경분.
먼저 git -C <워크트리> log -1, git -C <워크트리> status -s 를 실행해 보고하라. (ADR: docs/architecture/ADR-037-NAE-Public-Evidence-in-Answer-Generation.md, Proposed)
[검증 항목] 명령을 직접 실행하고 출력 원문을 붙여라. 확인 못 하면 "미확인".
R1 <워크트리>에서 python -m pytest tests/test_nae_public_answer.py tests/test_citation_verifier.py tests/test_nae_f6_chat_wiring.py -q → 전부 통과
R2 git diff --stat 으로 ui/pages/chat.py, core/retrieval.py, NAE/retrieval_adapter.py 가 이번 변경에 없는지 (ADR-024 §B, ADR-001)
R3 NAE/public_answer.py 를 읽고 저장소 쓰기(upsert/delete/create_collection), dbma_qdrant(6333) 접근이 코드에 없는지, Qdrant 접근이 읽기 전용 scroll 하나뿐인지 (ADR-013, ADR-024 §H)
R4 ui/components/nae_public_section.py: 답변 생성이 버튼 클릭 때만 일어나는지, modules.nae_pd.enabled 게이트 밖에서 실행되는 경로가 없는지, 새 스위치가 없는지 (ADR-024 §F)
R5 생성 입력이 공개 근거 패키지뿐인지(내 서재 검색 결과·대화 기록이 섞이지 않는지) 코드로 확인
R6 core/citation_verifier.py 의 두 수정(서지 형식 인용 인식, 제목·저자를 지지 근거에 포함)이 오탐/미탐을 늘릴 가능성을 코드 읽기만으로 2건 이상 제시
R7 docs/NAE_EUAT_001_FU001_B_BUILD_REPORT.md 의 수치(신규 테스트 29건, 전체 회귀 3,490 passed)를 <워크트리>에서 python -m pytest tests -q --ignore=tests/test_nae_retrieval_bridge_integration.py 로 재현(약 90초)
[금지] 수정·패치 금지. 문제는 OBSERVED → EVIDENCE → IMPACT → RECOMMENDATION 형식으로만.
[보고 형식] 15줄 이내: STATUS / R1~R7 각 CONFIRMED·DISPUTED·미확인 + 한 줄 근거 / 발견 사항
```

C1 보고는 CUE가 매번 직접 교차검증한다.
