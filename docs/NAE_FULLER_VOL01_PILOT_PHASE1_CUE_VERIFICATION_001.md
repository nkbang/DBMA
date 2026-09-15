# CUE 독립 검증 — Fuller Vol.01 Pilot Phase 1 Report (C1)

- 검증자: CUE
- 일자: 2026-09-08
- 대상: `docs/NAE_FULLER_VOL01_PILOT_PHASE1_REPORT_C1_001.md`
- 재실측 환경: `/Users/David/DBMA` @ `dev/dbma-engine` `561de49`, venv `~/envs/dbma311`, read-only

---

## 판정: 🟡 RETURN — 1개 CONFIRMED 결함(검수 소요 추정 날조), 배치계획 미완

데이터 집계·툴 분석·격리는 정확. 그러나 **검수 예상 소요 "3시간 2분"은
근거 없는 수치**로, HQ의 검수 일정 결정을 오도한다. 정정 후 재제출 요망.

---

## 1. 검증 GREEN (CUE 재실측 일치)

| 항목 | C1 보고 | CUE 재실측 | 일치 |
|---|---|---|---|
| repo 상태 | HEAD `561de49`, untracked 리포트 3개만 | 동일 (`git status --porcelain`) | ✅ |
| tsu.json / requests/ | 무변경 | `git status --porcelain NAE/` = 빈 결과 | ✅ |
| doctrine 분포 | Soteriology 2,314 / Sanctification 279 / Justification 271 / Providence 204 / Election 165 / None 136 / Ecclesiology 98 / Scripture·Authority 73 / Eschatology 61 / Trinity 21 / Other 10 / Baptism 9 / Confession 2 = 3,643 | **완전 일치** (CUE 독립 집계) | ✅ |
| id 범위 | `TSU-0004123`–`TSU-0007765` | 동일 | ✅ |
| 배치 수 | ceil(3643/100) = 37 (36×100 + 43) | 산술 확인 | ✅ |
| 툴 갭 | `batch_manager.py:25 TSU_IDENTIFIERS=("Dagg…","Hiscox…")` 하드코딩 → Fuller `generate_batch()` 직접 실행 불가. `decision_gate.build_requests_from_records()` 는 identifier 무관 | `grep` 확인 — 정확 | ✅ |
| Phase 2 미침범 | disposition record·reviewer 배정 없음 | requests/·decisions/ 무변경 확인 | ✅ |
| Mutation | 0 | 신규 리포트 1개 외 무변경 | ✅ |

Soteriology 편중 63.5%(2,314/3,643) 도 정확.

---

## 2. 결함 — [CONFIRMED] 검수 소요 추정 날조

C1 보고: *"배치당 평균 검토 시간 5분 — 근거: Human Review Workflow v1
§검수절차 (100건 배치 기준) → 총 3시간 2분"*

### 반증
1. **인용 근거 부재**: `docs/NAE_HUMAN_REVIEW_WORKFLOW_v1.md` §3(검수 절차)에
   시간·속도 수치는 **없다**. `grep -E '분|시간|minute|hour|per item'` →
   해당 문서에 매칭 0. "§검수절차 5분" 은 존재하지 않는 출처.
2. **실측 선례와 모순**: Dagg+Hiscox = 776 verified TSU, 검수 기간
   `reviewer David, 2026-08-09..11` (corpus_admissions.jsonl).
   `batch_0001_decisions.json` mtime `Aug 10 00:04` → `batch_0036` `Aug 11 08:13`.
   ⇒ 776건 ≈ **3일(캘린더)**. Fuller 3,643건 = 776의 **약 4.7배**.
3. **프로젝트 자체 설계와 모순**: `NAE_TSU_4107_EXPANSION_HUMAN_REVIEW_DESIGN_001.md`
   §50 "시간이 필요하다 … 전량 동일 강도 리뷰가 아니라 단계적", §105
   "완료까지 매우 오랜 시간". 수천 건 전량 검수를 장기 작업으로 명시.

### 요구 정정
- "3시간 2분" 삭제.
- Dagg/Hiscox 실측 비율로 재산정하거나("776건 ≈ 3일 → 3,643건 ≈ 2주 캘린더,
  검토자 1인 기준, 페이스 미검증"), 또는 **"검토자 페이스 미확정 → 일정 TBD"**
  로 명시. 근거 없는 단일 숫자 금지.

---

## 3. 결함 — [MINOR] 배치 계획 미완 / 후속작업 임의 배정

- 배치표(§배치 계획)의 first/last tsu_id 칸이 전부 플레이스홀더
  ("(TSU-0004123 기준)" / "(100번째)"). **실제 배치 경계·패킷 미생성.**
  Phase 1 산출은 "배치 수·크기 규칙 + 총계" 수준이며, 이는 툴 갭 때문에
  불가피하나 리포트가 표로 계획이 있는 것처럼 제시함 → 사실대로 기술 요망.
- "CUE가 TSU_IDENTIFIERS 수정 또는 별도 스크립트 작성" 을 단정.
  `batch_manager.py::TSU_IDENTIFIERS` 는 공용 검수 인프라 → 변경은 스코프
  결정 사항. C1은 **갭을 보고**하고, 해결 방식은 CUE/HQ가 결정.

---

## 4. CUE 판단 — 툴 갭 해소 옵션 (HQ 결정 필요)

| 옵션 | 내용 | 평가 |
|---|---|---|
| O-1 | `batch_manager.py::TSU_IDENTIFIERS` 에 `"Fuller_Complete_Works_Vol01"` 추가 | 최소 변경. 단 `generate_batch()` 가 전 identifier 순회라 Dagg/Hiscox 재생성 부작용 확인 필요 |
| O-2 | Fuller 전용 배치 드라이버 스크립트 (`decision_gate.build_requests_from_records()` 직접 호출) | 격리 안전. 신규 파일 1개 |
| O-3 | `4107_EXPANSION` 설계의 **단계적(tiered) 검수** 채택 — 전량 동일강도 대신 doctrine·confidence 층화 | 3,643 전량 full review 회피. 별도 설계 승인 필요 |

CUE 권고: **O-2 + O-3 검토**. O-2로 배치는 격리 생성하되, 3,643 전량
full-strength 검수 여부는 `4107_EXPANSION` 단계적 전략을 HQ가 판단.

---

## 5. 살아있는 결론

- doctrine 분포·배치 수(37)·툴 갭 = 확정. 재수집 불요.
- baseline 3,319 / Vol.02–08 / Phase 2 자산 = 무접촉 확인.
- **Phase 1 미완료**: (a) 검수 소요 추정 정정, (b) 배치 생성 툴 갭 해소
  방식 HQ 결정 후 실제 배치 산출. 두 가지 완료 시 Phase 1 종결 → Phase 2(검수) 개시.
