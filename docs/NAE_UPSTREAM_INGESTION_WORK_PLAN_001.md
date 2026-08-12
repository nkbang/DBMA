# NAE Upstream Ingestion Layer — Work Plan v1

작성일: 2026-08-11
대상 ADR: [ADR-021](architecture/ADR-021-NAE-Source-Registration-Raw-Preservation-Extraction.md) (Proposed, 승인 대기)
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
- [x] ADR-021 C1 Review (CONDITIONAL GREEN, 2026-08-11)
- [x] 4개 조건 사용자 승인 (Authority=Option C / dry-run=C1권장안 /
      Quality Gate=WARNING우선 / validator=기존확장, 2026-08-11)
- [ ] ADR-021 Approved 승격 (구현 완료 후 — Evidence Before Promotion Rule)
- [ ] Phase A: authority 시드 파일 생성 (Option C — read-only legacy snapshot)
- [ ] Phase B: NAE/pipeline/registration/ 모듈 구현
- [ ] Phase C: Quality Gate 구현 (WARNING 우선)
- [ ] Phase D: 단위 테스트
- [ ] Phase E: 샘플 신규 source 1건 dry-run (C1 권장 검색조건)
- [ ] Phase F: Evidence Package + 회귀
진행률: 15%
```

## 2. Phase 순서 및 산출물

### Phase A — Authority 시드 (결정 완료: Option C)
- 기존 3,319건의 Author/Work Authority를 `NAE/authority/legacy_snapshot/`
  (읽기전용)로 보존
- `NAE/authority/authors.yaml`, `NAE/authority/works.yaml`은 빈 상태로 신설
  (신규 registration 전용, legacy snapshot과 분리)

### Phase B — `NAE/pipeline/registration/` 모듈
| 파일 | 책임 |
|---|---|
| `identity.py` | source_id/author_id/work_id/edition_id 발급 + 충돌 시 suffix 규칙(ADR-021 §4) |
| `raw_preservation.py` | SHA256 체크섬 기록, read-only 권한 부여, 재확인 로직(ADR-021 §5) |
| `authority.py` | Author/Work Authority 대조·병합 후보 제시(자동 병합 금지) |
| `manifest_writer.py` | `source_manifest.yaml` entry 작성/갱신(기존 schema v1.2 재사용) |
| `state.py` | ADR-021 §7 상태 머신(DISCOVERED~QUALITY_PASSED + 4 실패 상태) |
| `pipeline.py` | 위 모듈을 오케스트레이션, `extract.py`/`tsu/builder.py` 호출 지점만 연결(코드 무수정) |

### Phase C — Quality Gate (결정 완료: WARNING 우선)
- `quality_gate.py` — Phase 7 3범주(File/OCR/Metadata) 체크, PASS/WARNING/FAIL
- FAIL은 치명적 오류(원본 파일 손실, OCR 0페이지)로만 한정, 나머지는 WARNING
  으로 진행하고 사람이 확인. 실측 샘플 축적 후 임계값 조정

### Phase D — 테스트
- ADR-020 패턴 그대로: fake client/isolated fixture, Production 파일 미접근
- 최소 커버: identity 충돌 처리, 체크섬 불일치 감지, duplicate 감지, quality gate 3판정, 상태 전이(성공/4개 실패 경로)

### Phase E — Dry-run (대상 선정 기준 확정: C1 권장안)
- 검색 조건: `possible-copyright-status:"Public" AND ocr:"hocr" AND (language:kor OR language:eng)`,
  1900년 이전 한국 관련 Protestant missionary 문서, 50페이지 이하
- Phase E 착수 시 Archive.org 조회로 구체 항목 1건 확정
- 전체 경로 실행, **manifest/raw 파일만 생성, TSU Builder 호출 직전에 정지**
  (Quality Gate 결과까지만 확인, TSU 생성은 별도 승인 후)

### Phase F — Evidence + 회귀
- `scripts/generate_*_evidence.py` 패턴 재사용해 신규 evidence generator 작성
- 전체 회귀(NAE 관련 스위트) 통과 확인, Production mutation 0 재확인

## 3. 착수 전 결정 사항 — 전부 승인 완료 (2026-08-11)

1. **첫 dry-run 대상 source 기준** — C1 권장 검색조건 채택(§Phase E)
2. **Authority 시드 방식** — Option C(read-only legacy snapshot) 채택
3. **Quality Gate 초기 임계값 성향** — WARNING 우선 채택
4. **`source_validator.py` 처리** — 기존 확장(신규 validator 신설 안 함)

## 4. 예상 변경 파일 (Phase B~D)

```
신규:
  docs/architecture/ADR-021-*.md          (완료, 본 커밋)
  docs/NAE_UPSTREAM_INGESTION_WORK_PLAN_001.md  (완료, 본 커밋)
  NAE/authority/authors.yaml
  NAE/authority/works.yaml
  NAE/pipeline/registration/__init__.py
  NAE/pipeline/registration/identity.py
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
```

---

## 비고

이 문서는 ADR-021 승인 전까지 계획 문서로만 유지한다. 승인 후 각 Phase
완료 시 진행률(§1)을 갱신한다.
