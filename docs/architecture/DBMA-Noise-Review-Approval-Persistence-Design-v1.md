---
title: DBMA Noise Review Approval Persistence Design v1
category: architecture
status: draft (design only — 구현 없음)
based_on:
  - docs/architecture/DBMA-Noise-Diff-Review-Script-Design-v1.md (§7 이월 항목)
  - core/identity_registry.py (스키마/atomic write 패턴 재사용)
  - core/config.py (경로 상수 컨벤션)
created: 2026-07-27
scope_modified: docs/architecture/ only (코드 미수정)
---

# DBMA Noise Review Approval Persistence Design v1

목적: `DBMA-Noise-Diff-Review-Script-Design-v1.md` §7이 범위 밖으로 명시적으로
이월한 "승인 상태 영속화"를 설계한다. **코드는 작성하지 않는다.**

---

## 0. 설계 원칙 — 왜 별도 파일인가

`core/identity_registry.py`(`output/registry/documents.json`)에 승인 필드를
직접 추가하는 방안도 검토했으나 **기각**한다:

- `identity_registry.py`는 **파이프라인 자동화 상태**(추출/청킹/색인 완료 여부)를
  소유한다 — `ingest_status`, `pipeline_flags` 전부 기계가 판정하는 값이다.
- 리뷰 승인은 **사람의 판단**이며 완전히 다른 관심사다. 두 개념을 같은
  레코드에 섞으면 "이 문서가 처리됐는가"와 "이 문서가 사람에게 승인됐는가"가
  뒤섞여, DocumentContext 설계(SPRINT16-C-1) 당시 확립한 "Does Not Own" 경계
  원칙(계산/판정 로직과 그 결과를 구분해서 소유)에 위배된다.
- 리뷰 레지스트리가 없어지거나 초기화되어도 처리 파이프라인 자체는 영향받지
  않아야 한다 — 반대로 처리 레지스트리가 재구축(REPROCESS)되어도 사람이
  이미 내린 승인 판단은 보존되어야 한다. 즉 **두 레지스트리는 독립적인
  생애주기를 가진다.**

따라서 신규 파일 `output/reports/noise_review/review_registry.json`을
별도로 둔다. `document_id`로 `identity_registry.py`의 레코드와 조인
가능하지만, 물리적으로는 분리된 저장소다.

---

## 1. Review Registry 스키마

`identity_registry.py`의 이미 검증된 패턴(schema_version, atomic write,
append-only 마이그레이션)을 그대로 재사용한다 — 새 저장 메커니즘을
발명하지 않는다.

```json
{
  "schema_version": "1.0",
  "created_at": "2026-07-27T10:00:00",
  "updated_at": "2026-07-27T10:00:00",
  "documents": {
    "<document_id>": {
      "document_id": "<document_id>",
      "review_status": "APPROVED",
      "reviewer": "david",
      "reviewed_at": "2026-07-27T10:00:00",
      "notes": "본문 노이즈 제거 적절, 8p 각주 오탐 1건 확인",
      "chunk_overrides": {
        "<chunk_id>": {
          "original_policy": "REMOVE",
          "override_action": "KEEP",
          "reason": "각주가 실제로는 성경 인용 본문 — 오탐"
        }
      },
      "diff_report_version": "sha256:abcd...(export_noise_review.py 실행 시점의 tsu_dataset.jsonl 해시)"
    }
  },
  "_meta": { "total_reviewed": 1, "approved": 1, "rejected": 0, "needs_revision": 0 }
}
```

### 필드 설명

| 필드 | 의미 | 근거 |
|---|---|---|
| `review_status` | `PENDING`/`APPROVED`/`REJECTED`/`NEEDS_REVISION` 중 하나 | 아래 §2 상태 머신 |
| `reviewer` | 검토자 식별자 (자유 문자열, 1인 운영 전제) | 다인 운영 확장 시 인증 체계는 범위 밖 |
| `chunk_overrides` | 특정 청크의 자동 판정을 사람이 뒤집은 기록 | §3에서 핵심 이유 설명 |
| `diff_report_version` | 승인이 어느 시점의 TSU 데이터셋 기준인지 해시로 고정 | §4 "데이터셋 갱신 시 무효화" 문제 대응 |

