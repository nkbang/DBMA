# NAE Upstream Ingestion Layer — Work Plan v1

작성일: 2026-08-11
최종 개정: 2026-08-11 (FINAL-DRAFT 반영)
대상 ADR: [ADR-021](architecture/ADR-021-NAE-Source-Registration-Raw-Preservation-Extraction.md) (Proposed/FINAL-DRAFT, C1 Final Review 대기)
상태: 계획 단계 — **코드 구현 미착수**

---

## 0. 전제

- 이 작업은 ADR-021이 **Approved**로 승격된 이후에만 착수한다(Evidence Before
  Promotion Rule — 구현 완료·회귀 PASS·C1 리뷰·사용자 승인 4개 조건).
- 기존 3,319 verified TSU / Qdrant 3,319 vector(ADR-020 baseline)는 이번
  작업 전 구간에서 절대 건드리지 않는다.
- 776건 Human Review disposition 설계는 별도 트랙(현재 보류)이며 이 작업과
  독립적이다.

## 1. 진행률

```
- [x] ADR-021 C1 1차 리뷰 (CONDITIONAL GREEN, 2026-08-11)
- [x] 4개 조건 사용자 승인 (Authority=Option C / dry-run=C1권장안 /
      Quality Gate=WARNING우선, 2026-08-11)
- [x] ADR-021 FINAL-DRAFT 개정 (raw immutability 실질 메커니즘 확정,
      duplicate 2계층, exception queue 경계, dry-run 후보 3건 조사, 2026-08-11)
- [x] C1 Final Review — GREEN (baseline 수치 오류 재감사 후 정정 확인, 2026-08-11)
- [x] Phase A: Legacy Authority Snapshot 생성 (Option C, commit `61d4f59`,
      2026-08-11) — 2 authors/2 works/2 editions, Production mutation 0
- [ ] ADR-021 Approved 승격 (Phase B~F 구현 완료 후 — Evidence Before Promotion Rule)
- [ ] Phase B: NAE/pipeline/registration/ 모듈 구현
- [ ] Phase C: Quality Gate 구현 (WARNING 우선, FAIL 7항목 고정)
- [ ] Phase D: 단위 테스트
- [ ] Phase E: 샘플 신규 source 1건 dry-run (후보 3건 중 선정)
- [ ] Phase F: Evidence Package + 회귀
진행률: 40%
```

## 2. Phase 순서 및 산출물

### Phase A — Legacy Authority Snapshot (결정 완료: Option C)
- 기존 3,319건(전체 4,117건, review_status 무관)의 Author/Work Authority를
  `NAE/authority/legacy_snapshot/`(읽기전용)로 파생 생성(ADR-021 §4 생성 절차)
- `NAE/authority/authors.yaml`, `NAE/authority/works.yaml`은 빈 상태로 신설
  (신규 registration 전용, legacy snapshot과 물리적으로 분리, write target
  아님)
- 생성 과정 자체를 Evidence로 기록(입출력 해시, Production 무변경 확인)

### Phase B — `NAE/pipeline/registration/` 모듈
| 파일 | 책임 |
|---|---|
| `identity.py` | source_id/author_id/work_id/edition_id 발급 + 충돌 시 suffix 규칙(ADR-021 §4) |
| `source_validator.py` | **신규 upstream validator**(ADR-021 §5) — Raw/Metadata/Provenance/Integrity 검사. 기존 `scripts/source_validator.py`(manifest 필드 검사)와는 별개 모듈, 호출 관계 없음 |
| `raw_preservation.py` | SHA256 체크섬 기록 + append-only ledger, 접근 시점 재검증, duplicate detection 2계층(ADR-021 §6, §9) |
| `authority.py` | Author/Work Authority 대조·병합 후보 제시(자동 병합 금지), legacy snapshot 참조만 |
| `manifest_writer.py` | `source_manifest.yaml` entry 작성/갱신(기존 schema v1.2 재사용) |
| `state.py` | ADR-021 §10 상태 머신 + §11 exception queue(Production review 큐와 물리적 분리) |
| `quality_gate.py` | PASS/WARNING/FAIL, FAIL 7항목 고정(ADR-021 §8) |
| `pipeline.py` | 위 모듈을 오케스트레이션, `extract.py`/`tsu/builder.py` 호출 지점만 연결(코드 무수정) |

