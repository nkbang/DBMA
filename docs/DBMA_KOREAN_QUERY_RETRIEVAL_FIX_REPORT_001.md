# 한국어 질의 검색 복구 Build Report 001

- 작성: CUE · 일자: 2026-09-26
- 선행 진단: `docs/DBMA_P0_5_EVIDENCE_HOLD_ROOT_CAUSE_001.md`
- HQ 결정: (A) 질의 번역 우선 + 0건 시 솔직한 안내
- 결과: **STATUS = 성공.** P0-5 유보 17건 전량이 후보를 확보(0/17 → 17/17)

---

## 1. 실제로는 결함이 3개였다

진단 단계에서 하나(언어 불일치)로 보였던 것이 구현 중 **독립된 3개**로 갈라졌다.
모두 "게이트가 비었는데 폴백이 없다"는 같은 형태다.

| # | 결함 | 영향 범위 | 실측 |
|---|---|---|---|
| **1** | 한국어 질의 ↔ 영문 코퍼스 어휘 불일치 | 한글 질의 전부 | 코퍼스 `language` 분포 = `en` 119,595 / **한국어 0.00%** |
| **2** | `bible` route가 빈 포스팅 리스트로 종료 | 구절 참조 포함 질의 전부 | `bible_posting` 테이블 **0행**, TSU `verse_mapping` 보유 **0/119,595 (0.0%)** |
| **3** | 만족 불가능한 `book_id` 필터가 전건 탈락시킴 | 성경 책 이름 포함 질의 전부 | `"no condemnation in Christ Jesus"` → 2건 / `"Romans no condemnation in Christ Jesus"` → **0건** |

결함 2·3이 특히 무겁다 — **설교 준비 질의는 대개 구절 참조나 책 이름을 포함**하므로
가장 흔한 사용 패턴이 구조적으로 0건이었다.

---

## 2. 수정

| 파일 | 내용 |
|---|---|
| `core/query_translation.py` (신규) | 한국어 질의 → 영어 번역 전처리. 실패 시 `None`(예외 없음), 플래그 `QUERY_TRANSLATION_FALLBACK`(기본 on), 모델 `QUERY_TRANSLATION_MODEL`(기본 `llama3.1:8b`) |
| `core/hybrid_candidate_pipeline.py` | ① 언어 불일치 시 Stage-1 **전** 번역 ② `bible` route가 0건이면 자유 텍스트로 강하 ③ 코퍼스에 `book_id`가 없으면 book 필터를 애초에 얹지 않음. Stage-1 디스패치를 `_generate_candidates()`로 추출(로직 무변경) |
| `ui/pages/chat.py`, `ui/pages/sermon_draft.py` | 0건 안내에 서재 언어 고지 덧붙임 |
| 테스트 | `test_query_translation_fallback.py` 22건 신규 |

번역은 **검색 전처리**이며 새 검색 경로가 아니다 — `QueryProcessor`/`RetrievalEngine`
무변경, ADR-001(One Retrieval Engine) 저촉 없음.

---

## 3. 설계를 한 번 틀렸고, 실측이 잡아냈다

처음 구현은 **"Stage-1이 0건일 때만 번역"** 이었다. 그 설계는 실패했다.

한국어 토큰이 영문 코퍼스의 **OCR 잡음에는 걸린다.** 따라서 0건이 되지 않고,
번역이 영원히 발동하지 않는다. 실측으로 확인한 결과 구절 참조 질의 5건이 번역
없이 후보를 얻었고 그 내용은 전부 쓰레기였다:

```
A1 → "=) EY: == 6  EEKEY KEE EEK SE  . . . = _- ? . Lac # j «"     (OCR 쓰레기)
A3 → "AE A 30 1 Y Ls. „69200 19 xv.13 ... 1332 28 ZV 13"          (성구 색인 페이지)
C1 → "ajaAi tubj aq; jo 8;jBd uiB;jaQ 'pautf spuBq Jioq;"          (거울상 OCR)
```

