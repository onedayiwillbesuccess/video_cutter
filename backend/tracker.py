import numpy as np


def _detect_face_center(frame: np.ndarray) -> float | None:
    import mediapipe as mp

    rgb = frame
    h, w = rgb.shape[:2]
    if h == 0 or w == 0:
        return None

    detection = mp.solutions.face_detection
    with detection.FaceDetection(
        model_selection=0,
        min_detection_confidence=0.4,
    ) as detector:
        result = detector.process(rgb)

    if not result or not result.detections:
        return None

    best_cx = None
    best_w = -1.0
    for d in result.detections:
        bb = d.location_data.relative_bounding_box
        cx = (bb.xmin + bb.width / 2.0) * w
        face_w = bb.width * w
        if face_w > best_w:
            best_w = face_w
            best_cx = cx

    return best_cx


def compute_face_trajectory(subclip, sample_step: float = 0.5):
    """Detect faces across the subclip and return a smoothed face-center
    trajectory as (times, x_centers) in source pixels. Returns None if no
    faces are found anywhere in the clip."""
    duration = subclip.duration
    if duration <= 0:
        return None

    times = np.arange(0.0, duration, sample_step)
    if len(times) == 0:
        times = np.array([0.0])

    samples = []
    for t in times:
        try:
            cx = _detect_face_center(subclip.get_frame(float(t)))
        except Exception:
            cx = None
        samples.append(cx)

    valid = [(float(t), cx) for t, cx in zip(times, samples) if cx is not None]
    if not valid:
        return None

    sample_times = np.array([t for t, _ in valid], dtype=float)
    centers = np.array([cx for _, cx in valid], dtype=float)

    fill_times = np.arange(0.0, duration, 0.05)
    filled = np.interp(fill_times, sample_times, centers)

    ema = filled.copy()
    alpha = 0.45
    for i in range(1, len(ema)):
        ema[i] = ema[i - 1] + alpha * (filled[i] - ema[i - 1])

    return fill_times.tolist(), ema.tolist()