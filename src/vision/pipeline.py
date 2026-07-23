import queue
import threading

import cv2
import mediapipe as mp
from PyQt5.QtCore import QThread, pyqtSignal

from src.config import EngineConfig

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
        # 阻塞在此，直到主线程推帧，或者推入退出毒药丸 None
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
        self._state_buffer = []
        self._last_emitted_state = "RELEASE"


        # Hand gesture: regular inference
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # State debounce: prevent SCROLL->MOVE flicker

        
    def run(self):
        print("[Thread] Vision agent started.")
        while self.running:
            frame = self.pipeline.pop()
            
            # ── 💡 注入：毒药丸退出哨兵 ──
            if frame is None or not self.running:
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
                continue

            if not EngineConfig.ENGINE_ACTIVE:
                self.gesture_signal.emit("RELEASE", 0.0, 0.0)
                self.ui_signal.emit("SLEEP", 0.08)
                continue

            # --- Step 2: Hand gesture inference ---
            hand_results = self.hands.process(rgb)
            if hand_results.multi_hand_landmarks:
                landmarks = hand_results.multi_hand_landmarks[0].landmark
                thumb_tip = landmarks[4]
                index_tip, index_mcp = landmarks[8], landmarks[5]
                middle_tip, middle_mcp = landmarks[12], landmarks[9]
                ring_tip, ring_mcp = landmarks[16], landmarks[13]


                # --- Gesture state machine ---
                pd = ((thumb_tip.x - middle_tip.x)**2 + (thumb_tip.y - middle_tip.y)**2)**0.5
                io = index_tip.y < index_mcp.y
                mo = middle_tip.y < middle_mcp.y
                spread = abs(index_tip.x - middle_tip.x)

                if io and mo:
                    raw_state, intensity = "SCROLL", 0.7
                elif pd < EngineConfig.PINCH_THRESHOLD:
                    raw_state, intensity = "CLICK", 0.9
                elif io:
                    raw_state, intensity = "MOVE", 0.5
                else:
                    raw_state, intensity = "RELEASE", 0.15

                # Debounce: 5-frame buffer, 3/5 majority
                self._state_buffer.append(raw_state)
                if len(self._state_buffer) > 5:
                    self._state_buffer.pop(0)
                counts = {}
                for s in self._state_buffer:
                    counts[s] = counts.get(s, 0) + 1
                best = max(counts, key=counts.get)
                state = best if counts[best] >= 3 else self._last_emitted_state
                self._last_emitted_state = state

                self.gesture_signal.emit(state, index_tip.x, index_tip.y)
                self.ui_signal.emit(state, intensity)

            else:
                self.gesture_signal.emit("RELEASE", 0.0, 0.0)
                self.ui_signal.emit("RELEASE", 0.15)

        print("[Thread] Vision agent exited cleanly.")

    def stop(self):
        self.running = False
        print("[Thread] Vision agent exit signal sent.")
