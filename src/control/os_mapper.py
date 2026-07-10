# src/control/os_mapper.py
import math
import time

from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController

from src.config import EngineConfig


class AdaptiveSmoother:
    def __init__(self):
        self.sx, self.sy = None, None

    def update(self, rx, ry):
        if self.sx is None:
            self.sx, self.sy = rx, ry
            return rx, ry

        velocity = math.hypot(rx - self.sx, ry - self.sy)

        if velocity < EngineConfig.MOUSE_DEAD_ZONE:
            return int(self.sx), int(self.sy)

        ratio = min(1.0, velocity / EngineConfig.VELOCITY_THRESHOLD)
        alpha = EngineConfig.ALPHA_MIN + (
            EngineConfig.ALPHA_MAX - EngineConfig.ALPHA_MIN
        ) * (ratio ** 2)

        self.sx = alpha * rx + (1.0 - alpha) * self.sx
        self.sy = alpha * ry + (1.0 - alpha) * self.sy
        return int(self.sx), int(self.sy)

    def reset(self):
        self.sx, self.sy = None, None


class InputMapper:
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.smoother = AdaptiveSmoother()

        self.lock_until = 0.0
        self.was_clicking = False

        # Scroll baseline cache
        self.last_scroll_y = None

    def on_gesture_received(self, state: str, nx: float, ny: float):
        current_time = time.time()

        # --- Macro interception: DTW gesture macro trigger ---
        if "MACRO" in state:
            if state == "CIRCLE_MACRO":
                print("[Macro] Circle detected! Triggering Win+Shift+S (snipping tool)...")
                self.keyboard.press(Key.cmd)
                self.keyboard.press(Key.shift)
                self.keyboard.press("s")
                self.keyboard.release("s")
                self.keyboard.release(Key.shift)
                self.keyboard.release(Key.cmd)

            elif state == "CUSTOM_S_MACRO":
                print("[Macro] Custom S detected! Executing Ctrl+A then Ctrl+C...")
                with self.keyboard.pressed(Key.ctrl):
                    self.keyboard.tap("a")
                    time.sleep(0.05)
                    self.keyboard.tap("c")
            return

        if state == "MACRO_RECORDING":
            # Suppress all cursor movement during trajectory recording
            return

        # --- State exit reset chain ---
        if state != "SCROLL":
            self.last_scroll_y = None

        if state == "RELEASE":
            self.smoother.reset()
            if self.was_clicking:
                self.mouse.release(Button.left)
                self.was_clicking = False
            return

        # --- Calibrated spatial remapping ---
        cx = max(EngineConfig.CALIB_X_MIN, min(EngineConfig.CALIB_X_MAX, nx))
        cy = max(EngineConfig.CALIB_Y_MIN, min(EngineConfig.CALIB_Y_MAX, ny))
        range_x = EngineConfig.CALIB_X_MAX - EngineConfig.CALIB_X_MIN
        range_y = EngineConfig.CALIB_Y_MAX - EngineConfig.CALIB_Y_MIN
        nx_cal = (cx - EngineConfig.CALIB_X_MIN) / (range_x if range_x > 0 else 1)
        ny_cal = (cy - EngineConfig.CALIB_Y_MIN) / (range_y if range_y > 0 else 1)
        raw_x = int((1.0 - nx_cal) * self.sw)
        raw_y = int(ny_cal * self.sh)

        # --- SCROLL mode early intercept ---
        if state == "SCROLL":
            if self.was_clicking:
                self.mouse.release(Button.left)
                self.was_clicking = False

            if self.last_scroll_y is None:
                self.last_scroll_y = ny
                return

            delta_y = ny - self.last_scroll_y

            if abs(delta_y) > EngineConfig.SCROLL_DEAD_ZONE:
                scroll_steps = int(-delta_y * 100 * EngineConfig.SCROLL_SENSITIVITY)
                if scroll_steps != 0:
                    self.mouse.scroll(0, scroll_steps)
                    self.last_scroll_y = ny
            return

        # --- Click coordinate lock intercept ---
        if current_time < self.lock_until:
            return

        tx, ty = self.smoother.update(raw_x, raw_y)

        # --- Normal mouse control ---
        if state == "MOVE":
            if self.was_clicking:
                self.mouse.release(Button.left)
                self.was_clicking = False
            self.mouse.position = (tx, ty)

        elif state == "CLICK":
            if not self.was_clicking:
                self.lock_until = current_time + EngineConfig.CLICK_LOCK_DURATION
                self.mouse.position = (tx, ty)
                self.mouse.press(Button.left)
                self.was_clicking = True
