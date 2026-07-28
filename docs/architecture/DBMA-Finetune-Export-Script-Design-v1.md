---
title: DBMA Finetune Export Script Design v1
category: architecture
status: draft (design only — 구현 없음)
based_on:
  - docs/architecture/DBMA-Noise-Diff-Review-Script-Design-v1.md (§7 이월 항목)
  - docs/architecture/DBMA-Noise-Review-Approval-Persistence-Design-v1.md (승인 레지스트리 소비)
  - core/tsu_builder.py (write_manifest 패턴 재사용), core/noise_classifier.py
created: 2026-07-27
scope_modified: docs/architecture/ only (코드 미수정)
---

# DBMA Finetune Export Script Design v1

목적: 앞선 두 설계 문서가 이월한 마지막 조각 — **승인된 문서를 실제
파인튜닝 JSONL로 export**하는 스크립트를 설계한다. 세 문서(diff 리뷰 →
승인 저장 → export)로 "노이즈 제거 문서를 사람이 보고 승인하면 파인튜닝
데이터가 된다"는 전체 워크플로우가 완결된다. **코드는 작성하지 않는다.**

---

## 0. 이전 오류를 반복하지 않기 위한 전제

이전 C1 리뷰에서 확인된 오류(존재하지 않는 `TSUBuilder` 클래스, 잘못된
파일 구조 가정, 불필요한 재분류)를 반복하지 않도록, 이번 설계는 다음을
그대로 전제로 삼는다:

- TSU 데이터셋은 **청크 단위 flat JSONL**(`output/bench/tsu_dataset.jsonl`),
  레코드마다 `document_id`, `chunk_id`, `content`, `content_quality`
  (`noise_type`/`quality_score`/`section_type`) 보유. **재분류하지 않는다.**
- 승인 상태는 `output/reports/noise_review/review_registry.json`
  (전편 설계)에 `document_id` 키로 저장되어 있으며, `chunk_overrides`와
  `diff_report_version`(승인 시점 데이터셋 해시)을 포함한다.
- `core/tsu_builder.py::write_manifest()`가 이미 "생성 시점, 소스 해시,
  빌드 커밋을 기록하는" provenance 패턴을 확립해뒀다 — 이 스크립트도
  동일 패턴을 재사용한다(새 manifest 포맷을 발명하지 않는다).

---

## 1. 스크립트 개요

```text
scripts/export_finetune_dataset.py   ← 신규 (설계만, 미구현)

입력:
  output/bench/tsu_dataset.jsonl                    (TSU 레코드)
  output/reports/noise_review/review_registry.json  (승인 상태)

출력:
  output/finetune/{dataset_name}.jsonl   (파인튜닝용 데이터)
  output/finetune/{dataset_name}.manifest.json  (write_manifest 패턴)
```

**읽기 전용 원칙 유지**: TSU 데이터셋과 리뷰 레지스트리 둘 다 읽기만
한다. 이 스크립트가 두 입력 중 어느 것도 수정하지 않는다 — export는
새 산출물을 만드는 단방향 변환이다.

---

## 2. 문서 선정 로직 (누가 export 대상인가)

```text
review_registry.json의 각 document_id에 대해:

  review_status == "REJECTED"   → 제외
  review_status == "PENDING"    → 제외 (아직 아무도 안 봄)

  review_status == "APPROVED" 또는 "NEEDS_REVISION" (override 존재) 인 경우:
      1. diff_report_version(승인 시점 해시) vs 현재 tsu_dataset.jsonl 해시 비교
         (전편 설계 §4의 무효화 정책 그대로 적용)
      2. 불일치 → 제외 + "재검토 필요" 목록에 기록 (STALE_APPROVAL)
      3. 일치 → 다음 단계(§3)로 진행
```

이 로직은 새 판정 기준을 만들지 않고 전편 설계(승인 저장 문서 §4)가
이미 정한 무효화 정책을 그대로 소비한다.

---

## 3. 청크 필터링 및 재구성 (chunk_overrides 반영)

문서가 §2를 통과하면, 해당 문서의 TSU 청크들을 다음 규칙으로 재구성한다:

```text
for chunk in tsu_records[document_id] (chunk_id 순):
    override = review_record.chunk_overrides.get(chunk_id)

    if override is not None:
        action = override.override_action   # "KEEP" / "REMOVE" / "DOWNWEIGHT"
    else:
        # override 없으면 자동 분류 결과 그대로 사용
        action = "REMOVE" if chunk.content_quality.quality_score == 0.0 else "KEEP"

    if action == "REMOVE":
        skip (파인튜닝 텍스트에서 제외)
    else:
        포함, weight = chunk.content_quality.quality_score
                       (override가 DOWNWEIGHT면 0.3로 고정 — noise_classifier의
                        _QUALITY_SCORE_BY_POLICY["DOWNWEIGHT"]와 동일 값 재사용)
```

**핵심 설계 결정**: override가 없는 청크는 전편 설계(§0)에서 이미
결정한 대로 `quality_score == 0.0`을 REMOVE 상당으로 취급한다 — 이는
새 규칙이 아니라 diff 리뷰 스크립트(v1) §3-2에서 확정한 정책을 그대로
따르는 것이다. 세 스크립트가 동일한 판정 기준을 공유해야 "리뷰에서 본
내용"과 "실제 export된 내용"이 일치한다(그렇지 않으면 사람이 승인한
근거가 무효화됨).

