# src/ui/settings_window.py
import sys, time
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QSlider, QComboBox, QPushButton,
    QSystemTrayIcon, QMenu, QAction, QApplication,
)
from src.config import EngineConfig


class SettingsDashboard(QWidget):
    def __init__(self, ui_shell_reference):
        super().__init__()
        self.ui_shell = ui_shell_reference
        EngineConfig.load_json()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(420, 520)
        self.drag_position = QPoint()
        self._init_system_tray()
        self._init_ui()
        self._apply_initial_config()

    def _init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        tray_menu = QMenu()
        show_action = QAction("Open Dashboard", self)
        show_action.triggered.connect(self.show_normal_raised)
        self.pause_action = QAction("Pause Agent", self, checkable=True)
        self.pause_action.triggered.connect(self._toggle_agent_sleep)
        quit_action = QAction("Quit Application", self)
        quit_action.triggered.connect(self._completely_quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(self.pause_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _init_ui(self):
        self.main_panel = QWidget(self)
        self.main_panel.setGeometry(0, 0, 420, 520)
        self.main_panel.setObjectName("MainPanel")
        self.main_panel.setStyleSheet(
            "QWidget#MainPanel {"
            "  background-color: rgba(20, 20, 28, 235);"
            "  border: 1px solid rgba(255, 255, 255, 45);"
            "  border-radius: 24px;"
            "}"
            "QLabel { color: #E2E2EA; font-family: Segoe UI; }"
            "QSlider::groove:horizontal { height: 6px; background: rgba(255, 255, 255, 25); border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #00F2FE; width: 14px; margin-top: -4px; margin-bottom: -4px; border-radius: 7px; }"
            "QComboBox { background: rgba(255,255,255,12); border: 1px solid rgba(255,255,255,30); border-radius: 8px; padding: 5px; color: white; }"
            "QComboBox QAbstractItemView { background: #14141C; color: white; border: 1px solid rgba(255,255,255,30); }"
        )
        layout = QVBoxLayout(self.main_panel)
        layout.setContentsMargins(30, 25, 30, 25)

        title_box = QHBoxLayout()
        title = QLabel("AirControl Dashboard", self)
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        close_btn = QPushButton("X", self)
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet("background: transparent; color: #FF0080; font-size: 14px; border: none;")
        close_btn.clicked.connect(self.hide_to_tray)
        title_box.addWidget(title)
        title_box.addStretch()
        title_box.addWidget(close_btn)
        layout.addLayout(title_box)
        layout.addSpacing(15)

        layout.addWidget(QLabel("Glow Theme:", self))
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["Cyberpunk (Cyan/Purple/Pink)", "Night Hunter (Blue/Green/Dark)", "Solar Flare (Orange/Gold/Red)"])
        self.theme_combo.currentIndexChanged.connect(self._change_theme)
        layout.addWidget(self.theme_combo)
        layout.addSpacing(20)

        self._create_slider_row(layout, "Static Stability (Alpha Min)", 1, 30, int(EngineConfig.ALPHA_MIN * 100), 100.0, "ALPHA_MIN")
        self._create_slider_row(layout, "Pinch Sensitivity (Pinch)", 2, 8, int(EngineConfig.PINCH_THRESHOLD * 100), 100.0, "PINCH_THRESHOLD")
        self._create_slider_row(layout, "Scroll Sensitivity", 10, 40, int(EngineConfig.SCROLL_SENSITIVITY * 10), 10.0, "SCROLL_SENSITIVITY")

        layout.addStretch()

        status_box = QHBoxLayout()
        self.light_icon = QLabel("O", self)
        self.light_icon.setStyleSheet("color: #00F2FE; font-size: 15px;")
        self.light_text = QLabel("Space agent: active monitoring", self)
        self.light_text.setFont(QFont("Segoe UI", 9))
        self.light_text.setStyleSheet("color: rgba(255,255,255,160);")
        status_box.addWidget(self.light_icon)
        status_box.addWidget(self.light_text)
        layout.addLayout(status_box)

    def _create_slider_row(self, parent, label, lo, hi, init_val, divisor, cfg_key):
        row = QVBoxLayout()
        lbl = QLabel(f"{label}: {init_val / divisor:.2f}", self)
        lbl.setStyleSheet("color: rgba(255,255,255,170); font-size: 11px;")
        slider = QSlider(Qt.Horizontal, self)
        slider.setRange(lo, hi)
        slider.setValue(init_val)

        def on_changed(val, cfg=cfg_key, div=divisor, w=lbl, t=label):
            real = val / div
            w.setText(f"{t}: {real:.2f}")
            setattr(EngineConfig, cfg, real)
            EngineConfig.save_json()

        slider.valueChanged.connect(on_changed)
        row.addWidget(lbl)
        row.addWidget(slider)
        parent.addLayout(row)
        parent.addSpacing(12)

    def _apply_initial_config(self):
        self.theme_combo.setCurrentIndex(EngineConfig.CURRENT_THEME_INDEX)
        self._change_theme(EngineConfig.CURRENT_THEME_INDEX)

    def _change_theme(self, index):
        EngineConfig.CURRENT_THEME_INDEX = index
        EngineConfig.save_json()
        if index == 0:
            self.ui_shell.color_palette = [QColor(0, 242, 254), QColor(147, 39, 255), QColor(255, 0, 128)]
        elif index == 1:
            self.ui_shell.color_palette = [QColor(0, 102, 255), QColor(0, 255, 150), QColor(10, 20, 50)]
        elif index == 2:
            self.ui_shell.color_palette = [QColor(255, 95, 0), QColor(255, 210, 0), QColor(255, 0, 60)]

    def hide_to_tray(self):
        self.hide()
        self.tray_icon.showMessage("AirControl Agent", "App is running in the system tray.", QSystemTrayIcon.Information, 2000)

    def show_normal_raised(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible(): self.hide()
            else: self.show_normal_raised()

    def _toggle_agent_sleep(self, checked):
        if checked:
            self.light_icon.setStyleSheet("color: #FF0080; font-size: 15px;")
            self.light_text.setText("Space agent: PAUSED")
            self.ui_shell.update_ui_state("SLEEP", 0.05)
        else:
            self.light_icon.setStyleSheet("color: #00F2FE; font-size: 15px;")
            self.light_text.setText("Space agent: active monitoring")
            self.ui_shell.update_ui_state("RELEASE", 0.15)

    def _completely_quit(self):
        self.tray_icon.hide()
        QApplication.quit()
        sys.exit(0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    def update_status(self, state, intensity):
        colors = {
            "SLEEP": "#FF0080", "MACRO": "#FFD700",
            "CLICK": "#FF4500", "SCROLL": "#00F2FE",
            "MOVE": "#00FF96",             "RELEASE": "#808080",
        }
        prefix = state.split("_")[0] if "MACRO" in state else state
        self.light_icon.setStyleSheet(f"color: {colors.get(prefix, '#00F2FE')}; font-size: 15px;")
        self.light_text.setText(f"{state} ({intensity:.2f})")