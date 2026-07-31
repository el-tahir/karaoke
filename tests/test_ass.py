import pytest

from karaoke.ass import build
from karaoke.config import Config
from karaoke.errors import KaraokeError
from karaoke.models import Line

LINES = [
    Line(0.0, 2.0, "first"),
    Line(2.0, 4.0, "second"),
    Line(4.0, 6.0, "third"),
]


def events(doc):
    return [line for line in doc.splitlines() if line.startswith("Dialogue:")]


def styles(doc):
    return [event.split(",")[3] for event in events(doc)]


@pytest.mark.parametrize("resolution,width,height", [
    ("1920x1080", 1920, 1080),
    ("3840x2160", 3840, 2160),
    ("1280x720",  1280, 720),
])
def test_header_carries_the_configured_resolution(resolution, width, height):
    doc = build(LINES, Config(resolution=resolution))
    assert f"PlayResX: {width}" in doc
    assert f"PlayResY: {height}" in doc


@pytest.mark.parametrize("bad", ["1920", "1920*1080", "1920 x 1080", "", "widexhigh"])
def test_a_bad_resolution_raises(bad):
    with pytest.raises(KaraokeError, match="resolution"):
        build(LINES, Config(resolution=bad))


def test_one_line_gives_one_current_event():
    assert styles(build(LINES[:1], Config())) == ["Current"]


def test_the_first_group_has_all_three_styles():
    assert styles(build(LINES, Config()))[:3] == ["Current", "Next", "Next2"]


def test_the_last_lines_lose_their_previews():
    assert styles(build(LINES, Config())) == [
        "Current", "Next", "Next2",
        "Current", "Next",
        "Current",
    ]


def test_braces_and_backslashes_are_escaped():
    doc = build([Line(0.0, 1.0, r"a {b} c \d")], Config())
    assert events(doc)[0].endswith(r"a \{b\} c \\d")


def test_coordinates_track_the_resolution():
    hd = events(build(LINES[:1], Config(resolution="1920x1080")))[0]
    uhd = events(build(LINES[:1], Config(resolution="3840x2160")))[0]
    assert r"\move(960,605,960,454," in hd
    assert r"\move(1920,1210,1920,907," in uhd


def test_font_sizes_scale_with_the_resolution():
    assert "Montserrat,60," in build(LINES, Config(resolution="1920x1080"))
    assert "Montserrat,120," in build(LINES, Config(resolution="3840x2160"))


def test_no_lines_still_produces_a_valid_header():
    doc = build([], Config())
    assert doc.startswith("[Script Info]")
    assert events(doc) == []


EXPECTED = r"""[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Current,Montserrat,60,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,1,5,40,40,40,1
Style: Next,Montserrat,52,&H66FFFFFF,&H66FFFFFF,&H66000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,5,40,40,40,1
Style: Next2,Montserrat,44,&H88FFFFFF,&H88FFFFFF,&H88000000,&H00000000,0,0,0,0,100,100,0,0,1,2,1,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Current,,0,0,0,,{\move(960,605,960,454,0,300)}first
Dialogue: 0,0:00:00.00,0:00:02.00,Next,,0,0,0,,{\move(960,756,960,605,0,300)}second
Dialogue: 0,0:00:00.00,0:00:02.00,Next2,,0,0,0,,{\move(960,907,960,756,0,300)\fad(200,0)}third
Dialogue: 0,0:00:02.00,0:00:04.00,Current,,0,0,0,,{\move(960,605,960,454,0,300)}second
Dialogue: 0,0:00:02.00,0:00:04.00,Next,,0,0,0,,{\move(960,756,960,605,0,300)}third
Dialogue: 0,0:00:04.00,0:00:06.00,Current,,0,0,0,,{\move(960,605,960,454,0,300)}third
"""


def test_snapshot():
    assert build(LINES, Config()) == EXPECTED
