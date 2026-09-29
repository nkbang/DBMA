# CW-04 Architecture Decision Brief — Personal/Default Corpus Role

- 작성: CUE, 2026-09-28 (read-only 분석, 구현 없음)
- 근거: [GS-FINAL-RPV-CW04-SCOPE.md](GS-FINAL-RPV-CW04-SCOPE.md) Gate 1
  `[✓ HQ]`, [GS-FINAL-RPV-CW04-GATE2A-SCOPE.md](GS-FINAL-RPV-CW04-GATE2A-SCOPE.md)
  Gate 2A `[✓ VALIDATED / DESIGN EVIDENCE]`
- 목적: HQ가 분리 지시한 두 결정(Q8 — Membership SSOT, Personal/Default
  Retrieval Role Policy)을 위한 정책 결정 요청 문서. **CUE는 특정
  옵션을 권고하지 않는다 — C-03 Architecture Decision Brief와 동일
  원칙.** 구현하지 않는다.

---

## 0. 지금까지 확정된 사실 (Gate 1/2A, CUE 코드 검증 완료)

1. `Evidence.corpus_type`(`core/evidence_model.py:63`)은 정의만 있고,
   모든 adapter가 항상 `CORPUS_DEFAULT`로 하드코딩한다
   (`core/evidence_adapters/tsu_adapter.py:200-207` `resolve_corpus_type()`은
   `source_file` 인자를 받고도 무시하고 항상 `"default"` 반환).
2. `RankedCandidate`(`core/retrieval.py`)와 `CandidateRef`
   (`core/candidate_generator.py`)에는 corpus role을 표현할 필드
   자체가 없다 — retrieval lineage 전체에 corpus role이 전달되지 않는다.
3. GS(P4-P9)는 `EvidencePool`/`AssemblyManifest`를 읽기만 하고
   scoring/재정렬을 하지 않는다(`core/grounded_synthesis_input.py:4-5`)
   — corpus role 문제는 GS가 해결할 위치가 아니다(경계 유지 확정).
4. RPV-06a/06b fixture/query는 CUE가 baseline에서 직접 재현해
   `[✓ VALIDATED]` — fixture A rank 6, fixture B rank 8로 실제
   retrieval candidate pool에 존재함이 실측 확인됨(질문/fixture 유효성
   문제는 아니다).

## 0.1 신규 확인 사실 — 기존 Registry 구조 (본 브리프 작성 중 CUE 조사)

HQ 지시("새 corpus_resolver.py는 [Q8] 결정 이후에만 검토, 기존
Registry/metadata/selection 구조를 우선 검토")에 따라 CUE가
`/Users/David/DBMA-rpv-c8f7e41a`에서 직접 확인했다:

- **`ui/pages/library.py`**에 이미 "sample(curated read-only 참고
  자료)" vs "my library(사용자 본인 자료)" 구분 UX가 존재한다:
  - `_registry_path()` → `DEFAULT_REGISTRY_PATH`
    (`data/제련완성본/registry/documents.json`) — document_id →
    `{source_file, ...}` 매핑(`core/config.py:100`,
    `load_identity_registry()`)
  - `_get_sample_source_files()`(`ui/pages/library.py:394-417`) —
    `DEFAULT_SAMPLE_LIBRARY_PATH`(`core/config.py:114`,
    `sample_library.json`)의 `document_ids` 목록을 registry에서
    resolve해 "curated sample" source_file 집합을 얻는다
  - `_copy_sample_to_my_library()` — sample을 "내 서재"로 복제하는
    기존 기능 존재(정확한 명칭이 이미 Personal Corpus 개념과 일치)
