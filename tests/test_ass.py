import re

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

_MOVE = re.compile(r"\\move\((\d+),(\d+),(\d+),(\d+),(\d+),(\d+)\)")


def events(doc):
    return [line for line in doc.splitlines() if line.startswith("Dialogue:")]


def styles(doc):
    return [event.split(",")[3] for event in events(doc)]


def move(event):
    """(y_from, y_to, begin_ms, duration_ms) - the x is checked separately"""
    match = _MOVE.search(event)
    assert match, f"no move in {event}"
    return int(match[2]), int(match[4]), int(match[5]), int(match[6])


def sizes(doc):
    return [int(line.split(",")[2]) for line in doc.splitlines() if line.startswith("Style:")]


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
    hd = events(build(LINES, Config(resolution="1920x1080")))[:3]
    uhd = events(build(LINES, Config(resolution="3840x2160")))[:3]
    # the top gap is 120 and the two below it are 140 - the stack is not evenly spaced
    assert [move(event)[:2] for event in hd] == [(520, 400), (660, 520), (800, 660)]
    assert [move(event)[:2] for event in uhd] == [(1040, 800), (1320, 1040), (1600, 1320)]
    assert r"\move(960," in hd[0] and r"\move(1920," in uhd[0]


@pytest.mark.parametrize("resolution,size", [
    ("1920x1080",  65), # the height the configured size is written for
    ("3840x2160", 130),
    ("1280x720",   43),
])
def test_the_font_size_scales_with_the_resolution(resolution, size):
    """all three at once - the tiers differ by weight, opacity and outline, never by size"""
    assert sizes(build(LINES, Config(resolution=resolution))) == [size] * 3


def test_the_font_size_is_configurable():
    assert sizes(build(LINES, Config(font_size=48))) == [48] * 3


def test_only_the_sung_line_is_bold():
    doc = build(LINES, Config())
    bolds = [line.split(",")[7] for line in doc.splitlines() if line.startswith("Style:")]
    assert bolds == ["-1", "0", "0"] # -1 is true in ASS


def test_the_stack_rises_at_the_end_of_the_line():
    """the move sets up the next line rather than announcing this one"""
    for event in events(build(LINES, Config())):
        _, _, begin, duration = move(event)
        assert duration == 2000
        assert begin == duration - 300


@pytest.mark.parametrize("length,begin,duration", [
    (2.0,  1700, 2000), # comfortably longer than the transition
    (0.4,   200,  400), # too short for 300ms, so it gets half its length
    (0.05,   50,  100), # shorter than the floor, which clamps it to 100ms
])
def test_a_short_line_still_gets_a_proportional_rise(length, begin, duration):
    doc = build([Line(0.0, length, "x")], Config())
    assert move(events(doc)[0])[2:] == (begin, duration)


def test_only_the_outer_slots_fade():
    """the middle line is on screen either side of the handover, so it must not blink"""
    current, next_, next2 = events(build(LINES, Config()))[:3]
    assert r"\fad(0,300)" in current # dims on its way out, never on its way in
    assert r"\fad" not in next_
    assert r"\fad(100,0)" in next2   # genuinely new, so it appears from nothing


def test_a_line_is_handed_over_without_moving():
    """where a line stops in one event is exactly where it resumes in the next"""
    journeys = {}
    for event in events(build(LINES, Config())):
        y_from, y_to, _, _ = move(event)
        journeys.setdefault(event.rsplit("}", 1)[-1], []).append((y_from, y_to))

    assert len(journeys) == len(LINES)
    for text, hops in journeys.items():
        for (_, landed), (resumed, _) in zip(hops, hops[1:]):
            assert landed == resumed, f"{text!r} jumps from {landed} to {resumed}"


def test_no_lines_still_produces_a_valid_header():
    doc = build([], Config())
    assert doc.startswith("[Script Info]")
    assert events(doc) == []


EXPECTED = r"""[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Current,Montserrat,65,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,3,2,10,10,10,1
Style: Next,Montserrat,65,&H88FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1
Style: Next2,Montserrat,65,&H66FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,1,2,10,10,10,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Current,,0,0,0,,{\move(960,520,960,400,1700,2000)\fad(0,300)}first
Dialogue: 0,0:00:00.00,0:00:02.00,Next,,0,0,0,,{\move(960,660,960,520,1700,2000)}second
Dialogue: 0,0:00:00.00,0:00:02.00,Next2,,0,0,0,,{\move(960,800,960,660,1700,2000)\fad(100,0)}third
Dialogue: 0,0:00:02.00,0:00:04.00,Current,,0,0,0,,{\move(960,520,960,400,1700,2000)\fad(0,300)}second
Dialogue: 0,0:00:02.00,0:00:04.00,Next,,0,0,0,,{\move(960,660,960,520,1700,2000)}third
Dialogue: 0,0:00:04.00,0:00:06.00,Current,,0,0,0,,{\move(960,520,960,400,1700,2000)\fad(0,300)}third
"""


def test_snapshot():
    assert build(LINES, Config()) == EXPECTED
