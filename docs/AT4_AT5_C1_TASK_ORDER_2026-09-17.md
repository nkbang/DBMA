# AT-4/AT-5 실행 — C1(Cline) 위임 Task Order

## 배경
`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DEPLOY_VERIFICATION_001.md`에서 AT-4(인용
카드 스크린샷)·AT-5(생성 완결성)가 "F2 종료 후" 보류(DEFER)로 남아있었다.
2026-09-17 CUE 확인: GPU 유휴, F2 게이트 해제. 근거 문서: 설계
`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DESIGN_v1.md` §6(AT-4/AT-5 정의), §7(rollback),
구현 Task Order `docs/NAE_PARAGRAPH_ANSWER_DELIVERY_IMPL_TASK_ORDER_001.md`
("기계적 하위단계는 C1 위임 가능, §9").

**범위 확인**: `nae_pd`는 sandbox 연구 모듈(`nae_tsu_v1`: Dagg 2,958 + Hiscox 361
+ Fuller Vol.01-08)이며 프로덕션 `ui/pages/chat.py` 기본 경로와 무관(F6 배선
미승인, 설계 §5.3/§10-6). 이 작업은 `config.yaml: modules.nae_pd.enabled`를
**임시로 true**로 켜고 검증 후 **반드시 false로 원복**한다.

## C1이 할 일 (기계적 실행 — 판단 없이 그대로 수행)

### 0. 사전 확인 (필수, 순서대로)
```bash
cd /Users/David/DBMA
git rev-parse --show-toplevel   # /Users/David/DBMA 여야 함
git branch --show-current       # dev/dbma-engine 여야 함
git status                      # config.yaml이 목록에 없으면 통과(다른 파일 dirty는 무관)
curl -s http://localhost:11434/api/ps   # my-theology-bot-v2/dbma-planner-r1-q6:70b 등 "별도 무거운 모델"이 없으면 통과 — C1 자신의 백엔드 모델은 로드돼 있는 게 정상
```
[정정 2026-09-17] git status 조건: config.yaml이 dirty 목록에 없으면
통과(다른 파일 변경은 무관, 단 그 파일들은 건드리지 말 것). GPU 조건:
C1 자신의 백엔드 모델은 항상 로드돼 있어야 정상이므로 그것만 떠 있으면
통과 — 별도 대형 모델(my-theology-bot-v2 등)이 추가로 로드돼 있을 때만
중단.
넷 중 하나라도 다르면 **중단하고 CUE에게 보고**, 다음 단계 진행 금지.

### 1. nae_pd 임시 활성화
`config.yaml`의 `modules.nae_pd.enabled: false`를 `true`로 1줄만 수정.
다른 줄은 건드리지 않는다.

### 2. AT-5 — 생성 완결성 (텍스트만, UI 불필요)
아래 13개 고정 질의를 **순서대로**, `my-theology-bot-v2` 모델로 하나씩
실행(터미널에서 `ollama run my-theology-bot-v2` 또는 기존 rag_judge 실행
스크립트가 있으면 그것을 사용 — 있는지 먼저 `grep -rl "rag_judge" scripts/`로
확인). 각 질의의 원문 출력을 그대로 저장한다. 답은 한 글자도 요약·수정하지
말 것.

```
1. 오직 믿음으로 구원받는다는 것은 무엇을 뜻하는가?
2. 회개와 믿음의 관계를 설명해 달라.
3. 그리스도의 속죄가 모든 사람을 위한 것인가, 선택된 자만을 위한 것인가?
4. 중생(거듭남)은 믿음보다 먼저 일어나는가?
5. 복음을 모든 사람에게 값없이 제시해야 하는 근거는 무엇인가?
6. 침례의 합당한 대상은 누구인가?
7. 침례의 방식(침수)이 왜 중요한가?
8. 지역 교회의 회원권은 어떻게 결정되는가?
9. 교회의 권징(치리)은 어떤 절차로 이루어지는가?
10. 장로(감독)와 집사의 직분은 어떻게 다른가?
11. 성찬(주의 만찬)에 참여할 자격은 무엇인가?
12. 교회의 독립성(회중정치)을 성경적으로 어떻게 뒷받침하는가?
13. 신자의 견인(구원의 확신)은 어떤 근거로 주장되는가?
```

