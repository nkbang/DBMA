# CW-04 Gate 2B — Implementation Brief

- **Status**: AUTHORIZED (2026-09-29 HQ 발행)
- **Precondition**: [GS-FINAL-RPV-CW04-ARCHITECTURE-DECISION-BRIEF.md](GS-FINAL-RPV-CW04-ARCHITECTURE-DECISION-BRIEF.md)
  — AD-01 `[✓ HQ — Option C]`, AD-02 `[✓ HQ — Option D]`,
  CUE Architecture Verification `[✓ CUE]`
- **Implementation**: AUTHORIZED — 아래 허용 범위 안에서만
- **C1**: 구현 착수 가능 (G0 통과 후)
- **CUE**: C1 구현 보고 대기 → 독립 검증

---

## 0. 이 브리프가 구현을 승인하는 정확한 범위

AD-01(Option C — 업로드/등록 시점 명시적 membership) + AD-02
(Option D — Relevance retrieval + role-aware merge)를 실제 코드에
적용한다. HQ가 AD-01/AD-02 승인 시 붙인 제한 조건과 제외 항목,
CUE Architecture Verification에서 확인한 구체적 코드 지점을 그대로
따른다.

---

## 1. AD-01 구현 — Membership 명시적 필드 + 기존 document_id 연결 재사용

### 1.1 구현 원칙 (HQ 제한 조건 그대로)

```text
Authoritative source/document metadata
        ↓
explicit corpus membership
        ↓
retrieval/candidate
        ↓
Evidence.corpus_type
```

**`source_file` 패턴 추론은 membership authority가 아니다.** 새로운
독립 SSOT를 만드는 것이 아니라, CUE Architecture Verification이
확인한 기존 `document_id` 연결(`core/evidence_adapters/tsu_adapter.py:69,80,98`)
을 그대로 재사용해 downstream까지 전달한다.

### 1.2 허용 파일

1. **`data/제련완성본/registry/documents.json`(registry record)의
   스키마** — document_id별 record에 명시적 membership 필드 추가
   (필드명은 C1이 제안, CUE가 검증 — 예: `corpus_membership:
   "personal"|"default"`). 기존 필드(`source_file` 등)는 건드리지
   않는다.
2. **`ui/pages/processing.py`** — 업로드/등록 흐름
   (`_execute_processing()` 부근)에서 이 필드를 명시적으로 기록하는
   지점 추가. 업로드 UI에 "개인 자료 여부" 같은 사용자 선택지가
   필요하다면 최소 범위로 추가 가능하나, **기존 업로드 흐름의 구조는
   유지**한다(대규모 UI 개편 금지).
3. **`core/evidence_adapters/tsu_adapter.py`** —
   `TSUEvidenceFactory.resolve_corpus_type()`(200-207번째 줄)를
   하드코딩된 `return CORPUS_DEFAULT` 대신, registry에서 해당
   document_id의 membership 필드를 조회하도록 수정. registry가 없거나
   필드가 없는 문서는 **fail-safe로 `CORPUS_DEFAULT`를 유지**한다
   (기존 데이터 호환성 — 이미 처리된 문서를 갑자기 personal로
   재분류하지 않음).
4. **RPV fixture 등록**(`documents.json`의 fixture A/B 레코드) — 이번
   구현 검증을 위해 두 fixture record에 `corpus_membership: "personal"`
   을 명시적으로 설정(격리 워크트리 내 fixture 데이터만 대상, §5
   RPV-06 검증 조건 참고).

### 1.3 금지 파일 / 범위

- `core/retrieval.py`(RetrievalEngine, ADR-001) — 무변경
- `core/candidate_generator.py`(CandidateGenerator, Tantivy 스키마/인덱스) — 무변경
- `core/grounded_*.py`(GS P4-P9, ADR-036) — 무변경
- Qdrant, Tantivy 인덱스 재구성 — 금지
- TSU dataset 물리적 재생성/재처리 — 금지(fixture record 필드 추가는
  registry 레벨이며 TSU dataset 재생성이 아님)
- 기존 처리된 문서(RPV fixture 외)의 `corpus_membership` **일괄
  재분류 금지** — 이번 구현은 향후 업로드분(및 명시적으로 지정된
  fixture)에만 적용, 기존 대량 코퍼스 backfill은 별도 범위

