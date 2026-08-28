# NAE Manifest & Authority SSOT

**Governing ADR**: ADR-030 v2.1 §8 · **Baseline**: dev/dbma-engine @ fcaa380 (2026-08-27)

| 라벨 | 경로 | 역할 | Writer | Authority |
|------|------|------|--------|-----------|
| **M2** | `NAE/pipeline/registration/state/source_manifest.yaml` | Source Registry (14 records, schema_version '1.2') | registration pipeline — `NAE/pipeline/registration/manifest_writer.py::write_entry()` | **SSOT (최종 권위)** |
| **M1** | `NAE/authority/source_manifest.yaml` | Non-authoritative mirror (10 records) | — (M2 앞 10 레코드의 byte-identical 복사본) | derived, non-authoritative |
| **M3** | `NAE/manifest/NAE_SOURCE_MANIFEST_v1.csv` | Acquisition Backlog Tracker (25 rows, CSV) | acquisition layer (수동/외부) | backlog only — **source registry 아님** |

## M2 governance (CUE §2-1 forensic determination)

- **M2 는 enforced schema file 이 없다.**
  - `resources/theological_sources/modern/source_manifest.schema.yaml` — M2 의 governing schema **아님**.
    ADR-030 governance validator/test 만 참조. documentation schema 로만 취급.
  - `resources/theological_sources/source_manifest.schema.yaml` — `scripts/source_validator.py` 전용.
    이 validator 는 `resources/theological_sources/**` 만 스캔하며 `manifest_id` 를 요구한다. M2 경로를 읽지 않음.
  - `NAE/pipeline/registration/source_validator.py` — 하드코딩 필드 튜플. YAML 스키마 미사용.
- **M2 레코드 구조는 코드로 정의된다**: `NAE/pipeline/registration/pipeline.py:165` 의 dict 리터럴.
  현재 base 키 10개: `source_id, title, author, author_id, work_id, edition_id, year, license, archive_source, raw_checksum`.
- **Writer**: `manifest_writer.write_entry()` — append-only, `source_id` 중복 시 예외, 덮어쓰기 없음.
  내부 동작 = `yaml.safe_load → list.append → yaml.safe_dump(sort_keys=False, allow_unicode=True)`.
- **M2 YAML 주석은 내구적이지 않다**: 위 round-trip 에서 소실된다. M2 상단 `# ROLE: …` 주석은 다음 registration
  write 때 사라질 수 있으며, **그것은 회귀가 아니다.** M2 의 역할·권위에 대한 **내구적 authority 는 본 문서**다.
  (M1 `# DERIVED`, M3 `# ROLE` 은 코드 writer 가 없어 내구적이다.)
- **Validation**: `scripts/m2_source_registry_validator.py` 는 ADR-030 불변식을 **M2 YAML + 파일시스템 baseline
  에 직접** 검사한다. 어떤 스키마 파일도 그 PASS 판정에 관여하지 않는다.

## 계층 구분 — Category (TSU) vs authority_class (M2 source)

ADR-030 v2.1 §7.3: 두 축은 다른 계층이며 서로를 결정하지 않는다.

| 계층 | 필드 | 수준 | 축 |
|------|------|------|----|
| TSU record (per-claim) | `content_genre`, `theological_category`, `category` | 문서/claim 단위 | "무엇에 관한 것인가" (주제/장르) |
| M2 source (per-source) | `authority_class` | source 단위 | "근거로서 얼마나 무겁게 다룰 것인가" (교리적 무게) |

`authority_class` 는 TSU record 에 쓰지 않는다. 기존 3,319 production TSU 의 `category` 는 `None` /
`AUTHORITATIVE_SOURCE_MISSING` 유지(migration 없음).

## Additive metadata (ADR-030 v2.1 §7.4 / §8.4) — status: **A-2b-1 완료 / A-2b-2 완료**

아래 6필드 전부 M2 레코드에 반영됨.

| 필드 | 타입 | required | 확정 상태 |
|------|------|----------|-----------|
| `authority_class` | enum `primary_doctrinal\|historical_witness\|reference\|application` | false | **populated 14/14 (A-2b-1)** — 값 per ADR-030 v2.1 §7.3 (historical_witness ×10 / reference ×4) |
| `raw_path` | str | false | **populated 14/14 (A-2b-1)** — CUE-ADR030-M2-RAWPATH-…md §3 |
| `checksum_target` | str | false | **populated 14/14 (A-2b-1)** — 동 §3 |
| `content_genre` | list[str] | false | **populated 14/14 (A-2b-2)** — per-record 값 CUE 판정 + HQ 비준 (RATIFIED v1.1) |
| `theological_category` | list[str] | false | **populated 5/14 (A-2b-2)** — ecclesiology×2, soteriology×2, missions×1. 나머지 9 키 생략 |
| `tradition` | str | false | **populated 10/14 (A-2b-2)** — `"Particular Baptist"` ×10. Smith×4 키 생략 |

현재 M2 레코드 키 = **14~16** (base 10 + authority_class + raw_path + checksum_target + content_genre 14건 + [theological_category 5건] + [tradition 10건]). 분류 권위 = `docs/agents/cue/CUE-ADR-030-A2B2-CLASSIFICATION-RULE.md` (RATIFIED v1.1).

## Future SHOULD (A-2a/A-2b 아님)

- **S-9**: explicit enforced M2 schema + `manifest_writer` 검증 훅. 지금은 만들지 않는다. 새 스키마 파일 생성 금지.
- **S-3** (v2.1): M1 archival migration — consumer 0 전수 재확인 후 (`grep *.py` 결과 M1 `source_manifest.yaml`
  로드 코드 0건, 확인됨).

## References

- ADR-030 v2.1 §7 (Metadata Authority), §8 (M2 SSOT / M3 Backlog / M1), §10 (State Authority Map)
- `docs/agents/cue/CUE-ADR-030-POST-FORENSIC-REASSESSMENT.md`
- `docs/agents/cue/CUE-ADR030-M2-RAWPATH-CHECKSUM-TARGET-DETERMINATION.md`
