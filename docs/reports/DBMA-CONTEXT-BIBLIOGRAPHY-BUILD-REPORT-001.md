---
title: LLM 문맥 블록 서지정보 주입 빌드 보고서
created: 2026-09-10
author: CUE
status: 구현 완료 · 회귀 통과 · 커밋 전 승인 대기 (Retrieval Engine 변경)
audit_item: PM 정렬 감사 R3 / 선결 #3
base: claude/p0-6-no-evidence-hold (체인: #11 → #12 → #13 → 본 건)
scope: core/retrieval.py, core/generation.py, tests/test_context_assembler_source_label.py
---

# LLM 문맥 블록 서지정보 주입

## 문제 (R3)

`core/retrieval.py::ContextAssembler.assemble()`가 만드는 LLM 문맥 블록은
각 근거를 이렇게만 감쌌다:

```
<context id="TSU-..." score="0.6123">
{본문}
</context>
```

저자·문헌명·페이지·장절이 하나도 없었다. `Citation` 객체에는 있지만
그 값은 UI 카드로만 가고 **LLM에는 가지 않았다.** 그래서 모델은 답변
본문에서 "풀러는 …라고 말한다"처럼 출처를 지목할 수 없었고, 출처는
답변과 분리된 카드 목록으로만 남았다.

`core/generation.py::_format_sermon_context`에는 이미 저자·제목 라벨을
붙이는 별도 포맷이 있었으나 **설교 초안 경로 전용**이었고, 그 docstring은
"Chat/Research 공용 포맷이라 (assemble은) 변경하지 않는다"고 명시하고
있었다 — R3은 정확히 그 미변경이 남긴 공백이다.

## 변경

### 1. `core/retrieval.py` — `_format_context_source_label()` 신설 + `assemble()` 주입

블록 첫 줄에 `출처: {라벨}`을 넣는다. 라벨은 있는 필드만 조합한다
(없으면 줄 자체를 넣지 않음 — "출처: 미상" 같은 잡음 방지):

| 조각 | 소스 필드 | 형식 |
|---|---|---|
| 저작물 | `title` → `book` → `source_file` | 그대로 |
| 저자 | `author` | `{저작물} — {author}` (title에 이미 저자가 있으면 중복 안 함) |
| 장절 | `verse_mapping`(assemble이 이미 계산한 `ref_str`) | `ROM 8:1` |
| 페이지 | `page` | `p.42` |
| 문단 | `paragraph` | `문단 3` |
| 외부 위치 | `source_provenance.logos_location` | 그대로 (설교 경로와 동일 규칙) |

```
<context id="TSU-..." score="0.6123">
출처: 조직신학 — 김목사, ROM 8:1, p.42
{본문}
</context>
```

DBMA 개인서재 TSU(`title`/`author`/`page`/`verse_mapping`)와 NAE 브리지
매핑(`title`=`"{book} by {author}"` 합성, `author`, `verse_mapping`) 양쪽에서
동작한다. `<context id=... score=...>` 래퍼는 그대로 둔다.

### 2. `core/generation.py` — `_GROUNDING_DIRECTIVE`에 §5 추가

> 5. 자료를 근거로 진술할 때는 그 자료에 붙은 "출처:" 표시(저자·문헌·위치)를
>    답변 안에서 함께 밝혀라. 출처 표시가 없으면 위치를 지어내지 말고 내용만
>    인용하라.

주입한 데이터가 실제로 답변에 반영되게 하는 한 줄. 기존 §1~4 번호·문구
불변(추가만).

### 3. `_format_sermon_context` docstring 정정

"assemble은 변경하지 않는다"는 옛 서술을 현재 상태로 갱신. 설교 경로는
번호 지목("[자료1]")이 필요해 전용 포맷을 계속 쓴다는 이유는 유지.

## ADR-024 §C 영향 — 없음

§C가 계약으로 정의하는 것은 NAE payload → `Citation` **필드 매핑**이다
(`tsu_id`/`source_author`/`retrieval_score`/`source_type`/`content_excerpt`/
`scripture_reference` 6개 직접 + 5개 근사). `ContextAssembler.assemble()`이
만드는 LLM 문맥 블록 문자열은 §C 표에 없다 — P0-4에서 `RankedCandidate.
content`에 대해 내린 판단과 동일. **Freeze Rule 위반 없음, Amendment 불요.**
`Citation` 객체와 그 필드는 이 변경에서 손대지 않았다.

## 검증

```bash
~/envs/dbma311/bin/python -m pytest -q tests/
```

- 신규 `tests/test_context_assembler_source_label.py`: 11건
  (라벨 조합 8건 + assemble 통합 3건 — 서지 있을 때 주입/없을 때 생략/
   verse_mapping 장절 반영)
- 전체 회귀: **2896 passed, 15 skipped** (기존 2885 + 11)
- 문맥 블록 포맷을 문자열로 파싱하는 소비자 없음 확인
  (`grep -rn "<context" --include='*.py'` → assemble 자신 + 사람 읽기용 주석뿐)

## 승인 필요

`core/retrieval.py`는 CLAUDE.md 예외 조항의 "Retrieval Engine"에 속한다 —
Git 자동화(commit/push) 대상이 아니다. 구현·검증은 지시대로 완료했고,
**커밋·푸시 전에 사용자 승인을 요청한다.**

## 범위 밖 (후속)

- `bridge_query()`(NAE PD 섹션 표시용)는 `assemble()`을 거치지 않고
  `Citation` 리스트를 직접 반환 — 이 경로의 문맥 표기는 별도.
- 근거 강도/불일치를 답변 옆에 시각적으로 보여주는 검증 UX는 P0 이후 항목.
