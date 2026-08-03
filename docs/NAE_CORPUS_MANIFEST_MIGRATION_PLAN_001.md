# NAE Corpus Manifest Migration Plan 001

작성일: 2026-08-02
Project: NAE-CORPUS-MANIFEST-ARCHITECTURE-DESIGN-001 Phase 6
성격: **로드맵 문서 — 실행 없음.** 각 Phase는 별도 승인 후 착수한다.

---

## 로드맵

```
Phase 0   Architecture Design            ← 이번 작업(NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md)
Phase 1   Manifest Schema                (스키마 파일 실제 작성)
Phase 2   Monograph Pilot                (Dagg/Hiscox/Fuller에 Manifest Entry 실제 적용)
Phase 3   Periodical Pilot                (Baptist Missionary Magazine에 Manifest Entry 실제 적용)
Phase 4   Validator Integration           (source_validator.py 또는 별도 도구로 Manifest 검증)
Phase 5   TSU Connection                  (Manifest → 실제 TSU 생성 연결)
```

---

## Phase 0 — Architecture Design (완료, 이번 작업)

산출물: `NAE_CORPUS_MANIFEST_ARCHITECTURE_v1.md`,
`NAE_CORPUS_MANIFEST_ARCHITECTURE_REVIEW_001.md`(본 계획과 함께 작성).
Manifest Entity의 책임·필드·Lifecycle·Monograph/Periodical 통합
가능성을 확정. **코드/스키마/데이터 변경 없음.**

## Phase 1 — Manifest Schema (다음 단계, 별도 승인 필요)

- `resources/theological_sources/`에 실제 Manifest 스키마 파일 작성
  (위치는 이 Phase 착수 시 결정 — 후보: `modern/manifest.schema.yaml`
  또는 Registry와 동일 위치의 `authority/manifest_entries.schema.yaml`).
- `manifest_id`/`processing_status`/`tsu_access`/`schema_version` 등
  §Phase3 필드를 실제 YAML 스키마로 구체화.
- **전제조건**: 이번 Architecture Design 승인.

## Phase 2 — Monograph Pilot (Manifest 실제 적용)

- Pilot-001(Dagg/Hiscox)과 Pilot-002(Fuller, 10건)에 **실제 Manifest
  Entry**를 만들어 `processing_status`를 `MANIFEST_CREATED`까지
  진행시켜 본다 — 이미 Pilot manifest(`source_manifest.yaml`)가
  존재하므로 그 위에 Manifest Entry만 추가하면 됨(가장 낮은 리스크의
  착수 지점).
- **전제조건**: Phase 1 스키마 확정.

## Phase 3 — Periodical Pilot (Manifest 신규 생성)

- Baptist Missionary Magazine(10 issue)에 대해 **corpus manifest
  계층 자체가 없다는 gap**(Periodical Condition Resolution Report-001
  §4에서 발견)을 이 단계에서 실제로 메운다 — Registry(Author/Work/
  Volume/Issue/Source)는 이미 있으므로 그 위에 Manifest Entry를
  신설.
- **전제조건**: Phase 2 완료(Monograph에서 절차 검증 후 Periodical
  적용 — Pilot 확대 순서 원칙, Authority Registry Design v1 §4.2와
  동일한 "소규모 우선" 원칙 재적용).

## Phase 4 — Validator Integration

- Manifest Entry의 Reference Integrity(→Source, →Work 등)와
  `processing_status` 단조 증가 규칙을 검증하는 도구 필요.
- `scripts/source_validator.py`(manifest 대상)와
  `scripts/authority_validator.py`(Registry 대상, 설계만 존재,
  Registry Design v1 §Phase5)에 이은 **세 번째 검증 도구**가 될
  가능성 — 또는 기존 두 도구 중 하나를 확장할지 이 Phase에서 결정.
- **전제조건**: Phase 2/3에서 실제 Manifest 데이터가 있어야 검증
  로직을 실증할 수 있음.

## Phase 5 — TSU Connection

- `processing_status: TSU_ELIGIBLE`인 Manifest Entry만 TSU 빌더
  입력으로 사용하도록 파이프라인 연결.
- **전제조건**: Phase 4 검증 도구가 최소 1회 이상 실제 데이터에 대해
  성공적으로 실행됨.

---

## 단계 간 원칙

- **각 Phase는 이전 Phase 완료 및 별도 승인 후에만 착수**한다 — 이
  로드맵 문서 자체가 여러 Phase를 한꺼번에 승인하는 것이 아니다.
- **RAW는 어느 Phase에서도 변경되지 않는다.**
- Monograph를 먼저, Periodical을 나중에 적용하는 순서는 이미
  검증된 절차(Pilot-001/002)를 재사용해 리스크를 낮추기 위함이다.
