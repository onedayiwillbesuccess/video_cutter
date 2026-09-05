import os
import yt_dlp


def download_audio(url: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    audio_path = os.path.join(output_dir, "audio.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": audio_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "unknown")

    final_path = os.path.join(output_dir, "audio.mp3")
    if not os.path.exists(final_path):
        for f in os.listdir(output_dir):
            if f.startswith("audio.") and f.endswith((".mp3", ".m4a", ".wav", ".webm")):
                os.rename(os.path.join(output_dir, f), final_path)
                break

    return final_path, title


def download_video(url: str, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    video_path = os.path.join(output_dir, "full_video.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "outtmpl": video_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(url, download=True)

    final_path = os.path.join(output_dir, "full_video.mp4")
    if not os.path.exists(final_path):
        for f in os.listdir(output_dir):
            if f.startswith("full_video.") and f.endswith((".mp4", ".mkv", ".webm")):
                os.rename(os.path.join(output_dir, f), final_path)
                break

    return final_path
