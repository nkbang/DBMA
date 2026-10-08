# NAE EUAT-001 FU-004 — Fuller·1689 인덱싱 범위 결정 자료

- 일자: 2026-09-29 · 성격: 읽기 전용 조사 (인덱싱·임베딩·TSU 재생성·upsert·RAW/Registry 변경 없음, ADR 변경 없음)
- 기준: origin/main `d1c06d25` 워크트리, 코퍼스는 `~/DBMA/NAE/corpus/...`를 읽기 전용으로만 열람
- 형식: OBSERVED → EVIDENCE → IMPACT → RECOMMENDATION. 확인하지 못한 것은 "미확인".
- **결정은 사용자 몫이다.** 아래 권고는 근거와 함께 제시할 뿐이다.

---

## 0. 결론 요약

1. **Fuller는 지금 인덱싱 가능한 것이 Vol.08 한 권(verified 5,045건)뿐이다.** Vol.01–07(23,964건)은 전량 `generated`(미검수)라 게이트(`review_status == verified`)를 통과하는 건이 0이다.
2. **HOLD는 "결정 사항"이 아니라 이미 HQ 결정 B(2026-09-08, Vol.01 파일럿)로 조건부 해제된 상태**이며, 지금 막고 있는 것은 (i) ADR-030 Amendment A가 **여전히 PROPOSED**(F4/F5/F6는 Approved 후에만 착수), (ii) 사람 검수 미완, (iii) Amendment C가 F4/F6 착수 전 필수로 건 **Vol.08 추가 고지 미구현**이다.
3. **품질 경고**: F3 파일럿 표본 320건(전 권 40건씩)에서 **73건(22.8%)이 Q1 거부**됐다. Vol.08은 7/40(17.5%). 그런데 Vol.08을 일괄 승인한 근거(Amendment C, CUE 최종검증)의 Q1 오류율은 **2%**다. 두 수치가 충돌하며, 이 조사에서는 원인을 확정하지 못했다(§3.3).
4. **F5 스크립트는 지금 `--apply`하면 실패한다.** `EXPECTED_BASELINE_COUNT = 3319` 하드코딩인데 live `nae_tsu_v1`은 FU-002 이후 3,891이다(§4).
5. **SLBC1689(1689 신앙고백)**: canonical은 존재하고 1장 "성경에 관하여" 본문도 들어 있으나(OCR 잡음 큼), **raw 원본이 없고, 등록 기록보다 canonical이 6시간 먼저 생성**되어 provenance가 BROKEN이다. Admission Decision 기록이 없다. 즉 인덱싱 이전에 "출처 재확보(HQ decision)"가 선결이다.
6. 선택지별 요약(상세 §6):

| 선택지 | 인덱스 추가량 | 필요한 것 | EUAT-03 | EUAT-04 |
|---|---|---|---|---|
| (a) 전면 재개 | 최대 29,015 미만(검수 후 확정, 파일럿 승인율 기준 약 22k 추정) | Amendment A 승격, 사람 검수 23,964건, 고지 구현 | 해결 | 무관(1689 별도) |
| (b) 범위 축소 (Vol.08만) | 최대 5,045 (자동 신호 제외 시 3,713) | Amendment A 승격 + 고지 구현 + 품질 충돌 해소 | 부분 해결(Vol.08 주제 한정) | 무관 |
| (c) 보류 유지 | 0 | 없음 | 미해결 | 미해결 |
| 1689 | 별도 트랙 | raw 재확보 → 재추출 → Admission | — | 해결 |

---

## 1. Fuller 8권 실측 (OBSERVED / EVIDENCE)

출처: `NAE/corpus/tsu/Fuller_Complete_Works_Vol0N/{tsu.json, tsu_report.json, f3_triage_flags.json}`, 직접 집계(2026-09-29).
오염 기준 = `core/generation.py::_SCRIPT_CONTAMINATION_RE`(히라가나/가타카나·CJK·태국·그리스·키릴·히브리·아랍·데바나가리)를 claim에 적용. TOC 오염 = `scripts/nae_fuller_toc_contamination_scan.py`의 `scan_identifier()`를 **조회만** 호출(경로만 코퍼스로 지정, 파일 쓰기 없음).

