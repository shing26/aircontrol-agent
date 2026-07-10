# src/ui/recording_dialog.py
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
)


class GestureRecordingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 420)
        self.drag_position = QPoint()
        self.is_recording = False
        self.recorded_trajectory = []
        self.recorded_name = ""
        self.recorded_shortcut = ""
        self._init_ui()

    def _init_ui(self):
        panel = QWidget(self)
        panel.setGeometry(0, 0, 380, 420)
        panel.setObjectName("RecordPanel")
        panel.setStyleSheet(
            "QWidget#RecordPanel { background-color: #12121A; border: 2px solid rgba(0, 242, 254, 80); border-radius: 20px; }"
            "QLabel { color: #E2E2EA; font-family: Segoe UI; }"
            "QLineEdit { background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,25); border-radius: 8px; padding: 6px; color: white; }"
            "QPushButton { font-weight: bold; border-radius: 8px; padding: 8px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(25, 20, 25, 20)

        title = QLabel("Record New Gesture Macro", panel)
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #00F2FE;")
        layout.addWidget(title)
        layout.addSpacing(12)

        layout.addWidget(QLabel("1. Name your gesture:", panel))
        self.name_input = QLineEdit(panel)
        self.name_input.setPlaceholderText("e.g. SWIPE_LEFT_MACRO")
        layout.addWidget(self.name_input)
        layout.addSpacing(10)

        layout.addWidget(QLabel("2. Bind keyboard shortcut:", panel))
        self.shortcut_input = QLineEdit(panel)
        self.shortcut_input.setPlaceholderText("e.g. ctrl+v or win+d")
        layout.addWidget(self.shortcut_input)
        layout.addSpacing(12)

        self.capture_box = QWidget(panel)
        self.capture_box.setStyleSheet("background: rgba(255,255,255,6); border: 1px solid rgba(255,255,255,12); border-radius: 12px;")
        bx = QVBoxLayout(self.capture_box)
        self.status_label = QLabel("Enter name + shortcut first", panel)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: rgba(255,255,255,140); font-size: 11px;")
        bx.addWidget(self.status_label)
        self.action_btn = QPushButton("Start Recording", panel)
        self.action_btn.setStyleSheet("background: rgba(0, 242, 254, 20); border: 1px solid #00F2FE; color: #00F2FE;")
        self.action_btn.clicked.connect(self._handle_action_click)
        bx.addWidget(self.action_btn)
        layout.addWidget(self.capture_box)
        layout.addSpacing(12)

        bb = QHBoxLayout()
        cancel_btn = QPushButton("Cancel", panel)
        cancel_btn.setStyleSheet("background: transparent; color: rgba(255,255,255,120); border: none;")
        cancel_btn.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save Macro", panel)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("background: rgba(255,255,255,10); color: rgba(255,255,255,60); border: none;")
        self.save_btn.clicked.connect(self._save_and_exit)
        bb.addWidget(cancel_btn); bb.addStretch(); bb.addWidget(self.save_btn)
        layout.addLayout(bb)

    def _handle_action_click(self):
        if not self.name_input.text() or not self.shortcut_input.text():
            self.status_label.setText("Please fill in name and shortcut first!")
            self.status_label.setStyleSheet("color: #FF0080; font-size: 11px;")
            return
        if not self.is_recording:
            self.is_recording = True
            self.recorded_trajectory = []
            self.name_input.setEnabled(False)
            self.shortcut_input.setEnabled(False)
            self.action_btn.setText("Stop & Save")
            self.action_btn.setStyleSheet("background: rgba(255, 0, 128, 20); border: 1px solid #FF0080; color: #FF0080;")
            self.status_label.setText("Draw your gesture in front of camera...")
            self.status_label.setStyleSheet("color: #00F2FE; font-size: 11px;")
        else:
            self.is_recording = False
            self.action_btn.setEnabled(False)
            self.action_btn.setText("Trajectory locked")
            self.action_btn.setStyleSheet("background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,20); color: rgba(255,255,255,100);")
            self.status_label.setText(f"Captured {len(self.recorded_trajectory)} frames")
            self.status_label.setStyleSheet("color: #00FF96; font-size: 11px;")
            if len(self.recorded_trajectory) > 10:
                self.save_btn.setEnabled(True)
                self.save_btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00F2FE, stop:1 #9327FF); color: white;")

    def collect_coordinate(self, nx, ny):
        if self.is_recording:
            self.recorded_trajectory.append([nx, ny])
            self.status_label.setText(f"Tracking... {len(self.recorded_trajectory)} frames")

    def _save_and_exit(self):
        self.recorded_name = self.name_input.text()
        self.recorded_shortcut = self.shortcut_input.text()
        self.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()