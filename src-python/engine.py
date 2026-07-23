# src-python/engine.py
"""AirControl perception engine - Stdio JSON protocol sidecar.
Run standalone: python engine.py
Protocol: stdin JSON commands, stdout JSON events, stderr debug logs.
"""
import sys, os, json, time, threading, math
import numpy as np
import cv2
import mediapipe as mp
from pynput.mouse import Controller as MouseController, Button
from pynput.keyboard import Controller as KeyboardController, Key

# Ensure sibling imports work
sys.path.insert(0, os.path.dirname(__file__))
from config import EngineConfig
from dtw_recognizer import DTWRecognizer


class AdaptiveSmoother:
    def __init__(self):
        self.sx = self.sy = None
    def update(self, rx, ry):
        if self.sx is None: self.sx, self.sy = rx, ry; return rx, ry
        v = math.hypot(rx - self.sx, ry - self.sy)
        if v < EngineConfig.MOUSE_DEAD_ZONE: return int(self.sx), int(self.sy)
        r = min(1.0, v / EngineConfig.VELOCITY_THRESHOLD)
        a = EngineConfig.ALPHA_MIN + (EngineConfig.ALPHA_MAX - EngineConfig.ALPHA_MIN) * (r ** 2)
        self.sx = a * rx + (1.0 - a) * self.sx
        self.sy = a * ry + (1.0 - a) * self.sy
        return int(self.sx), int(self.sy)
    def reset(self): self.sx = self.sy = None


