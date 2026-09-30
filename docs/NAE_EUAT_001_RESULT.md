# NAE EUAT-001 RESULT

최종 상태: **FAIL**. 채팅 경로는 내장 코퍼스(Dagg/Hiscox)에 닿지 않고, 앱 안에는 "내장 코퍼스 근거 답변" 경로가 없다. EUAT-05에는 근거 없는 인용도 있었다. 코드와 데이터는 수정하지 않았다(READ-ONLY).

부록: [NAE_EUAT_001_APPENDIX_A_CORPUS_INDEX_OBSERVATION.md](NAE_EUAT_001_APPENDIX_A_CORPUS_INDEX_OBSERVATION.md)

## Environment

- **App**: `http://localhost:8501` (Streamlit `ui/app.py`, pid 66564, 2026-09-29 16:27 기동). 생성 모델은 `my-theology-bot-v2:latest`(53GB).
- **Branch / Commit**: `~/DBMA` 메인 체크아웃 `feat/peb-v0.1` @ `c2cdf147`. 미커밋 수정 17개가 이미 있는 상태였다. 이 문서를 작성한 세션 워크트리는 시험 대상이 아니다.
- **Test date**: 2026-09-29, 약 16:30~17:30 CDT
- **Corpus/index**
  - `nae_tsu_v1` = 3,319 points (Qdrant 실측). 내역은 Dagg 2,958 + Hiscox 361이고 **Fuller는 0**.
  - `nae_ref_v1` = 34,948 (Smith 사전만).
  - `nae_ref_commentary_v1` = 10,517 (Gill, Broadus, Spurgeon, Carroll).
  - `SLBC1689`는 `NAE/corpus/canonical/`에 있으나 어느 컬렉션에도 인덱싱돼 있지 않다.
  - 내 서재(채팅이 검색하는 곳)는 69권이고 설교집, 주석, 설교학 위주다. Dagg/Hiscox/Fuller/1689는 없다.

## EUAT-01 (Dagg)

- **Question**: "Dagg에 따르면 침례교회에서 교회의 질서와 권징을 결정하는 성경적 원리는 무엇입니까?" (그대로 입력)
- **UI**: 채팅은 약 90초 뒤 정상 완료. 같은 질문을 재시도하자 "검색 중 문제가 있었습니다"가 떴다(Issue 2).
- **Retrieval**
  - 채팅은 5건을 가져왔지만 모두 내 서재 자료다(Broadus, Spurgeon Vol30·Vol15, Keach, Maclaren). Dagg는 없다.
  - "내서재 공개 자료(Beta)" 패널은 처음엔 "결과 없음"이었고, 워밍 후에는 Dagg·Hiscox 10건을 반환했다(1위 Hiscox p.160 §767, 0.5985).
- **Evidence**: 공개 패널의 근거는 질문과 부분적으로만 관련된다. 상위 10건에 "권징"을 직접 다룬 Dagg p.95·p.103은 없다(인덱스에는 있음).
- **Source**: 채팅은 "출처(5개)"를 표시하지만 Dagg가 아니다. 공개 패널은 저자·페이지·TSU ID를 표시한다.
- **Answer**: "등록된 자료로는 답할 수 없다"고 정직하게 유보했다.
- **Grounding**: 주장(Dagg 언급 없음)과 실제 검색 결과(Dagg 없음)가 일치한다. 거짓 진술은 없다.
- **User usefulness**: 없음. Dagg 질문에 Dagg 근거를 못 준다.
- **Verdict**: **HOLD**

## EUAT-02 (Hiscox)

- **Question**: "Hiscox는 침례교회의 교회 질서와 실제 운영에 대해 어떤 원칙을 제시합니까?"
- **UI**: 처음 2회는 즉시 "검색 중 문제가 있었습니다". 페이지 새로고침 후 성공했고 약 5분 걸렸다.
- **Retrieval**: 채팅은 Maclaren, Spurgeon NPSP_D·F, Dargan을 가져왔고 Hiscox는 없다. 공개 패널은 1위 Hiscox p.160, 7위 Hiscox p.23, 나머지는 Dagg.
- **Answer**: "Hiscox의 *Baptist Church Directory*가 자료에 언급된다(출처: Spurgeon)"고 했다.
- **Grounding**: 원문 대조 결과 `Spurgeon_NPSP_F.txt`에 Hiscox 언급은 실재하지만 책 뒤 출판사 광고 목록 한 줄뿐이다. 진술 자체는 정확하고 이후 유보했다.
- **Other**: 답변에 "□" 치환과 한국어 외 문자 제거 경고가 붙었다.
- **Verdict**: **HOLD**

