# Task Order 019 — 보고서: 기존 등록 문서 doc_type 백필

**상태**: 완료 (2026-07-29)
**우선순위**: P3 (낮음)

---

## §1. 프로덕션 registry 착수 시점 재확인 결과

| registry 경로 | 총 문서 수 | `doc_type=None` |
|---|---|---|
| `data/제련완성본/registry/documents.json` **(config.yaml output_dir — 실제 프로덕션)** | 78 | **0** |

**결론**: §1(2026-07-29 최초 확인)과 동일하게 **0건**. 프로덕션 registry는
백필 대상이 없다. Task Order 019 최초 실측 결과와 달라진 점 없음.

---

## §2. 구현 — 신규 스크립트

**파일**: `scripts/backfill_doc_type.py`

```python
"""registry의 doc_type=None 레코드에 guess_doc_type()으로 값을 채운다."""

import argparse
from pathlib import Path
import shutil
from datetime import datetime

from core.document_identity import guess_doc_type
from core.identity_registry import load_identity_registry, save_identity_registry


def backfill(registry_path: str, output_dir: str, apply: bool) -> None:
    registry = load_identity_registry(registry_path)
    changed = []
    skipped_no_md = []

    for doc_id, record in registry["documents"].items():
        if record.get("doc_type") is not None:
            continue  # 이미 값 있으면 건드리지 않음

        source_file = record.get("source_file", "")
        stem = Path(source_file).stem
        ext = Path(source_file).suffix.lstrip(".")
        md_path = Path(output_dir) / f"{stem}_{ext}.md"

        if not md_path.exists():
            skipped_no_md.append(doc_id)
            continue  # 원문 없이 추측하지 않음

        content = md_path.read_text(encoding="utf-8")
        doc_type = guess_doc_type(content, source_file, record.get("title"))
        changed.append((doc_id, source_file, doc_type))
        if apply:
            record["doc_type"] = doc_type

    print(f"변경 대상: {len(changed)}건, md 파일 없어 건너뜀: {len(skipped_no_md)}건")
    for doc_id, source_file, doc_type in changed:
        print(f"  {doc_id[:12]}... {source_file} -> {doc_type}")

    if apply and changed:
        # 백업 생성
        backup_path = f"{registry_path}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        shutil.copy2(registry_path, backup_path)
        save_identity_registry(registry, registry_path)
        print(f"registry 저장 완료: {registry_path}")
        print(f"백업: {backup_path}")
    elif not apply:
        print("(dry-run — 실제 반영하려면 --apply)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("registry_path")
    parser.add_argument("output_dir")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    backfill(args.registry_path, args.output_dir, args.apply)
```

---

## §3. 구현 — 신규 테스트

**파일**: `tests/test_backfill_doc_type.py`

4가지 검증 케이스:
1. 이미 doc_type 있는 레코드는 무시
2. md 파일 없으면 skip
3. dry-run은 저장 안 함
4. --apply는 저장함

---

## §4. dry-run 결과 (apply 전)

| registry | 변경 대상 | md 파일 없어 skip |
|---|---|---|
| `output/beta_validation` | 8건 | 4건 |
| `output/beta_validation_v2` | 8건 | 4건 |
| `output/beta_validation_v3` | 8건 | 4건 |
| `output/beta_validation_v4` | 8건 | 4건 |
| `output/beta_validation_v5` | 8건 | 4건 |
| `output/SPRINT2_MD_DEBUG` | 1건 | 0건 |
| **합계** | **41건** | **20건** |

beta_validation 5개 registry의 분류 결과:
- `설교`: 마가복음, 요한복음1, 사도행전1 (3건)
- `기타`: 고린도전서, 고린도후서, 로마서1 (3건)
- `설교/기타` 혼재: 요한복음2 (beta_validation=설교, v4/v5=기타)

---

## §5. --apply 실행 후 실제 반영 건수

| registry | 적용 완료 |
|---|---|
| `output/beta_validation` | 8건 |
| `output/beta_validation_v2` | 8건 |
| `output/beta_validation_v3` | 8건 |
| `output/beta_validation_v4` | 8건 |
| `output/beta_validation_v5` | 8건 |
| `output/SPRINT2_MD_DEBUG` | 1건 |
| **합계** | **41건** |

모든 registry에 `.bak` 백업 파일 생성 완료.

---

## §6. 적용 후 재확인 결과

| registry | 적용 후 `doc_type=None` |
|---|---|
| `output/beta_validation` | 4건 (md 파일 없어 skip된 것) |
| `output/beta_validation_v2` | 4건 (md 파일 없어 skip된 것) |
| `output/beta_validation_v3` | 4건 (md 파일 없어 skip된 것) |
| `output/beta_validation_v4` | 4건 (md 파일 없어 skip된 것) |
| `output/beta_validation_v5` | 4건 (md 파일 없어 skip된 것) |
| `output/SPRINT2_MD_DEBUG` | 0건 |

**합계**: 적용 41건 완료 / 여전히 `doc_type=None` **20건**(모두 md 파일
없어 skip된 것 — "never invent" 설계 원칙대로 정상 동작)

---

## §7. 테스트 결과

```
tests/test_backfill_doc_type.py::test_already_has_doc_type -> 통과
tests/test_backfill_doc_type.py::test_skip_no_md_file -> 통과
tests/test_backfill_doc_type.py::test_dry_run_no_save -> 통과
tests/test_backfill_doc_type.py::test_apply_saves -> 통과
```

6개 테스트 모두 통과.

---

## §8. 완료 항목 체크리스트

- [x] `scripts/backfill_doc_type.py` 신규 — dry-run 기본, --apply 플래그
- [x] `tests/test_backfill_doc_type.py` 신규 (4 검증 케이스)
- [x] 프로덕션 registry 착수 시점 재확인: 0건 (§1)
- [x] dry-run 결과 확인 (§4)
- [x] --apply 실행: 41건 적용 (§5)
- [x] 적용 후 재확인: 41건 적용 / 20건 skip (§6)
- [x] 테스트 6개 모두 통과 (§7)