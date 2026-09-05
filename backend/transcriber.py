from faster_whisper import WhisperModel


_model = None


def _get_model():
    global _model
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def transcribe(audio_path: str) -> list[dict]:
    model = _get_model()
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        word_timestamps=True,
    )

    results = []
    for seg in segments:
        words = []
        if seg.words:
            for w in seg.words:
                token = w.word.strip()
                if token:
                    words.append({
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "word": token,
                    })

        results.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
            "words": words,
        })

    return results