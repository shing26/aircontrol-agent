# src/ui/main_dashboard.py
import sys, time
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QComboBox, QCheckBox,
    QDialog, QSystemTrayIcon, QMenu, QAction, QApplication,
)
from src.config import EngineConfig
from src.ui.recording_dialog import GestureRecordingDialog


class AirControlMainDashboard(QWidget):
    def __init__(self, ui_shell, on_master_toggle=None, on_theme_change=None):
        super().__init__()
        self.ui_shell = ui_shell
        self.on_master_toggle = on_master_toggle
        self.on_theme_change = on_theme_change
        EngineConfig.load_json()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(800, 550)
        self.drag_position = QPoint()
        self.master_active = True
        self.on_macro_recorded_callback = None
        self.active_dialog = None
        self._init_system_tray()
        self._init_ui()
        self._apply_initial_config()

    def _init_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        m = QMenu()
        a1 = QAction("Open Dashboard", self); a1.triggered.connect(self.show_normal_raised)
        a2 = QAction("Pause Agent", self, checkable=True); a2.triggered.connect(self._toggle_agent_sleep)
        self.pause_action = a2
        a3 = QAction("Quit", self); a3.triggered.connect(self._completely_quit)
        m.addAction(a1); m.addAction(a2); m.addSeparator(); m.addAction(a3)
        self.tray_icon.setContextMenu(m)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _init_ui(self):
        self.bg_wrapper = QWidget(self)
        self.bg_wrapper.setGeometry(0, 0, 800, 550)
        self.bg_wrapper.setObjectName("BgWrapper")
        self.bg_wrapper.setStyleSheet(
            "QWidget#BgWrapper { background-color: #0E0E14; border: 1px solid rgba(255, 255, 255, 30); border-radius: 20px; }"
            "QWidget#Sidebar { background-color: #14141E; border-top-left-radius: 19px; border-bottom-left-radius: 19px; border-right: 1px solid rgba(255, 255, 255, 15); }"
            "QWidget#MainPanel { background-color: rgba(22, 22, 32, 160); border: 1px solid rgba(255, 255, 255, 15); border-radius: 16px; }"
            "QLabel { color: #E2E2EA; font-family: Segoe UI; }"
            "QTableWidget { background: transparent; border: none; gridline-color: rgba(255, 255, 255, 10); color: #FFFFFF; font-family: Segoe UI; }"
            "QTableWidget::item { padding-left: 10px; }"
            "QHeaderView::section { background-color: rgba(255, 255, 255, 8); color: rgba(255, 255, 255, 160); border: none; font-weight: bold; padding: 6px; }"
            "QComboBox { background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,25); border-radius: 8px; padding: 5px; color: white; }"
            "QComboBox QAbstractItemView { background: #14141E; color: white; }"
            "QCheckBox::indicator { width: 16px; height: 16px; }"
        )

        main_layout = QHBoxLayout(self.bg_wrapper)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget(self)
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(20, 25, 20, 25)

        logo = QLabel("AirControl Core", self)
        logo.setFont(QFont("Segoe UI", 14, QFont.Bold))
        logo.setStyleSheet("color: #00F2FE;")
        sl.addWidget(logo)
        sl.addSpacing(25)

        nav1 = QPushButton("Dashboard", self)
        nav1.setStyleSheet("background: rgba(255,255,255,12); color: white; text-align: left; padding: 10px; border-radius: 8px; border: none; font-weight: bold;")
        nav2 = QPushButton("Gesture Library", self)
        nav2.setStyleSheet("background: transparent; color: rgba(255,255,255,150); text-align: left; padding: 10px; border-radius: 8px; border: none;")
        sl.addWidget(nav1)
        sl.addWidget(nav2)
        sl.addStretch()

        sl.addWidget(QLabel("Master Switch", self))
        self.master_btn = QPushButton("Engine ON", self)
        self._set_master_style(True)
        self.master_btn.clicked.connect(self._toggle_master)
        sl.addWidget(self.master_btn)
        sl.addSpacing(15)

        sl.addWidget(QLabel("Theme", self))
        self.theme_combo = QComboBox(self)
        self.theme_combo.addItems(["Cyberpunk", "Night Hunter", "Solar Flare"])
        self.theme_combo.currentIndexChanged.connect(self._change_theme)
        sl.addWidget(self.theme_combo)

        rc = QWidget(self)
        rl = QVBoxLayout(rc)
        rl.setContentsMargins(25, 20, 25, 20)

        # Top bar with telemetry + close
        tb = QHBoxLayout()
        self.telemetry_label = QLabel("O Space agent: active monitoring", self)
        self.telemetry_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.telemetry_label.setStyleSheet("color: #00F2FE;")
        cam_btn = QPushButton("Camera Preview: OFF", self)
        cam_btn.setStyleSheet("background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,20); border-radius: 6px; color: white; padding: 4px 10px; font-size: 11px;")
        self.cam_btn = cam_btn
        close_btn = QPushButton("X", self)
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("background: transparent; color: #FF0080; font-size: 14px; font-weight: bold; border: none;")
        close_btn.clicked.connect(self.hide_to_tray)
        tb.addWidget(self.telemetry_label); tb.addStretch(); tb.addWidget(cam_btn); tb.addSpacing(10); tb.addWidget(close_btn)
        rl.addLayout(tb)
        rl.addSpacing(15)

        # Main panel with gesture matrix
        mp = QWidget(self)
        mp.setObjectName("MainPanel")
        pl = QVBoxLayout(mp)
        pl.setContentsMargins(15, 15, 15, 15)

        pl.addWidget(QLabel("Gesture Matrix", self))
        pl.addSpacing(10)

        self.table = QTableWidget(0, 4, self)
        self.table.setHorizontalHeaderLabels(["Gesture", "System Action", "Status", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self.append_new_gesture_row("Point Up", "Move cursor", True, True)
        self.append_new_gesture_row("Pinch", "Left click", True, True)
        self.append_new_gesture_row("V-Sign", "Scroll", True, True)
        self.append_new_gesture_row("Circle", "Macro [Win+Shift+S]", False, False)

        pl.addWidget(self.table)
        rl.addWidget(mp)
        rl.addSpacing(15)

        self.record_btn = QPushButton("+ Record custom gesture macro (1.1 core feature)", self)
        self.record_btn.setEnabled(True)
        self.record_btn.setStyleSheet("background: rgba(0, 242, 254, 8); border: 2px dashed rgba(0, 242, 254, 50); border-radius: 12px; color: #00F2FE; padding: 12px; font-family: Segoe UI; font-weight: bold;")
        self.record_btn.clicked.connect(self._launch_recording_wizard)
        rl.addWidget(self.record_btn)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(rc)

    def append_new_gesture_row(self, name, action, checked, locked):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(name))
        self.table.setItem(row, 1, QTableWidgetItem(action))
        cbw = QWidget(); cbl = QHBoxLayout(cbw); cbl.setContentsMargins(0,0,0,0); cbl.setAlignment(Qt.AlignCenter)
        cb = QCheckBox(); cb.setChecked(checked); cbl.addWidget(cb)
        self.table.setCellWidget(row, 2, cbw)
        bw = QWidget(); bl = QHBoxLayout(bw); bl.setContentsMargins(0,0,0,0); bl.setAlignment(Qt.AlignCenter)
        if locked:
            lg = QLabel("Locked", self); lg.setStyleSheet("color: rgba(255,255,255,80); font-size: 11px;"); bl.addWidget(lg)
        else:
            d = QPushButton("Delete", self)
            d.setStyleSheet("background: rgba(255,0,128,20); border: 1px solid rgba(255,0,128,40); border-radius: 4px; color: #FF0080; padding: 2px 8px; font-size: 11px;")
            def make_handler(r=row, n=name):
                return lambda: self._handle_row_deletion(r, n)
            d.clicked.connect(make_handler())
            bl.addWidget(d)
        self.table.setCellWidget(row, 3, bw)
        self.table.setRowHeight(row, 36)

    def _toggle_master(self):
        self.master_active = not self.master_active
        self._set_master_style(self.master_active)
        if self.master_active:
            self.telemetry_label.setText("O Space agent: active monitoring")
            self.telemetry_label.setStyleSheet("color: #00F2FE;")
        else:
            self.telemetry_label.setText("X Space agent: engine OFF")
            self.telemetry_label.setStyleSheet("color: #FF0080;")
        if self.on_master_toggle:
            self.on_master_toggle(self.master_active)

    def _set_master_style(self, active):
        if active:
            self.master_btn.setText("Engine ON")
            self.master_btn.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00F2FE, stop:1 #9327FF); color: white; border-radius: 10px; font-weight: bold; padding: 10px; border: none;")
        else:
            self.master_btn.setText("Engine OFF")
            self.master_btn.setStyleSheet("background: rgba(255,255,255,10); color: rgba(255,255,255,100); border: 1px solid rgba(255,255,255,20); border-radius: 10px; padding: 10px;")

    def _change_theme(self, index):
        EngineConfig.CURRENT_THEME_INDEX = index
        EngineConfig.save_json()
        if index == 0:
            self.ui_shell.color_palette = [QColor(0, 242, 254), QColor(147, 39, 255), QColor(255, 0, 128)]
        elif index == 1:
            self.ui_shell.color_palette = [QColor(0, 102, 255), QColor(0, 255, 150), QColor(10, 20, 50)]
        elif index == 2:
            self.ui_shell.color_palette = [QColor(255, 95, 0), QColor(255, 210, 0), QColor(255, 0, 60)]

    def update_status(self, state, intensity):
        colors = {'SLEEP':'#FF0080','MACRO':'#FFD700','CLICK':'#FF4500','SCROLL':'#00F2FE','MOVE':'#00FF96','RELEASE':'#808080'}
        pfx = state.split('_')[0] if 'MACRO' in state else state
        self.telemetry_label.setText(f"O {state} ({intensity:.2f})")
        self.telemetry_label.setStyleSheet(f"color: {colors.get(pfx, '#00F2FE')}; font-size: 10pt; font-weight: bold;")

    def _handle_row_deletion(self, row_index, gesture_name):
        self.table.removeRow(row_index)
        print(f"[Dashboard] Removed row {row_index}: {gesture_name}")

    def _launch_recording_wizard(self):
        self.active_dialog = GestureRecordingDialog(self)
        if self.active_dialog.exec() == QDialog.Accepted:
            name = self.active_dialog.recorded_name
            shortcut = self.active_dialog.recorded_shortcut
            trajectory = self.active_dialog.recorded_trajectory
            display_name = f"Macro: {name}"
            display_action = f"Shortcut [{shortcut}]"
            self.append_new_gesture_row(display_name, display_action, True, False)
            if self.on_macro_recorded_callback:
                self.on_macro_recorded_callback(name, shortcut, trajectory)
        self.active_dialog = None

    def _apply_initial_config(self):
        self.theme_combo.setCurrentIndex(EngineConfig.CURRENT_THEME_INDEX)
        self._change_theme(EngineConfig.CURRENT_THEME_INDEX)

    def hide_to_tray(self):
        self.hide()
        self.tray_icon.showMessage("AirControl", "Running in system tray.", QSystemTrayIcon.Information, 2000)

    def show_normal_raised(self):
        self.showNormal(); self.activateWindow(); self.raise_()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isVisible(): self.hide()
            else: self.show_normal_raised()

    def _toggle_agent_sleep(self, checked):
        if checked:
            self.telemetry_label.setText('O PAUSED')
            self.telemetry_label.setStyleSheet('color: #FF0080; font-size: 10pt; font-weight: bold;')
            self.ui_shell.update_ui_state("SLEEP", 0.05)
        else:
            self.telemetry_label.setText('O Active monitoring')
            self.telemetry_label.setStyleSheet('color: #00F2FE; font-size: 10pt; font-weight: bold;')
            self.ui_shell.update_ui_state("RELEASE", 0.15)

    def _completely_quit(self):
        self.tray_icon.hide()
        QApplication.quit(); sys.exit(0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from src.ui.siri_window import SiriGlowShell
    shell = SiriGlowShell(800, 550)
    d = AirControlMainDashboard(shell)
    d.show()
    sys.exit(app.exec_())