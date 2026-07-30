import logging
import time
from pathlib import Path

from audio_separator.separator import Separator

from karaoke.config import Config
from karaoke.errors import KaraokeError

log = logging.getLogger(__name__)

def separate(audio: Path, work_dir: Path, cfg: Config) -> Path:
    out = work_dir / "instrumental.wav"
    if out.exists() and out.stat().st_size:
        log.info("instrumental already separated: %s", out)
        return out

    if not (audio.exists() and audio.stat().st_size):
        raise KaraokeError(f"no audio to separate: {audio}")

    log.info("separating %s with %s", audio.name, cfg.separation_model)
    log.info("the first run downloads the model and is slow")
    t0 = time.monotonic()

    try:
        separator = Separator(
            output_dir=str(work_dir),
            output_format="WAV",
            model_file_dir=str(cfg.model_dir),
            log_level=logging.INFO,
        )
        separator.load_model(model_filename=cfg.separation_model)
        names = separator.separate(str(audio))
    except Exception as e:
        raise KaraokeError(f"could not separate {audio.name} : {e}") from e

    stems = [work_dir / name for name in names] # the library returns bare filenames
    instrumental = next((p for p in stems if "instrumental" in p.name.lower()), None)
    if not (instrumental and instrumental.exists() and instrumental.stat().st_size):
        raise KaraokeError(f"no instrumental stem produced for {audio.name}; got {names}")

    for stem in stems:
        if stem != instrumental:
            stem.unlink(missing_ok=True) # we dont need vocals

    instrumental.replace(out)
    log.info("instrumental ready: %s (%.1f MB, %.0fs)",
        out, out.stat().st_size / 1e6, time.monotonic() - t0)
    return out
