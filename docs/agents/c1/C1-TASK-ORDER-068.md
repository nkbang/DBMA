# C1 Task Order 068 — 사이드카 메타데이터 구현 감사 (PR #55, 설계 대조)

- 발주자: CUE
- 일자: 2026-09-21
- 유형: **C1 Review — 구현 대조 감사 (Post-Implementation Audit)**
- 근거: CLAUDE.md "C1 Review 요청 시점" — Metadata Model 변경 항목 해당
  (`core/document_context.py`, `core/identity_registry.py`,
  `core/tsu_builder.py`에 `metadata_source` 필드 추가)
- 대상 커밋: `origin/dev/dbma-engine` HEAD (PR #55 병합 커밋
  `f56ae04`, 병합 시각 2026-09-17T19:06:45Z)

---

## 배경

RQ-1/RQ-2 설계 검토(RESULT_002, RESULT_003)를 거쳐 확정된
`docs/DBMA_SIDECAR_METADATA_DESIGN_FINAL_v2.md`를 CUE가 구현해
PR #55로 `dev/dbma-engine`에 병합했다(회귀 3,094 PASS, 신규 테스트
22건). **이번 요청은 설계 재검토가 아니라, 이미 승인된 설계와 실제
병합된 코드가 일치하는지에 대한 독립 대조 감사다.**

CUE가 구현 도중 스스로 발견·수정한 결함이 있다: 최초 구현은
`build_document_metadata()`에만 `metadata_source`를 연결했는데, 실제
registry 기록 경로는 `DocumentContext.to_metadata_dict()`였다(라이브
E2E 테스트로 발견). 이 결함이 최종 병합본에 실제로 고쳐져 있는지,
그리고 같은 패턴의 다른 누락이 남아있지 않은지 C1이 독립적으로
확인해야 한다.

---

## 확인 방법

**반드시 `origin/dev/dbma-engine` 브랜치 기준으로 확인할 것.**
`git checkout` 금지(작업 트리 변경 금지, 감사 목적의 읽기 전용
접근만 허용) — `git show origin/dev/dbma-engine:<path>` 명령으로
파일 내용을 읽을 것. 시작 전 아래를 실행해 기록으로 남길 것:

```
git fetch origin
git rev-parse origin/dev/dbma-engine
git remote -v
```

---

## 질의 사항

### RQ-A. `resolve_title_author()`가 설계(D-2/D-3)와 일치하는가?

`git show origin/dev/dbma-engine:core/processing.py`에서
`_is_untrustworthy_embedded_value`, `_load_sidecar_metadata`,
`resolve_title_author` 세 함수를 확인하고, 아래와 각각 대조:

1. 블랙리스트 목록(`_UNTRUSTWORTHY_EXACT`)이
   `DESIGN_FINAL_v2.md` D-3 절의 목록과 정확히 일치하는가?
2. 휴리스틱 3조건(길이 ≤5 / ASCII 알파벳만 / Title-Case 자동생성
   패턴) + "3점 이상 = 신뢰 불가" 임계값이 C1 RQ-2 권고안 그대로인가?
3. 사이드카 스키마가 `{"title", "author", "source"}` 3키이고,
   `source`는 어떤 필드에도 매핑되지 않은 채 사이드카 파일
   내부에서만 읽히는가(다른 곳으로 전파되지 않는가)?

### RQ-B. `metadata_source` 필드가 실제 프로덕션 경로 전체를 통과하는가?

이전 라운드(RESULT_002)에서 C1이 RQ-1 최초 답변 시 `source_provenance`
필드를 놓친 전례가 있었다(2026-09-17, CUE가 직접 grep으로 재확인해
정정 요청). 이번엔 반대 방향의 누락을 확인한다 — **설계가 요구하는
전파 경로 중 실제로 빠진 구간이 있는지** 직접 추적:

1. `core/processing.py::process_one_file()`에서
   `resolve_title_author()` 호출 결과(`metadata_source`)가
   `DocumentContext(...)` 생성자 호출에 실제로 전달되는가?
   (파일·행 번호로 인용)
2. `core/document_context.py`의 `DocumentContext` dataclass에
   `metadata_source: Optional[str] = None` 필드가 있고,
   `to_metadata_dict()`가 그 값을 딕셔너리에 포함하는가?
   (`process_one_file()`이 registry에 실제로 쓰는 값이 이
   `to_metadata_dict()` 반환값인지도 확인 — `build_document_metadata()`가
   아니라 이 경로가 진짜 registry 기록 경로임을 재확인할 것)
3. `core/identity_registry.py::register_document()`가
   `metadata.get("metadata_source")`를 record dict에 담는가?
4. `core/tsu_builder.py`가 registry record에서
   `doc.get("metadata_source")`를 읽어 TSU record에 담는가?
   (`title`/`author` 필드 바로 옆에 있는지도 확인)

**이 4단계 중 하나라도 빠져 있으면 RED로 판정하고 정확한 파일·행
번호를 제시할 것.**

### RQ-C. `source_provenance`가 이번 변경으로 오염되지 않았는가?

RESULT_003에서 확정한 대로, 사이드카의 `source` 키나 새
`metadata_source` 필드가 기존 `source_provenance`(6키 고정 스키마,
Logos 전용) 딕셔너리에 섞여 들어가면 안 된다.

1. `core/tsu_builder.py`의 `source_provenance` 딕셔너리 구성부(약
   458~467행 부근)에 `metadata_source`나 사이드카 `source` 값이
   섞여 있지 않은가?
2. `core/generation.py`의 `has_external` 판정(약 560행)과 인용
   라벨링(약 589행)이 이번 PR로 변경되지 않았는가(diff 없음을
   확인)?

### RQ-D. 테스트가 실제로 이 경로들을 검증하는가?

`tests/test_sidecar_metadata.py`를 열어(`git show
origin/dev/dbma-engine:tests/test_sidecar_metadata.py`) RQ-B의 4단계
전파 경로 중 최소 하나를 `DocumentContext.to_metadata_dict()`를 통해
실제로 검증하는 테스트가 있는지 확인하라(테스트 이름:
`test_document_context_to_metadata_dict_is_the_real_production_path`
로 CUE가 명명했다고 주장함 — 실제로 존재하고, 그 내용이 주장한
검증을 실제로 하는지 대조).

---

## 금지 사항

- 코드 수정 금지 (감사만, 구현 아님)
- `git checkout`/브랜치 전환 금지 — `git show <ref>:<path>`만 사용
- 확인하지 못한 사항은 "확인 불가"로 표기, 추정 금지
- RQ-A~D 외 범위 확장 금지(다른 모듈 전수 검사 등 요청하지 않음)

## 출력 형식

기존 라운드(RESULT_002/003)와 동일한 문서 형식 —
`docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_004.md`로 CUE에게 전달
(사용자가 C1 응답을 복사해 CUE에게 붙여넣는 방식). 각 RQ마다
GREEN/YELLOW/RED 판정 + 근거 파일·행 인용 필수.

```
STATUS:      C1 구현 대조 감사 요청 (PR #55 → origin/dev/dbma-engine)
Changed:     이 문서 1건만
Next:        C1이 RESULT_004 작성 → 사용자가 CUE에게 전달 →
             CUE 독립 재검증(라인 인용 grep 대조) → 문제 없으면 종결,
             문제 발견 시 후속 수정 PR
```
