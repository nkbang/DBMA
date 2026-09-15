# doc_type 변경 영향 목록 001 — 사이드카 메타데이터 적용 시

- 작성자: CUE
- 일자: 2026-09-15
- 근거: C1 Review 1차 조건 **C3** — "재처리 전 `doc_type` 변경 영향 문서 목록 산출 + HQ 승인"
  (`docs/DBMA_SIDECAR_METADATA_C1_REVIEW_RESULT_001.md`)
- 산출 도구: `scripts/doctype_impact_report.py` (읽기 전용)
- **변경 없음:** registry / 코퍼스 / TSU / 색인 / 파이프라인 코드 무변경

---

## 1. 결론

| 항목 | 값 |
|---|---:|
| 등록 문서 | 4건 |
| **`doc_type` 변경 예상** | **0건** |
| registry 값 ↔ 재계산 불일치 | 0건 |

**조건 C3는 충족되었다.** 사이드카가 title을 채워도 현 코퍼스의 `doc_type`은
전부 그대로다. 재처리로 인한 분류 변동 위험은 없다.

---

## 2. 산출 방법

사이드카를 구현하지 않고도 산출 가능하다 — `guess_doc_type()`을 **title 유무
두 조건으로** 돌려 비교하면 되기 때문이다.

```
guess_doc_type(content, source_file, title=현재값(None))   → 현재 doc_type
guess_doc_type(content, source_file, title=사이드카 후보)   → 적용 후 doc_type
```

후보 title은 같은 자료의 archive.org 원본 PDF `docinfo`에서 읽었다(전사 가능한
실제 값이며 지어낸 값이 아니다). 도구는 사이드카 파일이 이미 있으면 그쪽을
우선 읽도록 만들어, 구현 이후에도 같은 명령으로 재사용된다.

---

## 3. 문서별 결과

| 문서 | 현재 | 후보 title (출처: PDF docinfo) | 적용 후 | 변경 |
|---|---|---|---|:-:|
| `Spurgeon_Lectures_to_My_Students.txt` | 기타 | Lectures to my students : being addresses… | 기타 | — |
| `Spurgeon_Till_He_Come.txt` | 기타 | Till he come : communion meditations and addresses | 기타 | — |
| `Spurgeon_Metropolitan_Tabernacle_Pulpit_Vol01.txt` | 기타 | The Metropolitan Tabernacle Pulpit | 기타 | — |
| `Spurgeon_Metropolitan_Tabernacle_Pulpit_Vol02.txt` | 기타 | The Metropolitan Tabernacle Pulpit | 기타 | — |

---

## 4. 왜 0건인가 — 별개 결함이 드러났다

변경이 0건인 이유는 "분류가 이미 정확해서"가 아니다. **title을 줘도 분류기가
영어 설교를 인식하지 못하기 때문**이다.

### 4.1 `설교`만 영어 키워드가 없다

`core/document_identity.py::_DOC_TYPE_KEYWORDS` 실측:

| 유형 | 한국어/한자 | 영어 |
|---|---:|---|
| 주석 | 2 | 1 — `commentary` |
| **설교** | 5 | **0 — 없음** |
| 사전 | 3 | 2 — `dictionary`, `encyclopedia` |
| 논문 | 4 | 1 — `abstract` |
| 조직신학 | 1 | 1 — `systematic theology` |

5개 유형 중 **`설교`만 영어 키워드가 0개**다. 나머지 4개는 전부 영어 대응어가
있다. 따라서 영어 설교집은 어떤 title을 줘도 `설교`로 분류될 수 없다.

### 4.2 신호는 실제로 존재한다

분류기가 보는 haystack(파일명 + title + 본문 앞 2000자)에 영어 설교 신호가
실제로 들어 있는지 실측했다:

| 문서 | 발견된 신호 |
|---|---|
| `Spurgeon_Till_He_Come.txt` | `sermon`, `pulpit`, `discourse` |
| `Spurgeon_MTP_Vol01` | `pulpit` |
| `Spurgeon_MTP_Vol02` | `pulpit` |
| `Spurgeon_Lectures_to_My_Students.txt` | `lecture` |

**4건 전부 신호를 갖고 있다.** 키워드 표에 영어 항목이 없어서 놓치고 있을 뿐이다.

MTP 2건의 `pulpit`은 CUE가 붙인 파일명뿐 아니라 **PDF docinfo의 실제 title
(`The Metropolitan Tabernacle Pulpit`)에도 들어 있으므로** 자가 순환이 아니다.

### 4.3 왜 중요한가

무료 배포용 기본 코퍼스는 **전량 영어 퍼블릭 도메인 설교**다
(`docs/NAE_FREE_DISTRIBUTION_PLAN_v1.md` §2.3). 즉 이 결함은 배포 대상 자료
전체를 직격한다. `ui/pages/sermon_review.py::_list_candidate_files()`가
`doc_type`으로 후보를 거르므로 기능에도 영향이 있다.

이것은 `docs/DBMA_BASELINE_CORPUS_LOAD_REPORT_001.md` §5.2에서 "doc_type 오분류"로
보고했던 항목의 **정확한 원인**이다. 당시에는 EPUB title 누락이 원인의 일부였고
(2026-09-15 수정으로 `기타`→`주석` 개선 확인), **나머지 절반이 이 언어 비대칭**이다.

---

## 5. 후속 과제 (본 산출물의 범위 밖)

`설교` 유형에 영어 키워드를 추가하는 것은 **사이드카와 무관한 독립 결함 수정**이며
별도 작업으로 다룬다. 착수 시 주의할 점:

1. **`lecture`는 약한 신호다.** *Lectures to My Students*는 설교가 아니라
   설교학(homiletics) 강의다. `lecture`를 `설교` 키워드로 넣으면 오분류가 된다.
   `sermon` / `sermons` / `pulpit` / `preaching` 정도가 안전하고,
   설교학은 별도 유형이 필요한지 먼저 판단해야 한다.
2. **키워드 표 변경은 기존 문서 재분류를 유발한다.** 본 문서와 동일한 절차로
   영향 목록을 먼저 산출할 것 — `scripts/doctype_impact_report.py`는 title 변경
   영향만 보므로, 키워드 표 변경용으로는 도구를 확장해야 한다.
3. `주석`의 영어 키워드가 `commentary` 하나뿐인 점 등 다른 유형의 커버리지도
   같은 기회에 점검할 가치가 있다.

---

## 6. 재현

```bash
python scripts/doctype_impact_report.py --docinfo-map <map.json> --json <out.json>
```

`map.json`은 `{"<registry의 source_file>": "<원본 PDF 경로>"}` 형태.
사이드카(`<RAW파일명>.meta.json`)가 이미 있으면 그쪽이 우선 사용되므로,
구현 이후에는 `--docinfo-map` 없이 실행해도 된다.

---

## 7. 기록

```
STATUS:      산출 완료 — 변경 0건, 조건 C3 충족
Changed:     scripts/doctype_impact_report.py (신규, 읽기 전용 분석 도구)
             본 문서
             ※ registry·코퍼스·TSU·색인·파이프라인 코드 무변경
Tests:       해당 없음 (읽기 전용 분석)
Next:        C1 재요청 회신 대기 (RQ-1·RQ-2)
             별건: 설교 유형 영어 키워드 부재 — §5 주의사항 반영해 별도 착수
```