**append-only 원칙 준수**: `identity_registry.py::migrate_registry_schema()`와
동일하게, 스키마 확장 시 기존 필드를 변경하지 않고 신규 필드만 추가한다.

---

## 2. Review Status 상태 머신

```text
PENDING (기본값, 아직 검토 안 함)
   │
   ├──▶ APPROVED         (그대로 파인튜닝 후보로 사용 가능)
   │
   ├──▶ REJECTED          (이 문서 전체를 파인튜닝 데이터에서 제외)
   │
   └──▶ NEEDS_REVISION     (chunk_overrides가 1개 이상 있음 —
                             자동 정제 결과를 일부 수정해야 사용 가능)
```

`identity_registry.py::classify_ingest_decision()`의 B1~B7 패턴을 참고하되
그대로 복제하지 않는다 — 리뷰는 재시도(RETRY)/재처리(REPROCESS) 개념이
없다(사람이 한 번 내린 판단은 자동으로 되돌리지 않음). 대신 §4에서
"데이터셋이 바뀌면 무효화"라는 별도 메커니즘을 둔다.

---

## 3. chunk_overrides — 왜 문서 단위 승인만으로는 부족한가

diff 리뷰 스크립트(v1) 설계 시 실측 데이터(SPRINT27 전후 조사)에서
`policy=REMOVE`로 분류된 각주/헤더가 실제로는 성경 구절 인용을 포함하는
사례가 존재할 수 있음을 이미 인지했다(`ORIGINAL_LANGUAGE` 보호 로직이
`core/noise_classifier.py`에서 가장 먼저 체크되는 것도 같은 이유). 문서
단위로만 승인/거부하면 이런 **부분적 오탐**을 기록할 방법이 없다.

`chunk_overrides`는:
- 어떤 청크가 원래 어떤 정책으로 분류됐는지(`original_policy`)
- 사람이 그것을 어떻게 뒤집었는지(`override_action`: `KEEP`/`REMOVE`/`DOWNWEIGHT`)
- 왜 뒤집었는지(`reason`, 자유 텍스트)

를 기록한다. **이 override는 `core/noise_classifier.py`의 분류 로직 자체를
변경하지 않는다** — 저장만 될 뿐, `classify()` 함수는 그대로 두고 다음
파인튜닝 export 스크립트(별도 설계, §5)가 override를 최종 반영할 때만
사용한다.

**후속 가치(이번 설계 범위 밖, 기록만)**: `chunk_overrides`가 충분히
쌓이면 `noise_classifier.py`의 오탐 패턴을 정량적으로 파악하는 데
쓸 수 있다 — 예: "PDF 각주 형식에서 REMOVE→KEEP 오버라이드가 반복된다"는
신호. 이는 노이즈 분류기 개선을 위한 데이터이지, 이번 설계의 목표는 아니다.

---

## 4. 데이터셋 갱신과 승인의 관계 (무효화 처리)

**문제**: TSU 데이터셋(`output/bench/tsu_dataset.jsonl`)이 재생성되면
(예: `noise_classifier.py` 로직 변경, 원본 문서 재처리) 이미 승인해둔
문서의 diff 내용이 달라질 수 있다. 승인 당시 본 내용과 지금 내용이
다른데 `APPROVED` 상태가 그대로면 잘못된 승인이 파인튜닝 데이터에 섞인다.

**결정**: `diff_report_version` 필드(§1)로 승인 시점의 TSU 데이터셋
해시를 고정한다.
- 파인튜닝 export 스크립트(§5, 별도 설계)는 export 시점에 현재
  `tsu_dataset.jsonl` 해시와 각 레코드의 `diff_report_version`을 비교한다.