| 권 | TSU | generated | verified | rejected | 스크립트 오염 claim | CJK 잔존(residual) | CJK 복구됨(repaired) | triage 플래그 | 파일럿 표본 Q1 거부 |
|---|---|---|---|---|---|---|---|---|---|
| Vol01 | 3,643 | 3,643 | 0 | 0 | 90 (2.47%) | 75 | 326 | 1,461 | 12/40 (+조건부 1) |
| Vol02 | 2,674 | 2,674 | 0 | 0 | 34 (1.27%) | 32 | 224 | 1,306 | 13/40 |
| Vol03 | 3,277 | 3,277 | 0 | 0 | 48 (1.46%) | 39 | 295 | 1,280 | 13/40 |
| Vol04 | 4,314 | 4,314 | 0 | 0 | 58 (1.34%) | 46 | 381 | 1,285 | 6/40 |
| Vol05 | 2,597 | 2,597 | 0 | 0 | 23 (0.89%) | 19 | 246 | 588 | 8/40 |
| Vol06 | 2,712 | 2,712 | 0 | 0 | 31 (1.14%) | 24 | 258 | 1,065 | 8/40 |
| Vol07 | 4,746 | 4,746 | 0 | 0 | 77 (1.62%) | 63 | 393 | 1,173 | 6/40 |
| Vol08 | 5,052 | 1 | **5,045** | 6 | 74 (1.46%) | 54 | 437 | 1,275 | 7/40 |
| **합계** | **29,015** | **23,964** | **5,045** | **6** | 435 (1.50%) | 352 | 2,560 | 9,433 | 73/320 (22.8%) |

관찰 메모:
- 모든 TSU의 `extraction_method = llm`, `model = my-theology-bot-v2:latest`, `page = 1`(page-level provenance 없음, Amendment A §4 수용 한계).
- 태스크 문서의 "전체 33,132"는 Dagg 3,377 + Hiscox 740 + Fuller 29,015의 합. Fuller만은 29,015. (태스크가 준 수치와 일치)
- triage 플래그 합계는 9,433건인데, F3 전량 큐(`NAE/review/human/requests/fuller_f3_full_queue_*_requests.json`)는 **9,207건**이다(Vol01 1,421 / 02 1,271 / 03 1,247 / 04 1,258 / 05 573 / 06 1,044 / 07 1,142 / 08 1,251). 차이 226건은 CJK 잔존 등 큐 제외 레코드로 보이나 **원인은 미확인**.
- 스크립트 오염 1.50%는 "복구 후 잔존"이 아니라 현재 tsu.json 상태 기준이다. CJK 복구(`cjk_status=repaired`) 2,560건은 이미 본문이 교체된 상태이므로, 복구 품질은 별도 검증 대상이다(미확인).
- **TOC 오염(front-matter 목차가 claim이 된 경우)**: 스캔이 잡은 TOC성 단락에서 나온 TSU는 Vol01 7건 이상(TSU-0004126~0004131, 0004150), Vol02 1건, Vol03 4건, Vol05 1건, Vol07 8건 이상(출력 상한 8건까지만 확인, 그 이상은 미확인), Vol04·Vol06 0건. Vol08은 4건(전부 `rejected`, 정상 처리). Vol01–07의 해당 건은 전부 `generated`라 아직 게이트 밖이다. Vol08의 알려진 6건 중 2건(TSU-0030343/0030344)은 스캔의 알려진 한계(인접 단락)로 이 스캔에는 안 잡힌다 — 이미 rejected.
- Vol08 verified 5,045건 중: 스크립트 오염 claim 74, CJK 잔존 54, triage 플래그 1,272. **세 신호 모두 없는 건 3,713건.** 이 신호들은 사람 판정이 아니라 자동 신호이며, 신호가 없다고 정확하다는 뜻이 아님(§3.3 파일럿 참고).

---

## 2. HOLD의 사유·결정 주체·재개 조건 (OBSERVED / EVIDENCE)

### 2.1 시간순 기록