같은 이유로 **"0건이면 필터를 버리고 재시도"도 기각했다** — 한 번 넣어봤더니
필터 없는 검색이 위 잡음을 후보로 채우고, 그 결과 번역이 막혔다. 되돌렸다.

정정: 발동 기준을 "결과가 비었는가"가 아니라 **"질의 언어와 코퍼스 언어가
어긋났는가"**로 바꿨다. 코퍼스 한국어 비중이 20% 미만이면 한글 질의를 Stage-1
전에 번역한다. 한국어 자료가 쌓이면 조건이 저절로 거짓이 되어 번역이 멈춘다.

결함 3도 같은 원칙으로 고쳤다 — "0건이면 필터 해제" 대신 **필터가 만족
불가능할 때만 얹지 않는다**(구조적 판정, 1회 계산 후 캐시).

---

## 4. 검증

### 4.1 P0-5 유보 17건 전량

```
수정 전: 후보 0건 = 16/17  (유일한 예외 G2는 환각 트랩 — 0건이 정답이었어야 함)
수정 후: 후보 확보 = 17/17, 번역 적용 17/17, 잡음 상위 노출 0건
```

관련성 표본(상위 1건 원문):

| 질의 | 반환된 근거 |
|---|---|
| A1 로마서 8:1-4 정죄 없음 | *"There is therefore now no condemnation to them which are in Christ Jes…"* — **목표 구절 정확 적중** |
| E1 이혼·외도 상담 | *"Causeth her to commit adultery : and whosoever shall marry her that…"* |
| D1 유아세례 비교 | *"Episcopacy, Infant-baptism, etc., there is equal reason to…"* |
| H1 악과 고통 | *"His attribute of justice, which is as undoubtedly a part of his glory as…"* |
| F2 교회의 표지 | *"according to the Order and discipline Christ hath set in his Word…"* |

### 4.2 회귀

```
신규            22 passed
관련 회귀      505 passed / 0 failed
               (hybrid·candidate·retrieval·chat·sermon·evidence 범위)
```

수정 과정에서 3건이 깨졌고 전부 처리했다 — 2건은 중첩 `getattr` 누락(내 버그,
수정), 1건은 안내 문구에 고지가 붙은 것을 정확 일치로 검사하던 테스트(의도된
동작이므로 접두 일치로 조정).

---

## 5. 과장하지 않기 위한 단서

- **"17/17 후보 확보"는 "17/17 해결"이 아니다.** 구조적 0건은 사라졌으나 관련성은
  고르지 않다 — §4.1 표본에서 절반은 정확히 적중하고 절반은 주변적이다. 이제
  문제의 성격이 **구조적 실패에서 일반적인 랭킹 품질**로 바뀐 것이며, 품질은
  별도 측정 대상이다.
- **G2(환각 트랩)가 이제 후보를 받는다.** 내용은 질문과 무관하므로 하류
  근거 강제·ClaimGuard가 유보를 유지해야 한다. 이 경로는 재확인이 필요하다.
- 번역 품질에 의존한다. 신학 용어 오역 시 엉뚱한 근거를 부를 수 있다.
- 한글 질의마다 LLM 1회(실측 0.2~0.8초)가 추가된다. 영어 질의는 불변.
- **근본적으로 근거가 전량 영문이다.** 목회자는 한국어로 묻고 영문 근거를 받는다.
  Fuller/Dagg/Hiscox 편입이나 한국어 자료 확보는 별도 HQ 결정 사항이다.

---

## 6. 기록

```
STATUS:       성공
Changed:      core/query_translation.py(신규), core/hybrid_candidate_pipeline.py,
              ui/pages/chat.py, ui/pages/sermon_draft.py,
              tests/test_query_translation_fallback.py(신규),
              tests/test_sermon_insufficient_evidence.py(단정 조정)
              ※ core/candidate_generator.py 는 시도 후 되돌려 최종 무변경
Tests:        22 passed
Regression:   505 passed / 0 failed
Architecture: ADR-001 무위반 — 검색 경로 신설 없음, RetrievalEngine 무변경
Next:         관련성 품질 측정 / G2 트랩 하류 유보 재확인 / 한국어 자료 확보 결정
```
