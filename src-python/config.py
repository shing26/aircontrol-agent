# src-python/config.py
import os
import json


class EngineConfig:
    CAMERA_INDEX = 0
    FRAME_WIDTH = 640
    FRAME_HEIGHT = 480

    ALPHA_MIN = 0.05
    ALPHA_MAX = 0.60
    VELOCITY_THRESHOLD = 35.0

    MOUSE_DEAD_ZONE = 3
    CLICK_LOCK_DURATION = 0.15
    PINCH_THRESHOLD = 0.04

    SCROLL_SENSITIVITY = 1.8
    SCROLL_DEAD_ZONE = 0.015

    MACRO_WINDOW_SIZE = 35
    DTW_THRESHOLD = 0.18

    FACE_YAW_MIN = 0.45
    FACE_YAW_MAX = 2.20
    FACE_PITCH_MIN = 0.38

    CALIB_X_MIN = 0.25
    CALIB_X_MAX = 0.75
    CALIB_Y_MIN = 0.30
    CALIB_Y_MAX = 0.70

    ENGINE_ACTIVE = True
    CURRENT_THEME_INDEX = 0
    CONFIG_FILE_PATH = "config.json"

    @classmethod
    def load_json(cls):
        if os.path.exists(cls.CONFIG_FILE_PATH):
            try:
                with open(cls.CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for key, val in data.items():
                        if hasattr(cls, key):
                            setattr(cls, key, val)
            except Exception:
                pass

    @classmethod
    def save_json(cls):
        try:
            config_dict = {k: getattr(cls, k) for k in [
                "ALPHA_MIN", "ALPHA_MAX", "PINCH_THRESHOLD",
                "SCROLL_SENSITIVITY", "SCROLL_DEAD_ZONE",
                "CLICK_LOCK_DURATION", "VELOCITY_THRESHOLD",
                "CALIB_X_MIN", "CALIB_X_MAX", "CALIB_Y_MIN", "CALIB_Y_MAX",
                "CURRENT_THEME_INDEX", "ENGINE_ACTIVE",
            ]}
            with open(cls.CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