각 답변에 대해:
(a) `scripts/answer_completeness.py`(있으면) 또는 동등 규칙 기반 체크로
    - 문장 완결 어미 여부
    - 40자 초과 영어 원문 스팬 존재 여부
    - 인용 참조 ≥1건 존재 여부
    를 판정해 기록.
(b) CJK(중국어/일본어 한자 오염) 존재 여부를 육안으로 확인해 기록.

**판단하지 말 것**: PASS/FAIL 최종 판정은 CUE가 한다. C1은 관찰된 사실
(어미 완결 여부, 영어 스팬 글자수, 인용 개수, CJK 유무)만 있는 그대로 보고.

### 3. AT-4 — 인용 카드 스크린샷 (UI 필요)
1. `dbma_ui.py` 실행(Streamlit).
2. NAE 브리지 경로로 위 13개 질의 중 **1~3번**만 입력해 인용 카드가
   렌더되는 화면을 스크린샷으로 캡처(파일명: `AT4_q1.png` 형식).
3. 카드에 다음이 보이는지 육안 확인해 기록만 한다(판정 아님):
   - 카드 본문이 요약이 아니라 문단 전문으로 보이는가
   - 서지(저자·저작·페이지 범위) 줄이 있는가
   - anchor 문장이 하이라이트돼 있는가

### 4. 원복 (필수, 마지막)
`config.yaml`의 `modules.nae_pd.enabled`를 **다시 false로 되돌린다.**
`git diff config.yaml`로 원상복구 확인 후 보고.

## 보고 형식
CUE에게 아래를 그대로 붙여서 보고:
- 0단계 4개 명령 출력 전부
- 13개 질의 원문 답변 전문(요약 금지) + (a)(b) 관찰 기록
- 스크린샷 3장 경로
- `git diff config.yaml`(원복 후 빈 diff여야 함)

CUE가 이 원자료를 받아 AT-4/AT-5 PASS/FAIL을 직접 판정하고
`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DEPLOY_VERIFICATION_001.md`를 갱신한다.


## 실행 경위 및 최종 결과 (2026-09-18, CUE 직접 수행)

C1 위임 시도 중 2가지 문제 발견 후 CUE가 직접 전환:
1. C1의 `scripts/at4_screenshot.py`(Playwright)가 "AI에게 질문" 사이드바
   selector 실패로 엉뚱한 페이지("내 자료" 파일검색)를 캡처하고도
   "NAE Bridge 검색 결과"라고 잘못 보고 — 스크린샷 자체를 CUE가 직접
   열어 대조해 발견.
2. C1이 "스크린샷 기능이 없다"며 방금 자신이 만든 스크립트의 존재를
   부인하는 자기모순 — 파일 타임스탬프로 반박.

CUE가 built-in browser로 AT-4를 직접 재현, `ollama`/`core` 직접 호출로
AT-5를 직접 실행. 결과는 검증 문서
`docs/NAE_PARAGRAPH_ANSWER_DELIVERY_DEPLOY_VERIFICATION_001.md`의
Addendum(2026-09-18) 참고 — **AT-4/AT-5 둘 다 PASS**.

AT-5 실행 중 책 이름 없는 교리형 질의가 `RetrievalEngine` O(N) 콜드
스캔으로 84,766건 코퍼스에서 수 분 지연되는 배포 성능 이슈를 발견,
`USE_INVERTED_INDEX` 기본값 `true` 전환으로 해결(커밋 `ce8be59`).
그 전환이 노출시킨 Tantivy 쿼리 파서 크래시(괄호 포함 질의)도 같은
세션에서 수정·회귀테스트 추가·커밋·push 완료.

`config.yaml: modules.nae_pd.enabled`는 검증 완료 후 `false`로 원복함
(최종 `git diff config.yaml` 무변경 확인).
