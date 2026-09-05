import os
import subprocess

import numpy as np
from PIL import Image
from moviepy import VideoFileClip

from captions import make_ass
from tracker import compute_face_trajectory

TARGET_WIDTH = 1080
TARGET_HEIGHT = 1920


def _format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _generate_srt(segments: list[dict], output_path: str) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{_format_srt_time(seg['start'])} --> {_format_srt_time(seg['end'])}")
        lines.append(seg["text"])
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_path


def _center_x_values(width: int, height: int, ext_times: list[float], traj):
    target_ratio = TARGET_WIDTH / TARGET_HEIGHT
    new_w = int(round(height * target_ratio))
    max_x = width - new_w

    if traj is not None:
        traj_times, traj_xs = traj
        window = np.interp(ext_times, traj_times, traj_xs)
        xs = window - new_w / 2.0
    else:
        xs = np.full(len(ext_times), (width - new_w) / 2.0)

    return np.clip(xs, 0, max_x)


def _tracked_crop(clip, ext_times: list[float], x_values: np.ndarray):
    def transform(get_frame, t):
        frame = get_frame(t)
        h, w = frame.shape[:2]
        target_ratio = TARGET_WIDTH / TARGET_HEIGHT

        if w / h > target_ratio:
            new_w = int(round(h * target_ratio))
            x1 = int(round(float(np.interp(t, ext_times, x_values))))
            x1 = min(max(x1, 0), w - new_w)
            cropped = frame[:, x1:x1 + new_w]
        else:
            new_h = int(round(w / target_ratio))
            y1 = (h - new_h) // 2
            cropped = frame[y1:y1 + new_h, :]

        img = Image.fromarray(cropped)
        img = img.resize((TARGET_WIDTH, TARGET_HEIGHT), Image.Resampling.LANCZOS)
        return np.array(img)

    return clip.transform(transform)


def _burn_captions(temp_path: str, ass_path: str, output_path: str) -> None:
    filter_path = ass_path.replace(":", "\\:")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-i", temp_path,
        "-vf", f"ass={filter_path}",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        output_path,
    ]
    subprocess.run(ffmpeg_cmd, capture_output=True, check=True)


def cut_clip(
    video_path: str,
    start_time: float,
    end_time: float,
    output_path: str,
    transcript_segments: list[dict],
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    clip_segments = []
    for seg in transcript_segments:
        if seg["end"] > start_time and seg["start"] < end_time:
            clip_segments.append({
                "start": max(seg["start"] - start_time, 0),
                "end": min(seg["end"] - start_time, end_time - start_time),
                "text": seg["text"],
                "words": [
                    {
                        "start": max(w["start"] - start_time, 0),
                        "end": min(w["end"] - start_time, end_time - start_time),
                        "word": w["word"],
                    }
                    for w in seg.get("words", [])
                    if w["end"] > start_time and w["start"] < end_time
                ],
            })

    srt_path = output_path.replace(".mp4", ".srt")
    _generate_srt(clip_segments, srt_path)

    video = VideoFileClip(video_path)
    sub = video.subclipped(start_time, end_time)

    fps = int(round(sub.fps or video.fps or 30))
    fps = min(max(fps, 1), 30)

    trajectory = None
    try:
        trajectory = compute_face_trajectory(sub)
    except Exception:
        trajectory = None

    width, height = sub.size
    if trajectory is not None:
        traj_times, traj_xs = trajectory
    else:
        traj_times, traj_xs = None, None

    ext_times = traj_times if traj_times is not None else [0.0, sub.duration]
    x_values = _center_x_values(
        width, height, ext_times,
        (traj_times, traj_xs) if traj_times is not None else None,
    )

    sub = _tracked_crop(sub, ext_times, x_values)

    temp_cropped = output_path.replace(".mp4", "_cropped.mp4")
    sub.write_videofile(
        temp_cropped,
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="fast",
        threads=4,
        logger=None,
    )

    ass_path = output_path.replace(".mp4", ".ass")
    make_ass(clip_segments, ass_path, start_offset=0.0)

    _burn_captions(temp_cropped, ass_path, output_path)

    if os.path.exists(temp_cropped):
        os.remove(temp_cropped)

    sub.close()
    video.close()

    return output_path