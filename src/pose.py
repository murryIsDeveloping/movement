"""MediaPipe Pose Landmarker wrapper. Returns (33, 3) array or None."""
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import PoseLandmarker, PoseLandmarkerOptions, RunningMode

MODEL = Path(__file__).resolve().parent.parent / "models" / "pose_landmarker_lite.task"


class PoseTracker:
    def __init__(self, model_path: Path = MODEL):
        opts = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.lm = PoseLandmarker.create_from_options(opts)

    def process(self, frame_rgb: np.ndarray, ts_ms: int):
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        res = self.lm.detect_for_video(img, ts_ms)
        if not res.pose_landmarks:
            return None
        lms = res.pose_landmarks[0]
        return np.array([(l.x, l.y, l.z) for l in lms], dtype=np.float64)

    def close(self):
        self.lm.close()