- **실측**: 이 worktree의 `documents.json`에는 RPV fixture A/B가
  실제로 등록되어 있음(`6f323b08...→rpv_fixture_A_...`,
  `5ce2824e...→rpv_fixture_B_...`) — document_id가 evidence_id와
  일치. 단 `sample_library.json` 파일 자체는 이 worktree에 존재하지
  않음(seed 안 됨) — 따라서 "sample 여부" 판별은 현재 이 worktree
  기준으로는 전부 "sample 아님"이 되어, 결과적으로 모든 문서가
  "personal"로 분류될 위험이 있다(테스트 환경의 우연한 상태일 수
  있음, production 환경 검증 필요).

**이 발견의 함의**: source_file 문자열 패턴에 의존하지 않는 기존
document_id 기반 registry 인프라가 이미 존재하며, "sample(=Default
후보)" 개념도 이미 UI 레벨에 있다. 다만 이 registry가 "Personal vs
Default"를 직접 표현하는 것은 아니고 "curated sample vs 그 외"를
표현한다 — 이것이 Q8이 요구하는 corpus role과 정확히 같은 개념인지는
정책적으로 확정이 필요하다(예: "sample 아님" = "personal"이 항상
참인가? 사용자가 직접 업로드한 default-corpus formatted 문서는
어떻게 되는가?).

---

## AD-01 — Corpus Membership SSOT

**결정 대상**: Personal / Default를 누가(무엇이) 권위 있게 결정하는가?
**결정 원칙(HQ)**: 기존에 이미 권위 있는 사실을 표현하는 구조가 있다면
그것을 재사용하고, 구현이 편하다는 이유로 새 SSOT를 만들지 않는다.
**Invariant**: Personal/Default membership must have one authoritative
source.

### 옵션 A — `source_file` 경로 패턴 매칭

Gate 2A 산출물 1이 제안한 방식. `resolve_corpus_type(source_file)`이
경로 접두사(예: `data/내서재_개인/`)로 판별.

### 옵션 B — 기존 Registry(`documents.json`) + Sample Library 구조 활용

본 브리프 §0.1에서 확인한 기존 인프라. `_get_sample_source_files()`
로직을 역으로 사용 — "sample_library에 없는 문서 = personal" 또는
반대로 "sample_library에 있는 문서만 default, 나머지는 personal"로
간주.

### 옵션 C — 업로드 시점 명시적 필드 신설

`ui/pages/processing.py`의 업로드 흐름(`DEFAULT_RAW_DIR` 저장 →
`_execute_processing()`)에 corpus_type을 명시적으로 태깅해 TSU
record/registry에 영구 기록.

### Q8 결정 테스트 (HQ 5문항, CUE가 사실로 답변 — 판정 아님)

| 질문 | 옵션 A (경로 패턴) | 옵션 B (기존 Registry) | 옵션 C (명시적 필드) |
|---|---|---|---|
| Q8-1. 현재 데이터 전체에 적용 가능한가? | 모든 TSU record가 source_file을 가짐(사실) — 단 현재 경로 규칙에 Personal/Default 구분 convention이 존재한다는 근거는 CUE가 코드에서 확인하지 못함 | registry(`documents.json`)에는 처리된 문서만 등록됨 — RAW 업로드했지만 아직 처리 안 된 문서는 미포함 가능성(§0.1 실측: 이 worktree엔 fixture 2건만 등록). `sample_library.json`은 이 worktree에 부재 | 신규 필드이므로 정의상 전체 적용 가능하나, 기존 누적 데이터는 소급 미적용(backfill 필요) |
| Q8-2. membership을 명시적으로 표현하는가? | 아니오 — 경로 문자열에서 추론(암묵적) | 부분적 — document_id가 sample_library에 있는지는 명시적이나, "personal"이라는 라벨 자체는 없음(부재=personal로 간주하는 역추론) | 예 — 필드 자체가 명시적 라벨 |
| Q8-3. ingestion→indexing→retrieval→Evidence까지 일관 전달 가능한가? | 가능 — `TSUEvidenceFactory.resolve_corpus_type(source_file)`이 이미 그 지점에 존재(stub 상태, Gate 1 확인) | `RankedCandidate`/`CandidateRef`에 corpus_type 필드가 없다는 Gate 1 결론은 옵션 B에도 동일하게 적용 — registry lookup을 retrieval 단계에 새로 연결해야 함(현재 연결 없음) | 가능 — TSU record 자체에 필드를 넣으면 나머지 경로는 옵션 A와 동일한 방식으로 전달 가능 |
| Q8-4. 기존 Registry의 원래 의미를 왜곡하지 않는가? | 해당 없음(Registry 미사용) | **불확실** — `_get_sample_source_files()`의 원 설계 의도는 "curated 추천 문서 큐레이션"(§0.1)이며 "전체 corpus의 Personal/Default 이분류"로 설계된 근거를 CUE가 코드/문서에서 찾지 못함. 왜곡 여부는 정책 판단 필요 | 해당 없음(신규 필드, 기존 Registry 의미에 영향 없음) |
| Q8-5. 새 SSOT를 추가하지 않고도 유지 가능한가? | 예 — `source_file`은 이미 존재하는 필드 | 예 — `documents.json`/`sample_library.json`은 이미 존재 | **아니오** — 신규 필드가 곧 신규 SSOT |

