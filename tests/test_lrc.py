import pytest

from karaoke.lrc import parse
from karaoke.models import Line

BASIC = """\
[00:12.00]first line
[00:15.50]second line
[00:20.00]third line
"""

def test_line_level_only():
    assert parse(BASIC) == [
        Line(12.0, 15.5, "first line"),
        Line(15.5, 20.0, "second line"),
        Line(20.0, 25.0, "third line")
    ]

def test_metadata_headers_are_skipped():
    text = "[ar:Adele]\n[ti:Hello]\n[by:some tagger]\n[00:12.00]hello"
    assert parse(text) == [Line(12.0, 17.0, "hello")]

def test_multi_stamp_line_expands():
    text = "[00:12.00][01:20.00]same chorus\n[00:30.00]a verse\n"
    assert parse(text) == [
        Line(12.0, 30.0, "same chorus"),
        Line(30.0, 80.0, "a verse"),
        Line(80.0, 85.0, "same chorus"),
    ]

def test_blank_lines_crlf_and_trailing_whitespace():
    text = "\r\n[00:12.00]first \r\n\r\n  \r\n[00:15.00]second\r\n"
    assert parse(text) == [Line(12.0, 15.0, "first"), Line(15.0, 20.0, "second")]

def test_word_stamps_are_stripped():
    text = "[00:12.00]<00:12.00>Hello <00:12.50>world\n"
    assert parse(text) == [Line(12.0, 17.0, "Hello world")]

@pytest.mark.parametrize("bad", [
    "[9:99]ninety nine seconds",
    "[abc]not a stamp",
    "[]nothing in there",
    "no stamp at all",
    "[00:12.00]",
    "[00:12.00]   ",
    "[00:12.00]<00:12.00>",
])
def test_malformed_lines_are_skipped(bad):
    assert parse(f"{bad}\n[00:30.00]good\n") == [Line(30.0, 35.0, "good")]

def test_a_bad_stamp_does_not_lose_the_good_ones():
    assert parse("[00:12.00][9:99]chorus\n") == [Line(12.0, 17.0, "chorus")]

def test_out_of_order_input_comes_back_sorted():
    text = "[00:30.00]third\n[00:10.00]first\n[00:20.00]second\n"
    assert [line.text for line in parse(text)] == ["first", "second", "third"]

def test_end_chains_and_the_last_line_uses_tail():
    spans = [(line.start, line.end) for line in parse(BASIC, tail=2.5)]
    assert spans == [(12.0, 15.5), (15.5, 20.0), (20.0, 22.5)]

@pytest.mark.parametrize("stamp,start", [
    ("[00:12]", 12.0),
    ("[00:12.5]", 12.5),
    ("[00:12.00]", 12.0),
    ("[00:12.34]", 12.34),
    ("[00:12.345]", 12.345),
    ("[01:00.00]", 60.0),
    ("[100:00.00]", 6000.0),
])
def test_timestamp_formats(stamp, start):
    assert parse(f"{stamp}x")[0].start == pytest.approx(start)

@pytest.mark.parametrize("text", ["", "\n\n", "  \r\n", "[ar:Adele]\n[ti:Hello]\n"])
def test_empty_input_returns_nothing(text):
    assert parse(text) == []
