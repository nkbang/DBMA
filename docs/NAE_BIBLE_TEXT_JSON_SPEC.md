# 성경 본문 JSON 규격 (ADR-031, "연구하기 > 본문 해설")

"본문 해설" 탭의 성경뷰어가 절 본문을 표시하려면 성경 본문 JSON 파일이
필요하다. 이 파일은 **사용자가 직접 제공**한다(저작권이 있는 번역본은
저장소에 포함하지 않는다).

## 위치

- 기본 경로: `data/bible/reference.json`
- 변경: `config.yaml::directories.bible_text_path`
- `data/` 는 `.gitignore` 대상이므로 이 파일은 로컬에만 둔다.

## 스키마

```json
{
  "version": "개역개정",
  "books": {
    "PRO": {
      "name": "잠언",
      "chapters": [
        ["1장 1절 본문", "1장 2절 본문", "..."],
        ["2장 1절 본문", "..."]
      ]
    },
    "JHN": {
      "name": "요한복음",
      "chapters": [ ["1:1 본문", "1:2 본문", "..."] ]
    }
  }
}
```

| 필드 | 설명 |
|---|---|
| `version` | 표시용 번역본 이름. 생략하면 "성경". |
| `books` | `book_id → {name, chapters}` 매핑. |
| `books` 키 | **book_id** — `core/retrieval.py::BOOK_ID_TO_NAMES` 공간(예: 창세기 `GEN`, 잠언 `PRO`, 아가 `SOL`, 요한계시록 `REV`). 소문자·영문 약어·한글 이름(`"잠언"`, `"proverbs"`)도 로더가 정규 ID로 변환한다. |
| `name` | 뷰어에 보일 책 이름. 생략하면 기본 한글명을 채운다. |
| `chapters` | 장 배열. `chapters[0]` = 1장. |
| `chapters[i]` | 절 문자열 배열. `chapters[i][0]` = 1절. |

- 66권 전부가 아니어도 된다 — 존재하는 책만 뷰어에 나온다.
- 빈 장은 빈 배열 `[]` 로 둔다(장 번호 정렬 유지용).

## 견고성 (fail-closed)

파일이 없거나 JSON 이 깨졌거나 스키마가 어긋나면 앱은 **크래시하지 않고**
뷰어에 안내 문구만 표시한다(`core/bible_text.py::load_bible_text` →
`BibleText.unavailable`). 형식이 어긋난 개별 책 항목은 조용히 건너뛴다.

## book_id 참고 (자주 쓰는 것)

창세기 GEN · 출애굽기 EXO · 레위기 LEV · 민수기 NUM · 신명기 DEU ·
여호수아 JOS · 사사기 JDG · 룻기 RUT · 사무엘상 1SA · 사무엘하 2SA ·
열왕기상 1KI · 열왕기하 2KI · 역대상 1CH · 역대하 2CH · 에스라 EZR ·
느헤미야 NEH · 에스더 EST · 욥기 JOB · 시편 PSA · 잠언 PRO · 전도서 ECC ·
아가 SOL · 이사야 ISA · 예레미야 JER · 애가 LAM · 에스겔 EZE · 다니엘 DAN ·
호세아 HOS · 요엘 JOEL · 아모스 AMOS · 오바댜 OBA · 요나 JON · 미가 MIC ·
나훔 NAM · 하박국 HAB · 스바냐 ZEP · 학개 HAG · 스가랴 ZEC · 말라기 MAL ·
마태복음 MAT · 마가복음 MRK · 누가복음 LUK · 요한복음 JHN · 사도행전 ACT ·
로마서 ROM · 고린도전서 1CO · 고린도후서 2CO · 갈라디아서 GAL ·
에베소서 EPH · 빌립보서 PHP · 골로새서 COL · 데살로니가전서 1TH ·
데살로니가후서 2TH · 디모데전서 1TI · 디모데후서 2TI · 디도서 TIT ·
빌레몬서 PHM · 히브리서 HEB · 야고보서 JAS · 베드로전서 1PE ·
베드로후서 2PE · 요한일서 1JN · 요한이서 2JN · 요한삼서 3JN · 유다서 JUD ·
요한계시록 REV

(전체 별칭은 `core/retrieval.py::BOOK_ID_TO_NAMES` 참고.)
