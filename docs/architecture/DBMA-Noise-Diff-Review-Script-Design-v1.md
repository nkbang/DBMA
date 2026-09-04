---
title: DBMA Noise Diff Review Script Design v1
category: architecture
status: draft (design only — 구현 없음)
based_on:
  - core/noise_classifier.py, core/tsu_builder.py, core/config.py (읽기 전용 분석)
  - scripts/report_chunk_summary.py (컨벤션 참고)
  - 업계 조사: human-in-the-loop 데이터 큐레이션, diff/redline 리뷰 패턴
created: 2026-07-27
scope_modified: docs/architecture/ only (코드 미수정)
---

# DBMA Noise Diff Review Script Design v1

목적: "노이즈가 제거된 문서를 사람이 원문과 비교해 검토한 뒤, 승인된 것만
파인튜닝/고품질 데이터셋으로 확정한다"는 워크플로우를 실행 가능한 스크립트
설계로 구체화한다. 이전 조사(업계 관행: diff/redline 표시, 샘플링 기반 QA)와
DBMA 실제 코드(TSU 스키마, noise_classifier)를 근거로 한다. **코드는 작성하지
않는다** — 설계 문서다.

---

## 0. 설계 근거 (기존 코드 재확인)

이전 검증에서 확인한 사실을 그대로 전제로 삼는다:

- `core/noise_classifier.py::classify(text)` → `NoiseClassification(noise_type,
  policy, quality_score, section_type)`. `policy ∈ {"REMOVE", "PRESERVE",
  "DOWNWEIGHT", "NORMAL"}`.
- `core/tsu_builder.py::build_tsu_records()`가 만드는 TSU 레코드는 **청크 단위
  flat 구조**이며 이미 `content_quality = {"noise_type", "quality_score",
  "section_type"}` 필드를 갖는다(SPRINT28-B, 재분류 불필요). 단 `policy`는
  저장되지 않으므로, REMOVE 여부 판정에는 `quality_score == 0.0`(REMOVE의
  고정값, `core/noise_classifier.py`의 `_QUALITY_SCORE_BY_POLICY`) 또는 재분류
  중 하나를 선택해야 한다(§3-2에서 결정).
- 데이터셋 위치: `core/config.py::DEFAULT_TSU_DATASET_PATH`
  (`output/bench/tsu_dataset.jsonl`), 파일 하나에 레코드가 줄 단위(JSONL)로
  저장됨. 문서별 `*.json` 파일이 아니다(이전 검증에서 확인된 C1 오류를
  반복하지 않는다).
- 각 레코드는 `document_id`, `chunk_id`, `content`, `source_file`을 갖고
  있어 문서 단위로 그룹핑 가능하다.
- 컨벤션: `scripts/report_chunk_summary.py`가 이미 "registry/TSU를 읽기
  전용으로 읽어 `output/reports/`에 산출물을 쓰는" 패턴을 확립해뒀다 —
  이 신규 스크립트도 동일 패턴을 따른다(재정제·재청킹 없음, 순수 읽기+렌더링).

---

## 1. 스크립트 개요

```text
scripts/export_noise_review.py   ← 신규 (설계만, 미구현)

입력: output/bench/tsu_dataset.jsonl (또는 --tsu-path로 지정)
출력: output/reports/noise_review/{document_id}.html  (문서별 diff 리포트)
      output/reports/noise_review/index.html           (전체 목록 + 우선순위 정렬)
```

**읽기 전용 원칙**: 이 스크립트는 TSU 데이터셋과 원본 md/청크 파일을 읽기만
한다. `core/noise_classifier.py`를 재호출하지 않고 TSU 레코드에 이미 저장된
`content_quality`를 그대로 사용한다(§0). 노이즈 재분류, 재청킹, 원본 수정
전부 이 스크립트의 책임이 아니다.

---

## 2. 데이터 흐름

