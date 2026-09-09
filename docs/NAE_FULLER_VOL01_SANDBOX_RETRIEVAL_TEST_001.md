# Fuller Vol.01 — Sandbox Retrieval Test (isolated, non-production)
- records: 3643  embedded/upserted: 3643
- collection: nae_tsu_fuller_sandbox_v0 @ http://localhost:7333  (nae_tsu_v1 / nae_ref_v1 untouched)
- embed: bge-m3:latest, claim field, 1024d cosine (production path)

## doctrine distribution (Vol.01 TSU)
- Soteriology: 2314
- Sanctification: 279
- Justification: 271
- Providence: 204
- Election: 165
- None: 136
- Ecclesiology: 98
- Scripture / Authority: 73
- Eschatology: 61
- Trinity: 21
- Other: 10
- Baptism: 9
- Confession: 2

## sample queries (top-3)

### Q: 믿음은 모든 사람의 의무인가
  [FULLER-V01]
    0.915  TSU-0004125  (Soteriology)  그리스도에 대한 믿음은 모든 사람의 의무이다
    0.865  TSU-0005741  (Soteriology)  모든 사람에게는 복음을 믿는 것이 의무이다.
    0.850  TSU-0005257  (Soteriology)  믿음은 의무이다
  [DAGG/HISCOX-baseline]
    0.745  TSU-0003333  (Ecclesiology)  우리는 우리의 신앙과 질서에 대한 의무를 느끼고, 모두가 이 의무를 느끼어야 한다.
    0.711  TSU-0001869  (Justification)  진정한 믿음은 은혜로 말미암아 약속이 모든 후손에게 확실히 이루어지도록 하기 위해 필요하다
    0.705  TSU-0002704  (Ecclesiology)  모든 기독교인들은 어느 정도 크리스도의 지식을 전파할 의무를 공유한다.

### Q: 구원은 오직 은혜로 말미암는가
  [FULLER-V01]
    0.870  TSU-0007264  (Soteriology)  구원은 하나님의 주권적인 은혜로만 가능하다
    0.785  TSU-0007051  (Soteriology)  죄의 제거와 타락의 정복은 오직 은혜로만 가능하다.
    0.783  TSU-0007559  (Soteriology)  구원은 오직 하나님의 방법을 선택하는 자에게만 주어진다
  [DAGG/HISCOX-baseline]
    0.718  TSU-0003659  (Soteriology)  구원은 하나님의 은혜로 말미암아 믿음을 통하여 이루어지며, 그것은 우리 자신에게서 나온 것이 아니라 하나님의 선물이다.
    0.698  TSU-0002552  (Justification)  구원은 의식이나 의무를 통한 자체의 공로가 아니라 믿음으로 의지하는 것에 달려있다
    0.685  TSU-0001969  (Soteriology)  믿음이 없이는 구원은 불가능하다

### Q: 회심하지 못한 죄인도 그리스도를 믿으라는 명령을 받는가
  [FULLER-V01]
    0.832  TSU-0004289  (Soteriology)  성경을 통해 배우는 바에 따르면, 회심하지 않은 죄인들은 그리스도를 믿어야 할 의무가 있다.
    0.814  TSU-0005771  (Soteriology)  그리스도에 대한 믿음은 회심하지 않은 죄인의 의무이다.
    0.801  TSU-0004369  (Soteriology)  구원받기 위해 그리스도에게 믿음을 가지는 것은 회심하지 않은 죄인의 의무이다.
  [DAGG/HISCOX-baseline]
    0.670  TSU-0002737  (Ecclesiology)  성령은 회심하지 않은 사람을 목사로 삼지 않는다.
    0.665  TSU-0001973  (Soteriology)  믿지 않는 자는 정죄를 받을 것이라는 성경의 말씀과 영아 구원의 교리는 어떻게 조화시킬 수 있는가?
    0.657  TSU-0002367  (Church Discipline)  회개하지 않는 자는 그리스도가 명령하신 모든 것을 지키도록 가르치지 말아야 한다.

