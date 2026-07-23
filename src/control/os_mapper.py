import math
import time

from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Button, Controller as MouseController

from src.config import EngineConfig

class OneEuroFilter:
    """P2 级别打磨：自适应一欧元低通滤波器"""
    def __init__(self, t0, x0, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self.x_prev = x0
        self.t_prev = t0
        self.dx_prev = 0.0

    def __call__(self, t, x):
        te = t - self.t_prev
        if te <= 0.0:
            return self.x_prev

        # 1. 计算速度变化，并用低通滤波器去抖速度
        dx = (x - self.x_prev) / te
        alpha_d = 1.0 / (1.0 + (1.0 / (2.0 * math.pi * self.d_cutoff * te)))
        dx_hat = alpha_d * dx + (1.0 - alpha_d) * self.dx_prev

        # 2. 根据速度动态调整当前位置的截止频率
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        
        # 3. 计算最终滤波位置
        alpha = 1.0 / (1.0 + (1.0 / (2.0 * math.pi * cutoff * te)))
        x_hat = alpha * x + (1.0 - alpha) * self.x_prev

        self.x_prev = x_hat
        self.t_prev = t
        self.dx_prev = dx_hat
        return x_hat

    def reset(self, t, x):
        self.t_prev = t
        self.x_prev = x
        self.dx_prev = 0.0

class InputMapper:
    def __init__(self, screen_w, screen_h):
        self.sw = screen_w
        self.sh = screen_h
        self.mouse = MouseController()
        self.keyboard = KeyboardController()

        # ── 💡 升级：一欧元双通道去抖滤镜 ──
        t_init = time.time()
        self.filter_x = OneEuroFilter(t_init, screen_w / 2, EngineConfig.ONE_EURO_MIN_CUTOFF, EngineConfig.ONE_EURO_BETA, EngineConfig.ONE_EURO_D_CUTOFF)
        self.filter_y = OneEuroFilter(t_init, screen_h / 2, EngineConfig.ONE_EURO_MIN_CUTOFF, EngineConfig.ONE_EURO_BETA, EngineConfig.ONE_EURO_D_CUTOFF)

        self.lock_until = 0.0
        self.was_clicking = False

        # Scroll baseline cache
        self.last_scroll_y = None
        self._prev_state = None
        self._prev_state = None

    def on_gesture_received(self, state: str, nx: float, ny: float):
        current_time = time.time()
        prev = self._prev_state
        self._prev_state = state
        prev = self._prev_state
        self._prev_state = state

        # --- 3. 完全保留原有舒适空间重映射（P1） ---
        cx = max(EngineConfig.CALIB_X_MIN, min(EngineConfig.CALIB_X_MAX, nx))
        cy = max(EngineConfig.CALIB_Y_MIN, min(EngineConfig.CALIB_Y_MAX, ny))
        range_x = EngineConfig.CALIB_X_MAX - EngineConfig.CALIB_X_MIN
        range_y = EngineConfig.CALIB_Y_MAX - EngineConfig.CALIB_Y_MIN

        nx_cal = (cx - EngineConfig.CALIB_X_MIN) / (range_x if range_x > 0 else 1)
        ny_cal = (cy - EngineConfig.CALIB_Y_MIN) / (range_y if range_y > 0 else 1)
        raw_x = int((1.0 - nx_cal) * self.sw)
        raw_y = int(ny_cal * self.sh)

        # --- 2. 状态退出重置链 ---
        if state != "SCROLL":
            self.last_scroll_y = None
        self._prev_state = None

        if state == "RELEASE":
            # 释放时清空一欧元历史
            t_now = time.time()
            # keep filter position (no center jump)
            if self.was_clicking:
                self.mouse.release(Button.left)
                self.was_clicking = False
            return

        # --- 4. 完全保留原有 SCROLL 早期拦截 ---
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

        # --- 5. 💡 注入：P0 点击防抖锁与一欧元滤波融合 ---
        # 5a. 如果处于 150ms 锁定保护中，拒绝任何更新，直接返回
        if current_time < self.lock_until:
            return

        # 5b. 利用一欧元滤波器（P2）进行高动态去抖
        tx = int(self.filter_x(current_time, raw_x))
        ty = int(self.filter_y(current_time, raw_y))

        # --- 6. 正常键鼠注入 ---
        if state == "MOVE":
            if self.was_clicking:
                self.mouse.release(Button.left)
                self.was_clicking = False
            if prev == "SCROLL":
                self.filter_x.reset(current_time, raw_x)
                self.filter_y.reset(current_time, raw_y)
            self.mouse.position = (tx, ty)

        elif state == "CLICK":
            if not self.was_clicking:
                # 进入合拢瞬间：锁定 150ms[cite: 3]
                self.lock_until = current_time + EngineConfig.CLICK_LOCK_DURATION
                self.mouse.position = (tx, ty)
                self.mouse.press(Button.left)
                self.was_clicking = True