---

## 2. AD-02 구현 — Relevance retrieval + role-aware merge

### 2.1 구현 원칙 (HQ 제외 항목 그대로 — 절대 포함 금지)

```text
Personal score boost       X
Personal rank-1 강제       X
4:6 fixed quota            X
Default 제거               X
새로운 retrieval engine    X
GS에서 corpus 분류         X
```

relevance는 relevance대로 유지하고, Personal/Default 역할은 별도
metadata/assembly 차원에서만 보존한다. "merge"는 순위를 조작하는
것이 아니라 **corpus role을 결과에 명시적으로 부착해 보존하는 것**을
의미한다 — 이번 CW-04 범위에서 role-aware merge는 **ranking을
바꾸지 않는다**(정렬 기준은 기존 `final_score` 그대로 유지, Option D
의 "merge"는 corpus_type 정보가 retrieve() 결과에서 유실되지 않고
Evidence까지 도달하게 하는 데 한정한다 — Gate 2A에서 논의된 "quota"나
"boost" 방식의 merge와 혼동하지 않는다).

### 2.2 허용 파일

1. **`core/evidence_adapters/tsu_adapter.py`** — §1.2-3과 동일
   (corpus_type resolver를 registry 연동으로 변경하는 것 자체가
   AD-02의 "역할 보존"과 AD-01의 "membership 전달"을 동시에 만족).
2. **`core/evidence_pool.py`** — `by_corpus_type()`(144-146번째 줄)는
   이미 존재하므로 무변경 가능. 필요시 `EvidencePool`에 corpus role별
   집계/조회 편의 메서드를 **추가만** 한다(기존 메서드 시그니처
   변경 금지).
3. **`core/evidence_assembly.py`** — `AssemblyManifest`에 corpus role
   정보가 필요하다면 **추가 필드**로만 확장(기존 `by_query_order`,
   `evidence_to_queries` 필드는 변경 금지, ADR-036 B8 데이터 구조
   정본 영향 여부는 CUE가 검증 시 확인).

### 2.3 금지 파일 / 범위

- `core/hybrid_candidate_pipeline.py::HybridRetriever.retrieve()`
  **내부**(112-241번째 줄) — scoring/ranking 로직 무변경. corpus role
  전달이 필요하면 `retrieve()`가 반환하는 `RankedCandidate`에
  `metadata`(이미 존재하는 dict 필드, `core/retrieval.py`의
  `RankedCandidate.metadata: dict`)를 통해 전달하는 방식을 우선
  검토한다(신규 dataclass 필드 추가가 필요하면 C1이 제안, CUE가
  ADR-001 저촉 여부 검증).
- `HybridQueryProcessor.process()` 자체의 top-K 선택/정렬 순서 변경
  — 금지(§2.1 "ranking을 바꾸지 않는다")
- quota 기반 슬롯 할당, score에 corpus_type 가중치 직접 반영 — 금지
  (Policy A/B는 이번 결정에서 명시적으로 배제됨)

---

## 3. Gate 0 (예외 없음, 승계)

```text
pwd
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
```
Expected: `/Users/David/DBMA-rpv-c8f7e41a`, detached HEAD,
`c8f7e41acfa0e5444d8b02ecb84da9c53a588441`. 불일치 시 예외 없이 STOP.
매 보고서에 위 4개 명령의 **실제 출력**을 포함한다(Gate 1/2A에서
반복 지적된 생략 재발 금지).

## 4. 테스트 (Gate 2A §11 Test A-H 그대로 승계, 구현 후 필수)

- Test A — Personal only: 정상 검색/조립
- Test B — Default only: 기존 검색 동작 보존(회귀 없음)
- Test C — Personal + Default: 양쪽 evidence 모두 후보가 되는지,
  `corpus_role`/source identity/evidence identity/provenance 보존
- Test D — Personal relevance advantage: corpus role만으로 부당
  대체되지 않는지
- Test E — Default supplementation: Personal 불충분 시 Default 정상
  보완
- Test F — No silent subordination: 한쪽 존재만으로 다른 쪽 제거/무시
  금지
- Test G — GS boundary: `core/grounded_*.py` 무변경, GS가
  corpus ranking 재수행하지 않음
