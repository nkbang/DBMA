# C1 Task Order 019 — 기존 등록 문서 doc_type 백필 스크립트

**상태**: 승인됨 — 구현 착수 가능 (2026-07-29, David 승인)
**우선순위**: **낮음(P3)** — 아래 §1의 실측 결과, 프로덕션 registry에는 백필
대상이 0건이다. 급한 버그 수정이 아니라 진단용 corpus 정리 + 향후 안전망
스크립트 작성 작업이다.
**선행 작업**: Task Order 017(스키마 필드 추가), Task Order 018(신규/재처리
문서부터 `doc_type` 실제 배선) — 둘 다 완료. 이번 작업은 **이미 등록된
문서**의 `doc_type=None`을 사후에 채우는 것만 다룬다.
**작성일**: 2026-07-29

---

## 1. 배경 — 실측 결과 (착수 전 반드시 확인할 것)

CUE가 착수 전 리포지토리 내 모든 `documents.json`을 직접 조회해 확인한
결과:

| registry 경로 | 총 문서 수 | `doc_type=None` |
|---|---|---|
| `data/제련완성본/registry/documents.json` **(config.yaml의 output_dir — 실제 프로덕션/대시보드가 읽는 registry)** | 78 | **0** |
| `output/beta_validation/registry/documents.json` | 12 | 12 |
| `output/beta_validation_v2/registry/documents.json` | 12 | 12 |
| `output/beta_validation_v3/registry/documents.json` | 12 | 12 |
| `output/beta_validation_v4/registry/documents.json` | 12 | 12 |
| `output/beta_validation_v5/registry/documents.json` | 12 | 12 |
| `output/SPRINT2_MD_DEBUG/registry/documents.json` | 1 | 1 |

**프로덕션 registry는 이미 78건 전부 `doc_type`이 채워져 있다**(`주석`
47/`조직신학` 11/`설교` 7/`기타` 7/`논문` 5/`사전` 1) — `created_at`이
2026-07-15~18로 Task Order 018(2026-07-29) 이전 문서인데도 값이 있는 걸
보면, `core/processing.py`의 자동 배선이 아니라 `ui/pages/dashboard.py`의
수동 설정 UI(503행)로 David가 이미 직접 분류해둔 것으로 보인다.

**결론**: 대시보드에서 실제로 보이는 "?" 문제는 이미 해소되어 있다(적어도
현재 프로덕션 registry에는). 백필이 실제로 필요한 곳은 `output/
beta_validation*`/`SPRINT2_MD_DEBUG` 같은 진단·canary용 registry(61건)
뿐이다 — 이들은 SPRINT33-D 등 청킹 실험에 쓰인 corpus로, 사용자가 일상적으로
보는 대시보드 대상이 아니다.

**착수 전 재확인 필수**: 위 표는 2026-07-29 시점 스냅샷이다. 착수 시 다시
한번 프로덕션 registry(`config.yaml`의 `output_dir` 기준)에 `doc_type=None`
문서가 실제로 생겼는지 확인할 것 — 만약 여전히 0건이면 이 Task Order는
beta_validation류 정리 작업으로만 진행하고, 그 이상으로 범위를 넓히지 말 것.

---

## 2. 구현 범위

### 2.1 신규 스크립트 — `scripts/backfill_doc_type.py`

