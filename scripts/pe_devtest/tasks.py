"""PE 개발업무 테스트 과제 4종 (버그수정 / 기능추가 / 테스트작성 / 스펙변경)."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATE = (ROOT / "core/date_extractor.py").read_text()
CITE = (ROOT / "core/citation_format.py").read_text()

# T1: 의도적 off-by-one 버그 주입
BUG = DATE.replace("range(anchor_index - 1, lower_bound - 1, -1)", "range(anchor_index - 2, lower_bound, -1)")
assert BUG != DATE

HIDDEN_T1 = '''
from core.date_extractor import find_nearest_date
def test_adjacent_line():
    assert find_nearest_date(["2025-01-05", "제목: A"], 1) == "2025-01-05"
def test_lookback_limit_inclusive():
    lines = ["2025-01-05"] + ["x"] * 9 + ["제목: A"]
    assert find_nearest_date(lines, 10, max_lookback=10) == "2025-01-05"
def test_stop_index_inclusive():
    lines = ["2025-01-05", "제목: A"]
    assert find_nearest_date(lines, 1, stop_index=0) == "2025-01-05"
    assert find_nearest_date(lines, 1, stop_index=1) is None
'''

HIDDEN_T2 = '''
from core.date_extractor import extract_all_dates
def test_mixed_order_dedup():
    t = "2025-01-05 예배\\n2026년 2월 11일 수요\\n2025-1-5 재방송"
    assert extract_all_dates(t) == ["2025-01-05", "2026-02-11"]
def test_invalid_skipped():
    assert extract_all_dates("2025-13-40 and 2025-03-09") == ["2025-03-09"]
def test_empty():
    assert extract_all_dates("") == []
'''

HIDDEN_T4 = '''
from core.date_extractor import extract_date_from_line as f
def test_calendar_valid():
    assert f("2025-02-30") is None
    assert f("2025-04-31") is None
    assert f("2026년 2월 29일") is None
def test_leap_ok():
    assert f("2024-02-29") == "2024-02-29"
    assert f("2000-02-29") == "2000-02-29"
    assert f("1900-02-29") is None
def test_normal_ok():
    assert f("2025-01-05 예배") == "2025-01-05"
'''


def _fail_out(tmp, pytest):
    return pytest(tmp, "tests/test_date_extractor.py")[1][-900:]


def _t1_prompt(tmp):
    ok, out = _fail_out(tmp, None) if False else (None, "")
    return (f"아래 core/date_extractor.py에 버그가 있다. find_nearest_date의 탐색 범위가 "
            f"docstring과 다르게 동작한다(anchor 바로 윗줄과 경계 줄이 누락됨). 최소 수정으로 고친 전체 파일을 출력하라. "
            f"다른 동작은 바꾸지 마라.\n\n```python\n{BUG}\n```")


def _g_t1(tmp, pytest):
    (tmp / "tests/test_hidden.py").write_text(HIDDEN_T1)
    a, _ = pytest(tmp, "tests/test_date_extractor.py")
    b, o = pytest(tmp, "tests/test_hidden.py")
    return {"pass": a and b, "existing_ok": a, "hidden_ok": b}


def _t2_prompt(tmp):
    return ("core/date_extractor.py에 `extract_all_dates(text: str) -> list[str]`를 추가하라. "
            "텍스트 전체(여러 줄)에서 기존 정규식/정규화(_normalize_date)를 재사용해 모든 날짜를 찾아 "
            "'YYYY-MM-DD'로 정규화하고, 등장 순서를 유지하며 중복은 제거, 유효하지 않은 날짜는 제외한다. "
            "한 줄에 ISO와 한글 형식이 섞여도 등장 위치 순서로 반환한다(위치 기준). 기존 함수는 변경하지 말고 "
            f"수정된 전체 파일을 출력하라.\n\n```python\n{DATE}\n```")


def _g_t2(tmp, pytest):
    (tmp / "tests/test_hidden.py").write_text(HIDDEN_T2)
    a, _ = pytest(tmp, "tests/test_date_extractor.py")
    b, _ = pytest(tmp, "tests/test_hidden.py")
    return {"pass": a and b, "existing_ok": a, "hidden_ok": b}


def _t3_prompt(tmp):
    return ("core/citation_format.py에 대한 pytest 파일 tests/test_citation_format_new.py 전체를 작성하라. "
            "extract_citation_year(None/''/'202'/'abcd-01'/'2025-03-01')와 format_footnote_line의 "
            "(저자 없음, 제목 없음 fallback, doc_type만, year만, 둘 다 없음, location 유무, 마침표 종료)를 "
            "모두 검증한다. `from core.citation_format import ...`로 import한다.\n\n"
            f"```python\n{CITE}\n```")


MUTANTS = [
    ("year 길이검사 제거", 'if not created_at or len(created_at) < 4 or not created_at[:4].isdigit():', 'if not created_at:'),
    ("마침표 제거", 'return f"{body}."', 'return body'),
    ("location 무시", 'if location:\n        body = f"{body}, {location.strip()}"', 'if False:\n        pass'),
    ("fallback 무시", 't = (title or "").strip() or fallback_title', 't = (title or "").strip()'),
]


def _g_t3(tmp, pytest):
    f = tmp / "tests/test_citation_format.py"  # 모델 출력이 target(tests/test_citation_format_new.py)에 이미 기록됨
    new = "tests/test_citation_format_new.py"
    orig_ok, _ = pytest(tmp, new)
    killed = 0
    for _, old, rep in MUTANTS:
        assert old in CITE, old
        (tmp / "core/citation_format.py").write_text(CITE.replace(old, rep))
        ok, _ = pytest(tmp, new)
        killed += (not ok)
    (tmp / "core/citation_format.py").write_text(CITE)
    return {"pass": orig_ok and killed == len(MUTANTS), "original_pass": orig_ok, "mutants_killed": f"{killed}/{len(MUTANTS)}"}


def _t4_prompt(tmp):
    return ("core/date_extractor.py의 _normalize_date가 일(day)을 1~31로만 검사해 2025-02-30 같은 존재하지 않는 "
            "날짜를 통과시킨다. 달력상 유효한 날짜만 허용하도록(윤년 규칙 포함: 400배수 윤년, 100배수 평년) 수정하라. "
            "표준 라이브러리만 사용, 기존 테스트 동작은 유지, 반환 형식 불변. 수정된 전체 파일을 출력하라.\n\n"
            f"```python\n{DATE}\n```")


def _g_t4(tmp, pytest):
    (tmp / "tests/test_hidden.py").write_text(HIDDEN_T4)
    a, _ = pytest(tmp, "tests/test_date_extractor.py")
    b, _ = pytest(tmp, "tests/test_hidden.py")
    return {"pass": a and b, "existing_ok": a, "hidden_ok": b}


TASKS = [
    {"id": "T1_bugfix", "target": "core/date_extractor.py", "prompt": _t1_prompt, "grade": _g_t1},
    {"id": "T2_feature", "target": "core/date_extractor.py", "prompt": _t2_prompt, "grade": _g_t2},
    {"id": "T3_tests", "target": "tests/test_citation_format_new.py", "prompt": _t3_prompt, "grade": _g_t3},
    {"id": "T4_spec_change", "target": "core/date_extractor.py", "prompt": _t4_prompt, "grade": _g_t4},
]
