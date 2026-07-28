"""
gets song metadata from youtube url or query
tries to use official youtube music track as source of truth
"""

import json
import logging
import re
from dataclasses import asdict
from pathlib import Path
from urllib.parse import quote

from yt_dlp import YoutubeDL
from yt_dlp.utils import YoutubeDLError

from karaoke.config import Config
from karaoke.errors import KaraokeError
from karaoke.models import Song
from karaoke.paths import work_dir_for

log = logging.getLogger(__name__)
_URL = re.compile(r"^https?://([\w-]+\.)*(youtube\.com|youtu\.be)/", re.I)
_BRACKETED = re.compile(r"[(\[{][^)\]}]*[)\]}]")
_SEP = re.compile(r"\s+[-–—|]\s+")
_TOPIC = re.compile(r"\s*-\s*Topic$", re.I)

def parse_title(title: str) -> tuple[str, str] | None:
    parts = _SEP.split(_BRACKETED.sub(" ", title), maxsplit=1)
    if len(parts) != 2:
        return None
    artist, track = [p.strip(" \t\"'") for p in parts]
    return (artist, track) if artist and track else None

def _ydl_opts(cfg: Config, **extra) -> dict:
    opts = {"quiet": True, "no_warnings": True}
    if cfg.cookie_file:
        opts["cookiefile"] = str(cfg.cookie_file)
    if cfg.cookies_from_browser:
        opts["cookiesfrombrowser"] = (cfg.cookies_from_browser, )
    return opts | extra

def _extract(url: str, cfg: Config, **extra) -> dict:
    try:
        with YoutubeDL(_ydl_opts(cfg, **extra)) as ydl:
            info = ydl.extract_info(url, download=False)
    except YoutubeDLError as e:
        raise KaraokeError(f"could not fetch metadata for {url}: {e}") from e
    if not info:
        raise KaraokeError(f"no metadata return for {url}")
    return info

def _search(query: str, cfg: Config) -> str:
    url = "https://music.youtube.com/search?q=" + quote(query, safe="") # AC/DC would break the url
    info = _extract(url, cfg, extract_flat=True, playlistend=1)
    entries = info.get("entries") or []
    if not entries or not entries[0].get("url"):
        raise KaraokeError(f"no results for {query!r}")
    return entries[0]["url"]

def _is_official_track(info: dict) -> bool:
    return bool((info.get("artist") or "").strip() and (info.get("track") or "").strip())

def _search_terms(info: dict) -> str:
    title = (info.get("title") or "").strip()
    if parsed := parse_title(title):
        return f"{parsed[0]} {parsed[1]}"
    uploader = _TOPIC.sub("", (info.get("uploader") or "")).strip()
    return f"{uploader} {title}".strip() or title

def _identify(info: dict) -> tuple[str, str]:
    artist = (info.get("artist") or "").strip()
    track = (info.get("track") or "").strip()
    if artist and track:
        return artist, track

    title = (info.get("title") or "").strip()
    if parsed := parse_title(title):
        return parsed

    uploader = (info.get("uploader") or info.get("channel") or "").strip()
    uploader = _TOPIC.sub("", uploader).strip()

    if not (uploader or title):
        raise KaraokeError(f"no usable metadata for {info.get('webpage_url')}")
    return uploader or "Unknown", title or "Unknown"

def _write_json(path: Path, data: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)

def get_song(query: str, work_dir_root: Path, cfg: Config) -> tuple[Song, Path]:
    query = query.strip()

    if _URL.match(query):
        info = _extract(query, cfg)
        if not _is_official_track(info):
            terms = _search_terms(info)
            log.info("not an official track; searching YouTube Music for %r", terms)
            candidate = _extract(_search(terms, cfg), cfg)
            if _is_official_track(candidate):
                info = candidate
            else:
                log.warning("no official track found for %r; using the original", terms)
    else:
        info = _extract(_search(query, cfg), cfg)

    artist, track = _identify(info)

    song = Song(
        artist=artist,
        track=track,
        url=info.get("webpage_url") or query,
        duration=info.get("duration"),
    )
    work_dir = work_dir_for(work_dir_root, artist, track)
    work_dir.mkdir(parents=True, exist_ok=True)
    _write_json(work_dir / "song.json", asdict(song))
    log.info("resolved %r -> %s - %s", query, artist, track)
    return song, work_dir