```text
output/bench/tsu_dataset.jsonl (청크 단위 flat JSONL)
        │
        ▼
[Group by document_id]
        │
        ▼
문서별 청크 리스트 (chunk_id 순 정렬)
        │
        ├── 원문 재구성: 모든 청크의 content를 순서대로 이어붙임 (RAW)
        │
        └── 정제본 재구성: content_quality.quality_score == 0.0(REMOVE 상당) 청크 제외 (CLEANED)
        │
        ▼
[Diff 계산] RAW vs CLEANED (라인 단위)
        │
        ▼
[우선순위 산정] §4 참고
        │
        ▼
HTML 리포트 렌더링 (문서별 1개 + index)
```

**주의**: TSU 청크의 `content`가 이미 `core/chunking_optimizer.py`로 청킹된
결과이므로, "원문 재구성"은 파일시스템의 원본 md/PDF가 아니라 **TSU가 참조하는
청크들을 이어붙인 근사 원문**이다. 진짜 원본과의 완전 일치를 보장하지 않는다
— 필요 시 `source_file` 필드로 원본 md 경로(`core/files.py` 스캔 대상)를
찾아 대조하는 것은 후속 확장(§7)으로 분리한다.

---

## 3. Diff/Redline 표시 설계

업계 조사(Draftable, Word 문서비교 관행)에서 확인한 두 가지 원칙을 반영한다.

### 3-1. Line Diff 기본, Word Diff는 선택적 확장

- 기본 뷰: 청크(문단) 단위로 RAW에는 있고 CLEANED에는 없는 줄을 **취소선 +
  회색 배경**으로 표시, 유지된 줄은 그대로 표시.
- 각 삭제된 줄 옆에 `noise_type`/`policy`/`quality_score`를 배지로 표시
  (예: `[PAGE_NUMBER · REMOVE · 0.0]`) — 왜 지워졌는지 사람이 바로 판단
  가능하게 한다.
- Word-level diff(정확히 어느 단어가 달라졌는지)는 REMOVE 정책은 줄 단위
  전체 삭제이므로 불필요 — DOWNWEIGHT처럼 "유지하되 표시만" 하는 경우에는
  별도 스타일(취소선 없이 옅은 노란 배경)로 구분해 word diff가 필요 없게
  설계한다.

### 3-2. REMOVE만 지우고 DOWNWEIGHT/PRESERVE는 시각적으로만 구분

```text
policy=REMOVE      → CLEANED에서 실제 제외, RAW 뷰에서는 취소선 표시
policy=DOWNWEIGHT  → CLEANED에 유지하되 옅은 배경(품질 낮음 경고)
policy=PRESERVE    → CLEANED에 유지, 원어 보존 배지(예: 히브리어/그리스어)
policy=NORMAL      → 스타일 없음(일반 본문)
```

이 결정은 이전 조사(§ADR 시리즈에서 확인한 `_POLICY_BY_TYPE`)를 그대로 따르며
새 정책을 만들지 않는다.

### 3-3. Cosmetic noise 숨김

업계 조사에서 확인한 "공백/대소문자 같은 cosmetic 차이는 diff에서 숨겨
진짜 판단 대상에 집중하게 한다"는 원칙을 반영한다 — 줄 비교 전에
`core/text_normalizer.py::reflow_wrapped_lines()`와 동일한 정규화를
diff 계산 직전에만(표시용으로만) 적용하고, 실제 CLEANED 산출물에는
영향을 주지 않는다.

---

## 4. 우선순위 산정 (전수 검토 방지)

업계 조사 결과("전수 검토가 아니라 샘플링 기반 QA")를 반영해, `index.html`은
모든 문서를 검토 대상으로 나열하지 않고 **우선순위 정렬**로 상위 N개만
"검토 필요"로 표시한다.

| 우선순위 신호 | 계산 | 근거 |
|---|---|---|
| DOWNWEIGHT 비율 | 문서 내 `policy=DOWNWEIGHT` 청크 수 / 전체 청크 수 | 경계선 판정(quality_score=0.3)이 많은 문서일수록 사람 판단이 유용 |
| REMOVE 비율 극단값 | REMOVE 청크 비율이 매우 높거나(>50%, 과다 제거 의심) 매우 낮은(0%, 필터 미작동 의심) 문서 | 두 극단 모두 오탐 가능성 신호 |
| 평균 quality_score | 문서 전체 평균이 0.5 미만 | 낮은 품질 문서 우선 검토 |

