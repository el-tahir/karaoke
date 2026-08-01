import json
from dataclasses import dataclass, fields
from pathlib import Path

from karaoke.errors import KaraokeError

_PATH_FIELDS = ("work_dir", "out_dir", "cookie_file", "model_dir")  # to tell json loader which fields are Path objects

@dataclass
class Config:
    work_dir: Path = Path("work")
    out_dir: Path = Path("out")
    resolution: str = "1920x1080"
    fps: int = 30
    background: str = "black"
    both_versions: bool = True
    font: str = "Montserrat"
    font_size: int = 90
    separation_model: str = "UVR-MDX-NET-Inst_HQ_4.onnx" # best model i found for speed / quality
    ffmpeg: str = "ffmpeg"
    cookie_file: Path | None = None
    cookies_from_browser: str | None = None
    model_dir: Path = Path("models")

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        if path is None:
            return cls()

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except OSError as e:
            raise KaraokeError(f"cannot read config {path}: {e}") from e
        except json.JSONDecodeError as e:
            raise KaraokeError(f"invalid JSON in {path}: {e}") from e

        if not isinstance(data, dict):
            raise KaraokeError(f"config {path} must be a JSON object")

        unknown = set(data) - {f.name for f in fields(cls)}
        if unknown:
            raise KaraokeError(f"unknown config keys: {', '.join(sorted(unknown))}")

        for key in _PATH_FIELDS:
            if data.get(key) is not None:
                data[key] = Path(data[key])

        return cls(**data)