## EUAT-03 (Fuller)

- **Question**: "Andrew Fuller는 믿음과 순종, 그리고 그리스도인의 삶의 관계를 어떻게 설명합니까?"
- **UI**: 정상 완료, 약 5분.
- **Retrieval**: Fuller 근거가 원천적으로 없다. TSU 파일은 디스크에 있으나 `nae_tsu_v1`의 Fuller 포인트는 0. 채팅은 Maclaren, Broadus만, 공개 패널은 Dagg·Hiscox만 반환했다(Fuller 0건).
- **Answer**: "Fuller에 대한 언급은 Broadus의 설교 스타일 부분뿐"이라며 유보했다.
- **Grounding**: 정직한 유보.
- **Verdict**: **HOLD**. Fuller 트랙은 실질적으로 미작동.

## EUAT-04 (1689)

- **Question**: "1689 침례교 신앙고백은 성경의 권위에 대해 무엇을 가르칩니까?"
- **UI**: 정상 완료, 약 7분. 생성 모델이 재로드되면서 첫 토큰까지 약 5분 걸렸다.
- **Retrieval**: 채팅에는 Spurgeon Vol53·39·48·28과 Broadus가 나왔다. Vol48의 "No. 1,691" 같은 숫자 노이즈가 섞였다. 공개 패널은 Dagg·Hiscox만 반환.
- **Evidence**: 1689 신앙고백 본문은 어디에도 인덱싱돼 있지 않다.
- **Answer**: 유보하면서 Broadus 영문 인용을 덧붙였다.
- **Grounding**: Broadus 인용은 청크 파일에서 실재를 확인했다. "1689 런던신앙고백서가 언급"은 Spurgeon Vol39·48의 출판 광고다. 정직했지만 1689와 무관한 내용이다.
- **Verdict**: **HOLD**

## EUAT-05 (실제 목회자 질문)

- **Question**: "침례교 목회자로서 성경의 권위와 교회의 질서, 그리고 신실한 목회 사역의 관계를 어떻게 이해해야 합니까? 내 서재에 있는 자료를 근거로 답하고 출처를 밝혀 주세요."
- **UI**: 약 8분. 스트리밍 중 "□"가 섞이고 경고가 떴다.
- **Retrieval**: 채팅은 Spurgeon Vol41·13·06, NPSP_D, Dargan Vol01을 가져왔다. 그중 두 건은 "• • ••»" 같은 깨진 청크. 공개 패널은 Dagg 10건으로 가장 관련 높은 근거(p.282, p.295 등)를 냈으나 채팅 답변에는 쓰이지 않았다.
- **Answer**: 대부분 일반적인 신학 서술이다. 두 문장 뒤에 "(출처: Spurgeon)" 인용이 붙었다. 끝에서 자체 유보했다.
- **Grounding**
  - "1689 런던신앙고백서는 성경이 완전하고 오류가 없으며… (출처: Spurgeon MTP)"는 인용된 Vol41에 1689 언급이 없고, "Confession of Faith"는 회심자의 개인 고백 설교다. **일반 지식을 코퍼스 출처처럼 제시한 것으로 FAIL 조건에 해당한다.**
  - "목사들은 서로를 돌보아야 하며… (출처: Spurgeon)"는 정확한 출처 문단을 특정하지 못했다.
- **Synthesis 구분**: 자료 기반 종합이 아니라 일반 AI 신학 답변이다.
- **Verdict**: **FAIL**

## Cross-Test Findings

### Verified

- Landing → 내서재 → 홈(대시보드, 69권) → 연구·채팅 → 질문 입력 → 스트리밍 답변 → 출처 확장 흐름이 동작했다.
- 자료에 없을 때 지어내지 않고 유보하는 동작이 5건 중 4건에서 확인됐다.
- 공개 패널의 Dagg/Hiscox 근거는 저자·페이지·TSU ID가 표시되고 Qdrant 직접 조회 결과와 순위·점수가 일치했다.

### Issues (OBSERVED → EVIDENCE → IMPACT → RECOMMENDATION)

1. **채팅이 내장 TSU에 닿지 않음**
   - 근거: 채팅 출처 25건에 Dagg/Hiscox/Fuller가 0건. `ui/pages/chat.py`는 `core.retrieval.QueryProcessor`와 Smith 사전만 사용한다. Dagg/Hiscox는 별도 패널(`nae_public_section.py`)이며 LLM 답변이 없다.
   - 영향: 사용자가 물은 자료에 대한 답을 받을 수 없다.
   - 권고: TSU 검색을 채팅 답변 경로에 연결하거나 두 영역의 분리를 UI에서 명시하는 별도 Task Order.