### Q: 세례의 의미와 대상은 누구인가
  [FULLER-V01]
    0.659  TSU-0004618  (Baptism)  세례는 그리스도와 그의 말씀을 받아들이는 것에 앞서서는 성인들의 의무가 아니다
    0.629  TSU-0007583  (Baptism)  세례는 오직 믿는 자들에게만 주어져야 한다.
    0.629  TSU-0004634  (Soteriology)  믿는 자와 세례를 받은 자는 구원을 받을 것이다
  [DAGG/HISCOX-baseline]
    0.722  TSU-0000612  (Baptism)  세례의 적절한 대상은 죄를 회개하고 그리스도를 믿는 사람들이다.
    0.715  TSU-0000663  (Baptism)  세례 의식은 하나님께 대한 순종과 헌신의 서약을 의미한다.
    0.701  TSU-0000590  (Baptism)  세례는 그리스도의 매장과 부활, 그리고 죄의 씻김을 대표하며, 이 모든 목적을 이루지 못하는 사람은 세례를 소홀히 하는 사람이다.

### Q: 교회의 권징은 어떻게 시행되는가
  [FULLER-V01]
    0.566  TSU-0006062  (Election)  신의 명령과 일치하면서도 믿음은 의무일 수 있는가?
    0.544  TSU-0006635  (Soteriology)  우리의 믿음 의무는鼓勵에서 비롯되는가, 아니면 그것과 관련된 명령에서 비롯되는가?
    0.543  TSU-0006221  (Soteriology)  그리스도에 대한 믿음이 도덕법에 의해 요구되는가?
  [DAGG/HISCOX-baseline]
    0.692  TSU-0000689  (Ecclesiology)  교회는 성경의 가르침에 따라 무엇인가?
    0.635  TSU-0000786  (Ecclesiology)  교회가 교회 규율을 수행하는 적절한 주체라는 것
    0.615  TSU-0000840  (Ecclesiology)  교회는 결정하고 그 결정을 발표한다.

### Q: 성경의 권위와 무오성
  [FULLER-V01]
    0.684  TSU-0006435  (Scripture / Authority)  성경의 권위를 인정하지 않으면 어려움이 더 커진다
    0.666  TSU-0006089  (Scripture / Authority)  성경의 진리는 명확한 증명이 가능하다
    0.640  TSU-0005547  (Sanctification)  성경에서 성령의 영향으로 인한 영적 지식이 거룩함에 기인한다
  [DAGG/HISCOX-baseline]
    0.650  TSU-0003135  (Ecclesiology)  성경적 교회 질서는 탁월하다.
    0.648  TSU-0004086  (Scripture / Authority)  성경은 종교적 신앙과 실천에 관한 유일한 규칙이자 권위이다.
    0.623  TSU-0003720  (Providence)  신이 정한 권위가 존재한다

### Q: 선택과 예정 교리
  [FULLER-V01]
    0.623  TSU-0006312  (Election)  선택과 성령의 성결은 순종의 적절한 원인이다.
    0.621  TSU-0006772  (Election)  선출 교리는 증명된다
    0.596  TSU-0006311  (Election)  선택과 성령의 거룩하게 하심은 순종에 대한 적절한 원인이다.
  [DAGG/HISCOX-baseline]
    0.584  TSU-0003474  (Ecclesiology)  교회에서 성례와 예배의 시간, 장소, 빈도는 선택사항이다.
    0.555  TSU-0001606  (Ecclesiology)  예수님의 말씀과 행동의 순서는 중요하며, 그 순서에 따라 제자들의 이해가 준비되었다.
    0.551  TSU-0003433  (Ecclesiology)  교회에서 집사들의 수는 선택사항이다.

