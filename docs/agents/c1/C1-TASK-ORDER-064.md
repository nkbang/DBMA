# C1 Task Order 064 — 사이드카 메타데이터 설계 검토 재발송 (RQ-1, RQ-2)

- 발주: CUE · 일자: 2026-09-16
- 모드: **PLAN MODE 전용 — ACT MODE 금지. 구현하지 않는다** — 검토 대상은
  여전히 코드가 존재하지 않는 설계안이다
- 사용 모델: `dbma-planner-r1-q6:70b`(분석용)
- 성격: 개방형 설계 판단(Q&A) — 이전 선행 문서 재발송, 내용 변경 없음

## 배경 — 왜 재발송인가

`docs/DBMA_SIDECAR_METADATA_C1_REREQUEST_001.md`(2026-09-15)가 이미
발송됐으나 응답(`RESULT_002`)이 한 번도 도착하지 않았다. 2026-09-16
현재까지 `docs/agents/c1/`, `docs/`에 후속 문서가 없음을 확인했다.

**내용 재검증(2026-09-16, CUE):** 원 요청서가 인용한 모든 파일·라인
번호를 이 시점 코드로 다시 대조했다 — 그 사이 30여 건의 커밋이
`dev/dbma-engine`에 병합됐지만(다른 세션들의 NAE 리뷰 배치 등), 인용된
위치는 전부 그대로다:

| 파일 | 인용 라인 | 재확인 |
|---|---|---|
| `core/extractors.py` | 108(PDF 함수 시작)~190(HTML 함수 끝) | 일치 |
| `core/extractors.py` | 116, 117 (PDF `.strip() or None`) | 일치 |
| `core/extractors.py` | 129, 130 (DOCX) | 일치 |
| `core/extractors.py` | 150 (EPUB) | 일치 |
| `core/extractors.py` | 184, 189 (HTML) | 일치 |
| `core/identity_registry.py` | 163, 164 (`"title"`/`"author"` 키) | 일치 |
| `core/tsu_builder.py` | 382, 383 | 일치 |

**따라서 질문 내용을 바꾸지 않고 그대로 재발송한다** — 아래 RQ-1, RQ-2는
`DBMA_SIDECAR_METADATA_C1_REREQUEST_001.md`와 동일하다. 이번 Task Order는
이번 세션의 번호 체계(061~063)와 형식을 맞추기 위한 재포장일 뿐이다.

## 선행 문서 (읽는 순서)

1. `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_REQUEST_001.md` — 1차 요청서(설계 D-1~D-7)
2. `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_001.md` — C1 1차 결과(원문 보존)
3. `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_VERIFICATION_001.md` — CUE의 1차 오진 반박 근거
4. `docs/DBMA_SIDECAR_METADATA_C1_REREQUEST_001.md` — 재요청 원문(본 문서와 질문 동일)

## 사실 확정 — 재론하지 말 것

1차에서 최우선 조건으로 제시한 "내장 메타데이터가 빈 문자열이면 `None`이
아니라 사이드카가 못 채운다"는 성립하지 않는다. 빈 문자열 → `None` 강등은
이미 `core/extractors.py` 116, 117, 129, 130, 150, 184, 189행에
`.strip() or None`으로 전부 구현돼 있고, 공백 `<title>` + 빈 `author`
content HTML로 실증했을 때 `(None, None)`이 반환된다. 이 조건은 기각됐다.
원인은 저장소 오인이 아니라 **호출부(638행)만 읽고 함수 본문을 읽지 않은
것**이다.

## 답할 질문 2개

### RQ-1 — Metadata Model 변경 범위 판정

D-2의 3키 스키마(`title`/`author`/`source`)가 기존 Metadata Model
(`core/document_context.py::DocumentContext` 53, 54행,
`core/identity_registry.py` 163, 164행, `core/tsu_builder.py` 382,
383행)에 **필드를 추가하지 않고** 기존 `title`/`author`를 채우기만 하는
것이 맞는가? 그렇다면 이것은 "Metadata Model 변경"인가 "Model 무변경 +
새 데이터 소스 추가"인가? 후자라면 이번 C1 Review 트리거 자체가
과잉이었는지도 함께 판정하라.

