import pytest

from karaoke.errors import KaraokeError
from karaoke.meta import (
    _URL,
    _identify,
    _is_official_track,
    _search_terms,
    _parse_title,
    _pick_track
)

ART_TRACK = {
    "artist": "Adele", "track": "Hello", "title": "Hello", "uploader": "Adele",
    "duration": 296, "webpage_url": "https://www.youtube.com/watch?v=yjo_aXygRDI",
}
MUSIC_VIDEO = {
    "title": "Adele - Hello (Official Music Video)", "uploader": "Adele",
    "channel": "Adele", "duration": 367,
    "webpage_url": "https://www.youtube.com/watch?v=YQHsXMglC9A",
}

CASES = [
    ("Adele - Hello (Official Music Video)",                ("Adele", "Hello")),
    ("Rick Astley - Never Gonna Give You Up (Video)",       ("Rick Astley", "Never Gonna Give You Up")),
    ("Daft Punk — Get Lucky [Official Audio]",              ("Daft Punk", "Get Lucky")),
    ("a-ha – Take On Me (Official 4K Video)",               ("a-ha", "Take On Me")),
    ("Blink-182 - All The Small Things",                    ("Blink-182", "All The Small Things")),
    ("Queen | Bohemian Rhapsody",                           ("Queen", "Bohemian Rhapsody")),
    ("Beyoncé - Halo [Lyrics]",                             ("Beyoncé", "Halo")),
    ("Nirvana - Smells Like Teen Spirit (Remastered 2021)", ("Nirvana", "Smells Like Teen Spirit")),
    ("The Weeknd - Blinding Lights (Official Video) [4K]",  ("The Weeknd", "Blinding Lights")),
    ("AC/DC - Thunderstruck (Official Video)",              ("AC/DC", "Thunderstruck")),
    ("Drake - God's Plan (feat. Someone)",                  ("Drake", "God's Plan")),
    ("Sigur Rós - Hoppípolla",                              ("Sigur Rós", "Hoppípolla")),
    ("Coldplay - Yellow - Live at Glastonbury",             ("Coldplay", "Yellow - Live at Glastonbury")),
    ("Hello",                                               None),
    ("(Official Music Video)",                              None),
    ("- Hello",                                             None),
]


@pytest.mark.parametrize("title,expected", CASES)
def test_parse_title(title, expected):
    assert _parse_title(title) == expected


@pytest.mark.parametrize("url,expected", [
    ("https://www.youtube.com/watch?v=abc",      True),
    ("https://music.youtube.com/watch?v=abc",    True),
    ("https://youtu.be/abc",                     True),
    ("http://youtube.com/watch?v=abc",           True),
    ("https://notyoutube.com/watch?v=abc",       False),
    ("https://youtube.com.evil.com/abc",         False),
    ("https://evil.com/youtube.com/abc",         False),
    ("https://www.youtube-nocookie.com/embed/x", False),
    ("//youtube.com/watch?v=abc",                False),
    ("youtube.com/watch?v=abc",                  False),
    ("hello adele",                              False),
])
def test_url_detection(url, expected):
    assert bool(_URL.match(url)) is expected # for boolean tests, use *is* instead of ==


@pytest.mark.parametrize("info,expected", [
    (ART_TRACK,                       True),
    (MUSIC_VIDEO,                     False),
    ({},                              False),
    ({"artist": "Adele"},             False),
    ({"track": "Hello"},              False),
    ({"artist": "  ", "track": "  "}, False),
    ({"artist": None, "track": None}, False),
])
def test_is_official_track(info, expected):
    assert _is_official_track(info) is expected


@pytest.mark.parametrize("info,expected", [
    (MUSIC_VIDEO,                                          "Adele Hello"),
    ({"title": "DJ set 2019", "uploader": "Some Channel"}, "Some Channel DJ set 2019"),
    ({"title": "Hello", "uploader": "Adele - Topic"},      "Adele Hello"),
    ({"title": "Hello"},                                   "Hello"),
    ({},                                                   ""),
])
def test_search_terms(info, expected):
    assert _search_terms(info) == expected


@pytest.mark.parametrize("info,expected", [
    (ART_TRACK,                                                  ("Adele", "Hello")),
    (MUSIC_VIDEO,                                                ("Adele", "Hello")),
    ({"artist": "Adele", "track": "", "title": "Adele - Hello"}, ("Adele", "Hello")),
    ({"artist": "  ", "track": "  ", "title": "Adele - Hello"},  ("Adele", "Hello")),
    ({"title": "DJ set 2019", "uploader": "Some Channel"},       ("Some Channel", "DJ set 2019")),
    ({"title": "", "uploader": "Adele - Topic"},                 ("Adele", "Unknown")),
    ({"title": "Live", "channel": "Chan"},                       ("Chan", "Live")),
])
def test_identify(info, expected):
    assert _identify(info) == expected


def test_identify_raises_on_empty_metadata():
    with pytest.raises(KaraokeError, match="no usable metadata"):
        _identify({"webpage_url": "https://youtu.be/x"})


SEARCH_ENTRIES = [
    {"ie_key": "YoutubeTab", "url": "https://music.youtube.com/browse/MPREb_052spLgIbYg"},
    {"ie_key": "Youtube",    "url": "https://music.youtube.com/watch?v=ZiXW1Lf0XkY", "title": "I'm So Green"},
    {"ie_key": "Youtube",    "url": "https://music.youtube.com/watch?v=WUVEnXw8zH0", "title": "CAN - I'm So Green"},
]

@pytest.mark.parametrize("entries,expected", [
    (SEARCH_ENTRIES,                          "https://music.youtube.com/watch?v=ZiXW1Lf0XkY"),
    (SEARCH_ENTRIES[1:],                      "https://music.youtube.com/watch?v=ZiXW1Lf0XkY"),
    ([SEARCH_ENTRIES[0]],                     None),
    ([],                                      None),
    ([{"ie_key": "Youtube"}],                 None),
    ([{"url": "https://x/watch?v=a"}],        None),
])
def test_pick_track(entries, expected):
    assert _pick_track(entries) == expected
