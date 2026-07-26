from dataclasses import dataclass, field

@dataclass
class Song:
    artist: str
    track: str
    url: str
    duration: float | None = None

@dataclass
class Line:
    start: float
    end: float
    text: str