def emit(payload):
    """Write single-line JSON to stdout, flush immediately."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle_stdin(cmd, state):
    """Process a command from stdin."""
    c = cmd.get("cmd", "")
    if c == "SET_CONFIG":
        key, val = cmd.get("key"), cmd.get("value")
        if hasattr(EngineConfig, key):
            setattr(EngineConfig, key, val); EngineConfig.save_json()
            emit({"event": "CONFIG_UPDATED", "key": key, "value": val})
    elif c == "RECORD_START":
        state["recording"] = True; state["trajectory"] = []
        emit({"event": "RECORDING_ACTIVE", "frames": 0})
    elif c == "RECORD_STOP":
        state["recording"] = False
        emit({"event": "RECORDING_STOP", "frames": len(state["trajectory"])})
    elif c == "REGISTER_MACRO":
        name = cmd.get("name", "UNNAMED"); data = cmd.get("data", [])
        if data and len(data) > 5:
            state["dtw"].register_template(f"Custom_{name}", data)
            emit({"event": "MACRO_SAVED", "name": name})
    elif c == "SAVE_CONFIG":
        EngineConfig.save_json(); emit({"event": "CONFIG_SAVED"})
    elif c == "SHUTDOWN":
        emit({"event": "SHUTDOWN"}); os._exit(0)


def stdin_reader(state):
    for line in sys.stdin:
        line = line.strip()
        if line:
            try: handle_stdin(json.loads(line), state)
            except json.JSONDecodeError: pass


def compute_state(landmarks, state):
    """Gesture state machine from MediaPipe landmarks."""
    tt, it, im = landmarks[4], landmarks[8], landmarks[5]
    mt, mm = landmarks[12], landmarks[9]
    rt, rm = landmarks[16], landmarks[13]
    pd = ((tt.x - it.x) ** 2 + (tt.y - it.y) ** 2) ** 0.5
    io = it.y < im.y; mo = mt.y < mm.y; ro = rt.y < rm.y
    if pd < EngineConfig.PINCH_THRESHOLD:
        return "CLICK", 0.9, it.x, it.y
    if io and mo and not ro:
        return "SCROLL", 0.7, it.x, it.y
    if io:
        return "MOVE", 0.5, it.x, it.y
    return "RELEASE", 0.15, it.x, it.y


def calibrate_coords(nx, ny):
    """Comfort zone clamp + interpolate to full range."""
    cx = max(EngineConfig.CALIB_X_MIN, min(EngineConfig.CALIB_X_MAX, nx))
    cy = max(EngineConfig.CALIB_Y_MIN, min(EngineConfig.CALIB_Y_MAX, ny))
    rx = EngineConfig.CALIB_X_MAX - EngineConfig.CALIB_X_MIN
    ry = EngineConfig.CALIB_Y_MAX - EngineConfig.CALIB_Y_MIN
    return (cx - EngineConfig.CALIB_X_MIN) / (rx or 1), (cy - EngineConfig.CALIB_Y_MIN) / (ry or 1)


def main():
    EngineConfig.load_json()
    engine_state = {"recording": False, "trajectory": [], "dtw": None,
                    "lock_until": 0.0, "was_clicking": False,
                    "last_scroll_y": None, "smoother": AdaptiveSmoother()}

    # Initialize DTW with pre-registered circle macro
    dtw = DTWRecognizer()
    mock_circle = [[math.cos(t), math.sin(t)] for t in np.linspace(0, 2*math.pi, 30)]
    dtw.register_template("CIRCLE_MACRO", mock_circle)
    engine_state["dtw"] = dtw

    # Initialize MediaPipe
    mp_face = mp.solutions.face_mesh
    mp_hand = mp.solutions.hands
    face_mesh = mp_face.FaceMesh(
        static_image_mode=False, max_num_faces=1,
        refine_landmarks=False, min_detection_confidence=0.5,
        min_tracking_confidence=0.5)
    hands = mp_hand.Hands(
        static_image_mode=False, max_num_hands=1,
        model_complexity=0, min_detection_confidence=0.5,
        min_tracking_confidence=0.5)

    # Initialize camera
    cap = cv2.VideoCapture(EngineConfig.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, EngineConfig.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, EngineConfig.FRAME_HEIGHT)
    if not cap.isOpened():
        emit({"event": "ERROR", "message": "Camera not available"}); return

    # Stdin listener thread
    threading.Thread(target=stdin_reader, args=(engine_state,), daemon=True).start()

    mouse = MouseController(); kb = KeyboardController()
    traj = []  # Sliding window for DTW
    emit({"event": "SYSTEM_READY"})

    while True:
        ret, frame = cap.read()
        if not ret: continue
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        now = time.time()

        # Step 1: Face orientation early exit
        face_r = face_mesh.process(rgb)
        focused = True
        if face_r.multi_face_landmarks:
            fl = face_r.multi_face_landmarks[0].landmark
            yr = abs(fl[4].x - fl[33].x) / (abs(fl[4].x - fl[263].x) + 1e-6)
            pr = abs(fl[4].y - fl[10].y) / (abs(fl[4].y - fl[152].y) + 1e-6)
            if yr < EngineConfig.FACE_YAW_MIN or yr > EngineConfig.FACE_YAW_MAX or pr < EngineConfig.FACE_PITCH_MIN:
                focused = False
        else:
            focused = False

        if not focused or not EngineConfig.ENGINE_ACTIVE:
            s = engine_state["smoother"]; s.reset()
            if engine_state["was_clicking"]:
                mouse.release(Button.left); engine_state["was_clicking"] = False
            traj.clear(); emit({"state":"SLEEP","x":0,"y":0,"intensity":0.08})
            continue

        # Step 2: Hand inference
        hand_r = hands.process(rgb)
        if hand_r.multi_hand_landmarks:
            lm = hand_r.multi_hand_landmarks[0].landmark
            state, intensity, nx, ny = compute_state(lm, engine_state)

            # Recording mode
            if engine_state["recording"]:
                engine_state["trajectory"].append([nx, ny])
                emit({"event":"RECORDING_TRACK","frames":len(engine_state["trajectory"])})
                continue

            # Macro recording gesture: three-finger open
            tt, it, im = lm[4], lm[8], lm[5]
            mt, mm = lm[12], lm[9]; rt, rm = lm[16], lm[13]
            io = it.y < im.y; mo = mt.y < mm.y; ro = rt.y < rm.y
            pd = ((tt.x - it.x)**2 + (tt.y - it.y)**2)**0.5
            if io and mo and ro and pd > 0.08:
                engine_state["recording"] = True
                engine_state["trajectory"] = []
                emit({"event":"RECORDING_ACTIVE","frames":0})
                continue

            # DTW sliding window match
            if state == "MOVE":
                traj.append([nx, ny])
                if len(traj) > EngineConfig.MACRO_WINDOW_SIZE:
                    traj.pop(0)
                matched = dtw.match(traj)
                if matched:
                    emit({"event":"MACRO_MATCHED","name":matched})
                    if matched == "CIRCLE_MACRO":
                        kb.press(Key.cmd); kb.press(Key.shift); kb.press("s")
                        kb.release("s"); kb.release(Key.shift); kb.release(Key.cmd)
                    traj.clear(); continue

            # Coordinate mapping
            nxc, nyc = calibrate_coords(nx, ny)
            raw_x = int((1.0 - nxc) * w); raw_y = int(nyc * h)

            # Actions
            if state == "RELEASE":
                engine_state["smoother"].reset()
                if engine_state["was_clicking"]:
                    mouse.release(Button.left); engine_state["was_clicking"] = False
                emit({"state":"RELEASE","x":nx,"y":ny,"intensity":0.15})
            elif state == "SCROLL":
                if engine_state["was_clicking"]:
                    mouse.release(Button.left); engine_state["was_clicking"] = False
                if engine_state["last_scroll_y"] is None:
                    engine_state["last_scroll_y"] = ny
                dy = ny - engine_state["last_scroll_y"]
                if abs(dy) > EngineConfig.SCROLL_DEAD_ZONE:
                    steps = int(-dy * 100 * EngineConfig.SCROLL_SENSITIVITY)
                    if steps: mouse.scroll(0, steps); engine_state["last_scroll_y"] = ny
                emit({"state":"SCROLL","x":nx,"y":ny,"intensity":0.7})
            else:
                if now < engine_state["lock_until"]: continue
                tx, ty = engine_state["smoother"].update(raw_x, raw_y)
                if state == "MOVE":
                    if engine_state["was_clicking"]:
                        mouse.release(Button.left); engine_state["was_clicking"] = False
                    mouse.position = (tx, ty)
                    emit({"state":"MOVE","x":nx,"y":ny,"intensity":0.5})
                elif state == "CLICK":
                    if not engine_state["was_clicking"]:
                        engine_state["lock_until"] = now + EngineConfig.CLICK_LOCK_DURATION
                        mouse.position = (tx, ty); mouse.press(Button.left)
                        engine_state["was_clicking"] = True
                    emit({"state":"CLICK","x":nx,"y":ny,"intensity":0.9})
        else:
            traj.clear()
            engine_state["smoother"].reset()
            if engine_state["was_clicking"]:
                mouse.release(Button.left); engine_state["was_clicking"] = False
            emit({"state":"RELEASE","x":0,"y":0,"intensity":0.15})


if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: pass