**전수 나열도 가능**: `--all` 플래그로 우선순위 필터를 끌 수 있게 하되,
기본값은 상위 20건(또는 `--top N`)만 "즉시 검토" 섹션에 노출하고 나머지는
접힌(collapsed) 목록으로 분리한다.

---

## 5. 사용자 액션과 산출물

리뷰 스크립트 자체는 **읽기 전용 리포트 생성기**이며, 승인/거부 액션을
저장하는 것은 이 설계 범위 밖이다(이유는 §7). 1차 구현 범위는:

```text
HTML 리포트 열람
  → 사람이 육안으로 diff 확인
  → (수동) 승인 목록을 별도 텍스트 파일에 document_id 나열
  → (후속 스크립트, 미설계) 승인 목록 기반 파인튜닝 JSONL export
```

**설계 원칙**: 이 스크립트는 "보여주기"까지만 책임진다 — 승인 상태 저장,
파인튜닝 데이터 export는 별도 스크립트(§7)로 분리한다(단일 책임 원칙,
`core/processing.py` vs `core/chunking_optimizer.py` 분리와 동일한 논리).

---

## 6. 인터페이스 초안 (스케치, 구현 아님)

```text
Usage:
    python scripts/export_noise_review.py [--tsu-path PATH] [--top N] [--all]

Options:
    --tsu-path PATH   TSU 데이터셋 경로 (기본: core.config.DEFAULT_TSU_DATASET_PATH)
    --top N           우선순위 상위 N개 문서만 "즉시 검토"로 표시 (기본: 20)
    --all             우선순위 필터 없이 전체 문서 리스트

출력:
    output/reports/noise_review/{document_id}.html
    output/reports/noise_review/index.html
```

`scripts/report_chunk_summary.py`와 동일하게 `argparse` + `core.config`의
경로 상수를 재사용하고, 신규 경로 하드코딩을 피한다.

---

## 7. 이번 설계에서 다루지 않는 것

- **승인 상태 영속화**(어떤 문서를 누가 승인했는지 저장) — 별도 설계 필요,
  `identity_registry.py`의 `pipeline_flags` 패턴을 확장할지, 별도 리뷰
  레지스트리를 새로 만들지 결정 필요.
- **파인튜닝 JSONL export 스크립트 자체** — 이전 검증(C1 리뷰)에서 지적된
  실제 TSU 스키마 기반으로 별도 설계 문서 필요. 이 문서는 "보여주는" 단계만
  다룬다.
- **원본 파일(md/PDF) 대조**(§2 주의사항) — TSU 청크 재구성이 아니라 진짜
  원본과의 diff가 필요한 경우 후속 확장.
- **PDF 출력 형식** — 사용자 질문이 "텍스트나 PDF 형태"를 언급했으나, 브라우저
  HTML이 diff 색상 표시(취소선, 배경색 배지)를 가장 저비용으로 구현 가능해
  1차 설계는 HTML로 한정한다. PDF는 HTML을 `wkhtmltopdf`/`weasyprint` 등으로
  변환하는 후속 단계로 분리 가능(추가 의존성 필요, 이번 설계 범위 밖).

---

## 부록: 참고한 업계 관행 요약

- Diff/redline 표시가 원문-정제본 대조의 표준(Draftable, MS Word 비교 관행)
- Line diff 기본 + word diff는 필요한 경우만(cosmetic noise는 숨김)
- 전수 검토가 아니라 저신뢰 구간 샘플링(Auto-Filter → Auto-Correct 2단계 패턴)
- 승인/거부 저장은 검토 UI와 분리된 별도 책임(Prodigy의 annotate/review
  recipe 분리와 동일한 논리)

---

*본 문서는 설계만 다루며 어떤 코드도 작성하지 않았다. `core/`, `scripts/`,
`tests/`, `config.yaml`은 수정하지 않았다.*