**CUE는 위 표의 사실을 바탕으로 어느 옵션도 권고하지 않는다.** Q8-4의
"불확실" 판정(옵션 B)이 §0.1에서 이미 지적한 리스크와 일치한다는 점만
재확인한다.

---

## AD-02 — Retrieval Role Policy

HQ가 이미 명시한 제약 조건(변경 불가, 그대로 유지):

```text
Personal = primary research context
Default  = supplemental reference context

Personal rank 1 강제        [금지]
Default 제거                [금지]
임의 score boost            [미결정 — 아직 승인 아님]
고정 quota                  [미결정 — 아직 승인 아님]
Query role(primary/supplemental) 과 Corpus role(personal/default)
                             [독립 축으로 유지]
```

### 후보 메커니즘 (HQ 명명 A-D, Gate 2A 산출물 4 재정리 — 여전히 미승인)

| 후보 | 개요 |
|---|---|
| A. Score adjustment | relevance score + personal boost |
| B. Fixed quota | top-K 내 personal:default 고정 비율(예: 4:6) 보장 |
| C. Two-stage retrieval | Personal retrieval → Default retrieval → role-aware assembly |
| D. Relevance retrieval + role-aware merge | Personal/Default candidate를 각각 relevance로 뽑은 뒤 deterministic merge, corpus role을 EvidencePool까지 명시적으로 보존(rank 1 강제 아님) |

### Decision Matrix (사실/근거/리스크 — 점수화 안 함)

