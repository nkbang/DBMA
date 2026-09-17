# 사이드카 메타데이터 — 설계 확정본 v2 (C1 Review 종결)

- 작성: CUE · 일자: 2026-09-17
- 성격: **설계 확정 — 구현 전, HQ 승인 대기**
- 선행: `DBMA_SIDECAR_METADATA_C1_REVIEW_REQUEST_001.md`(1차, D-1~D-7),
  `..._RESULT_001/002/003.md`(C1 3라운드), `..._VERIFICATION_001/002.md`
  (CUE 대조검증, 전부 CONFIRMED)
- 근거: `docs/DBMA_RELEASE_GAP_CLOSURE_PIPELINE_v1.md` S3(B-3)

## 상태 — C1 Review 3라운드 전부 종결

| 질문 | 최종 판정 | 대조검증 |
|---|---|---|
| Q3(전사≠추론)·Q5(호출 위치)·Q7(배포 파급) | GREEN | 1차에서 수용 |
| C2(`source` 형식) | GREEN(구분자 형식 채택) | 1차에서 수용 |
| Q4(`metadata_source`) | GREEN(TSU 선택 필드) | 1차에서 수용 — **RQ-1 재검토로 재확인됨** |
| RQ-1(Metadata Model 변경 범위) | **YELLOW→반영 완료** | CONFIRMED(`VERIFICATION_002.md`) |
| RQ-2(쓰레기 내장 값) | **YELLOW→반영 완료** | CONFIRMED(`VERIFICATION_002.md`) |

**남은 조건 2건을 아래에 반영해 이 문서로 설계를 확정한다.**

---

## 확정 설계

### 1. 파일 규약 (D-1, 변경 없음)

원본과 같은 디렉터리에 전체 파일명 + `.meta.json`.
`data/RAW/Spurgeon_Lectures_to_My_Students.txt.meta.json`

### 2. 스키마 (D-2, RQ-1 반영으로 수정)

```json
{
  "title": "...",
  "author": "...",
  "source": "archive.org|original.pdf|docinfo"
}
```

`source`는 **사이드카 파일 내부에만** 존재한다 — `DocumentContext`/registry/
TSU record의 기존 `title`/`author` 필드처럼 직접 매핑되지 않는다.
`source_provenance`(`core/document_context.py:76`)에 담지 않는다 —
RQ-1 재검토로 확정: 그 필드는 Logos 전용 6키 고정 스키마이고
(`core/tsu_builder.py:458-467`, `source_tier`가 설정된 문서만), 여기 사이드카
출처를 넣으면 `core/generation.py:560`의 외부 소스 판정이 Logos 아닌
문서에서도 잘못 켜진다 — **실제 동작 오류**.

**신규 필드**: TSU record에 `metadata_source`(선택, 문자열) 추가 —
`"sidecar"` / `"embedded"` 중 하나. **registry는 무변경**(Q4 원 수용 범위
유지). `title`/`author`가 사이드카에서 왔는지 내장에서 왔는지만 표시한다
— `source_provenance`와 이름은 비슷하지만 완전히 별개 필드다(혼동 방지를
위해 UI/문서에서 항상 "메타데이터 출처"로 지칭, "provenance"라는 단어를
쓰지 않는다).

### 3. 우선순위 (D-3, RQ-2 반영으로 수정)

```
내장 메타데이터가 있고 "신뢰 가능"하면        → 그 값을 쓴다
내장이 None 이거나 "신뢰 불가"인 필드에 한해   → 사이드카로 채운다
```

**"신뢰 불가" 판정(C1 RQ-2 권고안 채택):**

1. **블랙리스트** — 대소문자 무시 정확 일치:
   `untitled`, `untitled-1`, `untitled-2`, 그리고 파일명 패턴
   `^.*\.(docx?|pdf|rtf)$`(예: `"Microsoft Word - doc1.doc"`), 제작
   도구명(`LuraDocument`, `Adobe Acrobat`, `Microsoft Word`,
   `LibreOffice`, `Google Docs`).
2. **휴리스틱** — 블랙리스트 미해당 시: 길이 ≤5자(+1점), 영문 알파벳만
   포함(+1점), Title Case 자동생성 패턴(+1점). **3점 이상 = 신뢰 불가.**
3. 블랙리스트 또는 휴리스틱 3점 이상 → 그 필드만 사이드카로 대체.
   `title`/`author` 각각 독립 판정(하나가 쓰레기여도 다른 하나는
   내장 유지 가능).

구현 위치: `core/processing.py::_load_sidecar_metadata()` 호출 직후,
신규 함수 `_is_untrustworthy_embedded_value(value: str) -> bool`.

### 4. 호출 위치 (D-4, 변경 없음)

`extract_text_from_file()`의 "파일 자신의 내장 메타데이터만" 계약을
지키기 위해 추출기 안에 넣지 않는다. `core/processing.py::process_one_file()`
에서 추출 직후 별도 단계로 처리.

### 5. 실패 시 거동 / RAW 무결성 / doc_type 파급 (D-5~D-7, 변경 없음)

원 요청서(`REQUEST_001.md` D-5~D-7) 그대로 유지 — C1 GREEN.

---

## 구현 체크리스트 (HQ 승인 후)

- [ ] `core/processing.py::_load_sidecar_metadata()` 신설
- [ ] `core/processing.py::_is_untrustworthy_embedded_value()` 신설
      (블랙리스트 + 휴리스틱, 단위 테스트로 "Untitled"/"LuraDocument"/
      정상 제목 3종 커버)
- [ ] `core/tsu_builder.py`에 `metadata_source` 선택 필드 추가
      (registry 스키마 무변경 확인 테스트 포함)
- [ ] 기존 문서 백필 스크립트(`scripts/backfill_doc_type.py` 패턴 재사용)
- [ ] 회귀: `title`/`author` null이던 인용이 실제로 채워지는지 실측
      (S2-3/2-4에서 이미 적재된 67종 코퍼스로 검증 가능)

## 게이트

이 문서 → **HQ 승인** → 위 체크리스트 구현 → S3(B-3, 인용 메타데이터
완성) 완료. Evidence Before Promotion Rule에 따라 HQ 승인 전 구현 착수
금지.
