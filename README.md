# Karaoke Video Creation Pipeline

This repository contains a proof-of-concept pipeline that automatically generates a karaoke video with word-by-word highlighted lyrics.

## Features

* Fetches time-synchronized lyrics (LRC format) with **syncedlyrics**
* Converts LRC to ASS subtitles with karaoke effects (word highlighting)
* Separates vocals to create an instrumental backing track
* Combines instrumental audio, subtitles, and a background into a final **MP4** karaoke video using **FFmpeg**
* Optional additions: download audio from YouTube, Japanese lyric romanization, Whisper-based alignment

## Quick Start

1. **Clone** the repository and create a Python virtual environment (recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install Python dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg** (required for video processing):

   * **macOS** (Homebrew): `brew install ffmpeg`
   * **Ubuntu / Debian**: `sudo apt-get update && sudo apt-get install ffmpeg`
   * **Windows**: Download a static build from <https://ffmpeg.org/download.html>, add the `bin` folder to your `PATH`.

4. Launch a **JupyterLab** session (optional, useful for experimentation):

   ```bash
   jupyter lab
   ```

5. Follow the tasks in `.taskmaster/tasks/tasks.json` to implement each part of the pipeline (starting with environment setup—already covered by this README).

---

## External Dependencies

| Tool        | Purpose                                   | Install Method                           |
|-------------|-------------------------------------------|------------------------------------------|
| FFmpeg      | Video generation & subtitle burn-in       | System package manager / static binary   |
| UVR-MDX or Spleeter models | Vocal / instrumental separation | Downloaded automatically by `audio-separator` on first run |

GPU acceleration is optional but recommended for faster audio separation. Consult the `audio-separator` documentation for CUDA-enabled installation instructions.

---

## Next Steps

After installing the dependencies, proceed with Task 2 (**Implement Audio Input and Metadata Handling**) in the Taskmaster list:

```bash
task-master next    # shows the next actionable task
```

Happy singing! 🎤 