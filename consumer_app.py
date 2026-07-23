# consumer_app.py
"""AirControl 2.0 - Minimalist consumer-grade desktop client.
Slate theme, card-based gesture display, custom iOS toggles.
"""
import sys, time
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QDialog, QLineEdit, QFrame, QScrollArea,
    QSystemTrayIcon, QMenu, QAction,
)


class SlateToggle(QWidget):
    """iOS-style animated toggle switch"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 24); self.setCursor(Qt.PointingHandCursor)
        self._checked = True
        self._thumb_position = 24.0 if self._checked else 2.0
        self.anim = QPropertyAnimation(self, b"thumb_position")
        self.anim.setDuration(180); self.anim.setEasingCurve(QEasingCurve.InOutQuad)

    @pyqtProperty(float)
    def thumb_position(self): return self._thumb_position
    @thumb_position.setter
    def thumb_position(self, pos): self._thumb_position = pos; self.update()

    def isChecked(self): return self._checked
    def setChecked(self, state):
        if self._checked != state:
            self._checked = state; self.anim.stop()
            self.anim.setStartValue(self._thumb_position)
            self.anim.setEndValue(24.0 if state else 2.0); self.anim.start()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton: self.setChecked(not self._checked); event.accept()

    def paintEvent(self, event):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        bg = QColor("#38BDF8") if self._checked else QColor("#334155")
        p.setBrush(QBrush(bg)); p.setPen(Qt.NoPen)
        p.drawRoundedRect(QRectF(0, 0, 46, 24), 12, 12)
        p.setBrush(QBrush(QColor("#FFFFFF")))
        p.drawEllipse(QRectF(self._thumb_position, 2, 20, 20))


class ConsumerGestureCard(QFrame):
    """Card-based gesture display with hover glow"""
    def __init__(self, icon, name, desc, is_locked, delete_cb=None, parent=None):
        super().__init__(parent)
        self.card_name = name; self.delete_cb = delete_cb
        self.setFixedHeight(80); self.setObjectName("GestureCard")
        self.setStyleSheet(
            "QFrame#GestureCard { background-color: #1E293B; border: 1px solid #334155; border-radius: 16px; }"
            "QFrame#GestureCard:hover { background-color: #243249; border: 1px solid #38BDF8; }"
        )
        l = QHBoxLayout(self); l.setContentsMargins(16,12,16,12)
        self.icon_lb = QLabel(icon, self); self.icon_lb.setStyleSheet("font-size:20px;")
        l.addWidget(self.icon_lb); l.addSpacing(12)
        vl = QVBoxLayout(); vl.setSpacing(2)
        self.name_lb = QLabel(name, self); self.name_lb.setStyleSheet("color:#F1F5F9;font-size:13px;font-weight:bold;")
        self.desc_lb = QLabel(desc, self); self.desc_lb.setStyleSheet("color:#64748B;font-size:11px;")
        vl.addWidget(self.name_lb); vl.addWidget(self.desc_lb)
        l.addLayout(vl, 1)
        self.toggle = SlateToggle(self)
        l.addWidget(self.toggle)
        if not is_locked:
            db = QPushButton("X", self)
            db.setFixedSize(24,24)
            db.setStyleSheet("background:rgba(255,0,128,15);border:1px solid rgba(255,0,128,30);border-radius:12px;color:#FF0080;font-size:10px;font-weight:bold;")
            db.clicked.connect(self._request_delete); l.addWidget(db)

    def _request_delete(self):
        if self.delete_cb: self.delete_cb(self)


class GestureRecorderDialog(QDialog):
    """Recording wizard dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(360, 340); self.drag_pos = QPoint()
        self.recorded_trajectory = []; self.is_recording = False
        self.recorded_name = ""; self.recorded_shortcut = ""
        self.setStyleSheet(
            "GestureRecorderDialog { background-color: #1E293B; border: 2px solid #38BDF8; border-radius: 18px; }"
            "QLabel { color: #CBD5E1; font-family: Segoe UI; }"
            "QLineEdit { background: #334155; border: 1px solid #475569; border-radius: 8px; padding: 8px; color: white; font-size: 12px; }"
        )
        l = QVBoxLayout(self); l.setContentsMargins(22,18,22,18)
        l.addWidget(QLabel("Record Gesture Macro", self)); l.addSpacing(12)
        l.addWidget(QLabel("Gesture Name", self))
        self.name_in = QLineEdit(self); self.name_in.setPlaceholderText("e.g. SWIPE_RIGHT")
        l.addWidget(self.name_in); l.addSpacing(8)
        l.addWidget(QLabel("Keyboard Shortcut", self))
        self.key_in = QLineEdit(self); self.key_in.setPlaceholderText("e.g. ctrl+shift+v")
        l.addWidget(self.key_in); l.addSpacing(12)
        self.status_lb = QLabel("Ready", self)
        self.status_lb.setAlignment(Qt.AlignCenter)
        self.status_lb.setStyleSheet("color:#94A3B8;font-size:11px;padding:8px;")
        l.addWidget(self.status_lb)
        self.act_btn = QPushButton("Start Recording", self)
        self.act_btn.setStyleSheet("background:rgba(56,189,248,15);border:1px solid #38BDF8;color:#38BDF8;border-radius:8px;padding:10px;font-weight:bold;font-size:12px;")
        self.act_btn.clicked.connect(self._on_action)
        l.addWidget(self.act_btn); l.addStretch()
        bb = QHBoxLayout()
        cx = QPushButton("Cancel", self)
        cx.setStyleSheet("background:transparent;color:#64748B;border:none;font-size:12px;")
        cx.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save", self); self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("background:#334155;color:#64748B;border:none;border-radius:8px;padding:10px;font-size:12px;")
        self.save_btn.clicked.connect(self._validate)
        bb.addWidget(cx); bb.addStretch(); bb.addWidget(self.save_btn)
        l.addLayout(bb)

    def collect_coord(self, nx, ny):
        if self.is_recording: self.recorded_trajectory.append([nx, ny])
        self.status_lb.setText(f"Tracking... {len(self.recorded_trajectory)} frames")

    def _on_action(self):
        if not self.name_in.text() or not self.key_in.text():
            self.status_lb.setText("Fill in name + shortcut first!"); self.status_lb.setStyleSheet("color:#EF4444;font-size:11px;")
            return
        if not self.is_recording:
            self.is_recording = True; self.recorded_trajectory = []
            self.name_in.setEnabled(False); self.key_in.setEnabled(False)
            self.act_btn.setText("Stop Recording")
            self.act_btn.setStyleSheet("background:rgba(255,0,128,15);border:1px solid #FF0080;color:#FF0080;border-radius:8px;padding:10px;font-weight:bold;")
            self.status_lb.setText("Draw gesture in front of camera..."); self.status_lb.setStyleSheet("color:#38BDF8;font-size:11px;")
        else:
            self.is_recording = False; self.act_btn.setEnabled(False)
            self.act_btn.setText("Trajectory Locked"); n = len(self.recorded_trajectory)
            self.status_lb.setText(f"Captured {n} frames"); self.status_lb.setStyleSheet("color:#10B981;font-size:11px;")
            if n > 10:
                self.save_btn.setEnabled(True)
                self.save_btn.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #38BDF8,stop:1 #8B5CF6);color:white;border:none;border-radius:8px;padding:10px;font-weight:bold;")

    def _validate(self):
        self.recorded_name = self.name_in.text(); self.recorded_shortcut = self.key_in.text(); self.accept()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.drag_pos = e.globalPos() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton: self.move(e.globalPos() - self.drag_pos); e.accept()


