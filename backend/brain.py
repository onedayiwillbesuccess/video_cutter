import json
import re

import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:1b"

FALLBACK_CLIPS = [
    {"start_time": 0.0, "end_time": 30.0, "title": "Default Clip"},
]


def _build_prompt(full_text: str) -> str:
    return f"""You are a viral video editor for short-form vertical video (TikTok, Reels, Shorts).

Below is a transcript from a YouTube video with timestamps. Analyze it and pick 3-5 high-impact clips.
Each clip must be under 60 seconds, start with a strong hook, and contain a complete thought.

TRANSCRIPT:
{full_text}

RETURN ONLY A JSON ARRAY. DO NOT EXPLAIN. NO MARKDOWN. NO EXTRA TEXT.
Format:
[
  {{"start_time": 12.5, "end_time": 45.0, "title": "Clip Title"}},
  {{"start_time": 50.0, "end_time": 80.0, "title": "Clip Title"}}
]"""


def _parse_json_response(raw_content: str) -> list:
    raw_content = raw_content.strip()

    try:
        parsed = json.loads(raw_content)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    json_match = re.search(r"\[.*\]", raw_content, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group(0))
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            raise ValueError(f"Could not parse JSON from Ollama:\n{raw_content[:500]}")

    raise ValueError(f"No JSON array found in Ollama response:\n{raw_content[:500]}")


def _validate_clips(clips: list) -> list[dict]:
    validated = []
    for clip in clips:
        try:
            start = float(clip["start_time"])
            end = float(clip["end_time"])
            title = str(clip["title"])
        except (TypeError, KeyError, ValueError):
            continue
        if end <= start or end - start > 60:
            continue
        validated.append({
            "start_time": start,
            "end_time": end,
            "title": title,
        })
    return validated


def select_clips(transcript: list[dict]) -> list[dict]:
    full_text = ""
    for seg in transcript:
        full_text += f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}\n"

    payload = {
        "model": MODEL_NAME,
        "prompt": _build_prompt(full_text),
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.3,
            "num_predict": 1000,
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=600)
        resp.raise_for_status()

        raw_content = resp.json().get("response", "")
        clips = _parse_json_response(raw_content)
        validated = _validate_clips(clips)

        if not validated:
            print(f"Ollama returned invalid clips, using fallback. Raw:\n{raw_content[:500]}")
            return list(FALLBACK_CLIPS)

        return validated

    except Exception as e:
        print(f"Ollama Error: {str(e)}")
        return list(FALLBACK_CLIPS)