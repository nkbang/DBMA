# NAE Pilot Annotation Template

작성일: 2026-07-31
목적: 첫 Baptist 문서 수동 검증(Pilot annotation)용 템플릿. NAE_METADATA_POLICY_v1.md §2(baptist_theme "Pilot annotation 후 자동화")의 실행 도구.
이 템플릿은 양식만 정의하며, 실제 문서에 대한 채움(annotation 실행)은 별도 승인 후 진행한다.

## 사용 방식

- 문서 1건당 이 템플릿 1개 인스턴스를 채운다 (document-level 필드 + 대표 chunk 예시 1~3개)
- 사람이 원문을 읽고 직접 판단하여 채운다 — 자동 생성/추론 금지
- 채운 결과는 향후 `baptist_theme`/`doctrine_category` 자동 태깅 로직의 학습/검증 기준(gold standard)으로 활용 예정

## 템플릿

```yaml
# --- Document-level (theological_position은 document당 1회, chunk가 상속) ---
source: ""              # 원문 제목 (예: "New Hampshire Baptist Confession (1833)")
genre: []                # content_genre, multi-value array (예: ["confession"])
theological_position: "" # NAE_SOURCE_SCHEMA_v1.md 제안 enum 중 택1 (미확정 목록, 주석 참고)
provenance:
  author: ""
  publication_year: null
  copyright_status: ""   # public_domain / licensed / unknown
  denomination_context: "" # optional, 서술형

# --- Chunk-level 예시 (대표 chunk 1~3개, chunk마다 반복) ---
chunk_examples:
  - chunk_excerpt: ""    # 원문 발췌 (짧게, 인용 목적)
    doctrine_category: [] # controlled vocabulary 예정 — 현재는 자유 텍스트로 임시 기록, 어휘집 확정 후 정규화
    baptist_theme: []     # 자유 텍스트 임시 기록 (예: ["침례_예식", "회중_자치"])
    notes: ""             # 판단 근거나 애매한 지점 메모
```

## 필드 설명

| 필드 | 설명 |
|---|---|
| `source` | 원문 제목, NAE_SOURCE_SCHEMA_v1.md `title`과 동일 개념 |
| `genre` | `content_genre` — NAE_SOURCE_TYPE_MODEL_v1.md/NAE_METADATA_POLICY_v1.md §5 기준 8개 값 중 해당하는 것(복수 가능) |
| `theological_position` | document-level, chunk가 상속 — NAE_METADATA_POLICY_v1.md §1 정책 반영 |
| `doctrine_category` | chunk-level, controlled vocabulary 예정(현재 미확정이므로 자유 텍스트로 임시 기록) |
| `baptist_theme` | chunk-level, 기존 TSU 필드 재사용 대상 — Pilot에서는 사람이 직접 판단해 채움 |
| `provenance` | 출처 추적 정보 — `source_provenance`(기존 TSU 필드)와 `nae_metadata`(copyright_status 등)에 최종 매핑될 예정 |

## Pilot 대상 우선순위

STEP3_SAMPLE_DOCUMENT_SPEC.md 기준 1순위: New Hampshire Baptist Confession (1833)

## 주의

- 이 템플릿으로 실제 annotation을 수행하려면 원문 확보(다운로드)가 선행되어야 하며, 이는 별도 승인 대상
- controlled vocabulary(`doctrine_category` 어휘집)가 아직 없으므로, Pilot 단계에서는 자유 텍스트로 기록하고 이후 여러 문서의 결과를 모아 어휘집을 역으로 도출하는 상향식(bottom-up) 접근을 권장
