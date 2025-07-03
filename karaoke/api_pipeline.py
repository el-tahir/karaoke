"""API-specific pipeline logic for streaming progress updates."""
from __future__ import annotations

import argparse
import logging
from typing import Generator

from .pipeline import KaraokePipeline

logger = logging.getLogger(__name__)

def run_pipeline_streaming(args: argparse.Namespace) -> Generator[str, None, None]:
    """
    Run the karaoke pipeline, yielding progress updates as Server-Sent Events.
    """
    pipeline = KaraokePipeline(
        track=getattr(args, 'track', None),
        artist=getattr(args, 'artist', None),
        file_path=getattr(args, 'file', None),
        youtube_url=getattr(args, 'youtube_url', None),
        cookies=getattr(args, 'cookies', None),
        resolution=getattr(args, 'resolution', None),
        background=getattr(args, 'background', None),
    )
    return pipeline.run_streaming()
 