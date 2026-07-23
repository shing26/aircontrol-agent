# src/ui/siri_window.py
import math

from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont, QPainterPath, QBrush
from PyQt5.QtWidgets import QWidget, QLabel, QHBoxLayout


class GlowCapsule(QWidget):
    """Self-painted capsule: glassmorphism + gradient glow border, synced with Siri phase."""

    STATE_STYLES = {
        "MOVE":    (QColor(0, 210, 150), "\u2726"),
        "CLICK":   (QColor(230, 77, 0),  "\u26a1"),
        "SCROLL":  (QColor(0, 153, 242), "\u2195"),
        "SLEEP":   (QColor(153, 25, 204),"\u25cb"),
        "RELEASE": (QColor(120, 120, 120),"\u25cf"),
        "MACRO":   (QColor(255, 215, 0),  "\u25c6"),
        "MACRO_RECORDING": (QColor(255, 50, 50), "\u25cf"),
        "MACRO_SAVED":     (QColor(0, 220, 100), "\u2713"),
    }

    def __init__(self, screen_w, screen_h):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.get_phase = lambda: 0.0
        self.get_palette = lambda: [
            QColor(0, 242, 254), QColor(147, 39, 255), QColor(255, 0, 128),
        ]

        self.state_key = "RELEASE"
        self.accent = QColor(120, 120, 120)
        self.pulse = 1.0
        self.target_pulse = 1.0
        self._drag_pos = None

        cw, ch = 380, 52
        self.setGeometry((screen_w - cw) // 2, 20, cw, ch)
        self._build_labels()

    def _build_labels(self):
        self.mode_label = QLabel("\u25cf \u63a7\u5c4f\u7279\u5de5", self)
        self.mode_label.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.mode_label.setStyleSheet(
            "color: #FFFFFF; background: transparent; border: none;"
        )

        self.divider = QLabel("|", self)
        self.divider.setStyleSheet(
            "color: rgba(255,255,255,50); background: transparent; border: none;"
        )

        self.status_label = QLabel("\u7b49\u5f85\u624b\u52bf...", self)
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        self.status_label.setStyleSheet(
            "color: rgba(255,255,255,170); background: transparent; border: none;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(12)
        layout.addWidget(self.mode_label)
        layout.addWidget(self.divider)
        layout.addWidget(self.status_label)

    def apply_state(self, state_key):
        style = self.STATE_STYLES.get(state_key, self.STATE_STYLES["RELEASE"])
        self.accent = style[0]
        self.state_key = state_key
        self.mode_label.setText(style[1] + " \u63a7\u5c4f\u7279\u5de5")
        if state_key == "CLICK":
            self.target_pulse = 1.3
        elif state_key == "SLEEP":
            self.target_pulse = 0.92
        else:
            self.target_pulse = 1.0

    def tick_pulse(self):
        diff = self.target_pulse - self.pulse
        if abs(diff) > 0.001:
            self.pulse += diff * 0.15
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            new_pos = event.globalPos() - self._drag_pos
            parent = self.parent()
            if parent:
                new_pos.setX(max(0, min(parent.width() - self.width(), new_pos.x())))
                new_pos.setY(max(0, min(parent.height() - self.height(), new_pos.y())))
                self.move(new_pos)
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2
        phase = self.get_phase()
        palette = self.get_palette()
        p = self.pulse
        accent = self.accent
        is_sleep = self.state_key == "SLEEP"
        is_click = self.state_key == "CLICK"

        def mk_grad(phase_off, pen_width, alpha, accent_blend=0.0):
            ph = phase + phase_off
            grad = QLinearGradient(
                w / 2, h / 2,
                w / 2 + w * 0.5 * math.cos(ph),
                h / 2 + h * 0.5 * math.sin(ph),
            )
            b = accent_blend

            def mc(c1, c2):
                return QColor(
                    int(c1.red() * b + c2.red() * (1 - b)),
                    int(c1.green() * b + c2.green() * (1 - b)),
                    int(c1.blue() * b + c2.blue() * (1 - b)),
                    alpha,
                )

            grad.setColorAt(0.0, mc(palette[0], accent))
            grad.setColorAt(0.5, mc(palette[1], accent))
            grad.setColorAt(1.0, mc(palette[2], accent))
            pen = QPen(grad, pen_width * p)
            pen.setJoinStyle(Qt.RoundJoin)
            return pen

        # 1. Outer glow ring (thick, low alpha, phase-offset)
        inset = 6 * p
        painter.setPen(mk_grad(1.0, 10, 70, 0.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            int(inset), int(inset),
            int(w - 2 * inset), int(h - 2 * inset),
            radius - inset, radius - inset,
        )

        # 2. Glassmorphism background
        bg_alpha = 200 if is_sleep else 240
        painter.setBrush(QBrush(QColor(16, 16, 22, bg_alpha)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(
            0, 0, int(w), int(h), radius, radius,
        )

        # 3. Subtle top highlight (glass reflection)
        hl = QPen(QColor(255, 255, 255, 12), 1)
        painter.setPen(hl)
        painter.drawLine(
            QPointF(radius + 8, 2), QPointF(w - radius - 8, 2),
        )

        # 4. Inner gradient border
        ba = 220 if is_click else 200
        painter.setPen(mk_grad(0.5, 1.5, ba, 0.4))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(
            1, 1, int(w) - 2, int(h) - 2, radius - 1, radius - 1,
        )


class SiriGlowShell(QWidget):
    def __init__(self, screen_w, screen_h):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.WindowTransparentForInput | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setGeometry(0, 0, screen_w, screen_h)

        self.phase = 0.0
        self.current_intensity = 0.15
        self.target_intensity = 0.15
        self.glow_speed = 0.03

        self.color_palette = [
            QColor(0, 242, 254),
            QColor(147, 39, 255),
            QColor(255, 0, 128),
        ]

        self.card = GlowCapsule(screen_w, screen_h)
        self.card.show()
        self.card.get_phase = lambda: self.phase
        self.card.get_palette = lambda: self.color_palette

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    def _tick(self):
        self.phase += self.glow_speed
        if self.phase > 2 * math.pi:
            self.phase -= 2 * math.pi
        self.current_intensity += (
            self.target_intensity - self.current_intensity
        ) * 0.15
        self.card.tick_pulse()
        self.update()

    def set_glow_active(self, active):
        self.target_intensity = 0.15 if active else 0.0
        self.card.setVisible(active)

    def update_ui_state(self, state, intensity):
        self.target_intensity = max(0.05, min(1.0, intensity))

        if "MACRO" in state:
            if state == "MACRO_RECORDING":
                self.card.apply_state("MACRO_RECORDING")
                self.card.status_label.setText(
                    "\U0001f534 \u7a7a\u95f4\u5f55\u5236\u81ea\u5b9a\u4e49\u624b\u52bf\u8f68\u8ff9\u5b8f..."
                )
                self.glow_speed = 0.08
            elif state == "MACRO_SAVED":
                self.card.apply_state("MACRO_SAVED")
                self.card.status_label.setText(
                    "\U0001f4ee \u7a7a\u95f4\u8fde\u62db\u5b58\u50a8\u6210\u529f\uff01\u5df2\u56fa\u5316\u81f3\u7cfb\u7edf\u7279\u5de5"
                )
                self.glow_speed = 0.20
            else:
                self.card.apply_state("MACRO")
                self.card.status_label.setText(
                    f"\U0001f49c \u7a7a\u95f4\u8fde\u62db\u7206\u53d1\uff01\u91ca\u653e\u6838\u5fc3\u5feb\u6377\u952e: {state}"
                )
                self.glow_speed = 0.30
            return

        self.card.apply_state(state)

        speed_map = {
            "SLEEP": 0.01, "RELEASE": 0.02, "MOVE": 0.04,
            "CLICK": 0.15, "SCROLL": 0.06,
        }
        self.glow_speed = speed_map.get(state, 0.03)

        text_map = {
            "SLEEP":
                "\U0001f634 \u89c6\u7ebf\u504f\u79bb\uff0c\u7279\u5de5\u5df2\u81ea\u52a8\u4f11\u7720\u9632\u8bef\u89e6",
            "RELEASE":
                "\u672a\u68c0\u6d4b\u5230\u6709\u6548\u624b\u52bf",
            "MOVE":
                "\U0001f592 \u6b63\u5728\u9694\u7a7a\u5f15\u5bfc\u5149\u6807...",
            "CLICK":
                "\u26a1 \u89e6\u53d1\u9ad8\u7cbe\u5ea6\u70b9\u51fb\uff01\u9501\u5b9a\u5750\u6807",
            "SCROLL":
                "\U0001f4fb \u5168\u5c40\u6587\u6863/\u7f51\u9875\u6eda\u52a8\u4e2d...",
        }
        if state in text_map:
            self.card.status_label.setText(text_map[state])

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            new_pos = event.globalPos() - self._drag_pos
            parent = self.parent()
            if parent:
                new_pos.setX(max(0, min(parent.width() - self.width(), new_pos.x())))
                new_pos.setY(max(0, min(parent.height() - self.height(), new_pos.y())))
                self.move(new_pos)
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self.current_intensity < 0.01:
            return

        cx, cy = self.width() / 2, self.height() / 2
        r_dist = max(self.width(), self.height()) / 2
        x1 = cx + r_dist * math.cos(self.phase)
        y1 = cy + r_dist * math.sin(self.phase)
        x2 = cx - r_dist * math.cos(self.phase)
        y2 = cy - r_dist * math.sin(self.phase)

        base_alpha = int(690 * self.current_intensity)

        configs = [
            (24, 0.20),
            (16, 0.30),
            (10, 0.25),
            (6, 0.15),
            (3, 0.10),
        ]

        for width, alpha_factor in configs:
            alpha = int(base_alpha * alpha_factor)
            if alpha < 5:
                continue
            grad = QLinearGradient(x1, y1, x2, y2)
            grad.setColorAt(0.0, QColor(
                self.color_palette[0].red(),
                self.color_palette[0].green(),
                self.color_palette[0].blue(), alpha))
            grad.setColorAt(0.5, QColor(
                self.color_palette[1].red(),
                self.color_palette[1].green(),
                self.color_palette[1].blue(), alpha))
            grad.setColorAt(1.0, QColor(
                self.color_palette[2].red(),
                self.color_palette[2].green(),
                self.color_palette[2].blue(), alpha))

            painter.setPen(QPen(grad, width))
            inset = width / 2
            painter.drawRoundedRect(
                int(inset), int(inset),
                int(self.width() - width), int(self.height() - width),
                6, 6,
            )
