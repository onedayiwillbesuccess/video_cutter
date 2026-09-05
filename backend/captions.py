import os

MAX_CHUNK_WORDS = 5
PLAY_RES_X = 1080
PLAY_RES_Y = 1920

HIGHLIGHT_COLOR = "&H0000FFFF"  # BGR: bright yellow
BASE_COLOR = "&H00FFFFFF"       # white
OUTLINE_COLOR = "&H00000000"    # black

DEFAULT_FONT = os.environ.get("CAPTION_FONT", "Arial")


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
    return f"""[Script Info]
ScriptType: v4.00+
Collisions: Normal
PlayResX: {PLAY_RES_X}
PlayResY: {PLAY_RES_Y}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{DEFAULT_FONT},56,&H00FFFFFF,&H0000FFFF,&H00000000,&H96000000,-1,0,0,0,100,100,0,0,1,3,0,2,80,250,120,1
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
        text.replace("{", "(")
        .replace("}", ")")
        .replace("\n", " ")
        .strip()
    )


def _build_chunk_lines(chunk: list[dict]) -> list[str]:
    chunk_start = chunk[0]["start"]
    chunk_end = chunk[-1]["end"]
    base_text = " ".join(_word_escaped(w["word"]) for w in chunk)

    lines = []

    dialogue = (
        f"Dialogue: 0,{_ass_time(chunk_start)},{_ass_time(chunk_end)},"
        f"Default,,0,0,0,,{base_text}"
    )
    lines.append(dialogue)

    for i, w in enumerate(chunk):
        w_start = w["start"]
        w_end = w["end"]
        parts = []
        for j, other in enumerate(chunk):
            word_text = _word_escaped(other["word"])
            if j == i:
                parts.append(f"{{\\c{HIGHLIGHT_COLOR}}}{word_text}{{\\c{BASE_COLOR}}}")
            else:
                parts.append(f"{{\\alpha&HFF&}}{word_text}{{\\alpha&H00&}}")
        highlight_line = " ".join(parts)
        lines.append(
            f"Dialogue: 0,{_ass_time(w_start)},{_ass_time(w_end)},"
            f"Default,,0,0,0,,{highlight_line}"
        )

    return lines


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