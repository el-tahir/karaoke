"""Audio source utilities – *enhanced version*.

Handles audio input validation and YouTube downloads with yt‑dlp.  This
revision adds robust cookie handling to bypass YouTube’s anti‑bot page and
clarifies error messages when authentication is required.

Key **enhancements**:
    • Accept cookies in three forms:
        1. **Browser extraction** – pass `cookies="browser:chrome"` (or
           firefox, edge…) to let yt‑dlp pull cookies from the local browser.
        2. **Path** to an existing cookies.txt.
        3. **Raw Netscape cookie string** – we write a temp file.
    • Also reads from `YOUTUBE_COOKIES` env var as before.
    • Graceful fallback & actionable error if YouTube blocks download.
    • Cache‑key unchanged (URL) so no behaviour change once download ok.
"""
from __future__ import annotations

import logging
import os
import random
import tempfile
import time
from pathlib import Path
from typing import Optional

import yt_dlp
from yt_dlp.utils import DownloadError

from . import config
from .cache import cache_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validation helper
# ---------------------------------------------------------------------------

def validate_audio_file(path_str: str) -> Path:
    """Ensure the given path exists and is a supported audio format."""
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {path}")
    if path.suffix.lower() not in config.AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format '{path.suffix}'. Supported formats: {', '.join(config.AUDIO_EXTENSIONS)}"
        )
    return path


# ---------------------------------------------------------------------------
# YouTube download with cookie handling
# ---------------------------------------------------------------------------

def _attach_cookie_options(opts: dict, cookies_source: str) -> Optional[str]:
    """Add appropriate yt‑dlp cookie options. Returns temp file path if any."""
    temp_cookie_file: Optional[str] = None

    if cookies_source.startswith("browser:"):
        # syntax: browser:chrome OR browser:firefox:profile_name
        parts = cookies_source.split(":", 2)
        browser = parts[1] or "chrome"
        profile = parts[2] if len(parts) > 2 else None
        opts["cookiesfrombrowser"] = (browser,) if profile is None else (browser, profile)
        logger.info(f"Using cookies from local browser: {opts['cookiesfrombrowser']}")

    elif cookies_source.startswith("# Netscape") or "\t" in cookies_source:
        # Raw cookie text – write temp file
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        tf.write(cookies_source)
        tf.flush()
        tf.close()
        opts["cookiefile"] = tf.name
        temp_cookie_file = tf.name
        logger.info("Using raw cookies via temporary file")

    else:
        # Treat as path
        cookie_path = Path(cookies_source).expanduser()
        if cookie_path.exists():
            opts["cookiefile"] = str(cookie_path)
            logger.info(f"Using cookies file: {cookie_path}")
        else:
            logger.warning("Cookie source provided but file not found – ignoring")

    return temp_cookie_file


def download_from_youtube(url: str, cookies: Optional[str] = None) -> Path:
    """Download (and cache) audio from a YouTube URL.

    Parameters
    ----------
    url : str
        The YouTube video or music URL.
    cookies : str | None, optional
        * "browser:chrome" (or firefox/edge) → use local browser profile
        * Path to cookies.txt → use that file
        * Raw Netscape cookie string → temp‑file it
        * None → fall back to $YOUTUBE_COOKIES env var or unauthenticated
    """
    # -------------------------------------------------------------------
    # Cache first
    # -------------------------------------------------------------------
    try:
        cached_audio = cache_manager.get_cached_audio(url)
        if cached_audio:
            return cached_audio
    except (FileNotFoundError, RuntimeError) as e:
        logger.warning(f"Cache lookup failed – will redownload: {e}")

    # polite random delay (helps avoid rate‑limits)
    time.sleep(random.uniform(1, 3))

    opts = config.YDL_OPTS.copy()

    # -------------------------------------------------------------------
    # Cookies handling
    # -------------------------------------------------------------------
    cookies_source = cookies or os.getenv("YOUTUBE_COOKIES")
    temp_cookie_file = None
    if cookies_source:
        temp_cookie_file = _attach_cookie_options(opts, cookies_source)

    # -------------------------------------------------------------------
    # Actual download
    # -------------------------------------------------------------------
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)

    except DownloadError as e:
        # Provide a clearer error when YouTube demands login
        msg = str(e)
        if "confirm you’re not a bot" in msg or "Sign in to confirm" in msg:
            raise RuntimeError(
                "YouTube blocked the download – supply cookies via the `cookies` "
                "argument or YOUTUBE_COOKIES environment variable. See yt‑dlp docs."
            ) from e
        raise  # propagate other yt‑dlp errors

    finally:
        if temp_cookie_file and Path(temp_cookie_file).exists():
            os.unlink(temp_cookie_file)

    # -------------------------------------------------------------------
    # Resolve file path & cache
    # -------------------------------------------------------------------
    if info.get("_type") == "playlist":
        entries = info.get("entries") or []
        if not entries:
            raise RuntimeError("YouTube playlist returned no entries.")
        info = entries[0]

    requested = info.get("requested_downloads") or []
    if requested:
        filepath = requested[0].get("filepath")
        if filepath and Path(filepath).exists():
            audio_path = Path(filepath).resolve()
            try:
                cache_manager.cache_audio(url, audio_path)
            except (FileNotFoundError, RuntimeError) as e:
                logger.warning(f"Audio caching failed (non‑fatal): {e}")
            return audio_path

    # Some extractors might not populate requested_downloads – fall back
    fallback = config.DOWNLOADS_DIR / f"{info['title']}.mp3"
    if fallback.exists():
        audio_path = fallback.resolve()
        try:
            cache_manager.cache_audio(url, audio_path)
        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"Audio caching failed (non‑fatal): {e}")
        return audio_path

    raise RuntimeError("yt‑dlp finished but no downloaded file path could be determined.")
