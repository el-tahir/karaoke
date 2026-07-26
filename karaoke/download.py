from pathlib import Path

from karaoke.config import Config
from karaoke.models import Song

def download(song: Song, work_dir: Path, cfg: Config) -> Path: ...
