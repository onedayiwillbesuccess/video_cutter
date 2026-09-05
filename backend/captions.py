import os
import shutil
import subprocess

MAX_CHUNK_WORDS = 5
PLAY_RES_X = 1080
PLAY_RES_Y = 1920

# Font preference order. libass matches whatever is actually installed on the
# server via fontconfig, so we avoid hard-failing on a single missing face.
FONT_FALLBACKS = ["Arial Black", "Liberation Sans Bold", "DejaVu Sans Bold", "Arial"]

STYLE_CONFIG = {
    "Fontname": "Arial Black",
    "Fontsize": 85,
    "PrimaryColour": "&H00FFFFFF",
    "SecondaryColour": "&H0000FFFF",
    "OutlineColour": "&H00000000",
    "BackColour": "&H96000000",
    "Bold": -1,
    "Italic": 0,
    "Underline": 0,
    "StrikeOut": 0,
    "ScaleX": 100,
    "ScaleY": 100,
    "Spacing": 2,
    "Angle": 0,
    "BorderStyle": 1,
    "Outline": 4,
    "Shadow": 0,
    "Alignment": 2,
    "MarginL": 80,
    "MarginR": 250,
    "MarginV": 450,
    "Encoding": 1,
}

DEFAULT_FONT = os.environ.get("CAPTION_FONT", "").strip()
if DEFAULT_FONT:
    STYLE_CONFIG["Fontname"] = DEFAULT_FONT
elif shutil.which("fc-list"):
    _installed_fonts = []
    try:
        _installed_fonts = subprocess.check_output(
            ["fc-list", ":", "family"], text=True, stderr=subprocess.DEVNULL
        ).lower()
    except Exception:
        _installed_fonts = []
    for _candidate in FONT_FALLBACKS:
        if _candidate.lower() in _installed_fonts:
            STYLE_CONFIG["Fontname"] = _candidate
            break

STYLE_FIELDS = (
    "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
    "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, "
    "Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
)


def _ass_time(seconds: float) -> str:
    seconds = max(seconds, 0)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _header() -> str:
    style_values = [
        "Default",
        STYLE_CONFIG["Fontname"],
        STYLE_CONFIG["Fontsize"],
        STYLE_CONFIG["PrimaryColour"],
        STYLE_CONFIG["SecondaryColour"],
        STYLE_CONFIG["OutlineColour"],
        STYLE_CONFIG["BackColour"],
        STYLE_CONFIG["Bold"],
        STYLE_CONFIG["Italic"],
        STYLE_CONFIG["Underline"],
        STYLE_CONFIG["StrikeOut"],
        STYLE_CONFIG["ScaleX"],
        STYLE_CONFIG["ScaleY"],
        STYLE_CONFIG["Spacing"],
        STYLE_CONFIG["Angle"],
        STYLE_CONFIG["BorderStyle"],
        STYLE_CONFIG["Outline"],
        STYLE_CONFIG["Shadow"],
        STYLE_CONFIG["Alignment"],
        STYLE_CONFIG["MarginL"],
        STYLE_CONFIG["MarginR"],
        STYLE_CONFIG["MarginV"],
        STYLE_CONFIG["Encoding"],
    ]
    style_line = ",".join(str(v) for v in style_values)

    return f"""[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayResX: {PLAY_RES_X}
PlayResY: {PLAY_RES_Y}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: {STYLE_FIELDS}
Style: {style_line}
"""


def _chunk_words(words: list[dict]) -> list[list[dict]]:
    chunks = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= MAX_CHUNK_WORDS:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def _word_escaped(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("{", "(")
        .replace("}", ")")
        .replace("\n", " ")
        .strip()
        .upper()
    )


def _build_chunk_lines(chunk: list[dict]) -> list[str]:
    chunk_start = chunk[0]["start"]
    chunk_end = chunk[-1]["end"]

    karaoke_parts = []
    cumulative = 0
    for w in chunk:
        dur_cs = max(int(round((w["end"] - w["start"]) * 100)), 0)
        karaoke_parts.append(f"{{\\k{dur_cs}}}{_word_escaped(w['word'])}")
        cumulative += dur_cs

    line_text = " ".join(karaoke_parts)

    return [
        f"Dialogue: 0,{_ass_time(chunk_start)},{_ass_time(chunk_end)},"
        f"Default,,0,0,0,,{line_text}"
    ]


def _fallback_words_from_segments(segments: list[dict]) -> list[dict]:
    words = []
    for seg in segments:
        text = seg["text"].split()
        if not text:
            continue
        dur = seg["end"] - seg["start"]
        per_word = dur / len(text)
        for i, token in enumerate(text):
            words.append({
                "start": round(seg["start"] + i * per_word, 2),
                "end": round(seg["start"] + (i + 1) * per_word, 2),
                "word": token,
            })
    return words


def make_ass(segments: list[dict], output_path: str, start_offset: float = 0.0) -> str:
    words = []
    for seg in segments:
        words.extend(seg.get("words", []))

    if not words:
        words = _fallback_words_from_segments(segments)

    local_words = [
        {
            "start": max(w["start"] - start_offset, 0.0),
            "end": max(w["end"] - start_offset, 0.0),
            "word": w["word"],
        }
        for w in words
        if w["end"] > start_offset and w["start"] < w["end"]
    ]

    body = []
    for chunk in _chunk_words(local_words):
        body.extend(_build_chunk_lines(chunk))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(_header())
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
        f.write("\n".join(body))
        f.write("\n")

    return output_path