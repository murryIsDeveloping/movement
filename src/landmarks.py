"""Landmark indices, the body subset drawn on the preview, and its skeleton lines."""
from enum import IntEnum


class L(IntEnum):
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28


# Face and finger landmarks excluded: noisy and irrelevant to body poses.
BODY = [
    L.NOSE,
    L.LEFT_SHOULDER, L.RIGHT_SHOULDER,
    L.LEFT_ELBOW, L.RIGHT_ELBOW,
    L.LEFT_WRIST, L.RIGHT_WRIST,
    L.LEFT_HIP, L.RIGHT_HIP,
    L.LEFT_KNEE, L.RIGHT_KNEE,
    L.LEFT_ANKLE, L.RIGHT_ANKLE,
]

SKELETON = [
    (L.LEFT_SHOULDER, L.RIGHT_SHOULDER),
    (L.LEFT_SHOULDER, L.LEFT_ELBOW), (L.LEFT_ELBOW, L.LEFT_WRIST),
    (L.RIGHT_SHOULDER, L.RIGHT_ELBOW), (L.RIGHT_ELBOW, L.RIGHT_WRIST),
    (L.LEFT_SHOULDER, L.LEFT_HIP), (L.RIGHT_SHOULDER, L.RIGHT_HIP),
    (L.LEFT_HIP, L.RIGHT_HIP),
    (L.LEFT_HIP, L.LEFT_KNEE), (L.LEFT_KNEE, L.LEFT_ANKLE),
    (L.RIGHT_HIP, L.RIGHT_KNEE), (L.RIGHT_KNEE, L.RIGHT_ANKLE),
]