GESTURES = [
    ("\u261d","Point Up","Move cursor",True),
    ("\u270b","Pinch","Left click",True),
    ("\u270c","V-Sign","Scroll",True),
    ("\ud83c\udf00","Circle","Macro [Win+Shift+S]",False),
]

class AirControlClient(QWidget):
    """1050x580 consumer-grade slate-themed control center"""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1050, 580)
        self.drag_pos = QPoint(); self.cards = []
        self.active_dialog = None
        self._setup_tray(); self._init_consumer_ui()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        m = QMenu()
        a1 = QAction("Open", self); a1.triggered.connect(lambda: (self.showNormal(), self.activateWindow(), self.raise_()))
        a2 = QAction("Quit", self); a2.triggered.connect(lambda: (self.tray.hide(), QApplication.quit(), sys.exit(0)))
        m.addAction(a1); m.addSeparator(); m.addAction(a2)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self.hide() if r==QSystemTrayIcon.Trigger and self.isVisible() else (self.showNormal(), self.activateWindow(), self.raise_()))
        self.tray.show()

    def _init_consumer_ui(self):
        self.setStyleSheet(
            "QWidget#Canvas { background-color: #0F172A; border: 1px solid #1E293B; border-radius: 24px; }"
            "QWidget#Sidebar { background-color: #090D16; border-top-left-radius: 23px; border-bottom-left-radius: 23px; border-right: 1px solid #1E293B; }"
            "QLabel { color: #CBD5E1; font-family: Segoe UI; }"
            "QPushButton#NavBtn { background: transparent; color: #64748B; text-align: left; padding: 12px 16px; border: none; border-radius: 8px; font-size: 13px; }"
            "QPushButton#NavBtn:hover { background: rgba(255,255,255,6); color: #E2E8F0; }"
            "QPushButton#RecordBtn { background: rgba(56,189,248,8); border: 2px dashed rgba(56,189,248,40); border-radius: 12px; color: #38BDF8; padding: 12px; font-weight: bold; font-size: 12px; }"
            "QPushButton#RecordBtn:hover { background: rgba(56,189,248,15); border: 2px dashed #38BDF8; }"
            "QComboBox { background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 6px; color: white; font-size: 11px; }"
        )

        canvas = QWidget(self); canvas.setGeometry(0,0,1050,580); canvas.setObjectName("Canvas")
        ml = QHBoxLayout(canvas); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)

        # Sidebar
        sb = QWidget(self); sb.setObjectName("Sidebar"); sb.setFixedWidth(220)
        sl = QVBoxLayout(sb); sl.setContentsMargins(18,28,18,22)
        sl.addWidget(QLabel("AirControl", sb)); sl.addSpacing(28)
        for tag in ["Dashboard","Workshop","Calibrate","Settings"]:
            b = QPushButton(f"  {tag}", sb); b.setObjectName("NavBtn"); b.setCursor(Qt.PointingHandCursor)
            sl.addWidget(b)
        sl.addStretch()
        sl.addWidget(QLabel("Theme", sb))
        self.theme_cb = QComboBox(sb)
        self.theme_cb.addItems(["Slate Cyber","Night Hunter","Solar Flare"])
        sl.addWidget(self.theme_cb)
        ml.addWidget(sb)

        # Content
        rc = QWidget(self); rl = QVBoxLayout(rc); rl.setContentsMargins(24,20,24,20)

        # Top bar
        tb = QHBoxLayout()
        self.status_lb = QLabel("O Agent Online", rc)
        self.status_lb.setStyleSheet("color:#38BDF8;font-size:12px;font-weight:bold;")
        cx = QPushButton("X", rc); cx.setFixedSize(22,22)
        cx.setStyleSheet("background:transparent;color:#EF4444;font-size:12px;font-weight:bold;border:none;")
        cx.clicked.connect(lambda: (self.hide(), self.tray.showMessage("AirControl","Running in system tray.",QSystemTrayIcon.Information,2000)))
        tb.addWidget(self.status_lb); tb.addStretch(); tb.addWidget(cx)
        rl.addLayout(tb); rl.addSpacing(8)

        # Title
        rl.addWidget(QLabel("Gesture Matrix", rc)); rl.addSpacing(10)

        # Scrollable card area
        scroll = QScrollArea(rc); scroll.setWidgetResizable(True); scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        self.card_container = QWidget(rc); self.card_container.setStyleSheet("background:transparent;")
        self.card_layout = QVBoxLayout(self.card_container); self.card_layout.setSpacing(8); self.card_layout.setContentsMargins(0,0,0,0)

        for icon, name, desc, locked in GESTURES:
            c = ConsumerGestureCard(icon, name, desc, locked, delete_cb=self._remove_card, parent=self.card_container)
            self.cards.append(c); self.card_layout.addWidget(c)

        scroll.setWidget(self.card_container)
        rl.addWidget(scroll, 1)

        # Record button
        rec = QPushButton("+ Record New Gesture", rc); rec.setObjectName("RecordBtn")
        rec.setCursor(Qt.PointingHandCursor)
        rec.clicked.connect(self._open_recorder)
        rl.addWidget(rec)

        ml.addWidget(rc)

    def _open_recorder(self):
        self.active_dialog = GestureRecorderDialog(self)
        if self.active_dialog.exec() == QDialog.Accepted:
            n = self.active_dialog.recorded_name; s = self.active_dialog.recorded_shortcut
            t = self.active_dialog.recorded_trajectory
            c = ConsumerGestureCard("O", f"Custom: {n}", f"Shortcut [{s}]", False, delete_cb=self._remove_card, parent=self.card_container)
            self.cards.append(c); self.card_layout.addWidget(c)
            print(f"[Consumer] Macro: {n} -> {s} ({len(t)} frames)")
        self.active_dialog = None

    def _remove_card(self, card):
        self.card_layout.removeWidget(card); self.cards.remove(card); card.deleteLater()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.drag_pos = e.globalPos() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton: self.move(e.globalPos() - self.drag_pos); e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    c = AirControlClient(); c.show(); sys.exit(app.exec_())