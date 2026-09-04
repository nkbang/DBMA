"""DBMA-SIL — canonical 66-book Bible name list (Korean name, book_id).

Used by Sermon Draft's book-coverage picker
(ui/pages/sermon_draft.py::_render_book_coverage_buttons()). Deliberately
separate from core/query_enhancements.py's _KOREAN_FULL_NAMES alias table
— that table has two pre-existing typos ("예레미애" instead of
"애가"/Lamentations, "스게론" instead of "스가랴"/Zechariah) that are out
of scope to fix here (a query-parsing alias table, not this picker), but
must not be repeated in a new 66-button user-facing display.

book_id values match verse_mapping.book_id in TSU records
(core/tsu_builder.py) and core/query_enhancements.py's book_id space, so
RetrievalEngine.book_coverage() output keys directly against this list —
no separate ID scheme introduced.
"""

from __future__ import annotations

BIBLE_BOOKS: list[tuple[str, str]] = [
    # 구약 — 모세오경
    ("창세기", "GEN"),
    ("출애굽기", "EXO"),
    ("레위기", "LEV"),
    ("민수기", "NUM"),
    ("신명기", "DEU"),
    # 구약 — 역사서
    ("여호수아", "JOS"),
    ("사사기", "JDG"),
    ("룻기", "RUT"),
    ("사무엘상", "1SA"),
    ("사무엘하", "2SA"),
    ("열왕기상", "1KI"),
    ("열왕기하", "2KI"),
    ("역대상", "1CH"),
    ("역대하", "2CH"),
    ("에스라", "EZR"),
    ("느헤미야", "NEH"),
    ("에스더", "EST"),
    # 구약 — 시가서
    ("욥기", "JOB"),
    ("시편", "PSA"),
    ("잠언", "PRO"),
    ("전도서", "ECC"),
    ("아가", "SOT"),
    # 구약 — 대선지서
    ("이사야", "ISA"),
    ("예레미야", "JER"),
    ("애가", "LAM"),
    ("에스겔", "EZE"),
    ("다니엘", "DAN"),
    # 구약 — 소선지서
    ("호세아", "HOS"),
    ("요엘", "JOEL"),
    ("아모스", "AMOS"),
    ("오바댜", "OBA"),
    ("요나", "JON"),
    ("미가", "MIC"),
    ("나훔", "NAM"),
    ("하박국", "HAB"),
    ("스바냐", "ZEP"),
    ("학개", "HAG"),
    ("스가랴", "ZEC"),
    ("말라기", "MAL"),
    # 신약 — 복음서
    ("마태복음", "MAT"),
    ("마가복음", "MRK"),
    ("누가복음", "LUK"),
    ("요한복음", "JHN"),
    # 신약 — 역사서
    ("사도행전", "ACT"),
    # 신약 — 바울서신
    ("로마서", "ROM"),
    ("고린도전서", "1CO"),
    ("고린도후서", "2CO"),
    ("갈라디아서", "GAL"),
    ("에베소서", "EPH"),
    ("빌립보서", "PHP"),
    ("골로새서", "COL"),
    ("데살로니가전서", "1TH"),
    ("데살로니가후서", "2TH"),
    ("디모데전서", "1TI"),
    ("디모데후서", "2TI"),
    ("디도서", "TIT"),
    ("빌레몬서", "PHM"),
    # 신약 — 일반서신
    ("히브리서", "HEB"),
    ("야고보서", "JAS"),
    ("베드로전서", "1PE"),
    ("베드로후서", "2PE"),
    ("요한일서", "1JN"),
    ("요한이서", "2JN"),
    ("요한삼서", "3JN"),
    ("유다서", "JUD"),
    # 신약 — 예언서
    ("요한계시록", "REV"),
]
