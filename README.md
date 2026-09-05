# The Clip Snipper

A self-hosted, 100% open-source tool that automatically repurposes YouTube videos into short, viral vertical clips (9:16). No API costs.

## How It Works

```
YouTube URL
  → yt-dlp downloads audio (fast) + full video (background)
  → faster-whisper transcribes audio with sentence + word-level timestamps
  → Ollama (Llama 3.2) analyzes transcript and picks 5 viral segments
  → MoviePy + FFmpeg cut → 9:16 crop that TRACKS THE SPEAKER'S FACE (MediaPipe)
  → Karaoke-style captions burned in: active word highlights yellow as spoken
  → Clips shown on the web UI with in-page preview + Download buttons
```

## Professional Features

**1. Face Tracking / Auto-Reframe** — instead of a blind center-crop, MediaPipe detects faces across the clip, the crop window is EMA-smoothed, and the 9:16 window *follows* the speaker. If no face is detected, it falls back to center-crop. (Source: `backend/tracker.py`, applied in `backend/editor.py`)

**2. Word-Level Timestamps** — faster-whisper now runs with `word_timestamps=True`. Every transcript segment includes per-word `start`/`end`/`word` (saved to `transcript.json`). Used by the caption engine. (`backend/transcriber.py`, `backend/captions.py`)

**3. Karaoke-Style Captions** — captions are rendered as ASS subtitles burned via libass. The current word is highlighted in bright yellow as it's spoken; text sits in the bottom **safe zone** (left/center, outside TikTok/Reels right-side buttons) with a bold 56px font, black outline. Highlight color is tunable via `HIGHLIGHT_COLOR` in `backend/captions.py`.

## Stack

- **Backend:** FastAPI + uvicorn
- **Downloading:** yt-dlp + FFmpeg
- **Transcription:** faster-whisper (local, `base` model / int8, word timestamps)
- **AI Selection:** Ollama running llama3.2 locally
- **Face Tracking:** MediaPipe
- **Editing:** MoviePy + FFmpeg + libass
- **Frontend:** Streamlit

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and on `PATH`
- [Ollama](https://ollama.com/) installed and running
- Pull the LLM model once:
  ```bash
  ollama pull llama3.2
  ```

## Installation

```bash
python -m venv venv
source venv/bin/activate

# Backend deps
pip install -r requirements.txt

# Frontend deps
pip install -r requirements-streamlit.txt
```

## Run It

Terminal 1 — backend:
```bash
./run_backend.sh
# or: uvicorn main:app --host 0.0.0.0 --port 8000 (in backend/)
```

Terminal 2 — frontend:
```bash
./run_frontend.sh
# or: streamlit run app.py (in frontend/)
```

Then open **http://localhost:8501**, paste a YouTube URL, and hit **Snip It!**

## Project Structure

```
├── backend/
│   ├── main.py        # FastAPI app + job queue
│   ├── extractor.py   # yt-dlp audio/video download
│   ├── transcriber.py # faster-whisper transcription (word-level)
│   ├── brain.py       # Ollama clip selection
│   ├── editor.py      # MoviePy/FFmpeg cut + face-tracked crop + ASS burn
│   ├── tracker.py     # MediaPipe face detection + EMA-smoothed trajectory
│   ├── captions.py    # ASS karaoke captions (word highlight, safe zone)
│   └── models.py      # Pydantic models
├── frontend/
│   └── app.py         # Streamlit UI
├── outputs/           # Each job gets its own folder
├── temp/              # Working files
├── requirements.txt
├── run_backend.sh
└── run_frontend.sh
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/submit` | Submit a YouTube URL `{"url": "..."}` → `{job_id}` |
| GET | `/api/status/{job_id}` | Poll job progress |
| GET | `/api/clips/{job_id}` | List generated clips + download URLs |
| GET | `/api/download/{job_id}/{file}` | Download a clip MP4 |
| GET | `/api/health` | Health check |

## Tuning

- **Transcription speed/accuracy:** change the Whisper model in `transcriber.py` (`base` → `small`, `medium`, `large-v3`). Larger = slower but more accurate.
- **Face tracking:** tune `sample_step` and the EMA `alpha` in `tracker.py`. Lower `sample_step` = smoother but slower. If faces are frequently missed, lower `min_detection_confidence`.
- **Caption style:** adjust `MAX_CHUNK_WORDS`, `HIGHLIGHT_COLOR`, font size, and safe-zone margins in `captions.py`. Set `CAPTION_FONT` env var to use Montserrat (install the font on the system).
- **Mapping/verification:** if Ollama returns clip boundaries that drift slightly, context interval in `brain.py` prompt will keep it aligned since timestamps are embedded per line.
- **Clip count:** change "5 segments" in the `brain.py` prompt.

## Notes

- Clips are rendered at 1080×1920 (9:16), H.264 + AAC.
- Captions are karaoke-style: white text with the active word highlighted in yellow, in the bottom safe zone (clear of Reels/TikTok buttons), bold 56px with a black outline.
- Face tracking gracefully falls back to center-crop if MediaPipe isn't installed or no faces are found.
- The audio download enables instant transcription while the full video downloads; editing waits for the full video to finish.
- Output files land in `outputs/<job_id>/`, including the full transcript JSON (with word timestamps) and per-clip `.ass`/`.srt` files.
- **Not built yet (future work):** automatic emoji/keyword callouts and B-roll insertion at salient keywords ("Money" → 💰). Recommended roadmap: enrich `tracker.py`/`captions.py` stays, add a keyword→emoji map applied inside the ASS renderer, then an FFmpeg `overlay`/concat pass for B-roll stills.