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

## HQ Architecture Decision (작성 요청 — 아래 채워서 승인)

```text
### AD-01 — Corpus Membership SSOT

Decision:
[HQ 선택]

Rationale:
[기존 코드/데이터에서 확인된 사실 근거]

Rejected alternatives:
[선택하지 않은 옵션과 이유]

Invariant:
Personal / Default membership must have one authoritative source.

---

### AD-02 — Retrieval Role Policy

Decision:
[HQ 선택]

Rationale:
[relevance / role / architecture 근거]

Rejected alternatives:
[선택하지 않은 정책]

Invariants:
- Personal = primary research context
- Default = supplemental reference context
- Personal is not forced to rank 1
- Default is not excluded
- Query Role and Corpus Role remain independent
- GS does not perform corpus retrieval or corpus classification

---

### Gate 2B Authorization

Status:
NOT AUTHORIZED until CUE verifies AD-01 and AD-02.
```

이 결정문이 채워지고 CUE가 AD-01/AD-02를 baseline에서 독립 검증한
뒤에만 별도의 **Gate 2B Implementation Authorization** 문서를
발행하고, C1 구현이 착수될 수 있다. 그 전까지 C1/CUE는 STOP을
유지한다.

## 현재 상태

```text
CW-04 Gate 1                    [✓ HQ]
CW-04 Gate 2A                   [✓ VALIDATED / DESIGN EVIDENCE]
CW-04 Architecture Decision     [DRAFT — HQ 결정 대기, 본 문서]
CW-04 Gate 2B                   [NOT AUTHORIZED]
C1                              [STOP]
CUE                             [STOP — HQ 결정 대기]
```
