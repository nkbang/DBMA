# NAE Fuller Vol.08 TSU 처리 완료 보고

- **문서 ID**: NAE-REG-BAP-MISS-FULLER-VOL08
- **제목**: The Works of the Rev. Andrew Fuller, in Eight Volumes — Vol. 8: Miscellanies (Magazine Papers, Sketches of Sermons, Association Letters, Tracts)
- **저자**: Andrew Fuller
- **판본**: 1824-1825 New Haven, `public_domain`
- **작성일**: 2026-09-14
- **최종 갱신**: 2026-09-16 (인간 검토 완료 반영)

---

## 상태

- [x] Raw 등록 (`archive_org`, source_id `BAP-MISS-FULLER-VOL08`)
- [x] Canonical 정규화 (`canonical.json`, `canonical.txt`, `normalize_report.json`)
- [x] TSU 클레임 추출 — **COMPLETE**
- [x] 인간 검토(review_status: verified) — **COMPLETE** (2026-09-16)

**진행률: 100% (TSU 단계) / 100% (검토 승격)**

---

## TSU 처리 결과

| 항목 | 값 |
|---|---|
| builder_version | 3.0.0 |
| model | my-theology-bot-v2:latest |
| candidates_evaluated / total | 7,407 / 7,407 (100%) |
| claims_extracted | 5,052 |
| llm_errors | 0 |
| elapsed_seconds | 77,041.5 (약 21.4시간) |
| partial | false |
| generated_at | 2026-09-14T11:28:27Z |
| review_status | `verified` 5,046건 / `rejected` 6건 (2026-09-16 인간 검토 완료) |

## 교리 분류 분포 (doctrine_breakdown)

| 교리 범주 | 클레임 수 |
|---|---|
| Soteriology | 1,635 |
| Ecclesiology | 951 |
| Sanctification | 762 |
| Eschatology | 394 |
| Providence | 442 |
| Scripture / Authority | 224 |
| Trinity | 129 |
| Justification | 114 |
| Election | 91 |
| Baptism | 69 |
| Lord's Supper | 26 |
| Other | 27 |
| Church Discipline | 22 |
| Confession | 12 |
| Church Covenant | 1 |

## 이벤트 로그 (요약)

TSU 러너가 90.5% 지점(04:46:34)부터 99.9%(06:27:42)까지 약 100건 단위 체크포인트로 진행률을 저장했고, 06:28:30에 `Fuller_Complete_Works_Vol08: RUNNING → COMPLETE`로 전이된 직후 TSU 프로세스가 정상 종료(stopped)되었다. NAE 큐 상 VOL.01~VOL.08 전 볼륨이 COMPLETE 상태다.

---

## 인간 검토(Human Review) 결과 — 2026-09-16

### 검토 방식

Dagg_Church_Order·Hiscox_Standard_Manual 두 소스는 batch_0024~batch_0040에 걸쳐 Q1(Claim Fidelity)/Q2(Theological Accuracy)/Q3(Context Sufficiency) 개별 항목 검토 방식으로 처리되었으나, Fuller Vol.08은 규모(5,052건)를 고려해 **사용자(reviewer=David)의 명시적 판단**에 따라 개별 항목별 검토 없이 처리되었다:

> "Fuller 자료는 침례교 것이니까 그대로 사용한다" — 저자 Andrew Fuller가 침례교 신학자이므로 개별 Q1/Q2/Q3 검토 없이 일괄 승인하기로 결정 (범위는 `AskUserQuestion`으로 재확인: 전체 일괄 verified, 단 사전에 발견된 데이터 결함 6건은 제외).

이는 `NAE/pipeline/tsu/review_promotion.py::promote_tsu_to_verified()`(reviewer/review_date/review_decision 3개 필드 모두 명시 필수, CUE가 임의로 채울 수 없는 pure function)를 통해 정상적으로 수행되었다 — 결정의 주체는 사용자이며, CUE는 승인 절차를 실행·기록만 했다.

### 결과

| 항목 | 값 |
|---|---|
| 전체 레코드 | 5,052 |
| `verified` (승인) | 5,046 |
| `rejected` (거부) | 6 |
| `generated` (대기) | 0 |
| reviewer | David |
| review_date | 2026-09-16 |
| review_decision | approved (5,046) / rejected (6) |
| 감사 기록 | `NAE/review/human/decisions/batch_fuller_vol08_bulk_decisions.json` |

### 거부 6건 — 목차(TOC) 오분류 데이터 결함

Fuller Vol.08 검토 착수 전 사전 점검에서, canonical.json의 목차(Table of Contents) 페이지 일부가 `type: "prose"` 문단으로 잘못 분류되어 TSU 클레임 생성 파이프라인이 목차 항목 텍스트(제목+페이지번호)를 실제 저자 주장으로 오인해 클레임을 생성한 사례가 발견되었다. 전체 5,052건 중 6건(0.12%)에 한정된 국소적 결함으로 확인되어 별도 코퍼스 재처리 없이 개별 거부 처리했다.

| TSU ID | source_text (발췌) | 비고 |
|---|---|---|
| TSU-0030341 | "Degrees in Glory proportioned to Works of Piety, consistent with Salvation by Grace alone --- --_6£" | 목차 항목 + 페이지번호 |
| TSU-0030342 | "Answer to the Queries : How may a Man ascertain his Election of God to the Ministry..." | 목차 항목 |
| TSU-0030343 | "An Answer to the following Queries : Did not the law of God require of Christ..." | 목차 항목 |
| TSU-0030344 | "If it did, how can that obedience be imputed to sinners for their justification?" | 목차 항목(부제) |
| TSU-0030345 | "Christ should both obey the law in his people's stead..." | 목차 항목(부제) |
| TSU-0030346 | "The Deity of Christ Essential to Atonement 297" | 목차 항목 + 페이지번호 |

이 6건은 `claim_raw` 재작성 없이 `review_status: rejected`로 확정했다(재작성 대상이 되는 신학적 claim 자체가 존재하지 않는 케이스이므로).

---

## 최종 결론

Fuller_Complete_Works_Vol08의 TSU 파이프라인(추출) 및 Human Review Gate(검토·승격) 단계가 모두 완료되었다. `review_status="generated"`인 레코드는 더 이상 존재하지 않는다.

이로써 NAE-TSU-REVIEW-WORKFLOW 대상 3개 소스(Dagg_Church_Order 3,377건, Hiscox_Standard_Manual 740건, Fuller_Complete_Works_Vol08 5,052건, 총 9,169건) 전체의 human review가 종료되었다 — verified 9,111건, rejected 58건, generated(대기) 0건.

## 다음 조치

- 승격 후 Production Registry 반영 여부 결정 (본 자동화 정책상 Production Registry 대량 변경은 항상 별도 승인 필요)

---

*작성 도구: `내서재 작업현황모니터 v0.6.0` 이벤트 로그 + `NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu_report.json` + `NAE/review/human/decisions/batch_fuller_vol08_bulk_decisions.json` 기준.*
