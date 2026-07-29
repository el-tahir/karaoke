"""
shared yt-dlp options; both meta.py and download.py need the same auth
"""

from karaoke.config import Config

def ydl_opts(cfg: Config, **extra) -> dict:
    opts = {"quiet": False,
            "no_warnings": True,
            "source_address" : "0.0.0.0" #force ipv4 - ipv6 dead on my machine :(
    }
    if cfg.cookie_file:
        opts["cookiefile"] = str(cfg.cookie_file)
    if cfg.cookies_from_browser:
        opts["cookiesfrombrowser"] = (cfg.cookies_from_browser,)
    return opts | extra
