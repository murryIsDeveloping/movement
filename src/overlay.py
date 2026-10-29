import cv2
import numpy as np

from src.landmarks import BODY, SKELETON


def draw_skeleton(frame, p: np.ndarray | None):
    if p is None:
        return
    h, w = frame.shape[:2]

    def pt(i):
        return int(p[i, 0] * w), int(p[i, 1] * h)

    for a, b in SKELETON:
        cv2.line(frame, pt(a), pt(b), (80, 220, 80), 2)
    for i in BODY:
        cv2.circle(frame, pt(i), 4, (240, 240, 240), -1)
