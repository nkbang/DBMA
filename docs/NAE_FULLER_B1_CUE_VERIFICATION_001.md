# CUE 독립 검증 — B-1 Scripture 추출기 수정 (C1)

- 검증자: CUE / 2026-09-08
- 대상: `NAE/pipeline/canonical/annotate.py` + `tests/test_nae_canonical_annotate.py` (uncommitted, HEAD `3b3f214`)
- 재실측: `/Users/David/DBMA`, venv `~/envs/dbma311`

---

## 판정: 🟡 RETURN — 코어는 큰 개선, 그러나 회귀 1건 + 산출물 누락

수정의 핵심(F-1 로마숫자, F-2 all-caps/한글, F-4 노이즈, 오탐 필터)은
정상 작동하고 8권 전량 대폭 개선(예: Vol.01 2→266, 잡음 폭증 없음).
**그러나 번호 붙은 책(1 Cor, 1 John…)의 공백 표기가 전부 깨졌다.**

---

## 1. GREEN (CUE 재확인)

| 항목 | 결과 |
|---|---|
| 회귀 스위트 (§2 10개 파일) | **144 passed** — 기존 동작 회귀 없음 |
| F-1 로마숫자 | `Ps. xl. 6`→`Psalms 40:6`, `Ps. cxviii. 22`→`Psalms 118:22` ✅ (기존 xxviii 캡 해소). `iiii`/`vx` 라운드트립 거부 ✅ |
| F-2 all-caps | `ROM 8:1`→`Romans 8:1` ✅ |
| F-2/F-3 한글 | `요 3:16`→`John 3:16`, `요한복음 3장 16절`→`John 3:16`, `롬 8:1-2`→`Romans 8:1-2` ✅ (Option A) |
| 오탐 필터 | `page 3:16` / `Vol. iii. 5` / `No. ii. 3` / `Art. iv. 2` / `chapter 3:16` / `the year 1820` / `Christ III. 1` / `David lived 12 years` / `사랑 3:16` / `사람 2:5` → 전부 `[]` ✅ |
| 8권 before/after | Vol01 2→266 · Vol02 3→159 · Vol03 0→73 · Vol04 3→49 · Vol05 1→97 · Vol06 1→55 · Vol07 0→31 · Vol08 1→153. 매그니튜드 정상, Vol01 상위 책(John 53 / Romans 46 / Acts 22 / Luke 20 …) = 진짜 인용 |

---

## 2. 🔴 CONFIRMED 회귀 — 번호 붙은 책 공백 표기

```
'1 Cor 3:16'          -> []        (기대: 1 Corinthians 3:16)
'1 Corinthians 3:16'  -> []
'2 Cor. v. 17'        -> []
'I Cor. xiii. 4'      -> []
```

- **근본 원인**: `_ARABIC_REF`/`_LEGACY_REF` book 패턴을 `(?:[1-3]\s)?` →
  `(?:[1-3])?` 로 바꿔 숫자와 책 이름 사이 **공백을 제거**. "1 Cor" 는
  book="Cor" 로만 잡히고, `_ENG_ALIASES` 에 bare `"cor"`/`"corinthians"` 가
  없어 `_resolve_book_name` 이 None → 전체 미매칭.
- **영향**: Vol.01 canonical.txt 에 1/2 Cor·1/2/3 John·1/2 Tim 등 번호 책
  언급 ~95건, 그중 refs 로 잡힌 것 **0건**. Fuller(칼뱅주의 침례교)에서
  1 Corinthians·1 John 은 최다 인용군 → B-1 이 이 책들엔 오히려 손해.
- 테스트가 통과한 이유: 신규 테스트에 `1 Cor 3:16` / `1 John 5:7` /
  `1 Corinthians …` 케이스가 없음.

---

## 3. 산출물 / 프로세스 누락

- ❌ `docs/NAE_FULLER_B1_SCRIPTURE_EXTRACTOR_REPORT_C1_001.md` **미작성** (§5 필수)
- ❌ 8권 before/after 측정표 (§2) — 리포트에 없음
- ❌ 보고 첫 줄 `git rev-parse HEAD` / `remote -v` / `--show-toplevel`
- ⚠️ F-3(한글 canonical 형식) 은 **CUE 사전 승인 없이** 구현 (§1 F-3 위반).
  결과는 CUE 권고와 동일한 Option A라 수용하나, 절차는 기록.