| 일자 | 결정/문서 | 내용 |
|---|---|---|
| 2026-08-29 | `corpus_admissions.jsonl` lines 7–14 | Fuller Vol01–08 ADMITTED (`track: tsu`, `authority_class: historical_witness`, decided_by David/HQ). ADR-030 §12 N-9에서 "TSU/review/embedding 후속 승인 대기(HQ HOLD)" |
| 2026-09-08 | `NAE_FULLER_HOLD_RELEASE_HQ_DECISION_REQUEST_001.md` §7 | HQ 결정 **B: Vol.01만 파일럿**. 조건: Vol02–08 HOLD 유지, baseline 3,319 무접촉, `--apply`(임베딩/색인)는 dry-run 검토 + HQ go 이후에만, 검토자 David 단독, 단계적(tiered) 강도 |
| 2026-09-08 | ADR-030 Amendment A (Status **PROPOSED**) | 8권 처리(F0–F6) 인가 조건 서술. F4/F5/F6는 Amendment가 Approved된 후에만 착수(§8). F2·F3는 production 무접촉이라 선행 가능 |
| 2026-09-16 | ADR-030 Amendment C (Status **APPROVED**) | Vol.08만 개별 Q1/Q2/Q3 없이 일괄 승인(5,045 verified / 6 rejected). Vol.01–07은 Q1–Q3 전건 유지, 확장하려면 별도 Amendment 필요. 승인 조건 1: **F6/F4 착수 시 Vol.08 추가 고지 구현(미착수)** |
| 2026-09-26 | F3 파일럿 320건 재검토 (`NAE/review/human/decisions/fuller_f3_pilot_sample_001_decisions.json`) | 전 권 동일 rigor로 라인바이라인 재대조: APPROVED 246 / REJECTED 73 / CONDITIONAL 1 |

즉 **현재 HOLD를 유지시키는 것은 새 결정이 아니라 미충족 선행 조건들**이다.

### 2.2 재개 조건 표

| # | 조건 | 근거 | 현재 상태 | 비고 |
|---|---|---|---|---|
| 1 | Amendment A → Approved (구현·회귀·C1 독립검토·HQ 승인 4조건) | Amendment A §8 | **PROPOSED** | 지금 코드 게이트는 `review_status == verified` 하나뿐이라 문서 조건이 코드로 강제되지는 않는다. 그러나 스크립트 docstring이 "Approved 전 `--apply` 금지"를 명시 |
| 2 | Vol.01–07 사람 검수 (Q1–Q3 전건) | Amendment A §3 F3, Amendment C §3 | 0건 verified. 파일럿 표본 280건(Vol01–07)만 disposition, `tsu.json`에는 미반영(전량 `generated`) | 전량 큐 9,207건(플래그 기반 1차 큐)의 후속 정책은 문서상 **미확인** |
| 3 | Vol.08 추가 고지 구현 | Amendment C §4·§8 조건 1 | `NAE/` 코드에서 "일괄 승인" 관련 문구 없음(grep 0건) → **미구현** | F4/F6 착수 전 필수 |
| 4 | F4/F5 구현·회귀·C1 검토 | Amendment A §8 | 스크립트는 작성됨(`nae_fuller_f4_embed.py`, `nae_fuller_f5_upsert.py`), 미실행. **F5는 baseline 3,319 하드코딩 → 현재 3,891에서 거부됨** | 수정 필요(§4) |
| 5 | 회귀: `nae_corpus_reconcile.py` drift 0, 벤치 회귀 없음 | Amendment A §3 F5·F6 | 미실행 | |
| 6 | F6: `modules.nae_pd` 활성 + disclosure 노출 확인 | Amendment A §3 F6 | 미실행 | |
| 7 | 사람 승인 기록 | `NAE/governance/corpus_admissions.jsonl` | 8권 ADMIT 기록 존재(14줄). 파일에 색인 승인 기록 없음(스키마상 admission=수용 결정, 인덱싱 go는 HQ 지시로 별도) | 추가 admission은 불필요 |

### 2.3 F3 검수 진행률

