# NAE Gold Benchmark v1 — 작성 기준

이 문서는 100문항짜리 Gold Benchmark Dataset을 작성하는 사람(CUE/HQ, 또는 향후 합류할
theologian reviewer)을 위한 기준이다. **이 문서 자체는 문항을 대신 작성해주지 않는다** —
각 원칙 아래 "왜"를 적었으니, 판단이 필요한 경계 사례에서는 그 이유로 되짜본다.

전제 조건: 이 가이드를 쓰기 전에 대상 문헌이 실제로 NAE corpus에 수집·정규화·TSU화·색인까지
완료되어 있어야 한다(`docs/agents/cue/CUE-PHASE5.1-ARCHITECTURE-REVIEW.md`의 ISSUE #1 참고).
corpus에 없는 내용을 묻는 질문은 애초에 gold_tsu_ids를 채울 수 없다.

---

## 1. 질문 작성 원칙

- **질문은 corpus에 실제로 답이 있는 것만 만든다.** NAE는 아직 신학 전체를 다루지 않는다 —
  지금 수집된 문헌이 다루지 않는 주제(예: 코퍼스에 없는 저자·교리)로 질문을 만들면 검색이
  실패하는 게 당연한데도 "검색 실패"로 잘못 기록된다.
- 질문은 **검색 가능한 형태**로 쓴다. "침례교 신학의 특징은 무엇인가?"처럼 지나치게
  포괄적인 질문보다 "존 길(John Gill)은 유아세례를 어떻게 반박했는가?"처럼 특정 TSU
  claim 하나(또는 소수)로 수렴할 수 있는 질문이 검색 평가에 적합하다.
- 답이 여러 문헌에 흩어져 있어도 괜찮다 — `gold_tsu_ids`는 리스트이므로 다중 정답을 허용한다.
  다만 너무 많은 TSU(10개 이상)를 정답으로 지정하면 recall/precision이 무의미해지므로,
  실제로 "이 claim이 이 질문에 직접 답한다"고 확신하는 것만 넣는다.
- 한국어(`language: "ko"`)와 영어(`"en"`) 둘 다 작성 가능하나, 질문의 언어와 corpus
  원문 언어가 다를 수 있음을 감안한다(현재 BGE-M3 임베딩은 다국어 지원이지만 완벽한
  교차언어 검색 성능은 검증되지 않았다 — 이것도 벤치마크가 측정해야 할 대상 중 하나다).

## 2. Gold TSU 선정 기준

- **반드시 `nae_qdrant`(`nae_tsu_v{N}` 컬렉션)에 실제로 존재하는 `tsu_id`만 사용한다.**
  Qdrant에서 직접 검색/scroll해서 확인한 값만 넣는다 — 기억이나 추측으로 TSU ID를 적지 않는다.
- 확인 방법 예시:
  ```bash
  curl -s -X POST http://localhost:7333/collections/nae_tsu_v1/points/scroll \
    -H 'Content-Type: application/json' \
    -d '{"limit": 50, "with_payload": true, "filter": {"must": [{"key": "doctrine", "match": {"value": "Baptism"}}]}}'
  ```
  또는 `NAE.pipeline.embed.client`로 질문 문장을 직접 임베딩해 Qdrant 유사도 검색으로
  후보를 찾은 뒤, 그 중 실제로 질문에 답하는 것만 사람이 골라 gold로 확정한다(이 방식이
  "완전 랜덤으로 답을 아는 TSU를 하나하나 찾는" 것보다 효율적이다 — 단, 검색 결과를
  기계적으로 전부 gold로 승인하면 안 된다. 검색이 맞았는지 여부를 사람이 판단해야
  gold의 의미가 있다).
- TSU의 `review_status`가 `"unverified"`인 것도 gold로 쓸 수 있다 — TSU 자체의 검증
  상태와 "이 TSU가 이 질문의 정답이다"라는 벤치마크 판단은 별개다. 다만 TSU의
  `source_text`를 반드시 읽고 원문 맥락에서도 실제로 그 주장을 하고 있는지 확인한다
  (claim 필드는 LLM이 재진술한 것이라 원문과 미묘하게 다를 수 있음 — Phase 3 설계 문서 참고).

## 3. Scripture 선택 기준

- `expected.expected_scriptures`는 **평가 지표 계산에는 쓰이지 않는 설명용 필드**다
  (TASK 1 개정 이후). 사람이 문항을 검토할 때 참고하기 위한 것이므로, gold_tsu_ids로
  고른 TSU들의 `scriptures` 필드 값을 그대로 가져와 채운다 — 새로 창작하지 않는다.
- TSU에 scripture가 비어있는 claim을 gold로 쓰는 것도 무방하다(모든 신학적 주장이
  성경 구절을 직접 인용하지는 않는다) — 이 경우 `expected_scriptures`는 빈 리스트로 둔다.

## 4. Doctrine Tag 기준 (`theology_area`)

- `NAE.pipeline.tsu.config.DOCTRINE_CATEGORIES`에서만 선택한다(새 카테고리 창작 금지 —
  `CUE-PHASE5.1-ARCHITECTURE-REVIEW.md`의 ONTOLOGY REVIEW 참고).
- **정합성 규칙**: `theology_area`는 gold_tsu_ids로 선택한 TSU들의 `doctrine` 값과
  일치하거나 최소 하나는 일치해야 한다. 불일치하면 둘 중 하나가 잘못된 것이니
  재검토한다(TSU의 doctrine 분류가 틀렸을 수도, 문항의 theology_area 판단이 틀렸을
  수도 있다 — 어느 쪽이든 이 불일치 자체가 유용한 신호다).

## 5. Difficulty 분류 기준

3단계 고정(자유 텍스트 금지):

| 값 | 기준 |
|---|---|
| `easy` | 질문의 핵심 키워드가 정답 TSU의 `claim`/`source_text`에 거의 그대로 등장한다. 어휘 매칭만으로도 검색이 성공할 가능성이 높다. |
| `medium` | 핵심 키워드는 일치하지 않지만 개념적으로 명확히 연결된다(동의어, 신학 용어 변환 등). 의미 기반 검색(임베딩)의 실질적인 테스트 대상. |
| `hard` | 여러 TSU를 종합해야 답이 되거나, 질문과 정답 TSU 사이에 명시적 어휘·개념 연결이 약해 순수 검색만으로는 찾기 어렵다. |

difficulty는 "신학적으로 어려운 질문"이 아니라 **"검색 엔진이 찾기 어려운 질문"** 기준이다 —
이 벤치마크는 신학 지식 시험이 아니라 retrieval 품질 측정 도구다.

## 6. Question Type 분류 기준

`NAE/benchmark/config.py`의 `QUESTION_TYPE_CATEGORIES`(버전 관리되는 리스트, 100문항을
실제로 작성하며 필요시 갱신 가능)에서 선택한다. 초기 제안값:

- `factual` — 특정 사실/정의를 묻는 질문 ("웨스트민스터 신앙고백은 언제 작성되었는가?")
- `doctrinal` — 특정 교리에 대한 입장/논증을 묻는 질문
- `comparative` — 두 인물/전통/교리를 비교하는 질문
- `exegetical` — 특정 성경 본문의 해석을 묻는 질문
- `historical` — 역사적 사건/맥락을 묻는 질문
- `other` — 위에 속하지 않는 경우

이 목록은 확정이 아니다 — 실제 100문항을 작성하다 보면 카테고리가 부족하거나 넘칠 수
있으므로, 그 경우 이 문서와 `config.py`를 함께 갱신한다(단, 이미 승인된 문항의
question_type을 소급 변경할 때는 review.status를 `needs_revision`으로 되돌린다).

---

## 체크리스트 (문항 1개 완성 기준)

- [ ] `question.text` — corpus가 실제로 답할 수 있는 구체적 질문
- [ ] `gold_tsu_ids` — Qdrant에서 직접 확인한 실제 TSU ID 1개 이상
- [ ] `expected.expected_scriptures` — gold TSU의 scriptures 필드에서 가져옴(창작 금지)
- [ ] `expected.expected_doctrine` — gold TSU의 doctrine 필드에서 가져옴
- [ ] `theology_area` — DOCTRINE_CATEGORIES 중 선택, gold TSU의 doctrine과 정합성 확인
- [ ] `difficulty` — 검색 난이도 기준으로 판단(신학적 난이도 아님)
- [ ] `question_type` — config.py의 QUESTION_TYPE_CATEGORIES 중 선택
- [ ] `metadata.dataset_version` — 현재 작업 중인 manifest 버전과 일치
- [ ] `review.status` — 작성 완료 시 `"in_review"`로 전환(검토자에게 전달 신호)