2. **콜드 상태 검색 실패**
   - 근거: 첫 질문 성공 후 채팅 4회가 "검색 중 문제가 있었습니다"였고 새로고침 후 복구됐다. 공개 패널은 대조군("아브라함")을 포함해 최소 7회 "결과 없음"이었다. 신규 프로세스의 어댑터 호출은 10건을 반환했고 이후 UI도 10건을 반환했다.
   - 영향: 첫 사용에서 "자료 없음"으로 오해할 수 있다.
   - 권고: 앱 로그로 원인 확정. bge-m3가 로드되지 않은 정황은 있으나 확정하지 못했다.
3. **Fuller 미인덱싱, 1689 미수록**: Fuller 0건, `SLBC1689`는 디스크에만 있다. 원인과 조치는 부록 A 참조.
4. **근거 없는 인용**: EUAT-05의 1689 문장. 인용이 붙어 있어 오히려 신뢰도가 높아 보인다. 권고: 인용-원문 일치 검증 강화.
5. **출처 고지 오표기**: Dagg/Hiscox 카드에 "Andrew Fuller, The Works of the Rev. Andrew Fuller에서 추출"이라는 고지가 붙는다. 원인은 확정됨: `NAE/citation_disclosure.py`의 `get_disclosure()`가 `historical_witness` 등급이면 Fuller 고정 문구를 반환한다(코드 주석은 "현재 이 등급은 Fuller 한 소스뿐"이라고 가정). Dagg/Hiscox도 같은 등급이라 잘못된 저자가 표시된다.
6. **출처 표시 품질**: 모든 출처의 관련성이 ☆☆☆☆☆, 깨진 청크가 제목으로 나옴, "주장 검증:" 라벨이 비어 있음.
7. **한국어 외 문자 혼입**: 답변 중 "□" 치환과 경고가 반복됨.
8. **지연**: 질문당 90초~8분, 모델 재로드 구간에 진행 표시가 없음.
9. **관련성**: Dagg 권징 근거(p.95, p.103)가 인덱스에는 있으나 상위 10건에 들지 않음.
10. **부수효과**: UI 사용으로 채팅 기록과 검색 텔레메트리 행이 기록됨. 이 외 저장소·데이터 변경은 없음.

### Corpus / Index Observation

- 디스크 33,132 TSU는 항목별로 재계수해 확인했다(Dagg 3,377 + Hiscox 740 + Fuller 29,015). 인덱스 3,319는 Dagg 2,958 + Hiscox 361로 정확히 일치했다.
- 차이는 결과에 **직접 영향**을 줬다. Fuller(EUAT-03)는 인덱싱이 없어 검색이 불가능했고, 1689(EUAT-04)는 어디에도 인덱싱돼 있지 않았다.
- Dagg/Hiscox 질문(EUAT-01·02)은 인덱스에 근거가 있으나 채팅 경로가 닿지 못했다.
- Dagg·Hiscox의 부분 인덱싱(verified 중 321·251건 누락)은 9/15~9/16 승인분이 8/11 이후 재인덱싱되지 않았기 때문이다. 상세는 부록 A.

## User Acceptance Assessment

1. **목회자가 자연스러운 질문을 할 수 있는가?** 예. 입력과 응답은 되지만, 첫 질문 이후 실패와 긴 대기가 있다.
2. **유용한 근거를 검색하는가?** 부분적. 공개 패널은 Dagg/Hiscox 근거를 내지만 관련성은 중간이고 Fuller/1689는 없다. 채팅은 내 서재 자료만 검색한다.
3. **답변을 서재 근거 연구로 신뢰할 수 있는가?** 아니요. 유보는 정직하지만 EUAT-05에는 근거 없는 인용이 있고, 내장 코퍼스 기반 답변은 존재하지 않는다.

## Final Status: FAIL

## 시험 방법의 한계

- EUAT-02·03의 채팅 실패 4회는 새로고침 전 결과다. 새로고침 후 재시도한 결과를 판정에 사용했다.
- 앱 로그는 접근할 수 없어 실패 원인은 추정이다.
- "연구" 탭의 AI 답변은 시험하지 않았다.
- 공개 패널 시험 중 브라우저 자동화로 입력창에 값을 직접 넣은 구간이 있다. 결과는 UI 화면 기준이다.
- UI 밖에서 임베딩, Qdrant 조회, 어댑터 호출을 각각 읽기 전용으로 실행했다. 쓰기 작업은 없다.
