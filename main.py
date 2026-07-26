import argparse
import logging
import sys
from pathlib import Path

from karaoke.config import Config
from karaoke.errors import KaraokeError

log = logging.getLogger(__name__)

def parse_args(argv : list[str] | None = None) -> argparse.Namespace:

    p = argparse.ArgumentParser(prog="kara", description="generate karaoke videos.")
    p.add_argument("input", help="search term or URL")
    p.add_argument("--config", type=Path, help="JSON config file")
    p.add_argument("--lrc-file", type=Path, help="use this .lrc instead of fetching")
    p.add_argument("--instrumental-only", action="store_true", help="skip the original-audio video")
    p.add_argument("--force", action="store_true", help="rebuild all stages, ignoring cached artifacts")
    p.add_argument("-v", "--verbose", action="store_true", help="debug logging")

    return p.parse_args(argv)

def main(argv : list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        cfg = Config.load(args.config)
        print("args:", vars(args))
        print("config:", cfg)
    except KaraokeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        log.debug("unexpected failure", exc_info=True)
        print(f"unexpected error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
