// deno-fmt-ignore-file
# C1 Task Order 009 — "독립된 성경 책" 지표가 66권을 초과하는 데이터 정규화 버그

발급: CUE (2026-07-23)
대상: C1 (Cline 작업창 #1)
성격: **데이터 파이프라인 버그 수정.** 화면 표시 버그가 아니라 수집·
정규화 단계에서 `bible_book` 필드에 원본 한글 약어/Unknown/오타가
그대로 저장되는 문제.

---

## 1. 배경

사용자가 사이드바의 "독립된 성경 책" 지표가 74로 표시되는데 성경은
66권뿐이라고 지적. CUE가 `data/sermon_corpus/**/*.jsonl` 전체를 직접
스캔해 원인을 확인했다.

## 2. CUE가 확인한 원인

`sermon_corpus/analyzer/frequency.py:278`:
```python
"unique_books": len(self.book_counter),
```
`book_counter`는 `add_record()`(`frequency.py:179`)가 넘겨받은
`bible_book` 문자열을 검증 없이 그대로 키로 쓴다. 실제 데이터를
스캔한 결과 정경 66권(canonical 영문명, `BIBLE_BOOKS` 상수) 외에
다음 48개 추가 값이 섞여 있었다(전체 jsonl 기준, 대시보드가 로드하는
부분집합은 이보다 적은 74개로 추정):

| 유형 | 예시 | 건수(전체 기준) |
|---|---|---|
| 매핑 안 된 한글 약어 원본값 | `창`, `출`, `레`, `시`(10), `창`(10), `롬`(5), `요`(6), `사`(6) 등 | 각 1~10건 |
| Unknown placeholder | `Unknown` | 8건 |
| 오타로 추정 | `눙` (아마 `눅`=Luke) | 1건 |
| 모호한 병합 참조 | `살전후` (데살로니가전서/후서 구분 불가) | 4건 |

`sermon_corpus/analyzer/frequency.py`에는 이미 `KOREAN_ABBREVIATIONS`
매핑(예: `"창": "Genesis"`)이 존재하는데, 일부 레코드는 이 매핑을
거치지 않고 한글 원본이 `bible_book` 필드에 그대로 들어간 채
저장돼 있다 — 즉 **정규화가 수집 단계 어딘가에서 누락됐다.**

## 3. 수정 지시 — 두 곳 모두 처리

### 3.1 근본 수정 — 수집 단계 정규화 강제 (우선)

`bible_book`을 채우는 모든 collector(`sermon_corpus/collector/*.py` —
`church.py::extract_bible_info()`, `sermonbank.py`, `youtube.py`,
`church_website.py` 등 각자 자체 Bible-book 추출 로직을 가진 파일
전부 대상)를 점검해서, 매핑이 성공하면 반드시 `FrequencyAnalyzer.
BIBLE_BOOKS`/`KOREAN_ABBREVIATIONS`가 쓰는 것과 동일한 canonical
영문명을 저장하고, **매핑 실패 시 원본 한글 문자열을 그대로 저장하지
말고 `None`(또는 `"Unknown"`으로 저장하려면 그렇게 명시적으로 통일)로
저장**하도록 고친다.

- `살전후`처럼 두 책 중 하나로 특정 불가한 경우는 매핑 실패로 취급 —
  임의로 둘 중 하나를 고르지 말 것.
- `눙` 같은 오타 케이스는 원본 소스(어느 collector가 만들었는지)를
  먼저 찾아 그 collector의 파싱 로직 버그인지 확인 후 수정.

### 3.2 방어 수정 — 집계 단계 필터링 (근본 수정과 별개로 반드시 추가)

`sermon_corpus/analyzer/frequency.py::FrequencyAnalyzer.add_record()`가
`bible_book`을 카운터에 넣기 전에 `BIBLE_BOOKS`(canonical 66권 목록)에
있는 값인지 검증하도록 고친다. canonical 목록에 없는 값(빈 문자열,
`Unknown`, 한글 원본, 오타 등)은 `book_counter`에 넣지 말고 별도
`unmapped_counter`(또는 로그)로 분리해 집계한다 — 이렇게 하면 앞으로
3.1을 완전히 놓친 신규 collector가 추가되더라도 `unique_books`가
66을 넘는 일이 재발하지 않는다. 이미 저장된 기존 jsonl 데이터를
당장 재수집/재처리할 필요는 없다 — 이 필터링만으로 화면 지표는
정확해진다.

### 3.3 검증

- 수정 후 `unique_books`가 66 이하로 표시되는지 실제 데이터로 확인.
- `unmapped_counter`(또는 이에 준하는 결과)에 몇 건이 걸러졌는지
  보고에 포함 — 데이터 품질 문제 규모를 알 수 있어야 한다.
- 기존 collector 테스트가 있으면 통과 확인, 없으면 최소한
  `add_record()`가 non-canonical 값을 걸러내는지 확인하는 단위 테스트
  1~2개 추가.

## 4. 범위 제한

이 Task Order는 이 버그 하나만 다룬다. 10만→1만 건 축소, YouTube
예배 영상 설교 구간 추출 등 별도로 지시한 항목과는 무관 — 그 작업들과
섞지 말 것.
