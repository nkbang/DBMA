# NAE Human Review Governance v1 (Design Only)

작성일: 2026-08-13
성격: Architecture/Governance 설계 — 776건 실제 판정, TSU 원본 수정,
Production/Qdrant 변경, Gold Standard 승격, ADR-021 pipeline 수정 전부
수행하지 않음.
전제: `docs/NAE_HUMAN_REVIEW_DISPOSITION_SCHEMA_v1.md`,
`docs/NAE_HUMAN_REVIEW_WORKFLOW_v1.md`.

---

## 1. 핵심 Governance 원칙

```
Original TSU
    │
    │ immutable — 이 설계의 어떤 절차도 원본 TSU 필드를 직접 쓰지 않는다
    ▼
Human Review Record (append-only)
    ├── disposition
    ├── reason
    ├── reviewer
    ├── evidence
    ├── timestamp
    └── review provenance
```

원본 TSU immutability는 ADR-020(`NAE/pipeline/ingest/state.py`가
Production TSU 파일과 완전히 분리된 상태 저장소를 쓰는 것)과 동일한
설계 원칙의 반복 적용이다 — 처리 상태(ADR-020)든 사람의 판정(본
설계)이든, Production TSU 스키마에 필드를 추가하지 않고 항상 별도
저장소에 기록한다.

## 2. Human Review 결과와 Production Admission의 분리 (재확인)

`docs/NAE_HUMAN_REVIEW_WORKFLOW_v1.md` §5의 파이프라인을 governance
관점에서 재확인한다:

```
Generated TSU → Human Review → Disposition → QA/Adjudication → Admission Decision → Production
```

이 분리가 지켜져야 하는 이유: Disposition record는 **의견의 기록**
이고, Admission은 **Production 상태를 바꾸는 행위**다. 두 가지를
합치면 "사람이 ACCEPT라고 썼다"는 사실과 "TSU가 실제로 verified로
승격됐다"는 사실을 구분할 수 없게 되어, 감사 시 "이 TSU가 언제
Production에 반영됐는가"라는 질문에 답할 수 없다. 별도 단계로
분리하면 두 시점(판정 시점 vs 반영 시점)이 항상 서로 다른 record에
남는다.

## 3. Evidence Model

### 3.1 원칙

Disposition record는 evidence를 **참조(reference)**로만 연결한다 —
원본 artifact(원문 페이지 이미지, TSU 전문, OCR 원본 등)를 record
안에 복제 저장하지 않는다. 이는 다음을 방지하기 위함:

- Evidence 원본이 갱신될 때(예: 원문 재스캔) record 내 사본이
  stale해지는 문제
- Disposition record의 크기가 원본 데이터 크기에 종속되는 문제
- 동일 evidence를 여러 record가 각자 복제해 저장 공간과 정합성
  부담이 커지는 문제

### 3.2 Evidence 종류와 참조 방식

| Evidence 종류 | 참조 방식 |
|---|---|
| Source page | `source_id` + page 번호(원문 canonical text 내 위치, `NAE/corpus/canonical/`의 기존 구조 재사용) |
| TSU text | `tsu_id`(TSU 레코드 자체가 evidence — 항상 Production TSU 파일을 통해 재조회) |
| Metadata | `tsu_id` + 필드명(예: `tsu_id=TSU-0000123, field=doctrine`) |
| OCR evidence | `source_id` + canonical 산출물 경로(`NAE/corpus/canonical/<identifier>/canonical.json`) 참조 |
| Source identifier | `source_id`(기존 `resources/theological_sources/*/source_manifest.yaml` 1차 키 재사용) |
| External authority | URL 또는 문헌 인용(자유 텍스트, 예: 특정 신학 사전/주석) |
| Reviewer note | disposition record의 `review_note` 필드 자체(참조가 아니라 직접 포함 — 사람이 작성한 판단 근거이므로 원본이 곧 이 필드) |

`evidence_refs` 필드(Disposition Schema §3)는 위 표의 참조 형식을
`{"type": "...", "ref": "..."}` 객체 배열로 담는다(§ JSON Schema
초안 참고).

## 4. Auditability

### 4.1 "누가 이 TSU를 언제 어떤 근거로 어떤 disposition으로 판정했는가?"

`tsu_id`로 disposition record를 조회하면 `reviewer_id` +
`reviewed_at` + `disposition` + `reason_code` + `evidence_refs`가
전부 하나의 record에 함께 있다 — 단일 조회로 답변 가능.

### 4.2 "이후 판정이 변경되었다면 누가 무엇을 왜 변경했는가?"

