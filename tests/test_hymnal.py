import os
import sqlite3

import pytest

import hymnal


def test_get_by_number_returns_known_hymn():
    result = hymnal.get_by_number(1, lang="en")
    assert result is not None
    assert result["number"] == 1
    assert result["title"]


def test_get_by_title_matches_known_hymn():
    known = hymnal.get_by_number(1, lang="en")
    match = hymnal.get_by_title(known["title"], lang="en")
    assert match is not None
    assert match["number"] == known["number"]


def test_search_titles_and_number_prefix():
    assert hymnal.search_titles("grace", lang="en")
    assert hymnal.search_by_number_prefix("1", lang="en")


def test_unknown_lang_never_creates_a_db_file():
    """Regression for PR #107: a `lib:` source picked in the hymn-language
    selector used to reach hymnal.py as `lang`, and sqlite3.connect() would
    silently create an empty `data/hymns_lib:<collection>.db` file instead of
    failing. The lookup must fail loudly and leave no file behind."""
    data_dir = os.path.join(os.path.dirname(hymnal.__file__), "data")
    bogus_lang = "lib:praise-english"
    bogus_path = os.path.join(data_dir, f"hymns_{bogus_lang}.db")
    assert not os.path.exists(bogus_path)

    with pytest.raises(sqlite3.OperationalError):
        hymnal.get_by_title("anything", lang=bogus_lang)

    assert not os.path.exists(bogus_path)
