"""
turns timed lines into an ASS subtitle document

three lines sit on screen at once; over the closing moments of each line the
whole stack rises one slot, so the line just sung leaves as the next arrives
already in place
"""

import re

from karaoke.config import Config
from karaoke.errors import KaraokeError
from karaoke.models import Line

_RESOLUTION = re.compile(r"^(\d+)x(\d+)$", re.I)

# the rungs the stack climbs, as fractions of the frame height. the top gap is
# deliberately shorter than the other two, so the sung line eases off the top
_SLOTS = (0.3704, 0.4815, 0.6111, 0.7407)

_STYLES = ("Current", "Next", "Next2")
_ALPHAS = ("&H00", "&H88", "&H66") # 00 is opaque, FF invisible
_OUTLINES = (3, 2, 1)
_SHADOWS = (3, 2, 1)
_BOLDS = (-1, 0, 0) # -1 is true in ASS; only the sung line carries the weight

_TRANSITION_MS = 300 # the rise runs at the END of a line, setting up the next one
_FADE_IN_MS = 100    # only a line entering the stack for the first time fades in
_FADE_OUT_MS = 300
_BASE_HEIGHT = 1080  # the height the configured font sizes are written for

_HEADER = """[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.601
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

    for i, line in enumerate(lines):
        start, end = _timestamp(line.start), _timestamp(line.end)
        duration = int(max(line.end - line.start, 0.1) * 1000)
        rise = min(_TRANSITION_MS, duration // 2) # a short line still gets half of one
        begin = duration - rise if duration > rise else 0
        fade_in = min(_FADE_IN_MS, duration // 2)
        fade_out = min(_FADE_OUT_MS, duration // 2)

        for offset, style in enumerate(_STYLES):
            if i + offset >= len(lines):
                break # the tail of the song has nothing left to preview
            move = rf"\move({x},{slots[offset + 1]},{x},{slots[offset]},{begin},{duration})"
            # the sung line dims as it leaves; a new arrival appears from nothing.
            # the middle slot never fades - it is already on screen either way
            fade = (rf"\fad(0,{fade_out})" if offset == 0 else
                    rf"\fad({fade_in},0)" if offset == 2 else "")
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
        f"{alpha}FFFFFF,&H00FFFFFF,&H00000000,&H00000000,"
        f"{bold},0,0,0,100,100,0,0,1,{round(outline * scale)},{round(shadow * scale)},"
        f"2,10,10,10,1"
        for name, size, alpha, outline, shadow, bold
        in zip(_STYLES, sizes, _ALPHAS, _OUTLINES, _SHADOWS, _BOLDS))
    return _HEADER.format(width=width, height=height, styles=styles)

def _timestamp(seconds: float) -> str:
    total = max(round(seconds * 100), 0) # centiseconds, so 59.999 cannot round to :60
    hours, rest = divmod(total, 360000)
    minutes, rest = divmod(rest, 6000)
    secs, centis = divmod(rest, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", r"\{").replace("}", r"\}")
