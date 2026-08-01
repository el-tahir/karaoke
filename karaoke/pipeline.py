"""
runs every stage in order and hands back the finished videos
"""

import logging
import shutil
from pathlib import Path


from karaoke import ass, download, lrc, lyrics, meta, render, separate
from karaoke.config import Config
from karaoke.errors import KaraokeError

log = logging.getLogger(__name__)

_ENCODINGS = ("utf-8-sig", "cp932", "latin-1") # latin-1 maps every byte, so it ends

def _read(path: Path) -> str:
    """lyrics.py copies raw bytes, because not all .lrc files are utf-8"""
    raw = path.read_bytes()
    for encoding in _ENCODINGS[:-1]:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode(_ENCODINGS[-1])


def run(query: str, cfg: Config, *, lrc_file: Path | None = None,
    instrumental_only: bool = False, force: bool = False) -> dict[str, Path]:

        song, wd = meta.get_song(query, cfg.work_dir, cfg)

        if force:
            log.info("clearing %s", wd)
            shutil.rmtree(wd, ignore_errors=True)
            wd.mkdir(parents=True, exist_ok=True)

        #lyrics first: they are cheapest, if fails, pipeline fails fast
        lrc_path = lyrics.get_lyrics(song, wd, lrc_file)
        lines = lrc.parse(_read(lrc_path))
        if not lines:
            raise KaraokeError(f"no timed lines in {lrc_path}; pass --lrc-file for supply your own")

        subs = wd / "subs.ass"
        subs.write_text(ass.build(lines, cfg), encoding = "utf-8")
        log.info("subtitles ready : %s (%d lines)", subs, len(lines))

        audio = download.download(song, wd, cfg)
        instrumental = audio if instrumental_only else separate.separate(audio, wd, cfg)

        out = {"karaoke" : render.render(instrumental, subs,
            cfg.out_dir / f"{wd.name}_karaoke.mp4", cfg)}

        if cfg.both_versions and not instrumental_only:
            out["original"] = render.render(audio, subs, cfg.out_dir / f"{wd.name}_original.mp4", cfg)

        return out
