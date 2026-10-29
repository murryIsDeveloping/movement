"""Synthetic landmark arrays. Shape (33, 3), mirrored image coords (user's left at small x), y down."""
import numpy as np

from src.landmarks import L


def standing(scale: float = 1.0, offset=(0.0, 0.0)) -> np.ndarray:
    """Upright, arms by sides. Torso length 0.2 * scale."""
    ox, oy = offset
    p = np.zeros((33, 3))

    def put(i, x, y, z=0.0):
        p[i] = (ox + x * scale, oy + y * scale, z)

    put(L.NOSE, 0.5, 0.20)
    put(L.LEFT_SHOULDER, 0.40, 0.30)
    put(L.RIGHT_SHOULDER, 0.60, 0.30)
    put(L.LEFT_ELBOW, 0.38, 0.40)
    put(L.RIGHT_ELBOW, 0.62, 0.40)
    put(L.LEFT_WRIST, 0.37, 0.50)
    put(L.RIGHT_WRIST, 0.63, 0.50)
    put(L.LEFT_HIP, 0.44, 0.50)
    put(L.RIGHT_HIP, 0.56, 0.50)
    put(L.LEFT_KNEE, 0.44, 0.70)
    put(L.RIGHT_KNEE, 0.56, 0.70)
    put(L.LEFT_ANKLE, 0.44, 0.90)
    put(L.RIGHT_ANKLE, 0.56, 0.90)
    return p


def arm_right_out(scale: float = 1.0, **kw) -> np.ndarray:
    p = standing(scale=scale, **kw)
    p[L.RIGHT_ELBOW, :2] = p[L.RIGHT_SHOULDER, :2] + (0.10 * scale, 0.0)
    p[L.RIGHT_WRIST, :2] = p[L.RIGHT_SHOULDER, :2] + (0.20 * scale, 0.0)
    return p


def squat(scale: float = 1.0, **kw) -> np.ndarray:
    p = standing(scale=scale, **kw)
    for i in (L.LEFT_HIP, L.RIGHT_HIP):
        p[i, 1] += 0.15 * scale
    for i in (L.LEFT_KNEE, L.RIGHT_KNEE):
        p[i, 1] += 0.05 * scale
    return p
