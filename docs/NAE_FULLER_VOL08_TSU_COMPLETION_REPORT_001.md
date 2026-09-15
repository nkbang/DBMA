# NAE Fuller Vol.08 TSU 처리 완료 보고

- **문서 ID**: NAE-REG-BAP-MISS-FULLER-VOL08
- **제목**: The Works of the Rev. Andrew Fuller, in Eight Volumes — Vol. 8: Miscellanies (Magazine Papers, Sketches of Sermons, Association Letters, Tracts)
- **저자**: Andrew Fuller
- **판본**: 1824-1825 New Haven, `public_domain`
- **작성일**: 2026-09-14

---

## 상태

- [x] Raw 등록 (`archive_org`, source_id `BAP-MISS-FULLER-VOL08`)
- [x] Canonical 정규화 (`canonical.json`, `canonical.txt`, `normalize_report.json`)
- [x] TSU 클레임 추출 — **COMPLETE**
- [ ] 인간 검토(review_status: verified) — 미승격

**진행률: 100% (TSU 단계) / 검토 승격 대기**

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
| review_status | `generated` (미검증 — self-reported confidence, 미보정) |

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

## 다음 조치

- 사람 검토(review_promotion) 진행 후 `review_status`를 `verified`로 승격
- 승격 후 Production Registry 반영 여부 결정 (본 자동화 정책상 Production Registry 대량 변경은 항상 별도 승인 필요)

---

*작성 도구: `내서재 작업현황모니터 v0.6.0` 이벤트 로그 + `NAE/corpus/tsu/Fuller_Complete_Works_Vol08/tsu_report.json` 기준.*
