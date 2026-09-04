// deno-fmt-ignore-file
# C1 Task Order 007 — Legacy Artifact 정리(항목5) + Logos 인제스트 실사용 준비(항목6)

발급: CUE (2026-07-22)
대상: C1 (Cline 작업창 #1)
성격: **두 개의 독립 작업.** 항목5는 실행 가능(아래 실측 근거 참고),
항목6은 실제 Logos 자료가 아직 없어 "준비"만 한다 — 가짜 데이터를
만들어 넣지 말 것.

---

## 항목5 — Legacy Artifact 정리

### CUE가 먼저 확인한 사실 (2026-07-22, 직접 대조 검증)

```
output/registry/documents.json  — 13,425 bytes, mtime 2026-07-14,
  문서 12건. 현재 실제 registry(data/제련완성본/registry/documents.json,
  76건, 오늘자 갱신)와 완전히 다른 stale snapshot.

output/baseline/*  — benchmark_results.csv, config.yaml.snapshot,
  processing_results.md, dbma.py.snapshot. 전부 mtime 2026-07-14 동일
  묶음. dbma.py는 이미 archive/legacy/로 이동된 legacy 진입점이므로
  이 스냅샷 자체가 legacy 시절 기록.

output_sav/  — 2.5MB, mtime 2026-07-14. output/registry, output/baseline
  과 거의 동일한 내용을 통째로 복제한 백업 폴더로 보임(bench/,
  baseline/, registry/, .batch_state.json, SPRINT5_ENGINEERING_
  VALIDATION/ 등 포함). 코드 어디에서도 참조되지 않음(core/scripts/
  ui/tests 전체 grep 결과 0건).
```

**core/identity_registry.py:6-11 자체가 이미 이 정확한 문제를 문서화해
뒀다**: "Multiple stale 'output/registry/documents.json' snapshots
exist on disk from before output_dir was repointed to '데이터/제련완성본';
treat any hardcoded 'output/registry/...' path as suspect."

### ⚠️ 이번에 새로 발견한 활성 버그 (정리보다 먼저 고쳐야 함)

`scripts/classify_documents_from_frontmatter.py:118`이 **지금도**
`Path("output/registry/documents.json")`(위 stale 12건짜리)을
하드코딩 참조하고 있다. 같은 파일 124행은 `Path("data/raw")`(소문자)도
하드코딩 — 실제 디렉터리는 `data/RAW`(대문자, `core.config.
DEFAULT_RAW_DIR`)다. 이 스크립트는 바로 어제(`48aaa9b`) 오타 수정으로
손댄, **현재도 쓰이고 있는 활성 스크립트**다. 즉 output/registry/를
그냥 지우면 이 스크립트가 다음 실행 때 "registry 파일을 찾을 수 없음"
으로 조용히 실패하거나(파일이 없으면 그렇게 됨, 118-120행), 혹시
누군가 stale 파일을 재생성해 두면 12건짜리 잘못된 데이터로 다시
분류를 실행하는 사고가 재발할 수 있다.

### 요구 작업 (순서 중요 — 반드시 이 순서로)

1. **먼저** `scripts/classify_documents_from_frontmatter.py`를 고쳐라:
   - `Path("output/registry/documents.json")` → `core.config.DEFAULT_REGISTRY_PATH` 사용
   - `Path("data/raw")` → `core.config.DEFAULT_RAW_DIR` 사용
   - import 패턴은 `scripts/ingest_logos_export.py`(신규, 이미 이 방식으로
     작성됨)를 참고할 것 — `from core.config import DEFAULT_REGISTRY_PATH,
     DEFAULT_RAW_DIR` 형태. (주의: `scripts/check_raw_only_originals.py`는
     `Path("data/RAW")`/`Path("data/제련완성본")`을 하드코딩하는 **구식
     패턴**이니 참고하지 말 것 — 그 스크립트 자체도 잠재적 개선 대상이지만
     이번 Task Order 범위 밖이다.)
   - 새 경로 상수를 만들지 말 것 — `core.config`에 이미 있는 것만 재사용.
   - 수정 후 실제로 한 번 실행해서 정상적으로 76건을 읽는지 확인하고
     결과를 캡처해 보고할 것.
2. **그 다음** `output/registry/`, `output/baseline/`, `output_sav/`를
   삭제가 아니라 `backups/legacy_artifact_cleanup_{YYYYMMDD}/`로
   **이동(move)**하라 — 이번 정리가 잘못됐을 경우 되돌릴 수 있어야 한다.
   완전 삭제는 이번 Task Order 범위가 아니다.
3. 이동 후 `scripts/classify_documents_from_frontmatter.py`를 다시 한번
   실행해 정상 동작을 재확인하라(1번에서 이미 고쳤으므로 이동 후에도
   문제없어야 한다 — 이게 이 순서로 진행해야 하는 이유다).

### 산출물 요구사항
- 코드 diff: `scripts/classify_documents_from_frontmatter.py`만
  (다른 파일 무접촉)
- 실행 로그: 수정 전(기존 stale 경로로 12건 읽음 확인) → 수정 후(올바른
  경로로 76건 읽음 확인) → 이동 후 재실행(76건 유지 확인) 3단계 캡처
- **이동 대상 파일 목록을 실행 전에 먼저 출력하는 dry-run이 기본**이어야
  한다(이 저장소의 `scripts/cleanup_duplicate_outputs.py` 관례와 동일).
  실제 이동은 `--execute` 플래그로만.

---

## 항목6 — Logos 인제스트 실사용 준비 (실행 아님, 준비만)

`scripts/ingest_logos_export.py`는 이미 구현·검증 완료 상태다(CUE가
합성 데이터로 직접 실행해 registry 등록 → TSU 빌드까지 전 구간 확인함).
**실제 Logos Clippings 파일이나 manifest는 아직 없다** — 이 항목에서
C1이 가짜 신학 콘텐츠를 만들어 채우는 것은 금지한다(근거 없는 데이터
생성 금지 원칙).

### 요구 작업 (준비 작업만)
1. `core/config.py`의 `DEFAULT_LOGOS_INBOX_DIR`/`DEFAULT_LOGOS_OUTPUT_DIR`
   경로가 실제로 디스크에 존재하는지 확인하고, 없으면 빈 디렉터리로
   생성만 하라(`.gitkeep` 등으로 git에 잡히게).
2. `data/manifests/logos_manifest.example.json` 같은 이름으로, 사용자가
   실제 Logos 자료를 넣을 때 그대로 복사해서 채울 수 있는 **manifest
   템플릿 파일**을 만들어라. 내용은
   `scripts/ingest_logos_export.py`의 docstring에 이미 있는 예시
   구조(export_filename/title/author/resource_type/language/
   logos_location/rights/export_method/source_tier/review_status)를
   그대로 쓰되, 값은 전부 `"<채워넣으세요>"` 같은 placeholder로 — 실제
   신학 서지 정보를 지어내지 말 것.
3. `.gitignore` 확인 결과 `data/`가 이미 통째로 제외되어 있어
   `data/inbox/`는 별도 추가가 필요 없다(확인만 하고 넘어갈 것 — 이미
   커버됨). 단, `manifest.example.json`을 `data/manifests/` 밖(예:
   `scripts/` 옆이나 `docs/`)에 두고 싶다면 그 경로가 `.gitignore`에
   안 걸리는지만 확인.

### 산출물 요구사항
- 신규 파일: 빈 디렉터리 2개(.gitkeep), manifest 템플릿 1개
- **코드 로직 변경 없음** — `scripts/ingest_logos_export.py` 자체는
  이미 검증된 상태이므로 이번엔 건드리지 않는다.

---

## 공통 제약 (변경 없음, 재확인)

- 항목5의 실제 이동(`--execute`)은 사용자의 명시적 확인 후에만 CUE가
  승인한다. dry-run 결과와 diff까지만 먼저 제출하라.
- 항목6은 정의상 승인이 필요 없다(가역적, 저위험 준비 작업) — 다만
  가짜 신학 콘텐츠 생성 금지는 예외 없이 지킨다.
