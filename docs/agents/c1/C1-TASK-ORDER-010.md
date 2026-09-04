// deno-fmt-ignore-file
# C1 Task Order 010 — "총 설교 수" vs "누계 데이터" 불일치는 캐싱 문제가 아니다 (라벨링 수정)

발급: CUE (2026-07-23)
대상: C1 (Cline 작업창 #1)
성격: **C1의 원인 진단 정정 + 라벨링 수정.** 코드 동작은 정상이다 —
숫자를 맞추는 게 아니라 설명을 붙이는 작업.

---

## 1. C1의 진단은 틀렸다

C1은 "총 설교 수 2745" vs "누계 데이터 2782건" 차이를 (1)
`@st.cache_resource` 캐싱 (2) 업로드 처리 중 필터링 (3) JSONL 파싱
오류 3가지로 추측하고, 해결책으로 "브라우저 새로고침 + 캐시 초기화"를
제안했다. **CUE가 실제 데이터로 직접 검증한 결과 셋 다 아니다** — 이건
캐시 문제가 아니라 두 지표가 원래 다른 모집단을 재도록 설계돼 있어서
생기는 차이이고, 새로고침으로는 절대 안 바뀐다.

## 2. CUE가 확인한 실제 원인

`sermon_corpus/analyzer/corpus_statistics.py::CorpusStatisticsAnalyzer.
load_records()`(95~125행)가 통계 계산 전에 다음 조건으로 레코드를
먼저 걸러낸다:

```python
REQUIRED_FIELDS = ["published_date", "title", "preacher"]
...
complete_records = [r for r in normalized if self._has_required_fields(r)]
for record in complete_records:
    self._process_record(record)   # total_records는 여기서만 증가
self.records = complete_records
```

- **"총 설교 수"**(`analyzer.get_full_statistics().total_records`)는
  이 필터를 통과한 레코드만 센다.
- **"누계 데이터"**(`len(cumulative_records)`)는 저장된 JSONL 파일의
  원본 줄 수를 그대로 센다.

`data/sermon_corpus/uploaded/uploaded_sermons.jsonl`(2782줄)을 CUE가
직접 스캔해 검증:

| 항목 | 건수 |
|---|---|
| 전체 줄 수 | 2782 |
| `preacher` 누락 | 33건 |
| `passage_raw`/`passage` 둘 다 없음 | 5건 |
| **필터 후 제외되는 총 레코드 수** | **37건** (2782 − 37 = 2745, "총 설교 수"와 정확히 일치) |

즉 코드는 정상 동작 중이다. 캐시를 지워도 이 37건이 다시 포함되지
않는다 — 애초에 통계 계산 로직이 의도적으로 제외하도록 짜여 있기
때문이다(`load_records()` 자체 docstring에도 "필수 필드 누락 레코드
제외"라고 이미 명시돼 있다).

## 3. 수정 지시 — 숫자를 맞추지 말고 설명을 붙여라

두 숫자를 억지로 통일시키려 하지 마라(예: 필터를 없애서 37건도
통계에 포함시키는 것은 하지 말 것 — `preacher`/본문 정보가 없는
레코드를 통계·시각화에 섞으면 다른 지표들의 정확도가 떨어진다).
대신 각 지표가 서로 다른 것을 잰다는 사실을 화면에 명시한다:

1. **사이드바 "총 설교 수"** (`web_app.py` — `render_sidebar()` 내
   `st.metric("총 설교 수", ...)`) 옆에 `help=` 파라미터를 추가해
   "통계 집계 대상(필수 필드 누락 레코드 제외)" 같은 설명을 붙인다.
2. **"데이터 관리" 페이지의 "누적 데이터 건수"**
   (`_render_data_load_status()` 또는 그 후신 함수) 아래에, 두 값이
   다를 때 그 차이를 명시적으로 캡션으로 보여준다. 예:
   ```python
   if cumulative_records is not None:
       total = len(cumulative_records)
       stats_total = analyzer.get_full_statistics().total_records
       if total != stats_total:
           st.caption(
               f"누계 {total:,}건 중 {total - stats_total:,}건은 "
               f"설교자/본문 정보가 없어 통계·차트에서 제외됩니다."
           )
   ```
   (변수명·호출 위치는 실제 함수 시그니처에 맞게 조정할 것 — 위는
   의도 전달용 예시 코드다.)
3. `main()`에 이미 있던 다음 no-op 코드(§4 참고)는 제거하거나, 위
   캡션 로직으로 대체한다:
   ```python
   if cumulative_records is not None and len(cumulative_records) != full_stats.total_records:
       pass  # 아무 일도 안 함 — 이번 작업으로 실제 캡션을 추가해 대체
   ```

## 4. 참고 — 이미 발견돼 있던 관련 코드

`web_app.py` 1537~1539행 부근에 이미 이 불일치를 감지하는 `if` 블록이
있었으나 `pass`만 하고 아무것도 하지 않는 죽은 코드였다. 이번 작업으로
그 자리를 실제 캡션 표시로 채운다.

## 5. 검증

수정 후 "총 설교 수"에 마우스를 올리면 설명(help 텍스트)이 뜨는지,
"데이터 관리" 페이지에 37건 차이에 대한 캡션이 정확한 숫자로 표시되는지
실제 화면에서 확인하고 스크린샷 또는 텍스트로 보고하라.

## 6. 범위 제한

이 작업은 라벨링/설명 텍스트 추가만 다룬다. `REQUIRED_FIELDS` 필터
로직 자체를 바꾸거나, 필수 필드 누락 레코드를 보완/추정해서 채우는
작업은 하지 마라 — 별도 지시 없이는 하지 않는다.