| 항목 | 값 |
|---|---|
| Vol.01–07 disposition이 tsu.json에 반영된 건 | **0 / 23,964 (0%)** |
| 파일럿 표본 disposition | 320건 (권당 40, doctrine 비례 층화, 시드 20260925, CJK 잔존 제외) |
| 재표본 `fuller_f3_vol0408_resample_001` | 40건 중 7건 후 2026-09-26 사용자 지시로 종료(위 파일럿 재검토가 목적을 대체) |
| C1 리뷰 상태 | Amendment A: C1 리뷰 요청서(`NAE_FULLER_AMENDMENT_A_C1_REVIEW_REQUEST_001.md`)·결과(`..._RESULT_001.md`)가 존재하나 **결과의 최종 판정과 승격 여부는 이번 조사에서 미확인**. Amendment C: C1 결과 2건은 원문 인용 오류로 CUE가 재검증(2026-09-16) |

---

## 3. 품질 근거 (EVIDENCE) — 결정에 직접 영향

### 3.1 파일럿 표본 결과 (320건)

| 권 | 승인 | 거부 | 조건부 |
|---|---|---|---|
| Vol01 | 27 | 12 | 1 |
| Vol02 | 27 | 13 | 0 |
| Vol03 | 27 | 13 | 0 |
| Vol04 | 34 | 6 | 0 |
| Vol05 | 32 | 8 | 0 |
| Vol06 | 32 | 8 | 0 |
| Vol07 | 34 | 6 | 0 |
| Vol08 | 33 | 7 | 0 |
| 합 | 246 | 73 | 1 |

- 문항별: Q1 거부 73 / Q2 거부 23 / Q3 거부 9. **거부의 지배 요인은 Q1(추출 충실도)**이다. Amendment A 절차서가 "Q1 위험: 높음"이라 한 것과 일치.
- 표본 크기(권당 40)에 따른 불확실성: Vol.08 7/40 = 17.5%, Wilson 95% 구간 대략 8.7–31.9%. 권 단위 비교는 표본이 작아 신뢰하기 어렵다.

### 3.2 triage 플래그의 판별력이 낮다

| 표본 구분 | 승인 | 거부 | 거부율 |
|---|---|---|---|
| 플래그 있음 (112) | 78 | 33 | 29% |
| 플래그 없음 (208) | 168 | 40 | 19% |

플래그가 없어도 거부율이 19%다. **"플래그 없는 건은 검수 생략" 같은 축소 정책은 이 표본으로는 뒷받침되지 않는다.** (단, 표본은 CJK 잔존 레코드를 제외했고, 플래그별 세부 거부율은 quote_attribution 31%, truncated_fragment 43%, rhetorical_question 29%, very_short 33%, conditional_hypothetical 20%.)

### 3.3 충돌: Vol.08 일괄 승인 근거 vs. 파일럿

| 출처 | Vol.08 Q1 오류 관찰 |
|---|---|
| Amendment C / CUE 최종검증 (2026-09-16) | **2%** |
| F3 파일럿 재검토 (2026-09-26) | **7/40 = 17.5%** (Q1 거부) |

- 두 측정의 표본·기준·검토자가 다르다. 파일럿이 더 엄격한 rigor(전 권 동일, 라인바이라인)를 적용했다고 기록에 적혀 있고, CUE 최종검증은 원문 대조로 산출됐다. **어느 쪽이 맞는지는 이 조사에서 확정하지 못했다(미확인).**
- ADR-030 Amendment C(Approved)와 어긋날 수 있는 데이터이므로, Approved ADR을 이 조사에서 변경하지 않고 **기록만** 한다. 필요하면 Amendment C R1(F4 임베딩 전 자동 스크리닝 표본 검증 최소 1회 권고)을 이 충돌 해소에 쓸 수 있다.

---

## 4. 인덱싱 재개의 기술적 전제 (EVIDENCE)

