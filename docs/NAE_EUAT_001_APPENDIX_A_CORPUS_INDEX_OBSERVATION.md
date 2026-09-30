# EUAT-001 부록 A — Corpus / Index Observation

기준일 2026-09-29. 조사는 모두 읽기 전용이었고, Qdrant·`tsu.json`·인제스트 상태 파일은 수정하지 않았다.

- 대상 앱: `~/DBMA` 메인 체크아웃, 브랜치 `feat/peb-v0.1` @ `c2cdf147` (미커밋 수정 17개 포함 상태)
- 상태: 관찰 기록. 수정은 별도 Task Order로 분리한다.

## A-1. 디스크 대비 인덱스

| 소스 | 디스크 `tsu.json` | 게이트 통과(verified) | 인덱싱됨 | 미인덱싱 (verified) |
|---|---|---|---|---|
| Dagg | 3,377 | 3,279 | 2,958 | **321** |
| Hiscox | 740 | 612 | 361 | **251** |
| Fuller Vol01–08 | 29,015 | 미확인 | **0** | 미확인 |
| **합계** | **33,132** | | **3,319** | |

- 게이트 제외분은 정상이다. Dagg는 rejected 52 + generated 46, Hiscox는 generated 128이다.
- 인덱스 3,319건은 전부 `verified`이다. 인덱스에 든 것은 전부 리뷰 게이트를 통과한 항목이다.
- Fuller의 게이트 통과 수와 미인덱싱 사유는 조사하지 않았다. 기존 메모리에는 처리 보류(HOLD)로 기록돼 있다.
- 다른 컬렉션은 `nae_ref_v1` 34,948건(Smith 사전 4권), `nae_ref_commentary_v1` 10,517건(Gill, Broadus, Spurgeon, Carroll)이다. 어디에도 1689 신앙고백(`SLBC1689`)은 없다. 디스크의 `NAE/corpus/canonical/SLBC1689`에만 있다.

## A-2. 누락의 원인: 인제스트가 8/11 이후 재실행되지 않음

**OBSERVED**: 미인덱싱 verified TSU 572건(Dagg 321, Hiscox 251)과 내용이 바뀐 17건이 검색에 반영되지 않았다.

**EVIDENCE**
- 승인일로 두 집단이 완전히 갈린다. 인덱싱된 건은 08-08~08-11 승인이고, 누락된 건은 09-15(Dagg 297, Hiscox 167)와 09-16(Dagg 24, Hiscox 84) 승인이다. 겹침이 없다.
- 코드의 게이트는 `review_status == "verified"` 하나뿐이고 날짜·배치 필터는 없다(`indexer.py`, `review_gate.py`, `nae_incremental_ingest.py`). `tsu_verified.json`은 존재하지 않아 `tsu.json`이 그대로 쓰인다.
- 증분 인제스트 dry-run 결과가 미인덱싱 수와 정확히 일치한다.

| | NEW | CHANGED | UNCHANGED |
|---|---|---|---|
| Dagg | 321 | 14 | 2,944 |
| Hiscox | 251 | 3 | 358 |

- `incremental_state.json`은 3,319건 전부 `INDEXED`, 마지막 갱신 2026-08-11T21:15Z이다. 매니페스트 `gen0002`도 같은 날이다. 2026-09-10 이후 인제스트 관련 커밋은 없다.

**IMPACT**: 9월 인간 리뷰(`batch_0024`, `batch_0027` 등) 결과가 사용자 검색에 반영되지 않았다. Hiscox의 verified "Church Discipline" 53건 중 45건(85%)이 빠져 있어 EUAT-01(권징 질문)의 근거 부족과 관련이 있다. 순위 저하의 유일한 요인인지는 검증하지 않았다.

**RECOMMENDATION**: 별도 Task Order로 `scripts/nae_incremental_ingest.py --apply`를 Dagg → Hiscox 순으로 실행한다. 신규·변경분만 upsert한다. Embedding Engine과 Qdrant 쓰기이므로 사전 승인이 필요하다. `docs/NAE_FULLER_PREFLIGHT_CUE_VERIFICATION_001.md`가 보호 파일(`embed/client.py`, `tsu/builder.py`)의 미커밋 수정 상태에서 `--apply`를 실행하는 것을 ADR-030 §14 위반으로 경고하므로, 실행 전에 메인 체크아웃의 미커밋 파일 17개 중 해당 파일이 있는지 확인해야 한다.

## A-3. CHANGED 17건: 오염된 claim의 사후 교정

**OBSERVED**: 색인된 TSU 17건(Dagg 14, Hiscox 3)의 claim에 타 문자가 섞인 옛 문장이 남아 있고, `tsu.json`에는 교정본이 있다.

**EVIDENCE**
- 바뀐 필드는 `claim`뿐이다. `page`, `book`, `scriptures` 변경은 0건이다.
- 오염 유형은 한자, 베트남어, 데바나가리, 태국어, 아랍 문자이다. 예: "지식来源" → "지식 근원", "vấn을" → "문제를", "다کن(deacon)" → "집사(deacon)".
- Qdrant payload 전수 스캔에서 타 문자 플래그가 Dagg 19건, Hiscox 3건이었고, 이는 17건과 규모가 일치한다(한 레코드가 여러 플래그를 가질 수 있어 레코드 수는 정확히 계산하지 않았다).

