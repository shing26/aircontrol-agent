# src/ui/control_center.py
import sys, time
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QFont, QColor, QIcon
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame,
    QSystemTrayIcon, QMenu, QAction, QApplication,
)
from src.config import EngineConfig


class ControlCenter(QWidget):
    def __init__(self, ui_shell, on_master_toggle=None, on_theme_change=None, on_delete_macro=None):
        super().__init__()
        self.ui_shell = ui_shell
        self.on_master_toggle = on_master_toggle
        self.on_theme_change = on_theme_change
        self.on_delete_macro = on_delete_macro
        EngineConfig.load_json()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("ControlCenter")
        self.resize(800, 550)
        self.drag_position = QPoint()
        self.master_active = True
        self.preview_active = False
        self._init_system_tray()
        self._init_style()
        self._init_sidebar()
        self._init_main_panel()
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

    def _init_style(self):
        self.setStyleSheet(
            "QWidget#ControlCenter { background-color: #12121A; }"
            "QWidget#MainPanel { background-color: rgba(26, 26, 36, 150); border: 1px solid rgba(255, 255, 255, 20); border-radius: 16px; }"
            "QWidget#Sidebar { background-color: transparent; }"
            "QWidget#StatusBar { background-color: rgba(26, 26, 36, 100); border: 1px solid rgba(255, 255, 255, 10); border-radius: 10px; }"
            "QLabel { color: #E2E2EA; font-family: Segoe UI; }"
            "QLabel#TitleLabel { color: #00F2FE; font-size: 16px; font-weight: bold; }"
            "QLabel#NavItem { color: rgba(255, 255, 255, 180); font-size: 13px; padding: 8px 12px; }"
            "QLabel#NavItemActive { color: #00F2FE; font-size: 13px; font-weight: bold; padding: 8px 12px; background-color: rgba(0, 242, 254, 15); border-radius: 6px; }"
            "QLabel#NavItemDisabled { color: rgba(255, 255, 255, 60); font-size: 13px; padding: 8px 12px; }"
            "QPushButton[state=\"active\"] { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00F2FE, stop:1 #9327FF); color: #FFFFFF; border: none; border-radius: 12px; font-size: 14px; font-weight: bold; padding: 12px 20px; }"
            "QPushButton[state=\"inactive\"] { background: rgba(255, 255, 255, 10); color: rgba(255, 255, 255, 100); border: 1px solid rgba(255, 255, 255, 20); border-radius: 12px; font-size: 14px; font-weight: bold; padding: 12px 20px; }"
            "QPushButton#PreviewBtn { background: rgba(255, 255, 255, 8); color: rgba(255, 255, 255, 140); border: 1px solid rgba(255, 255, 255, 15); border-radius: 6px; padding: 4px 10px; font-size: 11px; }"
            "QPushButton#PreviewBtn[state=\"on\"] { color: #00F2FE; border: 1px solid #00F2FE; }"
            "QPushButton#DeleteBtn { background: transparent; color: #FF0080; border: none; font-size: 14px; }"
            "QPushButton#DeleteBtn[state=\"locked\"] { color: rgba(255, 255, 255, 30); }"
            "QPushButton#FutureBtn { background: transparent; color: rgba(255, 255, 255, 40); border: 1px dashed rgba(255, 255, 255, 25); border-radius: 8px; padding: 10px; font-size: 12px; }"
            "QComboBox { background: rgba(255, 255, 255, 8); border: 1px solid rgba(255, 255, 255, 15); border-radius: 6px; padding: 4px 8px; color: white; font-size: 11px; }"
            "QComboBox QAbstractItemView { background: #1A1A24; color: white; border: 1px solid rgba(255, 255, 255, 15); }"
            "QTableWidget { background-color: transparent; border: none; gridline-color: rgba(255, 255, 255, 8); font-size: 12px; color: #E2E2EA; }"
            "QTableWidget::item { padding: 6px; border-bottom: 1px solid rgba(255, 255, 255, 8); }"
            "QHeaderView::section { background-color: transparent; color: rgba(255, 255, 255, 100); border: none; border-bottom: 1px solid rgba(255, 255, 255, 15); padding: 6px; font-size: 11px; font-weight: bold; }"
        )

    def _init_sidebar(self):
        self.sidebar = QWidget(self)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setGeometry(0, 0, 210, 550)
        s = QVBoxLayout(self.sidebar)
        s.setContentsMargins(20, 25, 15, 20)

        title = QLabel("AirControl Core", self.sidebar)
        title.setObjectName("TitleLabel")
        s.addWidget(title)
        s.addSpacing(25)

        nav1 = QLabel("Dashboard", self.sidebar)
        nav1.setObjectName("NavItemActive")
        s.addWidget(nav1)
        nav2 = QLabel("Gesture Library", self.sidebar)
        nav2.setObjectName("NavItemDisabled")
        s.addWidget(nav2)
        s.addSpacing(30)

        sep = QFrame(self.sidebar)
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,10);")
        s.addWidget(sep)
        s.addSpacing(20)

        s.addWidget(QLabel("Master Control", self.sidebar))
        self.master_btn = QPushButton("ENGINE ON", self.sidebar)
        self.master_btn.setObjectName("MasterBtn")
        self.master_btn.setProperty("state", "active")
        self.master_btn.setCursor(Qt.PointingHandCursor)
        self.master_btn.clicked.connect(self._toggle_master)
        self.master_btn.setMinimumHeight(48)
        s.addWidget(self.master_btn)
        s.addStretch()

        s.addWidget(QLabel("Theme", self.sidebar))
        self.theme_combo = QComboBox(self.sidebar)
        self.theme_combo.addItems(["Cyberpunk", "Night Hunter", "Solar Flare"])
        self.theme_combo.currentIndexChanged.connect(self._change_theme)
        s.addWidget(self.theme_combo)

    def _init_main_panel(self):
        main = QWidget(self)
        main.setObjectName("MainPanel")
        main.setGeometry(225, 20, 555, 510)
        ml = QVBoxLayout(main)
        ml.setContentsMargins(20, 15, 20, 15)

        # Status bar
        sb = QHBoxLayout()
        self.status_icon = QLabel("O", main)
        self.status_icon.setStyleSheet("color: #00FF96; font-size: 14px;")
        self.status_text = QLabel("Active monitoring", main)
        self.status_text.setStyleSheet("color: rgba(255,255,255,160); font-size: 11px;")
        sb.addWidget(self.status_icon)
        sb.addWidget(self.status_text)
        sb.addStretch()
        self.preview_btn = QPushButton("Camera Preview: OFF", main)
        self.preview_btn.setObjectName("PreviewBtn")
        self.preview_btn.setCursor(Qt.PointingHandCursor)
        self.preview_btn.clicked.connect(self._toggle_preview)
        sb.addWidget(self.preview_btn)
        ml.addLayout(sb)
        ml.addSpacing(15)

        # Gesture matrix title
        ml.addWidget(QLabel("Gesture Matrix", main))
        ml.addSpacing(8)

        # Gesture table
        self.table = QTableWidget(4, 4, main)
        self.table.setHorizontalHeaderLabels(["Gesture", "System Action", "Status", "Delete"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setColumnWidth(2, 80)
        self.table.setColumnWidth(3, 60)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setShowGrid(True)
        self.table.setMinimumHeight(200)

        gestures = [
            ("Point Up", "Move cursor", True, True),
            ("Pinch", "Left click", True, True),
            ("V-Sign", "Scroll", True, True),
            ("Circle", "Macro shortcut", False, False),
        ]

        for row, (g, a, enabled, locked) in enumerate(gestures):
            gi = QTableWidgetItem(g); gi.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            ai = QTableWidgetItem(a); ai.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table.setItem(row, 0, gi); self.table.setItem(row, 1, ai)

            # Toggle button
            tog = QPushButton("ON" if enabled else "OFF")
            tog.setFixedSize(60, 24)
            tog.setCursor(Qt.PointingHandCursor)
            if locked:
                tog.setEnabled(True)
            if not enabled:
                pass
            self.table.setCellWidget(row, 2, tog)

            # Delete button
            del_btn = QPushButton("X")
            del_btn.setObjectName("DeleteBtn")
            del_btn.setFixedSize(40, 24)
            del_btn.setCursor(Qt.PointingHandCursor)
            if locked:
                del_btn.setProperty("state", "locked")
                del_btn.setEnabled(False)
            else:
                del_btn.clicked.connect(lambda checked, r=row: self._delete_macro(r))
            self.table.setCellWidget(row, 3, del_btn)

            # Row height
            self.table.setRowHeight(row, 38)

        ml.addWidget(self.table)
        ml.addSpacing(15)

        # Future feature button
        future_btn = QPushButton("+ Record custom gesture macro (coming soon)", main)
        future_btn.setObjectName("FutureBtn")
        future_btn.setEnabled(False)
        ml.addWidget(future_btn)
        ml.addStretch()

        # Bottom status bar
        bot = QHBoxLayout()
        bot.addWidget(QLabel("Engine ready", main))
        bot.addStretch()
        self.config_label = QLabel("config.json synced", main)
        self.config_label.setStyleSheet("color: rgba(255,255,255,80); font-size: 10px;")
        bot.addWidget(self.config_label)
        ml.addLayout(bot)

    def _toggle_master(self):
        self.master_active = not self.master_active
        state = "active" if self.master_active else "inactive"
        self.master_btn.setProperty("state", state)
        self.master_btn.style().unpolish(self.master_btn)
        self.master_btn.style().polish(self.master_btn)
        self.master_btn.setText("ENGINE ON" if self.master_active else "ENGINE OFF")
        if self.on_master_toggle:
            self.on_master_toggle(self.master_active)

    def _toggle_preview(self):
        self.preview_active = not self.preview_active
        state = "on" if self.preview_active else "off"
        self.preview_btn.setProperty("state", state)
        self.preview_btn.style().unpolish(self.preview_btn)
        self.preview_btn.style().polish(self.preview_btn)
        txt = "Camera Preview: ON" if self.preview_active else "Camera Preview: OFF"
        self.preview_btn.setText(txt)

    def _change_theme(self, index):
        EngineConfig.CURRENT_THEME_INDEX = index
        EngineConfig.save_json()
        if index == 0:
            self.ui_shell.color_palette = [QColor(0, 242, 254), QColor(147, 39, 255), QColor(255, 0, 128)]
        elif index == 1:
            self.ui_shell.color_palette = [QColor(0, 102, 255), QColor(0, 255, 150), QColor(10, 20, 50)]
        elif index == 2:
            self.ui_shell.color_palette = [QColor(255, 95, 0), QColor(255, 210, 0), QColor(255, 0, 60)]
        self.config_label.setText("config.json synced")

    def _delete_macro(self, row):
        if self.on_delete_macro:
            self.on_delete_macro(row)
        self.table.setRowHidden(row, True)

    def update_status(self, state, intensity):
        colors = {'SLEEP':'#FF0080','MACRO':'#FFD700','CLICK':'#FF4500','SCROLL':'#00F2FE','MOVE':'#00FF96','RELEASE':'#808080'}
        pfx = state.split('_')[0] if 'MACRO' in state else state
        self.status_icon.setStyleSheet(f"color: {colors.get(pfx, '#00F2FE')}; font-size: 14px;")
        self.status_text.setText(f"{state} ({intensity:.2f})")

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
            self.status_icon.setStyleSheet('color: #FF0080; font-size: 14px;')
            self.status_text.setText('PAUSED')
            self.ui_shell.update_ui_state("SLEEP", 0.05)
        else:
            self.status_icon.setStyleSheet('color: #00F2FE; font-size: 14px;')
            self.status_text.setText('Active monitoring')
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