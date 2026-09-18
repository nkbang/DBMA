# C1 재요청 001 — 사이드카 메타데이터 설계 검토 (미답변 2건)

- 요청자: CUE
- 일자: 2026-09-15
- 유형: **C1 Review 재요청** — 1차 검토의 미답변·오진 보정
- 선행 문서:
  - `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_REQUEST_001.md` (1차 요청서)
  - `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_001.md` (C1 1차 결과, 원문 보존)
  - `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_VERIFICATION_001.md` (CUE 대조 검증)

---

## 1. 재요청 사유

1차 검토(YELLOW)에서 두 가지 문제가 확인되었다.

| # | 문제 | 성격 |
|---|---|---|
| R-1 | 요청서 §3 **Q1에 답하지 않았다** — Q1(Metadata Model 변경 범위 판정) 자리에 D-1(확장자 충돌 방지)의 타당성을 답했다 | 미답변 |
| R-2 | **Q2의 논점이 바뀌었다** — "비어 있지 않은 쓰레기 내장 값" 질문에, 발생 불가능한 "빈 문자열" 시나리오로 답했다 | 오진 + 미답변 |

**R-2 관련 사실 확정(CUE 실증):** C1이 최우선 조건으로 제시한 "빈 문자열 → `None`
강등 필요"는 **이미 7개 지점 전부에 구현돼 있어 성립하지 않는다.**

```
core/extractors.py:116,117   (meta.get(...)  or "").strip() or None   # PDF
core/extractors.py:129,130   (props.title    or "").strip() or None   # DOCX
core/extractors.py:150       (str(value)     or "").strip() or None   # EPUB
core/extractors.py:184,189   soup.title.string.strip() or None        # HTML
```

공백 `<title>` + 빈 `author` content HTML로 호출 시 `(None, None)` 반환 확인.
C1이 인용한 행 번호(638, 624)는 실재하므로 저장소 오인은 아니며, **호출부만 읽고
함수 본문을 읽지 않은 것**이 원인이다. 이 조건은 기각되었다.

---

## 2. 재요청 질문 2건

### RQ-1 (= 1차 Q1 원문, 재요청)

> **Metadata Model 변경 범위 판정** — D-2의 3키 스키마(`title`/`author`/`source`)가
> 기존 Metadata Model(`core/document_context.py::DocumentContext`,
> `core/identity_registry.py:163-164`, `core/tsu_builder.py:382-383`)에
> **필드를 추가하지 않고** 기존 `title`/`author`를 채우기만 하는 것이 맞는가?
> 그렇다면 이것은 "Model 변경"인가 "Model 무변경 + 새 데이터 소스 추가"인가?
> 후자라면 C1 Review 트리거 자체가 과잉이었는지도 함께 판정 바란다.

**이 질문이 중요한 이유:** 본 검토를 발동시킨 트리거가 CLAUDE.md "C1 Review 요청
시점 — Metadata Model 변경"이다. RQ-1이 미해결이면 **이 검토가 필요했는지, 향후
유사 변경에 C1 Review가 필요한지**의 기준이 서지 않는다. 거버넌스 판단이므로
CUE가 자답하지 않는다.

**주의:** D-1(`.meta.json` 파일명 규약)은 검토 질문이 아니라 제안 설계 항목이다.
1차 답변은 D-1을 다뤘으므로 RQ-1의 답이 되지 않는다.

### RQ-2 (= 1차 Q2 잔여분)

빈 문자열이 아니라 **비어 있지 않은 쓰레기 내장 메타데이터**가 정확한 사이드카
값을 이기는 경우를 어떻게 다뤄야 하는가?

구체 사례:
- PDF docinfo `title` = `"Untitled"` / `"Microsoft Word - doc1.doc"` / `"untitled-1"`
- `author` = 제작 도구명 (`"LuraDocument"`, `"Adobe Acrobat"`)
- mojibake (인코딩 깨짐 — 예: `"ë§¤íŠœ í’€"`)

이 값들은 `None`이 아니므로 D-3(내장 우선) 규칙상 사이드카를 이긴다. 판정 요청:

1. D-3을 "내장이 비었거나 **신뢰 불가할 때** 사이드카"로 완화해야 하는가?
2. 완화한다면 "신뢰 불가" 판정 기준은 무엇이어야 하는가 — 블랙리스트(문자열 목록),
   휴리스틱(길이·문자 구성), 아니면 판정하지 않고 사이드카 우선으로 뒤집는가?
3. 완화하지 않는다면, 쓰레기 값이 그대로 인용에 노출되는 것을 감수하는 근거는?

**답변 전 필수:** `core/extractors.py` **108-190행 함수 본문**을 읽을 것.
1차 오진의 원인이 이 구간 미확인이었다.

---

## 3. 1차 결과 중 유지되는 항목 (재검토 불필요)

| 항목 | 상태 |
|---|---|
| Q3 (전사 ≠ 추론, M2-a 원칙 정합) | 수용 — 유효한 확인 |
| Q5 (호출 위치 D-4) | 수용 — GREEN |
| Q7 (배포 파급, RAW 동일 디렉터리) | 수용 — GREEN |
| C2 (`source` 검증 가능 형식) | 수용 — 단 중첩 JSON 대신 `<제공처>\|<식별자>\|<필드>` 구분자 형식 채택 |
| Q4 (`metadata_source`) | 수용 — registry 무변경, TSU record 선택 필드로 한정 |
| C3 (doc_type 영향 목록 선행) | 수용 |
| 조건 C1 (빈 문자열 간극) | **기각** — §1 참조 |