---

## 4. 정정 요구 (C1)

1. **번호 책 공백 표기 복원**: book 패턴을 `(?:[1-3]\s?)?` 로(공백 optional),
   `_resolve_book_name` 이 `"1 cor"`, `"1cor"`, `"1 corinthians"`,
   `"i cor"`, `"1 john"`, `"2 pet"` 등 번호+공백/로마자 접두 형태를 모두
   해소하도록 보강. bare `"corinthians"`, `"samuel"`, `"kings"` 등 번호 없는
   전체명이 단독으로 매칭되면 안 됨(모호) — 번호가 있을 때만 해소.
2. **신규 테스트 추가**: `1 Cor 3:16`, `1 Corinthians 15:3`, `1 John 5:7`,
   `2 Cor. v. 17`, `I Cor. xiii. 4`, `II Pet. i. 4` → 정확한 canonical.
   음성: `1 year 3:16`, `2 page 5:1` 은 `[]`.
3. §2 회귀 스위트 재실행 (전량 PASS 유지).
4. `docs/NAE_FULLER_B1_SCRIPTURE_EXTRACTOR_REPORT_C1_001.md` 작성:
   git status/HEAD, F-1~F-4 diff 요약, F-3 결정 기록, pytest 결과,
   **8권 before/after 표**(수정본 whole-text 적용, 파일 무수정), Next.
5. 스키마 불변·canonical/tsu 무변경 유지.

## 5. 커밋 보류

`annotate.py`·테스트는 회귀 포함 상태 → **커밋하지 않음**. C1 정정 후 CUE 재검증 → 단일 커밋.

---

## 6. 2차 검증 (C1 정정본, uncommitted, HEAD `70eb286`) — 🟢 CONDITIONAL

### GREEN (CUE 재실측)
- 회귀 스위트 §2 10개 파일 **144 passed**
- **아라비아 번호책 복원**: `1 Cor 3:16`→`1 Corinthians 3:16`, `1 John 5:7`,
  `2 Cor. v. 17`→`2 Corinthians 5:17` ✅ (Fuller 내 ~300건 = 번호책 대부분)
- 오탐 전부 차단: `page 3:16` / `Vol. iii. 5` / `1 year 3:16` / `2 page 5:1` /
  `Christ III. 1` → `[]` ✅
- F-1/F-2/F-4 불변: `Ps. xl. 6`→`Psalms 40:6`, `Ps. cxviii. 22`→`Psalms 118:22`,
  `ROM 8:1`, `요 3:16`→`John 3:16`, `Rom.. ii. 3`→`Romans 2:3` ✅
- 8권 before/after (수정본 whole-text): Vol01 2→311 · 02 3→194 · 03 0→86 ·
  04 3→62 · 05 1→106 · 06 1→63 · 07 0→34 · 08 1→177. 매그니튜드 정상, 폭증 없음

### 미결
1. **[MINOR] 로마 접두 번호책 미지원**: `I Cor. xiii. 4` / `II Pet. i. 4` → `[]`.
   `(?:[1-3]\s?)?` 는 아라비아만. Fuller 내 `I Cor`/`II Pet` 형태 ~13건(전체
   번호책의 ~4%, 전체 refs의 <0.1%). §4.2 테스트 목록에 포함돼 있었음.
   → 소량 추가 수정 권장(불가 시 리포트에 known gap 명시).
2. **[BLOCKER-for-close] 리포트 파일 미작성**: `NAE_FULLER_B1_SCRIPTURE_EXTRACTOR_REPORT_C1_001.md`
   여전히 없음(2회 요청). §5 필수 — git HEAD줄 / F-1~4 요약 / F-3 결정 / pytest / 8권 표.
3. C1 채팅 주장 "I Cor. xiii. 4 통과"는 CUE 재실측과 불일치 — 해당 테스트가
   그 문자열을 실제로 assert하는지 확인 필요.

### 조치
C1: (1) `I Cor`/`II Pet` 로마 접두 추가 or known-gap 명시, (2) 리포트 파일 작성.
그 후 CUE가 `annotate.py`+테스트 단일 커밋.
