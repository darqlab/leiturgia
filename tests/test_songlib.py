import songlib


def test_search_titles_finds_known_song():
    matches = songlib.search_titles("Jesus Is My Captain", limit=1, collection="praise-english")
    assert len(matches) == 1
    assert matches[0]["slug"] == "jesus-is-my-captain"
    assert matches[0]["key"] == "lib:praise-english:jesus-is-my-captain"


def test_get_song_returns_stanzas_for_resolved_match():
    matches = songlib.search_titles("Jesus Is My Captain", limit=1, collection="praise-english")
    song = songlib.get_song(matches[0]["collection"], matches[0]["slug"])
    assert song is not None
    assert song["stanzas"]


def test_search_titles_no_match_returns_empty():
    assert songlib.search_titles("nonexistent song title xyz", collection="praise-english") == []


def test_parse_ref_valid_and_invalid_keys():
    assert songlib.parse_ref("lib:praise-english:jesus-is-my-captain") == (
        "praise-english", "jesus-is-my-captain",
    )
    assert songlib.parse_ref("not-a-lib-key") is None
    assert songlib.parse_ref("lib:only-one-part") is None


def test_slugify_normalizes_and_dedupes():
    assert songlib.slugify("Days of Elijah!") == "days-of-elijah"
    assert songlib.slugify("Days of Elijah", existing={"days-of-elijah"}) == "days-of-elijah-2"