### Q: 그리스도의 속죄의 범위
  [FULLER-V01]
    0.783  TSU-0006882  (Soteriology)  그리스도의 속죄는 구원에 대한 적용과 관련이 있다.
    0.727  TSU-0004712  (Soteriology)  그리스도의 속죄를 통한 구원은 받아들여질 수 있다.
    0.727  TSU-0005442  (Justification)  하나님과의 용서와 수용은 예수님의 속죄를 통해 가능하다
  [DAGG/HISCOX-baseline]
    0.626  TSU-0000419  (Lord's Supper)  주님의 만찬은 그리스도의 속죄 사역을 대표하며, 우리가 믿음으로 그리스도를 먹는 것을 나타내므로 이 목적에만 국한해서는 안 된다.
    0.598  TSU-0002729  (Soteriology)  유다의 고백은 그리스도의 무죄함과 그의 죽음의 중요성을 증명한다
    0.592  TSU-0003635  (Soteriology)  그리스도는 우리의 죄와 불의로 인해 상처를 입었고, 우리의 평화를 위한 징계가 그에게 내려졌으며, 그의 채찍으로 우리는 치유받았다.

### Q: 성화는 어떻게 이루어지는가
  [FULLER-V01]
    0.631  TSU-0006009  (Sanctification)  성도들의 성결은 그리스도에게서 비롯되며, 성령의 영향으로 자연적 유전이 아닌 방법으로 이루어진다.
    0.623  TSU-0006365  (Soteriology)  성령을 받기 전에 믿음을 가졌을 때 사람의 상태는 무엇인가?
    0.599  TSU-0004403  (Soteriology)  하나님을 기쁘게 하기 위해서는 무엇을 해야 하는가?
  [DAGG/HISCOX-baseline]
    0.638  TSU-0000368  (Baptism)  세례는 주로 성수를 뿌림으로써 행해진다.
    0.613  TSU-0002318  (Lord's Supper)  성찬을 받기 위해서는 믿음이 필요하다.
    0.608  TSU-0003903  (Baptism)  세례는 성찬전에 선행한다

### Q: 지역 교회의 자율성과 회중 정치
  [FULLER-V01]
    0.516  TSU-0007202  (Soteriology)  인간은 법과 복음에 관하여 선택의 자유를 가지고 있다.
    0.515  TSU-0006374  (Sanctification)  일부 사람들은 그리스도인들이 자신의 의를 강조하는 설교 방식은 자아도취와 자기충족感을 불러올 수 있다고 주장한다.
    0.507  TSU-0006731  (Ecclesiology)  교회는 이 곳에서 실제로 믿은 사람들만을 의미하지 않는다.
  [DAGG/HISCOX-baseline]
    0.663  TSU-0004004  (Ecclesiology)  독립교회는 자치적이며, 각 지역 교회가 회원들의 다수결에 따라 자신의 정부를 관리한다.
    0.633  TSU-0001358  (Ecclesiology)  지역 교회들은 독립적으로 조직되어 행동했지만 하나의 단체로서 공식적인 자문을 받거나 행동하지는 않았다.
    0.623  TSU-0001173  (Ecclesiology)  교회는 지역적인 것이 아니라 보편적이다.

### Q: 믿음으로 의롭다 하심을 받음
  [FULLER-V01]
    0.815  TSU-0005766  (Justification)  사람이 마음으로 믿음으로 의로움을 얻는다.
    0.803  TSU-0005415  (Justification)  의인은 믿음으로 의롭다 함을 받는다는 교리
    0.783  TSU-0005072  (Justification)  믿음으로 말미암은 의롭다 함을 받는 것은 믿는 자가 그리스도와 연합함으로써 가능하다
  [DAGG/HISCOX-baseline]
    0.720  TSU-0000639  (Justification)  인간은 마음으로 의로움을 믿고, 입으로 고백한다.
    0.709  TSU-0003638  (Justification)  그리스도께서 믿는 자들에게 보장하는 큰 복음의 축복은 의롭다함을 받는 것이며, 이는 죄를 사해 주심과 영생을 주시는 것으로 오직 믿음을 통해 하나님께 의롭다함을 받게 되고
    0.707  TSU-0003642  (Justification)  한 사람의 순종으로 많은 사람이 의롭다 하심을 받는다.

### Q: 하나님의 섭리와 고난
  [FULLER-V01]
    0.773  TSU-0006935  (Providence)  하나님의 섭리는 우리가 겪는 모든 고난과 어려움을 포함한다
    0.684  TSU-0006936  (Providence)  하나님의 섭리는 인간의 고통과 어려움을 포함하여 모든 일에 작용하며, 이는 하나님께서 각 개인에게 정하신 일을 수행하시는 것
    0.663  TSU-0006931  (Providence)  하나님의 섭리가 우리의 삶과 환경을 결정한다
  [DAGG/HISCOX-baseline]
    0.609  TSU-0003077  (Sanctification)  하나님의 섭리를 무시하는 것은 하나님의 계략을 거부하고 영적 가난을 초래한다.
    0.600  TSU-0001166  (Soteriology)  그리스도의 고난을 내가 몸으로 채워야 한다.
    0.596  TSU-0002283  (Lord's Supper)  성만찬에서 그리스도는 고난과 죽음의 모습으로 제시된다.

---

## 평가 (CUE, 2026-09-09)

### 파이프라인 — 정상 동작 ✅
- canonical → TSU(3,643) → bge-m3 임베딩(claim 필드, 프로덕션 경로) → Qdrant → 검색까지 end-to-end 작동.
- 격리 확인: `nae_tsu_v1` 3,319 point 무변동, `nae_ref_v1` 무접촉. sandbox 컬렉션만 추가.
- F2(Vol.02) 동시 실행 중 임베딩 3,628건 신규 계산 248초(~14.6/s), F2 llm_errors 증가 없음(2건 유지).

### 검색 품질 — Vol.01이 다루는 교리에서 강함
| 질의 유형 | FULLER-V01 top1 | baseline top1 | 판정 |
|---|---|---|---|
| 믿음=의무 | 0.915 | 0.745 | Fuller 압도 (Vol.01 핵심 주제) |
| 오직 은혜 구원 | 0.870 | 0.718 | Fuller 우세 |
| 미회심자의 믿을 의무 | 0.832 | 0.670 | Fuller 압도 |
| 믿음으로 의롭다 하심 | 0.815 | 0.720 | Fuller 우세 |
| 속죄의 범위 | 0.783 | 0.626 | Fuller 우세 |
| 섭리와 고난 | 0.773 | 0.609 | Fuller 우세 |
| **세례 대상** | 0.659 | **0.722** | baseline(Dagg) 우세 |
| **교회 권징** | 0.566 | **0.692** | baseline 우세, Fuller 결과 off-topic |
| **지역교회 자율성** | 0.516 | **0.663** | baseline 우세, Fuller off-topic |
| **선택/예정** | 0.623 | 0.584 | 둘 다 약함 |

→ **Vol.01("The Gospel Worthy of All Acceptation")은 구원론 전문 소스.** 교회론/권징/정치 질의는 Fuller Vol.01에 내용이 거의 없어 낮은 점수 + 무관 결과. Dagg(Church Order) baseline이 그 영역을 담당 → **상호 보완**. Vol.02–08이 들어오면 교회론 커버리지 개선 예상.

### 품질 결함 (F3 검수 대상)
| 결함 | 건수 | 비율 | 원인 |
|---|---|---|---|
| **claim에 한자(CJK) 혼입** | **366** | **10.0%** | `my-theology-bot-v2`(Qwen 계열)가 부하 시 중국어로 코드스위칭. 예: `相信`, `真正`, `義`, `荣耀`, `世間`, `人们` |
| 의문문 형태 claim | 58 | 1.6% | 추출기가 원문 수사의문문을 그대로 claim화 |
| 근사 중복 claim | 다수(미집계) | — | 반복 원문 구절에서 거의 동일한 claim 생성 (예: TSU-0006311/0006312) |

**한자 혼입 10%가 최대 이슈** — OCR 노이즈(~1.7%)보다 심각하고, 소스가 아니라 **모델 출력 결함**. 임베딩·가독성·인용 노출 모두 저하. Vol.02도 같은 모델이라 동일 발생 예상.

### 권고
1. **한자 혼입**: F3 검수에서 필수 수정 항목으로 등록. 또는 F2 완료분에 대해 후처리 정규화 스크립트(한자→한글 音역/재추출) 검토 — `builder_version` 불변(후처리는 별도 단계)이면 Amendment A 무영향.
2. **커버리지**: Vol.01만으로는 구원론 편중. F2 완료 후 재테스트.
3. 이 테스트는 **샌드박스** — `nae_tsu_fuller_sandbox_v0`는 임시. F4/F5/F6(프로덕션 색인)는 Amendment A Approved 후에만.
