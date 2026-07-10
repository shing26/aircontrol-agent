# src/vision/pipeline.py
import queue
import threading

import cv2
import mediapipe as mp
from PyQt5.QtCore import QThread, pyqtSignal

from src.config import EngineConfig
from src.vision.dtw_recognizer import DTWRecognizer

import numpy as np
import math


class FramePipeline:
    def __init__(self):
        self.buffer = queue.Queue(maxsize=1)
        self.lock = threading.Lock()

    def push(self, frame):
        with self.lock:
            if self.buffer.full():
                try:
                    self.buffer.get_nowait()
                except queue.Empty:
                    pass
            self.buffer.put(frame)

    def pop(self):
        return self.buffer.get(block=True)


class VisionAgentThread(QThread):
    gesture_signal = pyqtSignal(str, float, float)
    ui_signal = pyqtSignal(str, float)

    def __init__(self, pipeline):
        super().__init__()
        self.pipeline = pipeline
        self.running = True

        # Face mesh: early exit sentinel
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # Hand gesture: regular inference
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # DTW gesture macro engine
        self.dtw_engine = DTWRecognizer()
        self.active_trajectory = []
        self.is_recording_mode = False

        # Pre-register a circle gesture template for zero cold-start
        mock_circle = [
            [math.cos(t), math.sin(t)]
            for t in np.linspace(0, 2 * math.pi, 30)
        ]
        self.dtw_engine.register_template("CIRCLE_MACRO", mock_circle)

    def run(self):
        print("[Thread] Vision agent started.")
        while self.running:
            frame = self.pipeline.pop()
            # Poison pill check: None means kill yourself
            if frame is None:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # --- Step 1: Early exit face orientation check ---
            face_results = self.face_mesh.process(rgb)
            is_focused = True

            if face_results.multi_face_landmarks:
                face_lms = face_results.multi_face_landmarks[0].landmark
                nose = face_lms[4]
                left_eye = face_lms[33]
                right_eye = face_lms[263]
                forehead = face_lms[10]
                chin = face_lms[152]

                yaw_ratio = abs(nose.x - left_eye.x) / (abs(nose.x - right_eye.x) + 1e-6)
                pitch_ratio = abs(nose.y - forehead.y) / (abs(nose.y - chin.y) + 1e-6)

                if (
                    yaw_ratio < EngineConfig.FACE_YAW_MIN
                    or yaw_ratio > EngineConfig.FACE_YAW_MAX
                    or pitch_ratio < EngineConfig.FACE_PITCH_MIN
                ):
                    is_focused = False
            else:
                is_focused = False

            if not is_focused:
                self.gesture_signal.emit("RELEASE", 0.0, 0.0)
                self.ui_signal.emit("SLEEP", 0.08)
                self.active_trajectory = []
                continue

            if not EngineConfig.ENGINE_ACTIVE:
                self.gesture_signal.emit("RELEASE", 0.0, 0.0)
                self.ui_signal.emit("SLEEP", 0.08)
                self.active_trajectory = []
                continue

            # --- Step 2: Hand gesture inference ---
            hand_results = self.hands.process(rgb)
            if hand_results.multi_hand_landmarks:
                landmarks = hand_results.multi_hand_landmarks[0].landmark
                thumb_tip = landmarks[4]
                index_tip, index_mcp = landmarks[8], landmarks[5]
                middle_tip, middle_mcp = landmarks[12], landmarks[9]
                ring_tip, ring_mcp = landmarks[16], landmarks[13]

                pinch_dist = (
                    (thumb_tip.x - index_tip.x) ** 2
                    + (thumb_tip.y - index_tip.y) ** 2
                ) ** 0.5
                index_is_open = index_tip.y < index_mcp.y
                middle_is_open = middle_tip.y < middle_mcp.y
                ring_is_open = ring_tip.y < ring_mcp.y

                # --- Gesture macro recording mode ---
                if index_is_open and middle_is_open and ring_is_open and pinch_dist > 0.08:
                    if not self.is_recording_mode:
                        self.is_recording_mode = True
                        self.active_trajectory = []
                    self.active_trajectory.append([index_tip.x, index_tip.y])
                    self.gesture_signal.emit("MACRO_RECORDING", 0.0, 0.0)
                    self.ui_signal.emit("MACRO_RECORDING", 0.75)
                    continue

                else:
                    if self.is_recording_mode:
                        self.is_recording_mode = False
                        if (
                            len(self.active_trajectory) > 10
                            and "CUSTOM_S_MACRO" not in self.dtw_engine.templates
                        ):
                            self.dtw_engine.register_template(
                                "CUSTOM_S_MACRO", self.active_trajectory
                            )
                            self.ui_signal.emit("MACRO_SAVED", 1.0)
                        self.active_trajectory = []
                        continue

                # --- Sliding window DTW match ---
                if index_is_open:
                    self.active_trajectory.append([index_tip.x, index_tip.y])
                    if len(self.active_trajectory) > EngineConfig.MACRO_WINDOW_SIZE:
                        self.active_trajectory.pop(0)

                    matched = self.dtw_engine.match(self.active_trajectory)
                    if matched:
                        self.gesture_signal.emit(matched, 0.0, 0.0)
                        self.ui_signal.emit(matched, 1.0)
                        self.active_trajectory = []
                        continue

                # --- Base gesture state machine ---
                if pinch_dist < EngineConfig.PINCH_THRESHOLD:
                    state, intensity = "CLICK", 0.9
                elif index_is_open and middle_is_open and not ring_is_open:
                    state, intensity = "SCROLL", 0.7
                elif index_is_open:
                    state, intensity = "MOVE", 0.5
                else:
                    state, intensity = "RELEASE", 0.15
                    self.active_trajectory = []

                self.gesture_signal.emit(state, index_tip.x, index_tip.y)
                self.ui_signal.emit(state, intensity)

            else:
                self.gesture_signal.emit("RELEASE", 0.0, 0.0)
                self.ui_signal.emit("RELEASE", 0.15)
                self.active_trajectory = []

        print("[Thread] Vision agent exited cleanly.")

    def stop(self):
        self.running = False
        print("[Thread] Vision agent exit signal sent.")
