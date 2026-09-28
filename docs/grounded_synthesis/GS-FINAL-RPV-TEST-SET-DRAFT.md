# GS-FINAL-RPV Test Set — DRAFT (HQ 최종 승인 전, preflight 대기)

- 상태: **조건부 승인** (HQ, 2026-09-28) — RPV-01~07 PASS 기준을 "grounded 고정"에서
  "corpus snapshot 기준 기대 결과와 일치"로 재정의하기 위해 preflight 결과 대기 중
- 이 문서는 C1 preflight Work Order가 참조할 **질문 텍스트 정본**이다.
  WO 자체에는 질문 텍스트가 누락되어 있었으므로 이 파일로 보강한다.
- 실행 금지: 이 문서는 정의 단계 산출물이며, 실제 Real Pastoral Query Execution은
  preflight 결과 + HQ 최종 승인 후에만 시작한다.

## Preflight 1차 실행 결과 — 무효 (c2cdf147, 2026-09-28)

C1이 `/Users/David/DBMA`(로컬 HEAD `c2cdf147`)에서 실행한 1차 preflight는
**무효 처리**한다. 사유:
- `c2cdf147`은 main 병합 커밋 `c8f7e41a`의 조상이 아니며, `core/retrieval.py`의
  한국어→영어 질의 번역 기능(PR #88, `core/query_translation.py`)이 빠져 있음
- G0 비-GS 변경이 작업 트리에 섞여 있어 실행 환경이 배포 대상과 다름
- CUE 독립 재검증 결과: RPV-01a/01b/02/03a/03b/04/05a/07(8개 중 7개) top-10이
  전부 단일 문서(`Broadus_Lectures_on_History_of_Preaching.txt`, 코퍼스 내
  크기 순위 80/83위)에서만 나왔고, 표본 열람 결과 질의와 무관한 내용 확인.
  `bm25_score`가 질의 내에서 상수(0.5 또는 1.0)로 수렴하는 현상도 확인 —
  일부는 코드상 의도된 동작(bible route posting-list, `bm25_score=1.0`
  placeholder, `core/hybrid_candidate_pipeline.py:163-167`), 나머지
  free-text route의 0.5 수렴은 **원인 미확정 — 관찰값으로만 기록, 결함 판정
  내리지 않음**(HQ 지시, 2026-09-28)
- RPV-05a("Multi-source") 등 다출처 요건이 있는 항목은 이 결과 기준으로
  **HOLD**(PASS 기준 미충족)

## Preflight 2차 실행 WO (c8f7e41a, 격리된 새 워크트리)

**생성 명령**(HQ 확정, 2026-09-28):
```bash
git -C /Users/David/DBMA worktree add --detach /Users/David/DBMA-rpv-c8f7e41a c8f7e41a
```

**환경 격리 원칙(원본 코퍼스·인덱스 보호)** — 심볼릭 링크 금지:
- TSU dataset·manifest: `/Users/David/DBMA/output/bench/`에서 **읽기 전용
  복사본**을 새 워크트리 내부로 복사(`cp`, 링크 금지)
- Tantivy index: 새 워크트리 내부에 **별도 복사본**을 만들어 사용
  (원본 인덱스에 candidate index 재생성/쓰기 발생 위험 차단)
- cache·telemetry: 새 워크트리 내부의 임시 경로로 분리(원본 경로 사용 금지)
- 이유: preflight 실행이 candidate index 재생성, telemetry, cache 쓰기를
  유발할 수 있어 원본 코퍼스·인덱스를 오염시킬 위험이 있음

**보고 형식 변경** — "본문 전체" 금지, 감사 가능한 최소 정보만:
- top-3 각각에 대해: evidence ID(tsu_id), source_file, final_score,
  관련 구절의 **짧은 검토용 발췌**(1~2문장), content hash(sha256 등)
- 코퍼스 본문을 감사 보고서에 대량 복제하지 않는다

**점수 관찰 기록** — 결함 판정 아님, 관찰만:
- `bm25_score`/`vector_score`/`theological_score`가 질의 내 10건에서
  상수로 수렴하는지 여부를 항목별로 기록(원인 규명은 이번 범위 아님)

## Preflight 2차 결과 (c8f7e41a 격리 워크트리, 2026-09-28) — CUE 재검증 완료

**실행 범위**: raw JSON에 포함된 항목은 10개뿐이다 — `RPV-01a, 01b, 02, 03a,
03b, 04, 05a, 05b, 07, 08a`. 나머지 3개는 이번 100-슬롯 집계에서 **제외**했다:
- `RPV-06a`, `RPV-06b`: fixture 업로드 미실행(테스트 계정 미지정, 계속 보류)
- `RPV-08b`: `file_scope` 기반 인위적 0건 통제 질의라 자연어 10건 집계와
  성격이 달라 별도 처리(결과 자체는 별도 기록, 아래 §RPV-08b 참고)

**환경/격리 검증(CUE 독립 확인)**: `git -C /Users/David/DBMA-rpv-c8f7e41a
rev-parse HEAD` = `c8f7e41a` 일치. `find /Users/David/DBMA/output/bench
-newermt "2026-09-28 14:00:00"` 결과 없음(원본 미변경). `output/bench/`
전 파일 `-rw-r--r--` 실제 복사본(심볼릭 링크 아님), `tantivy_index` 254MB
실데이터. **격리 지시 정확히 준수됨.**

**숫자 검증**: RPV-04/05b/01a의 source_file 목록을 raw JSON에서 직접
추출해 보고서 표와 대조 — 정확히 일치. 날조 없음.

### 신규 발견 — 코퍼스 편중 (retrieval 랭킹, GS와 무관)

10개 질의 × 10건 = 100개 후보 슬롯 전체 집계:
```
19  Broadus_Lectures_on_History_of_Preaching.txt
18  Broadus_Preparation_and_Delivery_of_Sermons.txt
18  Dagg_Church_Order.jsonl
18  Hiscox_Standard_Manual.jsonl
12  Fuller_Complete_Works_Vol01.jsonl
 8  Dargan_History_of_Preaching_Vol01.txt
 2  Maclaren_Expositions_Vol01.txt
 2  Dargan_History_of_Preaching_Vol02.txt
 2  Fuller_Complete_Works_Vol02.jsonl
 1  Keach_Tropologia_1681.txt
```
83개 코퍼스 문서 중 **10개만** 100개 슬롯을 채웠고, 코퍼스에서 가장 큰
자료(`Smith_Bible_Dictionary` 4권, 전체 24%)는 **단 한 번도 등장하지 않음.**
이 패턴은 GS 결함이 아니다 — GS는 retrieval 후보의 관련성/다양성을 새로
판정하는 계층이 아니다(HQ, 2026-09-28). **별도 read-only WO로 분리 조사**
(아래 §Retrieval Ranking Investigation WO).

### RPV별 4-필드 판정 (HQ 지정 형식)

| RPV-ID | Retrieval Relevance | Source Diversity | GS Claim/Citation Integrity | Product-Use Finding |
|---|---|---|---|---|
| RPV-01a | 낮음(표본 발췌가 헬라어 문법과 무관 — 설교학 서적 인용) | 5개 문서(형식상 충족) | 미실행(real RPV 대기) | **관찰 대기** — real 실행 후 GS가 이 낮은 관련성 근거를 어떻게 처리하는지 관찰 필요 |
| RPV-01b | 낮음 | 5개 | 미실행 | 관찰 대기 |
| RPV-02 | 낮음 | 5개 | 미실행 | 관찰 대기 |
| RPV-03a | 낮음 | 5개 | 미실행 | 관찰 대기 |
| RPV-03b | 낮음 | 5개 | 미실행 | 관찰 대기 |
| RPV-04 | 중간(Maclaren/Keach 등 상대적으로 다양) | 6개(최다) | 미실행 | 관찰 대기 |
| RPV-05a | 낮음(Beatitudes 주석이 아니라 설교학 서적) | 5개(형식 충족, 실질 낮음) | 미실행 | **PRODUCT-USE FINDING / HOLD** — "여러 주석가 비교" 요건 미충족 |
| RPV-05b | **매우 낮음** — 질의가 명시한 "Fuller"가 top-10에 0건 | 5개(Fuller 배제) | 미실행 | **PRODUCT-USE FINDING / HOLD** — 질의가 지목한 저자 자체가 근거에서 빠짐 |
| RPV-07 | 낮음 | 5개 | 미실행 | 관찰 대기 |
| RPV-08a | 해당없음(가공 인물 통제) | 5개 | 미실행 | 정상 동작(의도된 semantic 매칭) |

RPV-05a/05b는 HQ 지시대로 **PRODUCT-USE FINDING / HOLD**로 기록하며,
GS 결함으로 분류하지 않는다.

### RPV-08b (통제 질의, 별도 집계)

```
Query: "the grace of God" (file_scope=["nonexistent_file_xyz_99887766.txt"])
Count: 0
Verdict: insufficient_evidence가 정상 (file_scope로 의도적 0건)
```
자연어 100-슬롯 집계에서 제외한 이유: 인위적 file_scope 통제라 실제
코퍼스 커버리지를 반영하지 않음.

## Retrieval Ranking Investigation WO (GS/RPV와 분리된 별도 read-only 조사)

```
WORK ORDER — RETRIEVAL RANKING INVESTIGATION (read-only, GS 범위 밖)

목적: RPV preflight에서 관찰된 코퍼스 편중의 원인을 read-only로 조사한다.
  코드/인덱스/코퍼스 수정 금지 — 조사 및 보고만.

조사 항목:
1. Smith_Bible_Dictionary(4권, 전체 코퍼스의 24%)가 왜 100개 슬롯에서
   한 번도 상위 10위 안에 들지 못하는지 (임베딩 생성 여부, 인덱싱 여부,
   스코어 정규화 등 확인)
2. bible route의 bm25_score=1.0 고정(core/hybrid_candidate_pipeline.py:163-167)이
   실제로 얼마나 자주 트리거되는지 — 성구 참조가 없는 일반 신학 질의
   (예: RPV-03a "예정론과 자유의지")도 이 경로를 타는지 classify() 로직 확인
2b. free-text route에서도 bm25_score가 상수로 수렴하는 경우가 있는지
   (1차 preflight에서 관찰됨) — Tantivy 점수 정규화/클램핑 로직 확인
3. Broadus/Dagg/Hiscox/Dargan 등 특정 문헌 클러스터가 반복적으로
   상위 랭킹을 차지하는 스코어 요인 분석(embedding 품질, chunk 길이,
   content_quality 필드 등)

Allowed files: 없음(코드 수정 금지)
Report: 원인 가설 + 근거 코드/데이터 인용. 수정 제안은 별도 WO로 분리.
```


## Preflight 실행 전 공통 확인 사항

- 실행 위치: `/Users/David/DBMA` (main, 병합 커밋 `c8f7e41a` 포함 여부 확인 후)
- G0 비-GS 변경(`config.yaml`, `core/candidate_generator.py`,
  `core/hybrid_candidate_pipeline.py`, `scripts/merge_nae_corpus.py`,
  `scripts/process_unprocessed_nae.py`, `scripts/test_default_corpus_query.py`)은
  RPV 실행 환경에서 제외한다.
- `tsu_manifest.json`의 sha256과 실행 시각을 먼저 기록한다.

## RPV 질문 목록 (13개)

| RPV-ID | 범주 | 질문 텍스트 | 비고 |
|---|---|---|---|
| RPV-01a | Biblical Text | 로마서 8장 28절의 헬라어 원문에서 "모든 것이 합력하여 선을 이룬다"는 표현의 문법 구조는 어떻게 되어 있습니까? | Default corpus |
| RPV-01b | Biblical Text | 요한일서와 요한복음에서 "사랑"(ἀγάπη)이 사용되는 용례 차이가 있습니까? | Default corpus |
| RPV-02 | Exegetical/Interpretive | 야고보서 2장의 "행함이 없는 믿음은 죽은 것"이라는 구절을 로마서의 이신칭의 교리와 어떻게 조화시킬 수 있습니까? | Default corpus |
| RPV-03a | Theological | 개혁주의 관점에서 예정론과 인간의 자유의지는 어떻게 양립합니까? | Default corpus |
| RPV-03b | Theological | 침례교 신앙고백(1689 LBC 등)에서 성찬에 대한 입장은 무엇입니까? | Default corpus (SLBC1689) |
| RPV-04 | Historical/Background | 1세기 로마 제국의 노예 제도가 빌레몬서의 배경을 이해하는 데 어떤 영향을 줍니까? | Default corpus |
| RPV-05a | Multi-source | 산상수훈의 팔복(마태복음 5장)에 대해 여러 주석가들의 해석을 비교해 주십시오. | Default corpus, 다출처 기대 |
| RPV-05b | Multi-source | 칭의(justification) 교리에 대해 Fuller와 다른 저자들의 견해 차이가 있습니까? | Default corpus (Fuller 등) |
| RPV-06a | Personal + Default Corpus | [fixture 설교노트: 요한복음 15장 포도나무 비유] 관련해 참고할 만한 추가 자료가 있습니까? | **fixture 업로드 후 실행 — 아래 §fixture 참고** |
| RPV-06b | Personal + Default Corpus | [fixture 개인자료: 성령의 은사] 제 개인 서재 자료를 우선으로, 부족하면 기본 코퍼스에서 보충해서 정리해 주십시오. | **fixture 업로드 후 실행** |
| RPV-07 | Sermon Research | 이번 주 설교 본문이 누가복음 15장(잃어버린 아들 비유)입니다. 설교 개요를 짜는 데 참고할 신학적/역사적 포인트를 정리해 주십시오. | Personal+Default |
| RPV-08a | Insufficient Evidence | "김민수 목사"라는 신학자가 주장했다는 "제3의 은혜론"의 핵심 내용은 무엇입니까? | 가공 인물, 근거 없음 기대 |
| RPV-08b | Insufficient Evidence | (실행 직전 manifest hash 기준으로 확정 — 아직 미확정, §fixture 참고) | 통제 질의 |

## RPV-06a/06b fixture 사양 (preflight에서 함께 처리)

**테스트 계정 결정 (HQ, 2026-09-28)**: C1이 RPV 전용 임시 테스트 계정을 직접
생성한다. 아래 4개 조건을 반드시 지킨다.

1. **실사용자·개인 자료 사용 금지** — 실제 사용자 계정이나 실사용자가 업로드한
   Personal Corpus 자료를 절대 사용하지 않는다.
2. **RPV fixture 문서만 업로드** — 이 문서 §fixture 문서 A/B로 지정된 것 외
   다른 자료를 이 테스트 계정에 올리지 않는다.
3. **계정 ID·fixture 원문·생성된 evidence ID를 preflight 보고서에 고정** —
   추정치가 아니라 실제 생성된 값을 그대로 기록한다(아래 보고 형식 참고).
4. **RPV 종료 후 계정·업로드 자료의 보존/삭제 상태를 기록** — RPV 전체 완료
   시점에 이 테스트 계정과 fixture를 삭제했는지, 보존했는지, 보존한다면
   사유를 별도로 남긴다(§RPV 종료 후 처리 참고).

### fixture 문서 A (RPV-06a용) — 확정본, C1 임의 작성 금지

**제목**: 요한복음 15장 포도나무 비유 설교노트

**본문**:
```
요한복음 15:1-8 묵상 (개인 설교 준비 메모)

"나는 참 포도나무요 내 아버지는 농부라"(요 15:1)

1. 포도나무-가지 비유의 핵심은 "거하라"(μένω, meno)는 동사의 반복이다.
   15장 안에서 이 단어가 10회 이상 반복된다 — 일회적 결단이 아니라
   지속적 관계를 강조.

2. 가지치기(καθαίρω, kathairo, 15:2)는 심판이 아니라 더 많은 열매를
   위한 손질이다. 같은 어근이 요 13:10 "씻다"(καθαρός)와 연결되어
   말씀으로 이미 깨끗해진 상태(15:3)를 전제한다.

3. "나를 떠나서는 아무것도 할 수 없음이라"(15:5) — 사역의 열매는
   능력이 아니라 관계에서 나온다는 것을 회중에게 어떻게 전달할지 고민 중.

적용 질문: 우리 교회 성도들에게 "거함"이 구체적으로 무엇을 의미하는가?
다음 주 설교에서 이 부분을 더 다뤄볼 것.
```

**용도**: 이 fixture 문서가 Personal Corpus에 업로드된 후, "이 설교노트와
관련해 참고할 만한 추가 자료가 있습니까?" 질의 시 Default Corpus가
이 개인 자료를 override하지 않고 보완적으로만 작동하는지 관찰한다.

### fixture 문서 B (RPV-06b용) — 확정본, C1 임의 작성 금지

**제목**: 성령의 은사 개인 연구노트

**본문**:
```
성령의 은사(고전 12장) 개인 연구 메모

1. 바울이 은사(χάρισμα, charisma) 목록을 제시하는 방식 — 고전 12:8-10과
   롬 12:6-8, 엡 4:11의 목록이 서로 겹치지 않는다. 각 본문의 목적이
   다르기 때문으로 보임(고전 12장은 교회의 하나됨, 롬 12장은 실천적
   섬김, 엡 4장은 직분).

2. "각 사람에게 유익하게 하려 하심이라"(고전 12:7) — 은사의 목적은
   개인의 은혜 체험이 아니라 공동체 유익. 이 부분을 설교에서
   강조하고 싶음.

3. 은사 중지론 vs 지속론 논쟁은 이번 설교에서 다루지 않기로 결정 —
   본문 자체(고전 12장)가 그 논쟁을 직접 다루지 않기 때문.

개인 서재 우선 참고, 부족하면 기본 코퍼스에서 보충 요청.
```

**용도**: "제 개인 서재 자료를 우선으로, 부족하면 기본 코퍼스에서 보충해서
정리해 주십시오" 질의 시 Personal Corpus 우선순위가 실제로 지켜지는지
관찰한다.

- preflight 산출물: 실제 업로드 후 시스템이 생성한 evidence_id를 그대로 기록
  (추정 금지) — 위 확정본 텍스트를 그대로 업로드하고, 임의로 내용을
  바꾸거나 요약하지 않는다.

## RPV-06a/06b 최종 preflight 결과 (2026-09-28) — CUE 검증 완료, HOLD

**fixture 업로드**: 격리 워크트리(`/Users/David/DBMA-rpv-c8f7e41a`)의
`data/RAW/`에 확정본 텍스트 그대로 저장 → `_execute_processing()` 파이프라인
실행 → TSU dataset 204,262건 → 204,272건(+10, fixture A 7청크 + fixture B
3청크). evidence_id: A=`6f323b08ce388551d2fa772c756a828e`(tsu_id 접두사
`TSU-JHN-` — 성구 참조 정상 파싱), B=`5ce2824e947da15da8893fbb45c07239`.
CUE가 `grep -c`로 청크 수·evidence_id 존재 직접 재확인, 원본
`/Users/David/DBMA` 미변경 확인.

**retrieval 결과** (`output/bench/rpv_preflight_result.json`, CUE가 직접
열람해 수치 대조 — 정확히 일치):

| 테스트 | 결과 수 | top-1 source | top-1 score |
|---|---|---|---|
| RPV-06a + file_scope | 7 | fixture A | 0.3404 |
| RPV-06b + file_scope | 3 | fixture B | 0.3785 |
| RPV-06a no-scope(실제 RPV 조건) | 10 | Broadus | 0.3643 |
| RPV-06b no-scope(실제 RPV 조건) | 10 | Broadus | 0.2171 |

**판정**: `file_scope`로 강제 지정하면 fixture가 정상 검색됨 —
청킹·임베딩 자체는 올바르게 동작. 그러나 **실제 RPV 조건(사용자가
scope를 지정하지 않고 그냥 질문)에서는 두 fixture 모두 top-10에
전혀 등장하지 않고 Broadus만 반환됨.** Tantivy candidate index가
`reindex_document()` schema mismatch로 신규 문서를 candidate
generation 경로에 반영하지 못하는 것이 원인으로 추정(C1 보고,
CUE 미검증 — 원인 자체는 별도 조사 필요).

**RPV-06a**: HOLD · **RPV-06b**: HOLD

**⚠️ 이 결과의 함의(RPV-05 편중 문제보다 더 근본적)**: RPV-06의 원래
목적은 "Personal Corpus가 Default Corpus에 override되지 않는가"였다.
그런데 지금은 **그 질문 이전 단계 — 방금 업로드한 개인 문서가 일반
질의에서 전혀 검색되지 않는다.** Personal Corpus 우선순위를 논하기
전에, 신규 업로드 문서가 애초에 retrieval candidate pool에 진입하지
못하는 더 기초적인 결함(추정)이다. GS 결함 아님(§4 동일 원칙 —
retrieval/인덱싱 계층), 단 실사용 임팩트가 RPV-05 편중보다 클 수
있어 별도로 강조 기록한다.

## RPV 종료 후 처리 (테스트 계정)

RPV-FINAL 보고 제출 시 다음을 함께 기록한다:
```
테스트 계정 ID:
보존 여부: 삭제됨 / 보존됨(사유: ___)
업로드 fixture 문서 처리: 삭제됨 / 보존됨(사유: ___)
확인 명령 및 raw 출력:
```

## RPV-08b 통제 질의 확정 절차

1. `tsu_manifest.json` sha256 + 시각 기록
2. 후보 질의 1~2개를 시험 실행해 RankedCandidate 0건인 것을 확인
3. 0건 확인된 질의를 RPV-08b 최종 텍스트로 이 문서에 업데이트

## Preflight 보고 형식 (C1 → CUE)

RPV-ID별로:
```
RPV-ID:
실행 명령:
raw 출력 (RankedCandidate 개수/ID 또는 fixture evidence_id):
기대 결과 판정: grounded 가능 / insufficient_evidence가 정상
```

RPV-06a/06b는 위에 추가로 테스트 계정 ID와 fixture 원문 전체를 포함한다.

## 실행 대상 정정 (2026-09-28)

real RPV 실행 대상은 **9개**다(8개 아님): `01a, 01b, 02, 03a, 03b, 04, 07,
08a, 08b`. 05a/05b/06a/06b는 HOLD.

## Candidate Pipeline Trace WO (2단계 조사, c8f7e41a 격리 워크트리, read-only)

**배경**: Tantivy 인덱스 재생성(Sep 28 15:54) 후에도 fixture 문서가
no-scope 검색에서 0건으로 확인됨(`rpv_preflight_v2_result.json`, CUE
검증 완료 — 117줄 전체, `pwd` 필드 포함, RPV-06a/06b 둘 다 10/10 Broadus).
단순 stale-index 문제가 아니라 "등록한 개인 자료를 일반 질문으로 찾을 수
있는가"라는 상위 사용자 경로 자체가 깨진 상태로 판단됨.

**조사 파이프라인 단계**(코드 참조 — `core/hybrid_candidate_pipeline.py`,
기본 `candidate_k=30`, `fetch_k = candidate_k * _INDEX_PAGE_OVERFETCH`):
```
classify() [core/query_planner.py]
  → CandidateGenerator.search() [core/candidate_generator.py]
  → fetch_k 단위 후보 생성
  → _demote_index_pages() candidate_k 절단 [hybrid_candidate_pipeline.py:100-110]
  → tsu_by_id join
  → Stage 2 scoring(theological/passage)
  → top-k 반환
```

**조사 항목**:
1. fixture의 TSU record·`tsu_id`·`source_file`·content가 `tsu_dataset.jsonl`과
   Tantivy 인덱스에 실제 존재하는지 직접 조회로 확인
2. fixture 본문의 고유 문구(예: "포도나무 비유 설교노트", "μένω")로
   exact/free-text 검색했을 때 candidate generation 단계(fetch_k 시점)에
   들어오는지 확인 — no-scope 자연어 질의가 아니라 fixture 고유어로
   직접 테스트
3. 위 파이프라인 6단계 중 정확히 어느 단계에서 fixture가 사라지는지
   각 단계 직후 중간값을 출력/기록해 추적
4. **high-k(예: candidate_k=200 이상)로 재실행**해 top-10과 비교 —
   "애초에 후보 생성이 안 됨"과 "후보엔 있지만 top-10 랭킹에서 밀림"을
   구분

**금지 사항**: 코드/인덱스/코퍼스 수정 금지. 원인 위치가 단계별로
확정된 뒤에만 별도 corrective WO를 발급한다. real RPV는 이 조사
완료 전까지 시작하지 않는다.
