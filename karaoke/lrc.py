"""
parses LRC text into timed lines
"""
import re
from karaoke.models import Line

_META = re.compile(r"^\[[a-zA-Z]{2,}:.*\]$")
_STAMP = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
_WORD = re.compile(r"<(\d+):(\d+(?:\.\d+)?)>")

def _split_stamps(raw: str) -> tuple[list[float], str]:
    """peels the leading [mm:ss.xx] stamps off a line, dropping the malformed ones"""
    starts, pos = [], 0
    while match := _STAMP.match(raw, pos):
        seconds = float(match.group(2))
        if seconds < 60: # [9:99] matches the pattern but isnt a time
            starts.append(int(match.group(1)) * 60 + seconds)
        pos = match.end()
    return starts, raw[pos:]

def parse(text: str, tail: float = 5.0) -> list[Line]:
    lines: list[Line] = []

    for raw in text.splitlines():
        raw = raw.strip() # also drops the \r of  CRLF file
        if not raw or _META.match(raw):
            continue

        starts, rest = _split_stamps(raw)
        body = _WORD.sub("", rest).strip() # word timing isnt used, only the words
        if not (starts and body):
            continue

        lines.extend(Line(start, 0.0, body) for start in starts)

    if not lines:
        return []

    lines.sort(key=lambda line: line.start)
    for line, nxt in zip(lines, lines[1:]):
        line.end = nxt.start
    lines[-1].end = lines[-1].start + tail
    return lines