| 기준 | A. Score adjustment | B. Fixed quota | C. Two-stage retrieval | D. Relevance + role-aware merge |
|---|---|---|---|---|
| relevance 보존 | 위험 — corpus_type이 score 공식에 직접 섞임(Gate 2A에서 이미 지적) | 위험 — quota가 채워지면 관련 없는 evidence도 강제 포함 가능 | 보존됨 — 각 stage 내부는 기존 scoring 그대로, 병합만 추가 | 보존됨 — retrieval 자체는 기존 relevance 그대로, merge 단계만 role-aware |
| Personal 역할 보존 | boost 크기가 곧 정책이 됨(정량적 근거 없이 조정 시 임의성) | quota로 최소 노출은 보장되나 "primary research context"라는 의미까지 표현하진 않음 | stage 분리로 역할이 구조적으로 드러남 | corpus role을 EvidencePool까지 명시 필드로 보존 가능(§0 Gate 1: 현재는 이 전달 경로가 없음 — 신규 구현 필요) |
| Default supplementation | 가능(제거 안 함) | 가능하나 quota 상한이 Default를 인위적으로 제한할 수 있음 | 명시적 2-stage로 구조상 보장하기 쉬움 | merge 로직이 "Personal 불충분 시 Default 보완"을 명시적으로 인코딩해야 함(설계 필요, 자동 보장 아님) |
| deterministic | 예(boost 값 고정 시) | 예(quota 고정 시) | 예 | 예(merge 규칙이 결정적이면) |
| 기존 retrieval 영향 | `core/retrieval.py`/`hybrid_candidate_pipeline.py` scoring 함수 수정 필요 | `hybrid_candidate_pipeline.py`의 top-K 선택 로직 수정, `core/retrieval.py` 무변경 가능 | `HybridRetriever.retrieve()`(`core/hybrid_candidate_pipeline.py`) 구조 변경 — Gate 2A 산출물 3이 이미 이 파일을 적용 지점으로 지목함 | `HybridRetriever.retrieve()` 이후 merge 단계 추가 — `core/retrieval.py` 무변경 가능(Gate 1 §GS boundary와 동일한 "무변경 파일" 전략과 정합) |
| 구현 범위(예상) | scoring 함수 다수 지점 수정(넓음) | top-K 선택 지점 1곳(좁음) | retrieve() 전체 재구조화(넓음) | retrieve() 이후 merge 단계 1곳 추가(중간) — Gate 2A 산출물 7의 "신규 파일 1개 + 수정 4-5개" 추정과 유사 |

**CUE는 이 표를 근거로도 특정 정책을 권고하지 않는다.** Gate 2A에서
C+D 조합이 "GS boundary 유지, Default 차단 방지" 조건을 기술적으로
만족한다는 관찰이 있었던 것과 위 표의 "기존 retrieval 영향"/"구현
범위" 행이 D를 상대적으로 국소적인 변경으로 시사하는 것은 사실이나,
이는 설계 비교 관찰이지 Architecture Decision이 아니다.

---

## 공통 전제 (변경 불가, CW-04 §6/§14.3 그대로)

ADR-001(Retrieval authority), 기존 retrieval pipeline/candidate
generation architecture, TSU corpus, Qdrant, Tantivy, GS P03A-P12,
CW-01/CW-02/CW-03, RPV-05 — 전부 보존. 신규 retrieval engine, 신규
embedding model, 대규모 ranking rewrite, GS architecture 변경은
이 Architecture Decision의 선택지에 포함되지 않는다.

---

## 결정 우선순위 (HQ 확정, ①·②가 ⑥보다 우선)

```text
① 기존 Architecture 보존
        ↓
② Membership의 권위성
        ↓
③ relevance integrity
        ↓
④ Personal/Default 역할의 명시성
        ↓
⑤ deterministic behavior
        ↓
⑥ 변경 범위 최소화
        ↓
⑦ 향후 확장성
```

"구현하기 가장 쉬운 방법"이 아니라 "기존 시스템에서 이미 의미를
가지고 있는 사실을 가장 정확하게 보존하는 방법"을 우선한다.

---

## CUE 권고안 (2026-09-29, HQ 명시적 요청에 의한 원칙 예외)

