import json
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2"


def select_clips(transcript: list[dict]) -> list[dict]:
    full_text = ""
    for seg in transcript:
        full_text += f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}\n"

    prompt = f"""Act as a viral content editor for short-form vertical video (TikTok, Reels, Shorts).

Below is a transcript from a YouTube video with timestamps. Analyze it and identify the 5 best segments to cut into standalone viral clips. Each clip must:
- Be under 60 seconds
- Start with a strong "hook" (question, bold statement, surprising fact)
- Contain a complete thought or story arc
- Have high emotional or informational impact

TRANSCRIPT:
{full_text}

Return ONLY a valid JSON array of objects with exactly these keys:
"start_time" (float, seconds), "end_time" (float, seconds), "title" (string, max 8 words).

Example:
[
  {{"start_time": 12.5, "end_time": 45.3, "title": "Why Most People Fail at Dieting"}},
  ...
]

No markdown, no explanation. ONLY the JSON array."""

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 2048,
        },
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()

    raw = resp.json().get("response", "")

    json_start = raw.find("[")
    json_end = raw.rfind("]") + 1
    if json_start == -1 or json_end <= 0:
        raise ValueError(f"Could not parse JSON from Ollama response:\n{raw[:500]}")

    clips = json.loads(raw[json_start:json_end])

    validated = []
    for clip in clips:
        validated.append({
            "start_time": float(clip["start_time"]),
            "end_time": float(clip["end_time"]),
            "title": str(clip["title"]),
        })

    return validated