### Phase C — Quality Gate (결정 완료: WARNING 우선)
- FAIL은 §8 7항목(원본 손실/체크섬 불일치/추출결과 없음/0페이지/손상/
  identity 없음/필수 메타데이터 없음)으로만 한정
- WARNING(OCR confidence 낮음 등)은 초기엔 비차단, 임계값은 첫 dry-run
  실측 후 결정 — 임의로 숫자 확정하지 않음

### Phase D — 테스트
- ADR-021 §17 Test Specification 그대로 사용(14개 영역, 표 정의 완료)
- 핵심 불변식: dry-run 후 Qdrant points_count 불변 + 기존 3,319 TSU ID셋 불변

### Phase E — Dry-run (후보 3건 조사 완료, ADR-021 §13)
- Candidate 1: Gifford, "Forward mission movement in North Korea"(1897,
  36p, hOCR) — 정상 PASS/WARNING 경로 검증에 적합, 1순위 추천
- Candidate 2: Hall, "Mrs. Esther Kim Pak, Korea's first woman doctor"
  (18p, hOCR)
- Candidate 3: "Kim Chang Sik: a Korean circuit rider"(10p, hOCR, 저자
  정보 결여) — FAIL 경로(Required metadata missing) 검증에 유용
- 최종 선정은 Phase A 착수 시 사용자 확인. 전체 경로 실행 후 **TSU Builder
  호출 직전 정지**(manifest/raw/state만 생성, TSU 생성은 별도 승인 후)

### Phase F — Evidence + 회귀
- `scripts/generate_*_evidence.py` 패턴 재사용해 신규 evidence generator 작성
- 전체 회귀(NAE 관련 스위트) 통과 확인, Production mutation 0 재확인

## 3. 착수 전 결정 사항 — 결정 이력

| 항목 | 최초 결정(1차 승인) | 최종 결정(FINAL-DRAFT) |
|---|---|---|
| Authority 시드 | Option C | **Option C 유지** |
| Quality Gate 성향 | WARNING 우선 | **WARNING 우선 유지**, FAIL 7항목 고정 |
| 첫 dry-run 대상 | C1 권장 검색조건만 | **후보 3건 실제 조사 완료**(§Phase E) |
| Source Validator | 기존 `source_validator.py` 확장 | **번복 — 신규 module로 분리**(이번 작업 명령서 §5, C1 권고 반영) |

**투명성 노트**: Source Validator 결정이 1차 승인(기존 확장)에서 이번
작업 명령서(신규 module 분리)로 번복되었다. 사용자가 이번 명령서에서
직접 지시한 내용이라 그대로 반영했으나, 의도치 않은 번복이면 정정 필요.

## 4. 예상 변경 파일 (Phase B~D)

```
신규:
  docs/architecture/ADR-021-*.md          (완료, 커밋됨)
  docs/NAE_UPSTREAM_INGESTION_WORK_PLAN_001.md  (완료, 커밋됨)
  NAE/authority/legacy_snapshot/{authors,works}.yaml   (Phase A)
  NAE/authority/authors.yaml                            (Phase A, 빈 상태)
  NAE/authority/works.yaml                              (Phase A, 빈 상태)
  NAE/pipeline/registration/__init__.py
  NAE/pipeline/registration/identity.py
  NAE/pipeline/registration/source_validator.py
  NAE/pipeline/registration/raw_preservation.py
  NAE/pipeline/registration/authority.py
  NAE/pipeline/registration/manifest_writer.py
  NAE/pipeline/registration/state.py
  NAE/pipeline/registration/quality_gate.py
  NAE/pipeline/registration/pipeline.py
  tests/nae/registration/test_*.py (신규 스위트)
  scripts/generate_upstream_ingestion_evidence.py

무수정:
  NAE/pipeline/canonical/*
  NAE/pipeline/tsu/*
  NAE/pipeline/ingest/*
  NAE/pipeline/index/*
  NAE/pipeline/embed/*
  NAE/collectors/*
  core/dataset_registry.py
  scripts/source_validator.py (기존 — 신규 upstream validator와 별개로 존치)
```

---

## 비고

이 문서는 ADR-021 Approved 승인 전까지 계획 문서로만 유지한다. C1 Final
Review 통과 및 Approved 승격 후 각 Phase 완료 시 진행률(§1)을 갱신한다.