**주의**: 이 세션 전체의 확립된 원칙("CUE는 architecture 정책을
권고하지 않는다", C-03/본 브리프 §Decision 1·2에서 유지)에 대한
**명시적 예외**다. HQ가 "Decision Matrix 근거로 권고안 작성"을 직접
지시했다. 아래는 CUE의 권고이며, **HQ의 최종 승인/수정/반려를
대체하지 않는다.**

### AD-01 — Corpus Membership SSOT

```text
Decision (CUE 권고):
옵션 C — 업로드/ingestion 시점 명시적 membership 필드 신설

Rationale:
우선순위 ①(기존 Architecture 보존)·②(Membership authority)가
⑥(변경 범위 최소화)보다 우선한다는 HQ 원칙 적용 결과:
- 옵션 A(source_file 패턴)는 Q8-2에서 "암묵적 추론"으로 판정됨 —
  membership을 명시적으로 표현하지 않아 ②(authority)를 만족 못함.
- 옵션 B(기존 Registry)는 Q8-4가 "불확실"로 판정됨 — 원 설계 의도
  (curated sample 큐레이션)를 Personal/Default 이분류 용도로 전용하면
  기존 구조의 의미를 왜곡할 위험이 있어, 오히려 ①(기존 Architecture
  보존)을 해칠 수 있다. "이미 있으니 재사용한다"가 "이미 있는 것의
  의미를 보존한다"와 다를 수 있음이 Q8-4에서 드러남.
- 옵션 C는 Q8-2(명시성) YES, Q8-3(propagation 가능) YES로 ②를 가장
  분명히 만족한다. Q8-5(새 SSOT 불필요)만 NO — 이는 ⑥ 항목이며
  우선순위상 ②보다 하위이므로 결정을 뒤집지 않는다.

Rejected alternatives:
- 옵션 A: membership이 암묵적(경로 문자열 추론)이라 authority
  invariant("must have one authoritative source")를 구조적으로
  보장하지 못함 — 경로 규칙이 바뀌면 조용히 깨짐.
- 옵션 B: 기존 Registry("sample_library.json"/"documents.json")를
  전용하는 것은 재사용이 아니라 의미 왜곡이 될 위험이 Q8-4에서
  확인됨. 또한 이 worktree 실측상 sample_library.json이 부재해
  즉시 전체 데이터에 적용 가능한지도 불확실(Q8-1 약함).

Invariant:
Personal / Default membership must have one authoritative source.
(옵션 C 적용 시 — 그 source는 업로드 시점에 기록되는 명시적 필드이며,
이후 TSU record/registry record에 영속적으로 보존된다.)
```

### AD-02 — Retrieval Role Policy

```text
Decision (CUE 권고):
옵션 D — Relevance retrieval + role-aware merge

Rationale:
우선순위 ③(relevance integrity)·④(역할 명시성)가 ⑥(변경 범위
최소화)보다 우선한다는 HQ 원칙 적용 결과:
- 옵션 A(Score adjustment)/B(Fixed quota)는 Decision Matrix의
  "relevance 보존" 행에서 둘 다 "위험"으로 판정됨(corpus_type이
  score 공식에 직접 섞이거나, quota가 관련 없는 evidence를 강제
  포함시킬 수 있음) — ③을 직접 위반할 위험이 있어 우선순위상 먼저
  배제됨.
- 옵션 C(Two-stage retrieval)와 D는 둘 다 ③·④를 만족한다. 그러나
  C는 "기존 retrieval 영향" 행에서 `HybridRetriever.retrieve()`
  전체 재구조화가 필요해 ①(기존 Architecture 보존)에 대한 영향이
  D보다 크다 — CW-04 금지 목록의 "대규모 ranking rewrite"와의 경계에
  더 가깝다.
- D는 동일하게 ③·④를 만족하면서 "기존 retrieval 영향"이 상대적으로
  국소적(`retrieve()` 이후 merge 단계 1곳 추가, `core/retrieval.py`
  무변경 가능) — ①을 D가 C보다 더 잘 보존한다. ①이 ⑥보다 우선하므로
  "구현이 더 쉬워서"가 아니라 "기존 아키텍처를 덜 건드려서" D를
  선택하는 것이 우선순위 원칙과 정합한다.

Rejected alternatives:
- 옵션 A: corpus_type을 score 공식에 직접 섞으면 relevance integrity
  (③)가 corpus membership 정책에 의해 훼손될 위험이 구조적으로 존재.
- 옵션 B: 고정 quota는 질문과 무관한 evidence를 강제 포함시킬 수
  있어 ③을 위반하며, quota 숫자 자체의 근거가 없음(Gate 2A에서
  "4:6 근거 없음"으로 이미 지적됨).
- 옵션 C: ③·④는 만족하나 기존 `HybridRetriever.retrieve()` 구조를
  더 크게 바꿔야 해 ①(기존 Architecture 보존) 원칙에서 D보다 불리.

Invariants:
- Personal = primary research context
- Default = supplemental reference context
- Personal is not forced to rank 1
- Default is not excluded
- Query Role and Corpus Role remain independent
- GS does not perform corpus retrieval or corpus classification
```

### Gate 2B Authorization

```text
Status:
NOT AUTHORIZED. 위 권고안은 HQ 승인 전까지 구현 근거로 사용되지 않는다.
```

---

## 진행 절차 (CUE 권고 제출 이후)

```text
CUE 권고안 (본 절)
    ↓
HQ 검토 — 승인 / 수정 / 반려
    ↓
[승인 또는 수정] → HQ Architecture Decision 확정 (Decision/Rationale/
                    Rejected alternatives/Invariant 최종본)
    ↓
Gate 2B Implementation Authorization 발행
    ↓
C1 구현 → CUE 독립 검증 → RPV-06 재검증 → HQ 최종 승인
```

CUE의 권고는 HQ의 결정을 대신하지 않는다 — HQ가 그대로 승인하든,
다른 옵션으로 수정하든, 반려하고 재검토를 요구하든 전부 HQ의
권한이다.

## HQ 최종 결정 (2026-09-29, APPROVED)

```text
AD-01 Membership SSOT       [✓ HQ APPROVED — Option C]
AD-02 Retrieval Role Policy [✓ HQ APPROVED — Option D]
CW-04 Architecture Decision [✓ HQ APPROVED]
CW-04 Gate 2B                [NOT AUTHORIZED — until CUE verification
                               of implementation plan]
```

### AD-01 승인 시 HQ 제한 조건 (CUE 권고문 표현 수정)

Option C를 "새로운 독립 SSOT를 만드는 것"으로 해석하지 않는다. 구현
시 하나의 authoritative membership 값이 downstream까지 그대로
보존되어야 한다:

```text
Authoritative source/document metadata
        ↓
explicit corpus membership
        ↓
retrieval/candidate
        ↓
Evidence.corpus_type
```

`source_file` 패턴 추론은 membership authority가 아니다(이미 CUE
권고안에서 옵션 A를 배제한 근거와 일치).

### AD-02 승인 시 HQ 제외 항목 (명시적으로 이번 결정에 불포함)

```text
Personal score boost       X
Personal rank-1 강제       X
4:6 fixed quota            X
Default 제거               X
새로운 retrieval engine    X
GS에서 corpus 분류         X
```

relevance는 relevance대로 유지하고, Personal/Default 역할은 별도
metadata/assembly 차원에서 보존한다.

### 반드시 유지할 Invariant (최종)

```text
Personal = primary research context
Default  = supplemental reference context

Query Role ≠ Corpus Role

Personal ≠ rank 1 강제
Default  ≠ 검색 제외

Corpus membership = authoritative metadata
GS ≠ retrieval/corpus classification
```

### 다음 단계 (HQ 확정 순서)

```text
AD-01/AD-02 HQ 승인
        ↓
CUE 독립 Architecture Verification
        ↓
Implementation Plan
        ↓
HQ Gate 2B Authorization
        ↓
C1 구현
        ↓
CUE 검증
        ↓
HQ 승인
```

**CW-04 Gate 2B Implementation Brief는 HQ가 작성 예정**(허용 파일,
금지 범위, 테스트, G0, RPV-06a/06b 검증 조건 포함). 그 전 단계인
"CUE 독립 Architecture Verification"이 현재 CUE의 작업 범위다.

## CUE 독립 Architecture Verification (2026-09-29)

HQ 승인된 AD-01(Option C)/AD-02(Option D)가 실제 baseline
(`/Users/David/DBMA-rpv-c8f7e41a`, HEAD `c8f7e41a`)에서 구조적으로
실현 가능한지 read-only로 확인(구현 아님, 코드 변경 없음).

### AD-01 — 4단계 propagation 경로 실현 가능성

```text
Authoritative source/document metadata → explicit corpus membership
→ retrieval/candidate → Evidence.corpus_type
```

- **document_id가 이미 전 구간에 연결되어 있음을 확인**:
  `core/evidence_adapters/tsu_adapter.py:69,80,98`에서
  `tsu_record.get("document_id")`가 TSU record → Evidence 변환 전
  구간에 이미 threading되어 있다. 즉 registry(`documents.json`)의
  document_id 레코드에 명시적 membership 필드를 추가하면, **기존
  document_id 연결고리를 그대로 타고 downstream까지 전달 가능** —
  HQ가 요구한 "새로운 독립 SSOT를 만들지 않는다"는 제약과 부합하는
  구현 경로가 실제로 존재함을 확인.
- TSU record는 일반 JSON dict이므로(`tsu_id, source_file, document_id,
  ...` 등 15개 필드 확인, 스키마 고정 아님) 신규 필드 추가에 구조적
  장벽 없음.
- `RankedCandidate`(`core/retrieval.py`), `CandidateRef`
  (`core/candidate_generator.py`)는 일반 `@dataclass`(frozen 아님) —
  신규 필드 추가에 구조적 장벽 없음.
- **결론**: AD-01의 4단계 경로는 기존 `document_id` 연결을 재사용하는
  방식으로 실현 가능하며, 이는 CUE 권고안의 "옵션 C" 취지와 HQ의
  "신규 독립 SSOT 아님" 제약을 동시에 만족하는 구체적 구현 지점이다
  (구현 방식 자체는 여전히 Gate 2B Implementation Brief에서 확정).

### AD-02 — Option D(post-processing role-aware merge) 실현 가능성

- `HybridRetriever.retrieve()`(`core/hybrid_candidate_pipeline.py:112`,
  return 지점 `ranked.sort(...); return ranked[:k_output]`)는 명확한
  단일 반환점을 가진다 — role-aware merge를 `retrieve()` **내부**가
  아니라 `HybridQueryProcessor.process()` 호출 경계에서 후처리
  단계로 삽입 가능함을 확인. 이는 AD-02 Decision Matrix에서 예상한
  "기존 retrieval 영향 국소적" 주장을 코드 구조로 뒷받침한다.
- `core/retrieval.py`(RetrievalEngine, ADR-001 authority)와
  `core/grounded_*.py`(GS, ADR-036 boundary)는 이 경로 어디에도
  개입하지 않아도 된다 — 기존 금지 목록(§공통 전제) 위반 없이 구현
  가능한 지점이 실제로 존재함을 확인.

### 검증 결론

AD-01/AD-02 둘 다 **HQ가 승인한 제약(신규 SSOT 아님, GS 무변경,
retrieval engine 무변경) 안에서 실현 가능한 구체적 코드 지점이
baseline에 실제로 존재**한다. 이 확인은 Implementation Plan의
타당성을 뒷받침하는 것이지, 구현 방식 자체를 확정하는 것은 아니다 —
정확한 파일/함수/필드 설계는 HQ의 Gate 2B Implementation Brief에서
다뤄야 한다.

## 현재 상태

```text
CW-04 Gate 1                    [✓ HQ]
CW-04 Gate 2A                   [✓ HQ]
CW-04 Architecture Decision     [✓ HQ APPROVED]
  AD-01 Membership SSOT         [✓ HQ — Option C]
  AD-02 Retrieval Role Policy   [✓ HQ — Option D]
CUE Architecture Verification   [✓ CUE — 실현 가능성 확인 완료]
CW-04 Gate 2B                   [NOT AUTHORIZED — HQ Implementation
                                  Brief 발행 대기]
C1                              [STOP]
CUE                             [STOP — HQ Gate 2B Implementation
                                  Brief 대기]
```
