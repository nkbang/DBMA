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

## Decision 1 — Q8: Personal/Default Membership SSOT

### 옵션 A — `source_file` 경로 패턴 매칭

Gate 2A 산출물 1이 제안한 방식. `resolve_corpus_type(source_file)`이
경로 접두사(예: `data/내서재_개인/`)로 판별.

- 장점: 구현이 가장 단순, 기존 `TSUEvidenceFactory` 진입점 하나만 수정
- 단점(Gate 2A에서 이미 지적됨): 경로 규칙 변경에 취약, ingestion과
  retrieval의 암묵적 결합 증가, corpus_type이 3종 이상으로 늘면
  확장성 저하

### 옵션 B — 기존 Registry(`documents.json`) + Sample Library 구조 활용

본 브리프 §0.1에서 확인한 기존 인프라. `_get_sample_source_files()`
로직을 역으로 사용 — "sample_library에 없는 문서 = personal" 또는
반대로 "sample_library에 있는 문서만 default, 나머지는 personal"로
간주.

- 장점: 이미 운영 중인 real 인프라(코드 신규 작성 최소화), source_file
  패턴 추측이 아니라 explicit document_id 목록 기반
- 단점: "sample = default 전체"라는 등식이 실제로 참인지 검증 필요
  (curated sample 외에도 대량의 TSU-derived 기본 코퍼스 문서가 있고,
  이들은 sample_library에 등록되지 않았을 가능성 — 즉 이 구조가
  원래 "일부 추천 문서 큐레이션"용으로 설계됐지 "전체 corpus의
  Personal/Default 이분류"용으로 설계된 게 아닐 수 있음). `sample_library.json`이
  현재 이 worktree에 없어 실제 production 데이터로 재검증 필요.

### 옵션 C — 업로드 시점 명시적 필드 신설

`ui/pages/processing.py`의 업로드 흐름(`DEFAULT_RAW_DIR` 저장 →
`_execute_processing()`)에 corpus_type을 명시적으로 태깅해 TSU
record/registry에 영구 기록.

- 장점: 가장 명확하고 안정적인 SSOT — 추측/패턴 매칭 없음
- 단점: 스키마 변경(TSU record, registry record 양쪽) 필요, 기존
  누적 데이터에는 소급 적용 안 됨(backfill 필요)

**CUE는 세 옵션 중 하나를 권고하지 않는다.** 옵션 B는 "새로 만들지
않고 기존 구조를 우선 검토하라"는 HQ 지시에 가장 부합하는 후보로
보이나, §0.1에서 지적한 대로 원래 설계 의도(sample curation)와
이번 요구(Personal/Default 이분류)가 정확히 일치하는지는 추가 확인이
필요하다.

---

## Decision 2 — Personal/Default Retrieval Role Policy

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

### 후보 메커니즘 (Gate 2A 산출물 4, 재정리 — 여전히 미승인 후보)

| 후보 | 개요 | 장점 | 단점 |
|---|---|---|---|
| A. Score adjustment | corpus_type별 scoring 가중치 | 구현 단순 | scoring/composition 경계 모호, "우선"이 "차단"으로 번질 위험(Gate 2A에서 이미 경고됨) |
| B. Candidate quota | top-K 내 personal:default 비율 보장 | 두 corpus 모두 최소 노출 보장 | 비율이 고정되면 query 무관성 무시, 유연성 부족 |
| C. Two-stage retrieval | default/personal 별도 조회 후 병합 | corpus 분리가 명확, `core/retrieval.py` 무변경 | 두 번의 candidate generation 비용 |
| D. Primary+supplemental merge | C의 구체화, tie-break만 personal 우선 | Default 차단 문제 최소화 | tie-break 기준 정의 필요 |

**CUE는 이 중 하나를 권고하지 않는다.** Gate 2A CUE 검증에서 C+D
조합이 "GS boundary 유지, Default 차단 방지" 조건을 기술적으로
가장 깔끔히 만족한다는 관찰은 있었으나, 이는 설계 후보 비교였지
Architecture Decision이 아니다.

---

## 공통 전제 (변경 불가, CW-04 §6/§14.3 그대로)

ADR-001(Retrieval authority), 기존 retrieval pipeline/candidate
generation architecture, TSU corpus, Qdrant, Tantivy, GS P03A-P12,
CW-01/CW-02/CW-03, RPV-05 — 전부 보존. 신규 retrieval engine, 신규
embedding model, 대규모 ranking rewrite, GS architecture 변경은
이 Architecture Decision의 선택지에 포함되지 않는다.

---

## HQ Decision (작성 요청 — 아래 채워서 승인)

```text
Q8 Membership SSOT 결정:        [ 옵션 A / B / C / 기타 — HQ 기입 ]
사유:

Personal/Default Role Policy 결정: [ A / B / C / D / 기타 — HQ 기입 ]
사유:

Gate 2B Implementation Authorization: [ 승인 대상 파일/범위 — 이 결정 이후 별도 문서 ]
```

이 결정문이 채워진 뒤에만 별도의 **Gate 2B Implementation
Authorization** 문서를 발행하고, C1 구현이 착수될 수 있다. 그 전까지
C1/CUE는 STOP을 유지한다.

## 현재 상태

```text
CW-04 Gate 1                    [✓ HQ]
CW-04 Gate 2A                   [✓ VALIDATED / DESIGN EVIDENCE]
CW-04 Architecture Decision     [DRAFT — HQ 결정 대기, 본 문서]
CW-04 Gate 2B                   [NOT AUTHORIZED]
C1                              [STOP]
CUE                             [STOP — HQ 결정 대기]
```