- 불일치하면 해당 문서는 **자동으로 제외**하고 "재검토 필요" 목록에 올린다
  (상태를 강제로 `PENDING`으로 되돌리지는 않는다 — 사람이 다시 볼 때까지
  마지막 승인 기록은 감사 이력으로 보존).
- 이 정책은 `identity_registry.py::classify_ingest_decision()`의
  B5/B6(`last_content_hash` 비교로 REPROCESS 판정)과 **동일한 아이디어를
  리뷰 레지스트리에 적용**한 것이다 — 새로운 개념을 만들지 않고 기존
  DBMA의 "콘텐츠 해시 기반 무효화" 패턴을 재사용한다.

---

## 5. 저장 메커니즘 (구현 시 재사용할 기존 함수)

신규 함수를 설계하지 않고, `identity_registry.py`에 이미 있는 패턴을
그대로 재사용할 것을 명시한다(SPRINT17 구현 시 참고):

| 기능 | 재사용할 기존 패턴 |
|---|---|
| 레지스트리 로드(없으면 빈 구조 생성) | `load_identity_registry()` / `_empty_registry()` 패턴 |
| atomic 저장(.tmp + os.replace) | `save_identity_registry()` 그대로 |
| 스키마 마이그레이션(append-only) | `migrate_registry_schema()` 패턴 |
| 콘텐츠 해시 기반 무효화 | `classify_ingest_decision()`의 B5/B6 판정 로직 참고 |

즉 `core/review_registry.py`(가칭, 신규 파일이나 함수 시그니처는
`identity_registry.py`를 그대로 본뜸)로 설계하면, 기존 코드 검증
자산(atomic write의 안전성 등)을 그대로 물려받는다.

---

## 6. 승인 액션을 기록하는 방법 (CLI, 1차 범위)

v1 설계(§5)에서 diff 리뷰 스크립트는 정적 HTML만 생성한다고 결정했다.
승인 액션 자체는 별도 CLI 스크립트로 분리한다(단일 책임 유지):

```text
scripts/record_noise_review.py   ← 신규 (설계만, 미구현)

Usage:
    python scripts/record_noise_review.py <document_id> --status APPROVED [--reviewer NAME] [--notes TEXT]
    python scripts/record_noise_review.py <document_id> --status NEEDS_REVISION \
        --override <chunk_id>:KEEP:"각주가 실제 성경 인용문"
```

**웹 폼(클릭으로 승인)은 이번 설계 범위 밖**이다 — 1인 운영 규모에서는
CLI가 충분하고, `dbma.py`류의 새로운 병행 UI를 또 만들지 않기 위해
(ADR-001의 "One Retrieval Engine" 원칙과 같은 이유로 "새 병행 UI를
늘리지 않는다"는 태도를 유지) 의도적으로 최소 구현을 택한다. Streamlit
기반 승인 UI가 필요해지면 `ui/pages/` 패턴을 따르는 별도 설계로 분리한다.

---

## 7. 이번 설계에서 다루지 않는 것

- `core/review_registry.py` 실제 코드 구현 (SPRINT 구현 단계)
- 다인 검토자 인증/권한 체계 (1인 운영 전제, 필요 시 별도 설계)
- 승인 이력 기반 노이즈 분류기 개선 루프(§3 "후속 가치") — 데이터가
  쌓인 뒤 별도 분석 스프린트로 분리
- Streamlit 기반 클릭형 승인 UI (§6)
- 파인튜닝 JSONL export 스크립트 자체 — 이 문서는 승인 **저장**만 다루며,
  승인된 문서를 실제로 어떻게 export하는지는 v1 §7이 이미 이월한 별도
  설계 대상

---

*본 문서는 설계만 다루며 어떤 코드도 작성하지 않았다. `core/`, `scripts/`,
`tests/`, `config.yaml`은 수정하지 않았다.*
