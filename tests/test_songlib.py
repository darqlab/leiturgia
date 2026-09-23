import json

import songlib


def test_search_titles_rejects_invalid_collection_path(tmp_path, monkeypatch):
    (tmp_path / "songs").mkdir()
    escape_dir = tmp_path / "escape"
    escape_dir.mkdir()
    (escape_dir / "secret.json").write_text(json.dumps({"title": "Escaped Song", "stanzas": []}))
    monkeypatch.setattr(songlib, "SONGS_DIR", str(tmp_path / "songs"))
    assert songlib.search_titles("Escaped", collection="../escape") == []


def test_load_meta_returns_none_for_non_object_json(tmp_path):
    path = tmp_path / "list-shaped.json"
    path.write_text(json.dumps(["not", "an", "object"]))
    assert songlib._load_meta(str(path)) is None


def test_list_songs_skips_list_shaped_file_without_raising(tmp_path, monkeypatch):
    collection_dir = tmp_path / "songs" / "some-collection"
    collection_dir.mkdir(parents=True)
    (collection_dir / "bad.json").write_text(json.dumps(["not", "an", "object"]))
    monkeypatch.setattr(songlib, "SONGS_DIR", str(tmp_path / "songs"))
    assert songlib.list_songs(collection="some-collection") == []


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