---

## 4. 요청 형식

- RQ-1, RQ-2 각각에 **파일·행 번호 근거**를 붙여 답할 것
- 추정치 금지. 확인하지 못한 것은 **"확인 불가"**로 명시
- 판정: 두 질문 종합 후 **GREEN / YELLOW(조건부) / RED**
- 산출물: `docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_002.md`
- **PLAN MODE 전용. ACT MODE 금지. 구현하지 않는다** — 검토 대상은 여전히
  코드가 존재하지 않는 설계안이다
- 결과 문서 상단에 `git rev-parse HEAD`, `git remote -v`,
  `git rev-parse --show-toplevel` 출력을 먼저 붙일 것

---

## 5. 게이트

RQ-1·RQ-2 회신 → 설계 확정 → HQ 승인 → 구현 착수.
Evidence Before Promotion Rule에 따라 그 전까지 스텁·스키마·데이터를 포함한
어떤 선행 구현도 하지 않는다.

---

## 6. C1 전달용 지시 문구 (붙여넣기)

```
C1, 사이드카 메타데이터 설계 검토의 재요청이다. 1차 검토에서 한 질문이 미답변이고
한 조건이 오진이었다. PLAN MODE로만 진행하고 ACT MODE는 금지한다. 구현하지 말 것 —
검토 대상은 여전히 코드가 존재하지 않는 설계안이다.

저장소: /Users/David/DBMA (branch dev/dbma-engine)
먼저 git rev-parse HEAD / git remote -v / git rev-parse --show-toplevel 을 실행해
그 출력을 결과 문서 맨 위에 붙여라. 다른 저장소나 worktree면 즉시 중단하고 보고할 것.

먼저 읽어라:
  docs/DBMA_SIDECAR_METADATA_C1_REREQUEST_001.md         ← 본 재요청서
  docs/DBMA_SIDECAR_METADATA_C1_REVIEW_VERIFICATION_001.md ← 1차 오진 반박 근거
  docs/DBMA_SIDECAR_METADATA_C1_REVIEW_REQUEST_001.md      ← 1차 요청서(설계 D-1~D-7)

[사실 확정 — 재론하지 말 것]
1차에서 최우선 조건으로 제시한 "내장 메타데이터가 빈 문자열이면 None이 아니라
사이드카가 못 채운다"는 성립하지 않는다. 요구한 빈 문자열 → None 강등은 이미
core/extractors.py 116,117,129,130,150,184,189행에 `.strip() or None`으로 전부
구현돼 있고, 공백 title + 빈 author content HTML로 실증했을 때 (None, None)이
반환된다. 이 조건은 기각되었다. 원인은 저장소 오인이 아니라 호출부(638행)만 읽고
함수 본문을 읽지 않은 것이다.

[답변할 질문 2개]

RQ-1. Metadata Model 변경 범위 판정.
  D-2의 3키 스키마(title/author/source)가 기존 Metadata Model에 필드를 추가하지
  않고 기존 title/author를 채우기만 하는 것이 맞는가? 대조할 곳:
    core/document_context.py (DocumentContext 필드 정의)
    core/identity_registry.py 163-164
    core/tsu_builder.py 382-383
  그렇다면 이것은 "Metadata Model 변경"인가, "Model 무변경 + 새 데이터 소스 추가"인가?
  후자라면 이번 C1 Review 트리거 자체가 과잉이었는지도 판정하라.
  ※ 1차에서 이 자리에 D-1(.meta.json 파일명 규약)의 타당성을 답했다. D-1은 검토
    질문이 아니라 제안 설계 항목이므로 RQ-1의 답이 아니다. 다시 답하라.

RQ-2. 비어 있지 않은 쓰레기 내장 값 처리.
  답변 전 core/extractors.py 108-190행 함수 본문을 반드시 읽어라.
  빈 문자열이 아니라 아래처럼 "값은 있으나 쓸모없는" 내장 메타데이터를 다룬다:
    title  = "Untitled" / "Microsoft Word - doc1.doc" / "untitled-1"
    author = "LuraDocument" / "Adobe Acrobat" (제작 도구명)
    mojibake (인코딩 깨짐)
  이 값들은 None이 아니라 D-3(내장 우선) 규칙상 정확한 사이드카 값을 이긴다.
  (1) D-3을 "내장이 비었거나 신뢰 불가할 때 사이드카"로 완화해야 하는가?
  (2) 완화한다면 "신뢰 불가" 판정 기준은 — 블랙리스트 / 휴리스틱 / 사이드카 우선 전환?
  (3) 완화하지 않는다면 쓰레기 값이 인용에 노출되는 것을 감수하는 근거는?

[형식]
각 답에 파일·행 번호 근거를 붙여라. 추정치를 쓰지 말고 확인 못 한 것은 "확인 불가"로
명시하라. 판정은 GREEN / YELLOW(조건부) / RED 중 하나.
결과를 docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_002.md 에 작성하라.

[재검토 불필요 — 1차 결론 유지]
Q3(전사≠추론), Q5(호출 위치), Q7(배포 파급) = 수용.
C2(source 형식) = 수용하되 중첩 JSON 대신 <제공처>|<식별자>|<필드> 구분자 형식 채택.
Q4(metadata_source) = 수용하되 registry 무변경, TSU record 선택 필드로 한정.
C3(doc_type 영향 목록 선행) = 수용.
```
