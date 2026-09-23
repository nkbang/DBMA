# NAE 상업용 앱 화면 구조 벤치마크 (Phase 1 화면 통합 보조 자료)

**작성일:** 2026-09-23
**작성자:** CUE
**목적:** `NAE_PASTOR_FEATURE_REALIGNMENT_REPORT_001.md`의 "3화면 모델"이
업계 표준 내비게이션 구조와 부합하는지 확인. 기능 매트릭스 비교는 이미
`docs/DBMA_COMMERCIAL_BENCHMARK_ASSESSMENT_2026-09-15.md`(2026-09-15,
코드 실측 기반)에 상세히 존재하므로 **중복하지 않고**, 이 문서는 그 문서가
다루지 않은 "화면/내비게이션 구조" 관점만 다룬다.

---

## 조사 대상

Logos Bible Software, PulpitAI(Subsplash), YouVersion — 목회자/성경 학습
카테고리에서 서로 다른 포지션(장서형/재가공형/읽기형)을 대표하는 3개 선정.

## 핵심 발견

1. **검색과 AI 답변은 같은 화면에서 인라인으로 처리한다.** Logos의 Smart
   Search는 자연어 질의 결과에 AI 생성 요약(출처 각주 포함)을 바로 붙여
   보여주며, 별도의 "채팅" 화면으로 보내지 않는다. YouVersion도 AI
   질의응답을 독립 챗 탭이 아니라 검색/읽기 흐름 안에 통합했다.
   → DBMA `ui/pages/research.py::_render_ai_answer`가 이미 검색 결과
   바로 아래에 AI 답변을 렌더링하는 동일 패턴을 쓰고 있음(이번 조사에서
   재확인) — 변경 불필요.
2. **독립된 "채팅" 최상위 화면은 드물다.** PulpitAI의 "PulpitGPT"도 이미
   생성된 설교 원고에 대한 질의응답이지, 범용 채팅 화면이 아니다. 즉
   `research.py`+`chat.py`를 탭으로 묶는 이번 결정은 방향은 맞지만,
   장기적으로는 "채팅"을 별 탭이 아니라 연구 결과에 종속된 보조 기능으로
   더 붙이는 편이 업계 표준에 더 가깝다 — 단 이는 코드 재구성(함수 분리)이
   필요해 이번 Phase 1(탭 래퍼) 스코프 밖. Phase 2 이후 과제로만 기록.
3. **설교 준비는 단일 워크플로우 화면으로 수렴한다.** Logos Sermon
   Builder는 개요 생성→구절 추가→편집을 한 화면에서 처리하고 별도
   "연구 허브" 화면을 두지 않는다 → `sermon_draft`+`sermon_research`
   탭 통합 방향과 일치.
4. **라이브러리는 콘텐츠 관리 전용 단일 화면**이며 "저장된 설교"를 별도
   최상위 메뉴로 분리하지 않고 라이브러리의 하위 컬렉션으로 둔다 →
   `library`+`sermon_library` 탭 통합 방향과 일치.
5. **개발자/운영 지표(파이프라인 상태, 벤치마크 점수 등)는 세 앱 모두
   사용자 화면에 노출하지 않는다.** → `monitor.py`를 `NAE_ADMIN_MODE`
   게이트로 숨긴 기존 결정이 업계 표준과 일치함을 재확인(신규 조치 불필요).

## 결론

3화면(탭 통합) 방향은 업계 내비게이션 패턴과 부합함 — 계획대로 Step 1~3
진행. 아키텍처를 바꿀 근거는 발견되지 않음. 유일한 차이(채팅의 완전 인라인화)는
코드 재구성이 필요해 이번 스코프 밖으로 분리 기록.

## 출처

- [Logos Bible Software Review](https://theleadpastor.com/tools/logos-bible-software-review/)
- [How to Simplify Sermon Prep Using AI Tools – Logos Help Center](https://support.logos.com/hc/en-us/articles/30452307318541-How-to-Simplify-Sermon-Prep-Using-AI-Tools)
- [Logos AI Sermon Assistant Sneak Peek](https://churchtechtoday.com/logos-ai-sermon-assistant-sneak-peek/)
- [Pulpit AI From Start to Finish](https://support.subsplash.com/en/articles/10185865-pulpit-ai-from-start-to-finish)
- [Why 5,000+ pastors use Pulpit AI](https://www.subsplash.com/blog/reasons-pastors-use-pulpit-ai)
- [Best Bible Apps With AI 2026](https://doxa.app/blog/best-bible-apps-with-ai)
- [YouVersion Bible App Review 2026](https://www.bibleinyear.com/blog/youversion-bible-app)