- Test H — Regression: CW-01/CW-02/CW-03/RPV-05 regression, 기존
  retrieval tests(`tests/test_retrieval*.py` 등), 기존 GS P03A-P12
  tests 전부 통과

## 5. RPV-06a/06b 검증 조건 (CW-04 Gate 2A §10 확정 질문 재사용)

구현 완료 후 아래 두 질문을 실제 baseline에서 재실행한다(질문 임의
변경 금지 — CW-03 이후 확립된 보고 표준):

- **RPV-06a**: "포도나무와 가지의 비유에서 열매를 맺기 위해 주님 안에
  거한다는 의미를 설명해 주세요" — CUE 확인 baseline: route=hybrid,
  fixture A(`TSU-JHN-6f323b08...`) rank 6
- **RPV-06b**: "성령께서 교회에 다양한 은사를 주신다는 관점에서 은사의
  종류와 목적을 정리해 주세요" — CUE 확인 baseline: route=hybrid,
  fixture B(`TSU-UNK-5ce2824e947da15da8893fbb45c07239...`) rank 8

**acceptance 기준**:
1. 두 질문 모두 **rank가 구현 전과 동일하게 유지**되어야 한다(§2.1 —
   ranking을 바꾸지 않는다는 원칙의 직접 검증. rank가 바뀌었다면
   scoring에 corpus role이 섞여 들어간 것이므로 AD-02 위반).
2. 결과에 포함된 fixture A/B 해당 candidate의 `Evidence.corpus_type`
   (또는 그에 상응하는 role 정보)이 `"personal"`로 정상 태깅되어야
   한다(구현 전에는 항상 `"default"`로 하드코딩됐던 것과 대조 확인).
3. 같은 결과 안의 다른(비-fixture) evidence들의 `corpus_type`은
   `"default"`로 유지되어야 한다(Test C의 라이브 재현).

## 6. C1 보고 표준 (CW-03/Gate 1/Gate 2A 승계, 예외 없이 적용)

Question integrity / Worktree identity(G0 실제 출력) / Execution
timestamp / Result artifact / Test question immutability / 서술적
결론이 아니라 파일:줄번호 코드 인용 + raw 실행 결과 포함. "구현
완료됐다", "정상 동작한다" 같은 문장만으로는 승인 근거가 되지 않는다.

## 7. CUE 독립 검증 (착수 전 확정)

C1 구현 완료 보고 후 CUE가 최소 확인할 항목:
1. 실제 diff(`git diff --stat`, 허용 파일 목록과 일치하는지)
2. §1.3/§2.3 금지 범위 위반 여부(특히 `retrieve()` 내부 미변경 확인)
3. Test A-H 라이브 재현
4. RPV-06a/06b rank 불변 + corpus_type 태깅 라이브 재현(§5)
5. Regression(CW-01/02/03/RPV-05) 라이브 재현
6. G0 준수(실제 출력 포함 여부)

CUE는 GREEN을 최종 선언하지 않는다 — 검증 결과만 HQ에 제출, HQ
승인 후에만 `[✓ HQ]`로 승격한다.

## 8. 완료 흐름

```text
Gate 2B Implementation Brief (본 문서)
    ↓
Gate 0 확인
    ↓
C1 구현(§1-2 허용 범위 내)
    ↓
C1 Test A-H + RPV-06a/06b 실행 + Regression 실행 (raw 결과 포함 보고)
    ↓
CUE 독립 검증(§7)
    ↓
HQ 최종 승인
    ↓
RPV-06 [✓ HQ] → GS-FINAL-RPV 최종 판단으로 복귀
```

## 9. 현재 상태

```text
CW-04 Gate 1                    [✓ HQ]
CW-04 Gate 2A                   [✓ HQ]
CW-04 Architecture Decision     [✓ HQ APPROVED — AD-01 Option C, AD-02 Option D]
CUE Architecture Verification   [✓ CUE]
CW-04 Gate 2B                   [AUTHORIZED — 본 문서 범위 내]
C1                              [구현 착수 가능, G0 필수]
CUE                             [C1 구현 보고 대기 → 독립 검증]
RPV-06                          [HOLD — 구현 후 재검증]
GS-FINAL-RPV                    [HOLD]
```