**중요한 이유:** 이 검토를 발동시킨 트리거가 CLAUDE.md "C1 Review 요청
시점 — Metadata Model 변경"이다. RQ-1이 미해결이면 이 검토가 필요했는지,
향후 유사 변경에 C1 Review가 필요한지의 기준이 서지 않는다. 거버넌스
판단이므로 CUE가 자답하지 않는다.

**주의:** D-1(`.meta.json` 파일명 규약)은 검토 질문이 아니라 제안 설계
항목이다. 1차 답변은 D-1을 다뤘으므로 RQ-1의 답이 되지 않는다 — 다시
답하라.

### RQ-2 — 비어 있지 않은 쓰레기 내장 값 처리

**답변 전 `core/extractors.py` 108~190행 함수 본문을 반드시 읽을 것**
(1차 오진의 원인이 이 구간 미확인이었다).

빈 문자열이 아니라 **비어 있지 않은 쓰레기 내장 메타데이터**가 정확한
사이드카 값을 이기는 경우를 어떻게 다뤄야 하는가?

구체 사례:
- PDF docinfo `title` = `"Untitled"` / `"Microsoft Word - doc1.doc"` / `"untitled-1"`
- `author` = 제작 도구명(`"LuraDocument"`, `"Adobe Acrobat"`)
- mojibake(인코딩 깨짐 — 예: `"ë§¤íŠœ í’€"`)

이 값들은 `None`이 아니므로 D-3(내장 우선) 규칙상 사이드카를 이긴다.

1. D-3을 "내장이 비었거나 **신뢰 불가할 때** 사이드카"로 완화해야 하는가?
2. 완화한다면 "신뢰 불가" 판정 기준은 무엇이어야 하는가 — 블랙리스트
   (문자열 목록), 휴리스틱(길이·문자 구성), 아니면 판정하지 않고
   사이드카 우선으로 뒤집는가?
3. 완화하지 않는다면, 쓰레기 값이 그대로 인용에 노출되는 것을 감수하는
   근거는?

## 재검토 불필요 — 1차 결론 유지 (다시 답하지 말 것)

| 항목 | 상태 |
|---|---|
| Q3 (전사 ≠ 추론, M2-a 원칙 정합) | 수용 |
| Q5 (호출 위치 D-4) | 수용 — GREEN |
| Q7 (배포 파급, RAW 동일 디렉터리) | 수용 — GREEN |
| C2 (`source` 검증 가능 형식) | 수용 — 단 중첩 JSON 대신 `<제공처>\|<식별자>\|<필드>` 구분자 형식 채택 |
| Q4 (`metadata_source`) | 수용 — registry 무변경, TSU record 선택 필드로 한정 |
| C3 (doc_type 영향 목록 선행) | 수용 |
| 조건 C1 (빈 문자열 간극) | **기각** — 위 "사실 확정" 참고 |

## 요청 형식

- RQ-1, RQ-2 각각에 **파일·행 번호 근거**를 붙여 답할 것
- 추정치 금지. 확인하지 못한 것은 **"확인 불가"**로 명시
- 판정: 두 질문 종합 후 **GREEN / YELLOW(조건부) / RED**
- 산출물: `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_002.md`
- 결과 문서 상단에 `git rev-parse HEAD`, `git remote -v`,
  `git rev-parse --show-toplevel` 출력을 먼저 붙일 것 — 다른
  저장소/worktree면 즉시 중단하고 보고

## 게이트

RQ-1·RQ-2 회신 → CUE 대조 검증(§5.6 패턴: 질문 1:1 대응, 함수 본문 직접
확인) → 설계 확정 → HQ 승인 → 구현 착수(S3, 배포 파이프라인). Evidence
Before Promotion Rule에 따라 그 전까지 스텁·스키마·데이터를 포함한 어떤
선행 구현도 하지 않는다.