```python
"""registry의 doc_type=None 레코드에 guess_doc_type()으로 값을 채운다.
core/processing.py의 정상 배선(Task Order 018)이 커버하지 못하는, 이미
등록된 과거 문서 전용 — dry-run 기본, --apply로만 실제 반영."""

import argparse
from pathlib import Path

from core.identity_registry import load_identity_registry, save_identity_registry
from core.document_identity import guess_doc_type


def backfill(registry_path: str, output_dir: str, apply: bool) -> None:
    registry = load_identity_registry(registry_path)
    changed = []
    skipped_no_md = []

    for doc_id, record in registry["documents"].items():
        if record.get("doc_type") is not None:
            continue  # [never invent 원칙] 이미 값이 있으면 건드리지 않음

        source_file = record.get("source_file", "")
        # [ADR-008/기존 관례] {output_dir}/{stem}_{ext}.md 명명 규칙
        # (scripts/shadow_boundary_analysis.py::_resolve_pdf와 동일 패턴)
        stem = Path(source_file).stem
        ext = Path(source_file).suffix.lstrip(".")
        md_path = Path(output_dir) / f"{stem}_{ext}.md"

        if not md_path.exists():
            skipped_no_md.append(doc_id)
            continue  # [never invent] 원문 없이 추측하지 않음

        content = md_path.read_text(encoding="utf-8")
        doc_type = guess_doc_type(content, source_file, record.get("title"))
        changed.append((doc_id, source_file, doc_type))
        if apply:
            record["doc_type"] = doc_type

    print(f"변경 대상: {len(changed)}건, md 파일 없어 건너뜀: {len(skipped_no_md)}건")
    for doc_id, source_file, doc_type in changed:
        print(f"  {doc_id[:12]}... {source_file} -> {doc_type}")

    if apply and changed:
        save_identity_registry(registry, registry_path)
        print(f"registry 저장 완료: {registry_path}")
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

위 코드는 뼈대 — 실제 구현 시 `core/identity_registry.py`/`core/document_
identity.py`의 정확한 함수 시그니처를 재확인하고 맞출 것.

### 2.2 적용 대상 (§1 실측 기준)

- `output/beta_validation/registry/documents.json` (output_dir: `output/beta_validation`)
- `output/beta_validation_v2/registry/documents.json`
- `output/beta_validation_v3/registry/documents.json`
- `output/beta_validation_v4/registry/documents.json`
- `output/beta_validation_v5/registry/documents.json`
- `output/SPRINT2_MD_DEBUG/registry/documents.json`

**프로덕션 registry(`data/제련완성본/`)는 착수 시점에 실제로 `None`이
있는 경우에만** 대상에 포함 — §1처럼 0건이면 손대지 않는다(빈 diff를
만들 이유 없음).

### 2.3 손대지 말 것

- `core/processing.py`, `core/document_context.py`, `core/identity_registry.py` —
  이미 Task Order 017/018에서 완료된 스키마·배선 코드, 이번엔 건드리지 않음
- `ui/pages/dashboard.py`의 수동 설정 UI — 그대로 유지, 이 스크립트는
  일괄 배치용 별도 도구
- 이미 `doc_type`이 있는 레코드 — 절대 덮어쓰지 않음(§2.1의 "이미 값이
  있으면 건드리지 않음" 그대로)

---

## 3. 실행 절차

1. **dry-run 먼저**: `python scripts/backfill_doc_type.py output/beta_validation/registry/documents.json output/beta_validation --apply` 없이 실행 — 변경 예정 목록만 출력
2. dry-run 결과를 사람이 훑어보고 이상한 분류(`guess_doc_type()`이 명백히
   틀린 값을 내는 경우)가 없는지 확인
3. 이상 없으면 `--apply`로 실제 반영 — beta_validation 5개 + SPRINT2_MD_DEBUG
   1개, 총 6개 registry 각각에 대해
4. **백업**: `--apply` 전에 대상 `documents.json`을 `.bak`으로 복사해둘 것
   (registry 직접 수정은 되돌리기 어려우므로)

---

## 4. 검증 계획

1. **단위 테스트** (`tests/test_backfill_doc_type.py` 신규):
   - `doc_type`이 이미 있는 레코드는 건드리지 않는지
   - md 파일이 없는 레코드는 건너뛰고 `skipped_no_md`에 기록되는지
   - dry-run(`apply=False`)일 때는 registry가 저장되지 않는지
   - `--apply` 시 실제로 `doc_type`이 채워지고 저장되는지
2. **실행 후 확인**: 6개 registry 각각 재실행해 `doc_type=None` 카운트가
   0이 됐는지(md 파일 없어 skip된 것 제외) 확인

---

## 5. 보고 형식

1. 스크립트 diff + 신규 테스트 diff
2. dry-run 결과(각 registry별 변경 예정 건수 + skip 건수)
3. `--apply` 실행 후 실제 반영 건수
4. 프로덕션 registry(`data/제련완성본/`)에 착수 시점 `doc_type=None`이
   있었는지/몇 건이었는지 재확인 결과 — §1과 달라졌으면 그 사실도 보고할 것

---

**다음 조치 없음** — 이 스크립트는 1회성 백필용이며, 향후 재발 방지는
이미 Task Order 018의 자동 배선이 담당한다.