`supersedes_review_id` 체인을 따라가면 이전 record들이 전부
보존되어 있다(append-only, §5 Disposition Schema). 각 record는
독립적으로 `reviewer_id`/`reviewed_at`/`review_note`를 가지므로
"누가, 언제, 왜 바꿨는가"가 체인의 각 링크에 기록된다. 변경
자체는 새 record 생성으로만 표현되며, 기존 record를 덮어쓰는
경로는 스키마상 존재하지 않는다(어떤 필드도 record 생성 후
in-place 수정을 허용하지 않음 — Disposition Schema §3 "append-only
원칙 적용 방식" 참고).

### 4.3 Provenance Log (record 자체의 상태 전이 이력)

Disposition Schema §3에서 유일하게 시스템이 갱신 가능하다고 표시한
필드는 record의 `review_status`(UNREVIEWED~FINALIZED)다. 이 전이
자체도 감사 가능해야 하므로, 각 전이를 별도의 append-only provenance
로그(개념: `{review_id, from_status, to_status, transitioned_by,
transitioned_at}`)에 기록하는 것을 governance 요구사항으로 둔다 —
구체적 저장 형식(파일/DB)은 구현 단계에서 결정.

## 5. Reviewer Disagreement 처리

`docs/NAE_HUMAN_REVIEW_WORKFLOW_v1.md` §4 Adjudication 절차를
그대로 governance 요구사항으로 채택한다. 요지: 상충하는 두 원본
판정은 절대 삭제되지 않고, adjudicator의 최종 판정이 **세 번째
record**로 추가되어 앞의 두 record를 `supersedes` 관계로 참조한다.

## 6. Gold Standard 승격 근거 보존

이번 설계는 Gold Standard 승격 절차 자체를 정의하지 않는다(작업
명령서 §2 범위 제한 — Gold Standard 승격은 이번 범위 밖). 다만
Acceptance Criteria #10("향후 Gold Standard로 승격할 근거를
보존하는가")에 답하기 위해, 다음이 이미 스키마상 보존됨을 확인한다:

- `disposition=ACCEPT` + `evidence_refs`가 충실한 record는 그 자체로
  "사람이 특정 근거를 들어 승인했다"는 근거가 되어, 향후 별도
  절차가 이 record 집합에서 Gold Standard 후보를 선별하는 입력으로
  사용할 수 있다.
- `ACCEPT_WITH_CORRECTION`의 `correction_payload`는 "원래 상태에서
  무엇이 왜 고쳐졌는가"를 보존하므로, Gold Standard가 "수정 이력이
  있는 항목"과 "수정 없이 승인된 항목"을 구분해야 할 경우 그대로
  활용 가능하다.
- Adjudication을 거친 record는 `final_disposition` +
  `adjudicator_id`로 "복수 검토를 거쳐 확정됨"을 표시하므로, Gold
  Standard가 더 높은 신뢰도 등급을 부여할 근거로 쓸 수 있다.

## 7. 기존 구조와의 경계 요약

| 기존 구조 | 관계 |
|---|---|
| `NAE/pipeline/tsu/review_gate.py` | 무수정. Embedding 진입 게이트는 여전히 `review_status="verified"` 하나만 본다 — 본 설계는 이 게이트의 상류에서 작동 |
| `NAE/pipeline/tsu/review_promotion.py` | 무수정. Admission 단계(§2)에서 FINALIZED disposition을 입력으로 호출하는 것으로 설계하되, 실제 배선은 범위 밖 |
| `NAE/review/human/schema.py::MAX_PENDING_REVIEW=100` | 무수정. Workflow §2/§3의 배치 크기 제약으로 그대로 재사용 |
| `docs/NAE_TSU_REVIEW_WORKFLOW_DESIGN_001.md`(Pilot 001 Gate 설계) | 본 설계는 그 상위 확장 — Pilot 001의 10건은 이미 `verified`이므로 본 워크플로우의 776건 대상에서 제외됨(중복 판정 없음) |
| ADR-020 (`NAE/pipeline/ingest/`) | 무수정. Admission 이후 `review_status="verified"`가 된 TSU만 여전히 ADR-020 incremental pipeline이 처리 |
| ADR-021 (`NAE/pipeline/registration/`) | 무수정. 완전히 다른 계층(신규 source 등록) — 본 설계와 직접 상호작용 없음 |

## 8. Acceptance Criteria — 응답

1. **하나의 TSU가 어떤 상태에 있는가?** → `tsu_id`로 최신(가장 큰
   `supersedes` 체인의 끝) disposition record를 조회하면
   `review_status`(UNREVIEWED~FINALIZED)로 즉시 확인 가능.
2. **왜 해당 disposition을 받았는가?** → 같은 record의
   `reason_code` + `review_note` + `evidence_refs`.
3. **누가 판정했는가?** → `reviewer_id`(또는 Adjudication을 거쳤다면
   `adjudicator_id`).
4. **어떤 evidence를 사용했는가?** → `evidence_refs`(§3 Evidence
   Model의 참조 형식).
5. **판정을 다시 변경할 수 있는가?** → 가능. 단, 기존 record를
   수정하지 않고 `supersedes_review_id`로 연결된 새 record를
   생성하는 방식으로만(§4.2).
6. **변경 이력을 보존하는가?** → 보존. `supersedes` 체인 전체가
   append-only로 남고, 상태 전이는 별도 provenance 로그로 추가
   기록(§4.3).
7. **reviewer disagreement를 어떻게 처리하는가?** → Adjudication
   절차(Workflow §4) — 상충 자동 감지 → `ADJUDICATION_REQUIRED` →
   adjudicator의 `final_disposition`이 새 record로 추가, 원본 두
   record는 보존.
8. **Human Review 결과와 Production admission을 어떻게
   분리하는가?** → §2의 5단계 파이프라인(Generated → Human Review →
   Disposition → QA/Adjudication → Admission Decision → Production).
   Admission은 별도 명시적 단계이며 FINALIZED 상태만으로는 Production이
   변경되지 않는다.
9. **776건을 batch review할 수 있는가?** → 가능. Workflow §3/§6 —
   `MAX_PENDING_REVIEW=100` 준수 하에 8개 배치로 분할 처리하는
   구조를 이미 설계(실행은 범위 밖).
10. **향후 Gold Standard로 승격할 근거를 보존하는가?** → §6에서
    확인 — evidence_refs/correction_payload/adjudication 필드가
    선별 근거로 재사용 가능하도록 보존됨(승격 절차 자체는 미정의).

## 9. 관련 문서

- `docs/NAE_HUMAN_REVIEW_DISPOSITION_SCHEMA_v1.md`
- `docs/NAE_HUMAN_REVIEW_WORKFLOW_v1.md`
- `docs/schemas/nae_human_review_disposition.schema.json`
