# src/ui/siri_window.py
import math

from PyQt5.QtCore import Qt, QTimer, QRectF
from PyQt5.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout


class SiriGlowShell(QWidget):
    def __init__(self, screen_w, screen_h):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, screen_w, screen_h)
        self.phase = 0.0
        self.current_intensity = 0.15
        self.target_intensity = 0.15
        self.glow_speed = 0.03

        # Dynamic color palette for glow themes
        self.color_palette = [
            QColor(0, 242, 254),
            QColor(147, 39, 255),
            QColor(255, 0, 128),
        ]
        self._init_status_card(screen_w, screen_h)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_animation)
        self.timer.start(16)

    def _init_status_card(self, sw, sh):
        self.card = QWidget(self)
        self.card.setObjectName("StatusCard")
        self.card.setStyleSheet(
            "QWidget#StatusCard {"
            "  background-color: rgba(18, 18, 24, 210);"
            "  border: 1px solid rgba(255, 255, 255, 35);"
            "  border-radius: 20px;"
            "}"
            "QLabel { color: #FFFFFF; background: transparent; }"
        )
        layout = QHBoxLayout(self.card)
        layout.setContentsMargins(20, 10, 20, 10)
        self.mode_label = QLabel("🛰️ 控屏特工", self)
        self.mode_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        divider = QLabel("|", self)
        divider.setStyleSheet("color: rgba(255,255,255,60);")
        self.status_label = QLabel("正在初始化感知空间...", self)
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 180);")
        layout.addWidget(self.mode_label)
        layout.addWidget(divider)
        layout.addWidget(self.status_label)
        cw, ch = 340, 50
        self.card.setGeometry((sw - cw) // 2, sh - ch - 50, cw, ch)

    def _update_animation(self):
        self.phase += self.glow_speed
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
        self.current_intensity += (
            self.target_intensity - self.current_intensity
        ) * 0.15
        self.update()

    def update_ui_state(self, state, intensity):
        self.target_intensity = max(0.05, min(1.0, intensity))

        if "MACRO" in state:
            if state == "MACRO_RECORDING":
                self.status_label.setText("⭐ 正在空间录制自定义手势轨迹宏...")
                self.glow_speed = 0.08
            elif state == "MACRO_SAVED":
                self.status_label.setText("📅 空间连招存储成功！已固化至系统特工")
                self.glow_speed = 0.20
            else:
                self.status_label.setText(f"💥 空间连招爆破！释放核心快捷键: {state}")
                self.glow_speed = 0.30
        elif state == "SLEEP":
            self.status_label.setText("👁 视线偏离，特工已自动休眠防误触")
            self.glow_speed = 0.01
        elif state == "RELEASE":
            self.status_label.setText("未检测到有效手势")
            self.glow_speed = 0.02
        elif state == "MOVE":
            self.status_label.setText("🖑 正在隔空引导光标...")
            self.glow_speed = 0.04
        elif state == "CLICK":
            self.status_label.setText("⚡ 触发高精度点击！锁死坐标")
            self.glow_speed = 0.15
        elif state == "SCROLL":
            self.status_label.setText("📐 全局文档/网页滚动中...")
            self.glow_speed = 0.06

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        r_dist = max(self.width(), self.height()) / 2
        x1 = cx + r_dist * math.cos(self.phase)
        y1 = cy + r_dist * math.sin(self.phase)
        x2 = cx - r_dist * math.cos(self.phase)
        y2 = cy - r_dist * math.sin(self.phase)
        base_alpha = int(230 * self.current_intensity)
        layers = 4
        max_pen_width = 20
        for i in range(layers):
            layer_factor = (i + 1) / layers
            current_pen_width = max_pen_width * (2.0 - layer_factor) * self.current_intensity
            current_alpha = int(base_alpha * 0.25 * layer_factor)
            gradient = QLinearGradient(x1, y1, x2, y2)
            gradient.setColorAt(0.0, QColor(
                self.color_palette[0].red(), self.color_palette[0].green(),
                self.color_palette[0].blue(), current_alpha))
            gradient.setColorAt(0.5, QColor(
                self.color_palette[1].red(), self.color_palette[1].green(),
                self.color_palette[1].blue(), current_alpha))
            gradient.setColorAt(1.0, QColor(
                self.color_palette[2].red(), self.color_palette[2].green(),
                self.color_palette[2].blue(), current_alpha))
            pen = QPen(gradient, current_pen_width)
            painter.setPen(pen)
            inset = current_pen_width / 2
            rect = QRectF(
                inset, inset,
                self.width() - current_pen_width,
                self.height() - current_pen_width,
            )
            painter.drawRect(rect)