| 항목 | 확인 결과 |
|---|---|
| 인덱싱 게이트 코드 | `review_status == "verified"` 하나뿐(`NAE/pipeline/tsu/review_gate.py`, `NAE/pipeline/index/indexer.py`). 날짜·배치·Amendment 승인 여부는 코드로 강제되지 않음 |
| 현재 Qdrant (읽기 전용 count 재확인, 2026-09-29) | `nae_tsu_v1` **3,891**, `nae_ref_v1` 34,948, `nae_ref_commentary_v1` 10,517. 컬렉션은 이 3개뿐 |
| `scripts/nae_fuller_f4_embed.py` | dry-run 기본, `--apply` 없으면 Ollama 호출 없음. docstring이 "verified 0건이라 no-op"이라고 적혀 있으나 **Vol.08 5,045건 때문에 더 이상 사실이 아니다**(문서 정정 필요) |
| `scripts/nae_fuller_f5_upsert.py` | `EXPECTED_BASELINE_COUNT = 3319` 하드코딩, `--apply` 시 실측이 다르면 `BaselineDriftError`. **live 3,891이므로 거부됨.** FU-002 결과와 ADR-030 baseline 서술이 어긋난 결과이며, 가드 값 갱신(=코드 변경)이 필요. 이 조사에서는 수정하지 않았다 |
| additive-only 규정 | Amendment A §7: 3,319 baseline 재처리·재승인·삭제 금지, F5는 additive. 현재 3,891 중 572건(Dagg 321 + Hiscox 251)은 FU-002-A로 추가된 것이라 "baseline"의 정의 갱신이 필요(ADR-030 기준선 서술 갱신은 이 조사의 범위 밖, 결정 대기 항목) |
| Vol.08 추가 고지 | 미구현(§2.2 #3) |
| 승인 기록 | `NAE/governance/corpus_admissions.jsonl` 존재(14줄, Fuller 8건 포함). Fuller 색인 승인 기록은 없음 |
| 디스크·캐시 | 임베딩 캐시 `NAE/corpus/embeddings` 1.2GB, 디스크 여유 2.0TiB. Fuller 추가량은 사실상 무시할 수준(아래 §5) |

---

## 5. 규모 추정 (EVIDENCE + 추정 표기)

| 시나리오 | 포인트 추가 | 비고 |
|---|---|---|
| Vol.08 verified 전량 | **5,045** | 확정 수치 |
| Vol.08에서 자동 신호(스크립트 오염·CJK 잔존·triage 플래그) 제외 | 3,713 | 신호 제외 정책은 §3.2에 따라 품질 보증이 아님 |
| Vol.01–08 전량 검수 후 | 최대 29,015 − 거부분 | 파일럿 승인율 76.9% 적용 시 약 22,300 (**추정**, 표본 오차 큼) |

- 임베딩 소요: FU-002-A(Dagg 321건·Hiscox 251건 색인)의 **소요 시간은 문서에 기록되어 있지 않다**(태스크 메모의 "수 초~수십 초"는 결과 문서에서 확인 못 함 — 미확인). 이번 조사에서는 Ollama 호출이 금지라 직접 측정하지 않았다. 규모비만 말하면 Vol.08은 FU-002-A 색인량(572)의 약 8.8배, 전량은 약 50배이며, 시간은 미측정.
- 벡터 저장: bge-m3 1024차원 float32 기준 벡터만 약 4KB/포인트 → Vol.08 약 20MB, 전량 약 120MB(payload 제외 추정).

---

## 6. 1689 신앙고백 (SLBC1689) (OBSERVED / EVIDENCE)

### 6.1 실제 상태

| 항목 | 값 |
|---|---|
| 경로 | `NAE/corpus/canonical/SLBC1689/` — `canonical.json` 514,471B, `canonical.txt` 124,113B, `normalize_report.json` |
| normalize_report | `status: ok`, 2026-08-01, 157쪽, 문단 1,202, 헤딩 28, verse 195, 성구 참조 2건, 원천 `hocr` |
| 본문 온전성 | 1장 "Of the Holy Scriptures"(`CHAP. I.`)가 canonical.txt에 존재. "Holy Scripture is the only sufficient, certain, and infallible rule of all saving Knowledge, Faith and Obedience"가 판독 가능. 목차에 1–32장 + "Appendix concerning Baptism"이 확인됨 |
| 품질 | **낮음**: 문단 1,202개 중 짧거나 알파벳 비율 낮은 문단 372개(31%). 헤딩 28개 중 정상 "CHAP. N" 판독은 약 20개, 나머지는 `EADER .`, `0. "FF`, `MSF.`, `CUM` 등 잡음. 장 번호가 `CHAP,`, `CH AP, III.`, `CHAP. XVIIE`처럼 깨진 것 다수 → **32장 중 일부 장 경계 유실**. 각 장의 옆 여백 성구 주(본문에 끼어듦)와 본문이 섞여 문장이 끊김. 초기 근대 영어 long-s(`ſ`) 2,351자 잔존 |
| raw | `NAE/corpus/raw/archive_org/`에 SLBC1689 없음(`AF1815`, `PBC1742`, `TH1612`는 빈 디렉터리) |
| Admission Decision | `corpus_admissions.jsonl` 14줄에 **SLBC1689 없음** |
| 인덱스 | 세 컬렉션 어디에도 없음 |

### 6.2 "N-8 BROKEN"의 의미 (원문 근거)

- ADR-030 §12: `N-8 | SLBC1689 / PBC1742 provenance 재구성 | BROKEN, HQ decision 대기`. (CUE-ADR-030-POST-FORENSIC-REASSESSMENT.md에서는 같은 항목이 N-7로 표기 — 번호 표기 불일치, 내용 동일.)
- 정의 (`CUE-NAE-BAPTIST-CORPUS-001-FINAL-GOVERNANCE-RECONCILIATION.md` §7–8): BROKEN = "timestamp/checksum/identity/source lineage 등에서 직접적 모순이 존재". SLBC1689의 모순은 **(1) manifest `BAP-CONF-1689`는 ACQUIRED인데 raw가 없음, (2) canonical 생성(2026-08-01 20:43:16 UTC)이 manifest 등록 커밋 `a7b894c`(2026-08-01 21:33 CDT)보다 약 6시간 앞섬** — 이 canonical이 해당 acquisition의 산출물일 수 없음을 시간순으로 직접 반증.
- 즉 **"본문이 깨졌다"가 아니라 "출처 계보를 증명할 수 없다"**는 뜻이다. 내용 자체(제목·연도·저자 정합)는 "PROBABLY MATCH"로 판정됐고 Production은 INELIGIBLE.
- 이 상태는 3-way 감사(CUE-NAE-BAPTIST-CORPUS-3WAY-FORENSIC-RECONCILIATION.md)에서도 "REAL"로 재확인됐고, "HQ decision 대기" 상태다. 이번 조사에서 그 decision의 기록은 **찾지 못했다(미확인)**.

### 6.3 같은 계열 자료 상태표

| 자료 | canonical | raw | Admission | 상태 | 비고 |
|---|---|---|---|---|---|
| SLBC1689 (1689) | ok, 157쪽 | 없음 | 없음 | provenance BROKEN, Production INELIGIBLE | 본문 판독 가능, 잡음 31% |
| PBC1742 (Philadelphia 1742) | **failed** (`no_extractable_source`) | 빈 디렉터리 | 없음 | BROKEN + FAILED | archive.org 오류 페이지를 콘텐츠로 오인한 정황(감사 문서). 복구는 처음부터 재확보 필요 |
| PBC1765 (1765) | ok, 114쪽, 문단 1,046, 잡음 문단 40% | `quarantine/PBC1765/original`(PDF+djvu.txt) | 없음 | **의도적 HQ HOLD**(`HQ-ADVISORY-PBC1765-CANONICAL-DECISION.md`, 2026-08-01) | provenance는 COMPLETE. 앞 60문단 중 62%가 표지 OCR 잡음. 참고: `BAPTIST_THEOLOGY_FOUNDATIONAL_SOURCES_v1.md`는 1742 필라델피아 고백을 "1689 + 2개 조항 추가"로 설명(PBC1765의 정확한 판본 성격은 미확인) |

### 6.4 트랙 귀속 (ADR-030 §5, Amendment B)

- 신앙고백은 장/조항 단위 구조와 저자·연도 귀속이 명확한 원문 자체가 최종 산출물이다. `CUE-ADR-030-POST-FORENSIC-REASSESSMENT.md` line 278은 SLBC1689/PBC1742를 confession 장르, `primary_doctrinal`(자격상)로 분류하되 provenance BROKEN이라 INELIGIBLE로 적는다. ADR-030 `EMBEDDING ELIGIBLE` 표(line 372)는 Reference 트랙 조건을 "Admission Decision + `reference_quality_confirmed == true` (예: PBC1765는 HQ HOLD)"로 두어 PBC1765를 Reference 후보 사례로 든다. (ADR-030 §5·Amendment B의 트랙 정의 본문은 이번에 끝까지 대조하지 못했다 — 미확인.) SLBC1689·PBC1742에 대한 **트랙 결정은 admission 기록이 없어 확정되지 않았다**.
- 근거 정리(설계 제안 아님): (a) TSU는 문장 단위 LLM 재진술로 Q1 위험이 높다는 것이 Fuller 파일럿에서 실측됐다(거부 22.8%). (b) 1689는 조항이 번호·장 구조로 이미 분절돼 있고 표준 인용 단위가 "장·항"이라 원문 그대로 인용되는 것이 자연스럽다. (c) 반면 SLBC1689 canonical은 장 경계·여백 성구 주가 깨져 있어 조항 단위 분절 자체가 지금 상태에서는 신뢰하기 어렵다. 어느 트랙으로 갈지는 결정 사항이다.

### 6.5 복구 가능성과 필요한 작업 (나열)

1. **출처 재확보 (선결, 결정 필요)**: archive.org 등에서 1689 원본(PDF/hOCR)을 새로 받아 raw에 두고 checksum·acquisition 기록을 남긴다. 현 canonical을 그대로 인정할지는 HQ decision(N-8). RAW 신규 추가이므로 사전 승인 대상.
2. 추출/정제: 재확보 원문으로 canonical 재생성. 현 canonical은 hOCR 기반, long-s·여백 성구 주 분리 필요. 장 단위 헤딩 복원(32장 + 부록) 필요.
3. 청킹: 장/항 단위 reference 청킹 또는 TSU. ADR-030 §5·Amendment B 적용 여부를 결정.
4. Admission Decision 기록 추가 (`track`, `authority_class`, `reference_quality_confirmed`).
5. 인덱싱: TSU면 사람 검수 후 `nae_tsu_v1`, Reference면 `nae_ref_*` 계열(`nae_ref_v1`은 Smith 사전 전용이라 신앙고백을 섞는 것은 부적합하다는 판단은 별도 결정 필요).

소요·비용은 미측정. 신앙고백은 약 12만 자(약 1,200 문단) 규모로 Fuller 단일 권 대비 작다.

---

## 7. 선택지 비교 (IMPACT)

### (a) 인덱싱 재개 — Fuller 8권 전면

| 항목 | 내용 |
|---|---|
| 수치 근거 | 대상 29,015, 미검수 23,964. 파일럿 거부율 22.8% |
| 필요한 승인 | Amendment A 승격(구현·회귀·C1·HQ), Amendment C 조건 1(Vol.08 고지) 이행. Vol.01–07 검수는 **별도 Amendment 없이는 Vol.08식 일괄 승인 불가**(Amendment C §8 조건 3) |
| 사람 검수량 | 최소 23,964건(전건) 또는 큐 9,207건 중심의 2단계 정책(후속 정책 미확인). §3.2상 무플래그 건 생략은 근거 부족 |
| 위험 | 검수 병목(1인 검수자, 과거 776건 human review도 미착수 사례), Q1 오류가 인덱스에 유입될 경우 신학적 오인용, F5 가드 미수정 시 즉시 실패 |
| EUAT 영향 | EUAT-03(Fuller) 직접 해소. EUAT-04(1689)는 무관 |

### (b) 범위 축소 — 권/기준 지정

| 세부안 | 규모 | 필요한 것 | 위험 |
|---|---|---|---|
| (b-1) Vol.08만 (verified 5,045) | +5,045 | Amendment A 승격, Vol.08 고지, F5 가드 갱신, §3.3 충돌 해소(자동 스크리닝 표본 등) | Vol.08은 파일럿 거부율 17.5%이나 일괄 승인 상태 → 미검수 오류 잔존 가능. Vol.08의 admission 장르는 theology·sermon·mission이며, EUAT-03 질문에 Vol.08 내용이 직접 답이 되는지는 **미확인**(Vol.01 표제는 *The Gospel Worthy of All Acceptation*) |
| (b-2) Vol.08 자동 신호 제외 (3,713) | +3,713 | 위와 동일 + 제외 정책 정당화 | §3.2상 신호 제외가 품질 보증 아님 |
| (b-3) Vol.01만 (F3 파일럿 완주) | Vol.01 disposition 0건 반영(3,643 대상) | Vol.01 사람 검수 3,643건 + 위 승인 | 1인 검수량이 큼. Vol.01은 파일럿 결정 B의 원 대상 |

### (c) 보류 유지

| 항목 | 내용 |
|---|---|
| 근거 | 파일럿 22.8% 거부, 승인 조건 다수 미충족, "배포 버전 완성 최우선" 방침 대비 검수 인력 부담 |
| 필요한 승인 | 없음 |
| 위험 | EUAT-03이 계속 검색 불가. 배포 전 "Fuller는 미포함" 고지 필요 여부는 별도 판단 |
| EUAT 영향 | EUAT-03·04 미해결 유지 |

---

## 8. RECOMMENDATION (근거 포함, 결정은 사용자)

1. **1689는 Fuller와 분리된 짧은 트랙으로 먼저 다룰 것을 권한다.** 규모가 작고(약 1,200 문단), Fuller처럼 사람 검수 수만 건이 필요하지 않다. 단 선결은 출처 재확보와 N-8 HQ decision이다. 현 canonical을 그대로 인덱싱하는 것은 계보 증명이 안 되므로 권하지 않는다.
2. **Fuller는 (b-1) Vol.08부터**가 선택지 중 인덱싱까지의 거리가 가장 짧다(verified 5,045건이 이미 있음). 다만 착수 전에 (i) Amendment A 승격 절차, (ii) Vol.08 추가 고지 구현, (iii) F5 baseline 가드 갱신, (iv) §3.3의 2% vs 17.5% 충돌 해소(예: Amendment C R1이 권고한 자동 스크리닝 표본 검증을 파일럿과 같은 rigor로 수행)를 먼저 처리할 것을 권한다. (iv)가 해소되지 않으면 (c)로 남기는 편이 안전하다.
3. **(a) 전면 재개는 지금 권하지 않는다.** 검수량과 1인 검수 병목, 파일럿 22.8% 거부율, 플래그 판별력 한계(§3.2)가 근거다.
4. 위 권고는 "배포 버전 완성 최우선" 방침과의 우선순위 비교를 하지 않았다. 배포 범위에 Fuller·1689 질문이 포함되는지는 사용자 판단이다.

---

## 9. 이번 조사에서 확인하지 못한 것 (미확인)

- Amendment A의 C1 리뷰 결과 최종 판정과 승격 여부.
- Vol.08 Q1 오류율 2%(Amendment C)와 17.5%(파일럿) 충돌의 원인(표본·기준·검토자 차이).
- 플래그 9,433건과 전량 큐 9,207건의 226건 차이 원인.
- F3 2단계 게이트에서 "무플래그 건"의 처리 정책.
- CJK 복구(repaired) 2,560건의 복구 품질.
- SLBC1689에 대해 HQ가 N-8 decision을 내렸는지 여부, 그리고 SLBC1689·PBC1742의 트랙 귀속.
- 임베딩 소요 시간 실측(Ollama 호출 금지로 미측정), FU-002-A 소요 시간 기록.
- Vol.08 주제가 EUAT-03 질문에 실제로 답이 되는지(검색 실험은 인덱싱 없이는 불가).
- TOC 오염 스캔 출력에서 Vol01·Vol07의 8건 초과분.

## 10. 실행 기록 (금지 사항 준수)

- Qdrant: `count`·`collections` 조회만.
- 코퍼스(`NAE/corpus/*`, `NAE/review/*`, `NAE/governance/*`): 파일 열기·집계만, 쓰기 0.
- 스크립트: 수정 모드(`--apply`) 미실행. `nae_fuller_toc_contamination_scan.py`는 함수를 import해 조회만 호출.
- 메인 체크아웃(`feat/peb-v0.1`) 무접촉. 이 문서 1개만 신규 작성.
