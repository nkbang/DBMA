"""tests/test_doc_type_english_sermon_keywords.py — 영어 설교 키워드 회귀 방지.

실측 근거(2026-09-15, docs/DBMA_DOCTYPE_IMPACT_REPORT_001.md §4):
core.document_identity._DOC_TYPE_KEYWORDS의 5개 유형 중 "설교"만 영어
대응어가 0개였다. 주석=commentary, 사전=dictionary/encyclopedia,
논문=abstract, 조직신학=systematic theology는 전부 있었다. 그 결과 영어
설교집(무료 배포 기본 코퍼스 전량)이 어떤 title을 줘도 "기타"로 떨어졌다.

키워드 선정 근거는 docs/DBMA_DOCTYPE_SERMON_KEYWORDS_REPORT_001.md —
백업 코퍼스 122개 출처 + archive.org 설교 67종 실측. 아래 오탐 테스트는
그때 실제로 관측된 두 사례를 고정한 것이다.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.document_identity import _DOC_TYPE_KEYWORDS, guess_doc_type  # noqa: E402


# ── 언어 커버리지 ────────────────────────────────────────────────


def test_every_doc_type_has_at_least_one_ascii_keyword():
    """어떤 유형도 영어 키워드 0개로 남지 않는다 — 이번 결함의 근본 형태."""
    for doc_type, keywords in _DOC_TYPE_KEYWORDS.items():
        ascii_kws = [k for k in keywords if k.isascii()]
        assert ascii_kws, f"{doc_type}: 영어 키워드가 없다 — 영어 자료를 분류할 수 없다"


# ── 진양성 (영어 설교집이 설교로 분류된다) ──────────────────────


@pytest.mark.parametrize(
    "title",
    [
        "The Metropolitan Tabernacle Pulpit",
        "Sermons on Various Subjects",
        "The Works of the Rev. Andrew Fuller — Vol. 7: Sermons on Various Subjects",
    ],
)
def test_english_sermon_titles_classify_as_sermon(title):
    assert guess_doc_type("", "somefile.txt", title) == "설교"


def test_sermon_keyword_matches_in_body_text():
    """title이 없어도 본문 앞부분의 신호로 분류된다."""
    body = "A selection of sermons delivered at the tabernacle during 1860."
    assert guess_doc_type(body, "unknown.txt", None) == "설교"


def test_till_he_come_classifies_via_body_not_title():
    """실제 코퍼스 사례 — title만으로는 신호가 없고 본문이 판정한다.

    "Till he come : communion meditations and addresses"에는 키워드가 없다.
    분류를 성립시키는 것은 본문 앞부분의 'Pulpit'이다(원문 확인:
    "(Not published in The Metropolitan Tabernacle Pulpit.)"). 이 구분을
    고정해 두는 이유는, title만으로 분류된다고 잘못 가정한 테스트가 실제로
    실패했기 때문이다.
    """
    title = "Till he come : communion meditations and addresses"
    assert guess_doc_type("", "Spurgeon_Till_He_Come.txt", title) == "기타"

    body = '"TILL HE COME." (Not published in The Metropolitan Tabernacle Pulpit.)'
    assert guess_doc_type(body, "Spurgeon_Till_He_Come.txt", title) == "설교"


# ── 오탐 방지 (실제 관측된 사례 고정) ────────────────────────────


def test_prose_mention_of_preaching_is_not_a_sermon():
    """'preaching'을 키워드로 넣었을 때 실제로 오분류된 문장.

    출처: 백업 코퍼스 "7. The Fundamentals.pdf" — 선교 고전 모음집이지
    설교집이 아니다.
    """
    body = (
        "there have been great awakenings without much preaching, "
        "and there have been great awakenings with absolutely no music."
    )
    assert guess_doc_type(body, "7. The Fundamentals.pdf", None) != "설교"


def test_publisher_series_catalog_does_not_make_a_commentary_a_sermon():
    """단수 'sermon'을 키워드로 넣었을 때 실제로 오분류된 사례.

    출처: 백업 코퍼스 "Hebrews … (Preaching the Word)" — 주석 시리즈의 한 권인데,
    앞부분에 실린 같은 시리즈 다른 권 광고 목록("the sermon on the mount")에
    단수 sermon이 걸렸다.
    """
    body = (
        "john | david l. allen revelation | james m. hamilton jr. "
        "the sermon on the mount | r. kent hughes preaching the word hebrews"
    )
    source = "Hebrews (2 volumes in 1 ESV Edition) An Anchor for the Soul (Preaching the Word).pdf"
    assert guess_doc_type(body, source, None) != "설교"


@pytest.mark.parametrize(
    "title",
    [
        "A History of Preaching",
        "Lectures on the History of Preaching",
    ],
)
def test_books_about_preaching_are_not_sermons(title):
    """설교학·설교사 저작은 설교집이 아니다 — 'preaching' 제외의 직접 근거."""
    assert guess_doc_type("", "book.pdf", title) != "설교"


def test_homiletics_lectures_are_not_classified_as_sermons():
    """Spurgeon, *Lectures to My Students*는 설교가 아니라 설교학 강의다."""
    title = (
        "Lectures to my students : being addresses delivered to the students "
        "of the Pastors' College, Metropolitan Tabernacle"
    )
    assert guess_doc_type("", "Spurgeon_Lectures_to_My_Students.txt", title) != "설교"


# ── 기존 동작 보존 ───────────────────────────────────────────────


def test_commentary_still_wins_over_sermon_signal():
    """정의 순서(주석 먼저)가 유지되는지 — 설교 신호가 섞인 주석서."""
    body = "This commentary collects sermons preached on the Psalms."
    assert guess_doc_type(body, "x.pdf", None) == "주석"


def test_korean_keywords_unchanged():
    assert guess_doc_type("", "x.txt", "요한복음 설교집") == "설교"
    assert guess_doc_type("", "x.txt", "로마서 주석") == "주석"


def test_no_signal_still_falls_back_to_기타():
    assert guess_doc_type("hello world", "x.txt", "Untitled") == "기타"
