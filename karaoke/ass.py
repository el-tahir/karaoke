"""
turns timed lines into an ASS subtitle document
"""

import re

from karaoke.config import Config
from karaoke.errors import KaraokeError
from karaoke.models import Line

_RESOLUTION = re.compile(r"^(\d+)x(\d+)$", re.I)

_SLOTS = (0.42, 0.56, 0.70) # current, next, next2 - fractions of the frame height
_ENTER = 0.84               # one slot lower still; new previews rise from here
_SCROLL_MS = 300            # the scroll runs at the start of a line, not the end
_BASE_HEIGHT = 1080         # the height the configured font sizes are written for

_STYLES = ("Current", "Next", "Next2")
_ALPHAS = ("&H00", "&H66", "&H88") # 00 is opaque, FF invisible
_OUTLINES = (3, 2, 2)

_HEADER = """[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{styles}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"""

def build(lines: list[Line], cfg: Config) -> str:
    width, height = _dimensions(cfg.resolution)
    doc = [_header(width, height, cfg)]

    x = width // 2
    slots = [round(height * fraction) for fraction in _SLOTS]
    slots.append(round(height * _ENTER)) # so slot n+1 is always where slot n comes from

    for i, line in enumerate(lines):
        start, end = _timestamp(line.start), _timestamp(line.end)
        scroll = min(_SCROLL_MS, max(int((line.end - line.start) * 1000), 0))

        for offset, style in enumerate(_STYLES):
            if i + offset >= len(lines):
                break # the tail of the song has nothing left to preview
            move = rf"\move({x},{slots[offset + 1]},{x},{slots[offset]},0,{scroll})"
            fade = r"\fad(200,0)" if style == "Next2" else "" # only new text fades in
            text = _escape(lines[i + offset].text)
            doc.append(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{{{move}{fade}}}{text}")

    return "\n".join(doc) + "\n"

def _dimensions(resolution: str) -> tuple[int, int]:
    match = _RESOLUTION.match(resolution.strip())
    if not match:
        raise KaraokeError(f"resolution must look like 1920x1080, got {resolution!r}")
    return int(match.group(1)), int(match.group(2))

def _header(width: int, height: int, cfg: Config) -> str:
    scale = height / _BASE_HEIGHT
    sizes = (cfg.size_current, cfg.size_next, cfg.size_next2)
    styles = "\n".join(
        f"Style: {name},{cfg.font},{round(size * scale)},"
        f"{alpha}FFFFFF,{alpha}FFFFFF,{alpha}000000,&H00000000,"
        f"0,0,0,0,100,100,0,0,1,{outline},1,5,40,40,40,1"
        for name, size, alpha, outline in zip(_STYLES, sizes, _ALPHAS, _OUTLINES))
    return _HEADER.format(width=width, height=height, styles=styles)

def _timestamp(seconds: float) -> str:
    total = max(round(seconds * 100), 0) # centiseconds, so 59.999 cannot round to :60
    hours, rest = divmod(total, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, centis = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")
