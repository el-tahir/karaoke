"""Vocal separation utility.

Uses the `audio-separator` library (UVR-MDX models) to split an audio file
into instrumental and vocal stems. The instrumental file is persisted for
later use in video generation.

CLI Usage
---------
python -m karaoke.separate --file "song.mp3" [--output-dir ./stems]

or using the metadata file from `karaoke.input`:
python -m karaoke.separate --meta "song.meta.txt" [--output-dir ./stems]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

try:
    from audio_separator.separator import Separator  # type: ignore
except ImportError as err:  # pragma: no cover
    print("audio-separator is not installed. Run `pip install audio-separator`.", file=sys.stderr)
    raise err

from .input import validate_audio_file, parse_args as _unused  # for type reuse

DEFAULT_OUTPUT_DIR = Path("stems")


def separate(audio_path: Path, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Tuple[Path, Path]:
    """Run audio separation and return (instrumental_path, vocals_path)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # `audio-separator` expects `output_dir` and `output_format` as constructor
    # arguments.  Passing them here avoids mismatching positional parameters
    # in the `.separate()` call (which takes only the audio path).
    separator = Separator(output_dir=str(output_dir))
    separator.load_model()  # downloads model on first run if needed

    # Returns a list/tuple [instrumental_path, vocals_path]
    result_paths = separator.separate(str(audio_path))
    if not isinstance(result_paths, (list, tuple)) or len(result_paths) != 2:
        raise RuntimeError("Unexpected result from audio-separator: " f"{result_paths}")

    instrumental_path, vocals_path = result_paths

    # The `audio-separator` library sometimes returns file paths without the
    # output directory prefix (i.e. just the basename). This causes downstream
    # consumers to fail when they try to access the file from a different
    # working directory.  Normalise the returned paths so that they are always
    # absolute (or at least include the provided `output_dir`).

    instrumental_path = Path(instrumental_path)
    vocals_path = Path(vocals_path)

    if not instrumental_path.is_absolute():
        instrumental_path = output_dir / instrumental_path
    if not vocals_path.is_absolute():
        vocals_path = output_dir / vocals_path

    # Resolve to eliminate any "../" components and get a consistent absolute
    # representation.  We deliberately *do not* enforce the paths to exist
    # here, because the caller may want to mock the separator during tests.
    instrumental_path = instrumental_path.expanduser().resolve()
    vocals_path = vocals_path.expanduser().resolve()

    print("Instrumental saved to:", instrumental_path)
    print("Vocals saved to:", vocals_path)

    return instrumental_path, vocals_path


def _parse_meta(meta_path: Path) -> Path:
    text = meta_path.read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    file_path = values.get("file")
    if not file_path:
        raise ValueError("meta file missing 'file=' entry")
    return Path(file_path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:  # pragma: no cover
    p = argparse.ArgumentParser(description="Separate vocals and instrumentals using audio-separator")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to an audio file to process")
    group.add_argument("--meta", help="Path to .meta.txt from karaoke.input")
    p.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to save stems")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = parse_args(argv)

    if args.meta:
        meta_path = Path(args.meta).expanduser().resolve()
        if not meta_path.exists():
            print(f"Meta file not found: {meta_path}", file=sys.stderr)
            sys.exit(1)
        audio_path = _parse_meta(meta_path)
    else:
        audio_path = validate_audio_file(args.file)

    try:
        separate(audio_path, Path(args.output_dir))
    except Exception as err:
        print("Error during separation:", err, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main() 