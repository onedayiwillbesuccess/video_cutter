import numpy as np


def center_x_values(width: float, height: float, t_values, face_centers, target_ratio=1080 / 1920):
    """Pure-math helper mirroring editor logic for validation/tests."""
    new_w = int(round(height * target_ratio))
    max_x = max(width - new_w, 0)

    if face_centers is not None:
        ws = np.interp(t_values, face_centers[0], face_centers[1]) - new_w / 2.0
    else:
        ws = np.full(len(t_values), (width - new_w) / 2.0)

    return np.clip(ws, 0, max_x)


if __name__ == "__main__":
    # 16:9 1920x1080 source, 9:16 target window = 608px wide
    w, h = 1920, 1080
    t = [0.0, 1.0]
    assert center_x_values(w, h, t, None).tolist() == [656.0, 656.0], "center fallback"

    face_left = ([0.0, 1.0], [400.0, 400.0])
    v = center_x_values(w, h, t, face_left)
    assert abs(v[0] - 96.0) < 1e-6, f"face left follow, got {v[0]}"

    face_edge = ([0.0, 1.0], [120.0, 120.0])
    assert center_x_values(w, h, t, face_edge)[0] == 0.0, "clamp left edge"

    face_right = ([0.0, 1.0], [1750.0, 1750.0])
    assert center_x_values(w, h, t, face_right)[0] == 1312.0, "clamp right edge"

    # portrait source 1080x1920 (w/h == target ratio) → no horizontal crop possible
    vp = center_x_values(1080, 1920, t, None)
    assert vp[0] == 0.0
    print("ALL CROP MATH TESTS PASS")