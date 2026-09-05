import os
import json
import uuid
import shutil
import threading
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from models import SubmitRequest, JobStatus, ClipResult
from extractor import download_audio, download_video
from transcriber import transcribe
from brain import select_clips
from editor import cut_clip

app = FastAPI(title="The Clip Snipper API")

if shutil.which("ffmpeg") is None:
    print("WARNING: ffmpeg not found on PATH. Video processing will fail. Install ffmpeg first.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "..", "outputs")

jobs: dict[str, JobStatus] = {}


def _download_video_safe(url: str, job_dir: str, error_store: dict):
    try:
        download_video(url, job_dir)
    except Exception as e:
        error_store["msg"] = str(e)


def _run_pipeline(job_id: str, url: str):
    job_dir = os.path.join(OUTPUTS_DIR, job_id)

    try:
        job = jobs[job_id]
        job.status = "processing"

        job.step = "downloading_audio"
        job.message = "Downloading audio..."
        audio_path, title = download_audio(url, job_dir)

        video_error = {}
        video_thread = threading.Thread(
            target=_download_video_safe,
            args=(url, job_dir, video_error),
            daemon=True,
        )
        video_thread.start()

        job.step = "transcribing"
        job.message = "Transcribing audio with Whisper..."
        transcript = transcribe(audio_path)

        transcript_path = os.path.join(job_dir, "transcript.json")
        with open(transcript_path, "w") as f:
            json.dump(transcript, f, indent=2)

        job.step = "selecting_clips"
        job.message = "Asking Ollama to select viral clips..."
        clips = select_clips(transcript)

        job.step = "downloading_video"
        job.message = "Waiting for full video download..."
        video_thread.join()
        if video_error:
            raise RuntimeError(
                f"Could not get video track for editing: {video_error['msg']}"
            )

        video_path = os.path.join(job_dir, "full_video.mp4")
        if not os.path.exists(video_path):
            raise RuntimeError(
                "Full video file was not produced. This source may be audio-only "
                "(e.g. a podcast) or the download was interrupted."
            )

        job.step = "editing"
        job.message = "Cutting and processing clips..."
        clip_paths = []
        for i, clip in enumerate(clips):
            job.message = f"Processing clip {i + 1}/{len(clips)}: {clip['title']}"
            output_path = os.path.join(job_dir, f"clip_{i + 1}.mp4")
            cut_clip(
                video_path=video_path,
                start_time=clip["start_time"],
                end_time=clip["end_time"],
                output_path=output_path,
                transcript_segments=transcript,
            )
            clip_paths.append(output_path)

        job.step = "done"
        job.status = "completed"
        job.progress = 1.0
        job.message = f"Done! {len(clips)} clips ready."
        job.clips = [ClipResult(**c) for c in clips]
        job.output_dir = job_dir

    except Exception as e:
        job = jobs[job_id]
        job.status = "failed"
        job.message = f"Error: {str(e)}"
        job.step = "error"
        traceback.print_exc()


@app.post("/api/submit")
def submit_job(req: SubmitRequest):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = JobStatus(
        job_id=job_id,
        status="queued",
        step="starting",
        progress=0.0,
        message="Job queued...",
    )

    thread = threading.Thread(target=_run_pipeline, args=(job_id, req.url), daemon=True)
    thread.start()

    return {"job_id": job_id, "message": "Job submitted"}


@app.get("/api/status/{job_id}")
def get_status(job_id: str) -> JobStatus:
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@app.get("/api/clips/{job_id}")
def list_clips(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job.status != "completed":
        raise HTTPException(status_code=400, detail=f"Job is {job.status}")

    clips_dir = job.output_dir
    clips = []
    for i, clip_info in enumerate(job.clips):
        clip_file = os.path.join(clips_dir, f"clip_{i + 1}.mp4")
        if os.path.exists(clip_file):
            clips.append({
                "index": i + 1,
                "title": clip_info.title,
                "start_time": clip_info.start_time,
                "end_time": clip_info.end_time,
                "download_url": f"/api/download/{job_id}/clip_{i + 1}.mp4",
            })

    return {"clips": clips}


@app.get("/api/download/{job_id}/{filename}")
def download_file(job_id: str, filename: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    file_path = os.path.join(OUTPUTS_DIR, job_id, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="video/mp4",
        filename=filename,
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "The Clip Snipper"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