---

## 4. 출력 형식 결정 (이전 C1 제안 수정)

이전 검증에서 C1이 제시한 3종 형식(`cleaned_sermons.jsonl`,
`noisy_vs_clean_pairs.jsonl`, `quality_weighted.jsonl`)과 HuggingFace
전용 필드는 **실제 코드 근거 없이 상상으로 만들어진 것**이었다. 이번
설계는 실제 존재하는 필드만으로 **단일 포맷**을 확정한다(불필요한
포맷 다양화는 프로젝트 원칙 "불필요하게 넓은 리팩터링 금지"에 위배):

```jsonl
{"document_id": "<document_id>", "text": "<재구성된 정제 텍스트>", "meta": {"source_file": "<source_file>", "chunk_ids": ["<chunk_id>", ...], "avg_quality": 0.91, "reviewer": "david", "reviewed_at": "2026-07-27T10:00:00", "override_count": 1}}
```

| 필드 | 출처 |
|---|---|
| `document_id`, `source_file` | TSU 레코드(§0)에서 그대로 |
| `text` | §3에서 재구성된 텍스트(포함된 청크만 이어붙임) |
| `chunk_ids` | 포함된 청크의 `chunk_id` 목록(추적성 — ADR-002 citation traceability 원칙 재적용) |
| `avg_quality` | 포함된 청크들의 `quality_score` 평균 |
| `reviewer`, `reviewed_at`, `override_count` | 리뷰 레지스트리(전편 설계)에서 그대로 — 감사 이력 |

**단일 포맷으로 확정하는 이유**: "노이즈 vs 정제 쌍(pairs)"이나 "가중치
학습용" 같은 다른 형식이 필요해지면, 이 기본 JSONL(추적 가능한 원자료)을
가진 상태에서 후처리 스크립트로 파생시키는 것이 원본을 두 번 재구성하는
것보다 안전하다(§6에서 후속 확장으로 분리).

---

## 5. Manifest (재현성 기록)

`core/tsu_builder.py::write_manifest()` 패턴을 그대로 재사용한다:

```json
{
  "generated_at": "2026-07-27T11:00:00",
  "record_count": 42,
  "source_tsu_dataset_sha256": "...",
  "source_review_registry_sha256": "...",
  "excluded_stale_approval_count": 2,
  "excluded_rejected_count": 3,
  "excluded_pending_count": 15,
  "exporter_script": "scripts/export_finetune_dataset.py",
  "build_commit": "<git rev-parse HEAD>"
}
```

**목적**: 나중에 "이 파인튜닝 데이터셋이 정확히 어느 시점의 어떤 승인
상태를 반영한 것인가"를 추적 가능하게 한다 — `CLAUDE.md`의 "작업은
반드시 추적 가능해야 한다" 원칙을 그대로 이 산출물에도 적용한다.

---

## 6. 이번 설계에서 다루지 않는 것

- **실제 코드 구현** — SPRINT 구현 단계로 이월.
- **HuggingFace/vLLM 등 특정 파인튜닝 프레임워크 어댑터** — 이전 검증에서
  지적했듯 이런 프레임워크별 포맷 변환은 이 export 스크립트의 책임이
  아니다. §4의 단일 JSONL을 원자료로 삼아 프레임워크별 후처리 스크립트를
  필요할 때 별도로 설계한다(YAGNI — 지금 요구사항에 없는 프레임워크를
  미리 지원하지 않는다).
- **noisy_vs_clean pairs / quality_weighted 등 파생 포맷** — §4에서
  이유를 밝힌 대로 원자료가 확정된 뒤 후속 파생 스크립트로 분리.
- **실제 파인튜닝 실행(학습 루프)** — DBMA는 RAG 시스템이며 파인튜닝
  실행 자체는 이번 조사·설계 전체의 범위 밖(이전 조사 §1에서 이미 확인:
  "DBMA에는 파인튜닝 관련 코드가 전혀 없음").

---

## 7. 전체 워크플로우 요약 (3개 설계 문서 연결)

```text
1. scripts/export_noise_review.py       (diff 리뷰 v1)
   TSU 데이터셋 → 원문/정제본 diff HTML 생성 (읽기 전용)
        │
        ▼ 사람이 HTML을 보고 판단
        │
2. scripts/record_noise_review.py       (승인 저장 v1)
   판단 결과 → review_registry.json에 저장 (APPROVED/REJECTED/NEEDS_REVISION
   + chunk_overrides + diff_report_version)
        │
        ▼
3. scripts/export_finetune_dataset.py   (이 문서)
   review_registry.json + tsu_dataset.jsonl → 파인튜닝 JSONL + manifest
```

세 스크립트 모두: (a) 기존 파일을 읽기 전용으로만 다루고, (b) 새 산출물만
생성하며, (c) `core/`의 기존 함수/패턴(atomic write, sha256 provenance,
quality_score 정책)을 재사용하고 새로 발명하지 않는다는 원칙을 공유한다.

---

*본 문서는 설계만 다루며 어떤 코드도 작성하지 않았다. `core/`, `scripts/`,
`tests/`, `config.yaml`은 수정하지 않았다.*