**관찰**
- TSU-0002210은 "Ευχαριστία(Eucharist)"가 "Eucharist"로 바뀌었다. 당초 정상 헬라어 삭제로 의심했으나(FU-006 원문 대조로 **정정**), 원문 `source_text`에는 헬라어 문자가 없고 OCR 깨짐 표기("evzaptorew")만 있다. 즉 삭제된 "Ευχαριστία"는 모델이 claim 생성 중 도입한 것이며 원문 헬라어가 아니다. 헬라어 손실 우려는 해소됐다.
- 17건의 `review_date`는 08-09~08-11로 교정 이전이다. 승인된 claim이 재승인 없이 수정됐다.
- 교정 주체·시점(FU-006에서 확인): `cjk_reextract` v1.0.0 도구(`model=my-theology-bot-v2`)가 2026-09-15 04:38~04:43Z(Dagg 후보 17건/잔존 16/실패 1, Hiscox 후보 3건/잔존 3)에 실행됐으나 자동 수리는 0건이었다. 이어 같은 날 04:49Z의 수작업 교정 패스(Dagg 51건, Hiscox 18건)가 원문 `source_text`와 대조해 손으로 교정했다. 수작업 실행자는 보고서에 기록되어 있지 않다.

**IMPACT**: 노출되면 한자·베트남어가 섞인 문장이 보이고 임베딩 품질이 소폭 저하된다. 규모는 3,319건 중 17건(0.5%)이다.

**RECOMMENDATION**: A-2의 `--apply`가 CHANGED 17건을 함께 교체한다. 승인 후 claim 수정 17건의 재승인 필요 여부는 정책 판단으로 남긴다(TSU-0002210 헬라어 우려는 해소, 위 정정 참조).

## A-4. EUAT 결과에 미친 영향

| 시험 | 인덱스 상태의 영향 |
|---|---|
| EUAT-01 (Dagg) | 근거는 인덱스에 있으나 채팅 경로가 TSU에 닿지 않음. 권징 근거 일부는 누락(Hiscox 45건) |
| EUAT-02 (Hiscox) | 인덱스의 Hiscox 361건 중에서만 검색됨. 251건 누락 |
| EUAT-03 (Fuller) | **직접 원인.** Fuller 인덱스 0건 |
| EUAT-04 (1689) | **직접 원인.** 1689가 어느 컬렉션에도 없음 |
| EUAT-05 | 인덱스 누락과 무관. 채팅 경로 구조와 인용 오류가 원인 |

## A-5. 미확인 항목

| 항목 | 상태 |
|---|---|
| 콜드 상태 검색 실패 원인 | **부분 해소 (FU-005).** 공개 패널 "결과 없음"은 확정(3초 하드 타임아웃 초과가 예외로 삼켜짐, Ollama 로그 3.03초 499 ×6). 채팅 "검색 중 문제"는 임베딩 타임아웃이 아님만 확인, 원인 미확정. 상세: [FU-005 결과](NAE_EUAT_001_FU005_COLD_SEARCH_FAILURE_RESULT.md) |
| Fuller 29,015건 미인덱싱 사유 | 미조사(메모리상 처리 보류) |
| "연구" 탭 AI 답변 | **해소 (FU-006).** 코드상 채팅과 같은 `QueryProcessor` 경로 + 같은 공개 패널. EUAT-01 UI 시험 결과도 채팅과 동일(유보 답변, 출처 Broadus·Spurgeon·Keach, Dagg 없음). EUAT-02~05는 연구 탭에서 미시험 |
| 교정 실행 시점·주체 | **해소 (FU-006).** 2026-09-15 04:38~04:49Z, `cjk_reextract` v1.0.0 도구(자동 수리 0건) + 수작업 교정 패스(Dagg 51, Hiscox 18). 수작업 실행자는 기록 없음. 9/26 v1.1.0 커밋은 Fuller용이며 무관 |
| 권징 근거가 상위 10건에 들지 않은 이유 | **해소 (FU-006).** 순수 벡터 순위 문제: p.95는 28위(0.515, 10위 컷 0.553), p.103은 170위. 질의의 "교회의 질서" 개념이 지배해 상위 10건이 Ecclesiology 9건. "Church Discipline" 분류 최고 순위 43위 |
| 생성 지연(90초~8분) 원인 | **해소 (FU-005).** 두 대형 모델 상호 evict 경합. 상세: [FU-005 결과](NAE_EUAT_001_FU005_COLD_SEARCH_FAILURE_RESULT.md) |
| 채팅이 TSU에 닿지 않는 문제의 설계 의도 | 코드상 구조는 확인했으나 의도는 미확인 |

## A-6. 교차검증 이력

- C1이 12개 항목(V1~V12)을 검증했고, CUE가 재실행해 5건은 유효, 4건(V3, V4, V10, V11)은 C1 오류로 판정했다. V4는 잘못된 경로 조회였고, V3는 잘못된 인스턴스를 본 것이다.
- 이 부록의 수치는 모두 CUE가 직접 실측한 값이며 C1 보고에는 의존하지 않는다.
- `output/euat_001_result.md`는 C1 세션이 생성한 출처 미상 파일(gitignored)로, 근거로 사용하지 않았다.
