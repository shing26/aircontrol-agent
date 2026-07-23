# client_app.py ? AirControl Premium Control Center
"""1020x680 multi-page spatial computing control center."""
import sys, time, math
import cv2
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QCheckBox, QDialog, QLineEdit, QSlider,
    QStackedWidget, QFrame, QSystemTrayIcon, QMenu, QAction,
)
from src.config import EngineConfig
from consumer_app import SlateToggle
from src.vision.pipeline import FramePipeline, VisionAgentThread
from src.control.os_mapper import InputMapper


class CameraProducer(QThread):
    frame_signal = pyqtSignal(object)
    def __init__(self): super().__init__(); self.running = True
    def run(self):
        cap = cv2.VideoCapture(EngineConfig.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, EngineConfig.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, EngineConfig.FRAME_HEIGHT)
        while self.running:
            ret, frame = cap.read()
            if not ret: break
            if self.running: self.frame_signal.emit(frame)
        cap.release()
    def stop(self): self.running = False


class PremiumRecordingWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setFixedSize(380, 380)
        self.drag_pos = QPoint()
        self.recorded_trajectory = []; self.is_recording = False
        self.recorded_name = ""; self.recorded_shortcut = ""
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet(
            "PremiumRecordingWizard { background-color: #14141E; border: 2px solid #00F2FE; border-radius: 18px; }"
            "QLabel { color: #E2E2EA; font-family: Segoe UI; }"
            "QLineEdit { background: rgba(255,255,255,8); border: 1px solid rgba(255,255,255,20); border-radius: 8px; padding: 8px; color: white; font-size: 12px; }"
        )
        l = QVBoxLayout(self); l.setContentsMargins(24,18,24,18)
        l.addWidget(QLabel("Record Gesture Macro", self)); l.addSpacing(12)
        l.addWidget(QLabel("Gesture Name", self))
        self.name_in = QLineEdit(self); self.name_in.setPlaceholderText("e.g. SWIPE_RIGHT")
        l.addWidget(self.name_in); l.addSpacing(8)
        l.addWidget(QLabel("Keyboard Shortcut", self))
        self.key_in = QLineEdit(self); self.key_in.setPlaceholderText("e.g. ctrl+shift+v")
        l.addWidget(self.key_in); l.addSpacing(12)
        self.status_lb = QLabel("Ready", self)
        self.status_lb.setAlignment(Qt.AlignCenter)
        self.status_lb.setStyleSheet("color:rgba(255,255,255,130);font-size:11px;padding:8px;")
        l.addWidget(self.status_lb)
        self.act_btn = QPushButton("Start Recording", self)
        self.act_btn.setStyleSheet("background:rgba(0,242,254,15);border:1px solid #00F2FE;color:#00F2FE;border-radius:8px;padding:10px;font-weight:bold;font-size:12px;")
        self.act_btn.clicked.connect(self._on_action)
        l.addWidget(self.act_btn); l.addStretch()
        bb = QHBoxLayout()
        cx = QPushButton("Cancel", self)
        cx.setStyleSheet("background:transparent;color:rgba(255,255,255,100);border:none;font-size:12px;")
        cx.clicked.connect(self.reject)
        self.save_btn = QPushButton("Save Macro", self); self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("background:rgba(255,255,255,8);color:rgba(255,255,255,50);border:none;border-radius:8px;padding:10px;font-size:12px;")
        self.save_btn.clicked.connect(self._validate)
        bb.addWidget(cx); bb.addStretch(); bb.addWidget(self.save_btn)
        l.addLayout(bb)

    def collect_coord(self, nx, ny):
        if self.is_recording: self.recorded_trajectory.append([nx, ny])
        self.status_lb.setText(f"Tracking... {len(self.recorded_trajectory)} frames")

    def _on_action(self):
        if not self.name_in.text() or not self.key_in.text():
            self.status_lb.setText("Fill in name + shortcut first!"); self.status_lb.setStyleSheet("color:#FF0080;font-size:11px;")
            return
        if not self.is_recording:
            self.is_recording = True; self.recorded_trajectory = []
            self.name_in.setEnabled(False); self.key_in.setEnabled(False)
            self.act_btn.setText("Stop Recording")
            self.act_btn.setStyleSheet("background:rgba(255,0,128,15);border:1px solid #FF0080;color:#FF0080;border-radius:8px;padding:10px;font-weight:bold;")
            self.status_lb.setText("Draw gesture in front of camera..."); self.status_lb.setStyleSheet("color:#00F2FE;font-size:11px;")
        else:
            self.is_recording = False; self.act_btn.setEnabled(False)
            self.act_btn.setText("Trajectory Locked"); n = len(self.recorded_trajectory)
            self.status_lb.setText(f"Captured {n} frames"); self.status_lb.setStyleSheet("color:#00FF96;font-size:11px;")
            if n > 10:
                self.save_btn.setEnabled(True)
                self.save_btn.setStyleSheet("background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #00F2FE,stop:1 #9327FF);color:white;border-radius:8px;padding:10px;font-weight:bold;")

    def _validate(self):
        self.recorded_name = self.name_in.text(); self.recorded_shortcut = self.key_in.text(); self.accept()
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.drag_pos = e.globalPos() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton: self.move(e.globalPos() - self.drag_pos); e.accept()


PAGES = ["Dashboard", "Gesture Workshop", "Calibration", "Settings"]
PAGE_ICONS = ["O", "W", "C", "S"]

class AirControlPremiumApp(QWidget):
    def __init__(self, ui_shell=None):
        super().__init__()
        self._ui_shell = ui_shell
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(1020, 680)
        self.drag_pos = QPoint(); self.engine_on = True; self.current_page = 0
        self.active_dialog = None

        EngineConfig.load_json()
        self.pipeline = FramePipeline()
        screen = QApplication.primaryScreen().geometry()
        self.mapper = InputMapper(screen.width(), screen.height())
        self.vision_thread = None; self.camera_thread = None

        self._setup_tray(); self._assemble_framework(); self._start_engine()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        m = QMenu()
        a1 = QAction("Open Dashboard", self); a1.triggered.connect(self._raise_window)
        a2 = QAction("Quit", self); a2.triggered.connect(self._completely_quit)
        m.addAction(a1); m.addSeparator(); m.addAction(a2)
        self.tray.setContextMenu(m); self.tray.activated.connect(lambda r: self._on_tray(r)); self.tray.show()

    def _start_engine(self):
        self.pipeline = FramePipeline()
        self.camera_thread = CameraProducer()
        self.vision_thread = VisionAgentThread(self.pipeline)
        self.camera_thread.frame_signal.connect(self.pipeline.push)
        self.vision_thread.gesture_signal.connect(self._on_gesture)
        self.vision_thread.ui_signal.connect(self._on_ui_state)
        if self._ui_shell:
            self.vision_thread.ui_signal.connect(self._ui_shell.update_ui_state)
        self.vision_thread.start(); self.camera_thread.start()
        self.status_lb.setText("Agent: active"); self.status_lb.setStyleSheet("color:#00FF96;font-size:14px;font-weight:bold;")

    def _stop_engine(self):
        for t in ["camera_thread","vision_thread"]:
            th = getattr(self, t, None)
            if th:
                try:
                    if t == "camera_thread": th.frame_signal.disconnect()
                    else: th.gesture_signal.disconnect(); th.ui_signal.disconnect()
                except TypeError: pass
                th.stop()
        self.pipeline.push(None)
        for t in ["camera_thread","vision_thread"]:
            th = getattr(self, t, None)
            if th: th.wait(); setattr(self, t, None)

    def _on_gesture(self, state, nx, ny):
        self.mapper.on_gesture_received(state, nx, ny)
        if self.active_dialog and self.active_dialog.is_recording and nx > 0.001:
            self.active_dialog.collect_coord(nx, ny)

    def _on_ui_state(self, state, intensity):
        lbl = self.status_lb
        colors = {"SLEEP":"#FF0080","MACRO":"#FFD700","CLICK":"#FF4500","SCROLL":"#00F2FE","MOVE":"#00FF96","RELEASE":"#808080"}
        c = colors.get(state.split("_")[0] if "MACRO" in state else state, "#00F2FE")
        lbl.setText(f"O {state} ({intensity:.2f})"); lbl.setStyleSheet(f"color:{c};font-size:14px;font-weight:bold;")
        self.telemetry_ind.setStyleSheet(f"color:{c};font-size:18px;")


    def _assemble_framework(self):
        self.setStyleSheet(
            "QWidget#Wrapper { background-color: #0C0C12; border: 1px solid rgba(255,255,255,25); border-radius: 20px; }"
            "QWidget#LeftBar { background: #12121A; border-top-left-radius:19px; border-bottom-left-radius:19px; border-right: 1px solid rgba(255,255,255,10); }"
            "QWidget#PageCard { background: rgba(22,22,32,160); border: 1px solid rgba(255,255,255,12); border-radius: 16px; }"
            "QWidget#TelemetryBar { background: rgba(30,30,45,200); border: 1px solid rgba(255,255,255,20); border-radius: 10px; padding: 6px; }"
            "QLabel { color: #E2E2EA; font-family: Segoe UI; }"
            "QPushButton#NavBtn { background: transparent; color: rgba(255,255,255,140); text-align: left; padding: 12px 16px; border: none; border-radius: 8px; font-size: 13px; }"
            "QPushButton#NavBtn:hover { background: rgba(255,255,255,8); }"
            "QPushButton#NavBtn[active=\"true\"] { background: rgba(0,242,254,12); color: #00F2FE; font-weight: bold; }"
            "QPushButton#MasterBtn[state=\"on\"] { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #00F2FE,stop:1 #9327FF); color: white; border: none; border-radius: 10px; padding: 10px; font-weight: bold; font-size: 12px; }"
            "QPushButton#MasterBtn[state=\"off\"] { background: rgba(255,255,255,8); color: rgba(255,255,255,100); border: 1px solid rgba(255,255,255,15); border-radius: 10px; padding: 10px; font-size: 12px; }"
            "QTableWidget { background: transparent; border: none; gridline-color: rgba(255,255,255,6); color: #FFF; font-family: Segoe UI; font-size: 12px; }"
            "QHeaderView::section { background: rgba(255,255,255,4); color: rgba(255,255,255,130); border: none; border-bottom: 1px solid rgba(255,255,255,10); padding: 8px; font-size: 11px; font-weight: bold; }"
            "QSlider::groove:horizontal { height: 6px; background: rgba(255,255,255,20); border-radius: 3px; }"
            "QSlider::handle:horizontal { background: #00F2FE; width: 14px; margin: -4px 0; border-radius: 7px; }"
            "QComboBox { background: rgba(255,255,255,8); border: 1px solid rgba(255,255,255,15); border-radius: 8px; padding: 5px; color: white; font-size: 11px; }"
        )

        wrapper = QWidget(self); wrapper.setGeometry(0,0,1020,680); wrapper.setObjectName("Wrapper")
        ml = QHBoxLayout(wrapper); ml.setContentsMargins(0,0,0,0); ml.setSpacing(0)

        # ?? Sidebar ??
        lb = QWidget(self); lb.setObjectName("LeftBar"); lb.setFixedWidth(220)
        sl = QVBoxLayout(lb); sl.setContentsMargins(16,25,16,20)
        sl.addWidget(QLabel("AirControl", lb)); sl.addSpacing(22)

        self.nav_btns = []
        for i, (tag, icon) in enumerate(zip(PAGES, PAGE_ICONS)):
            b = QPushButton(f"  {icon}  {tag}", lb)
            b.setObjectName("NavBtn"); b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda checked, idx=i: self._switch_page(idx))
            self.nav_btns.append(b); sl.addWidget(b)
        sl.addStretch()

        sl.addWidget(QLabel("Master Switch", lb))
        self.master_btn = QPushButton("Engine Active", lb)
        self.master_btn.setObjectName("MasterBtn"); self.master_btn.setProperty("state","on")
        self.master_btn.setCursor(Qt.PointingHandCursor)
        self.master_btn.clicked.connect(self._toggle_master)
        sl.addWidget(self.master_btn); sl.addSpacing(12)
        sl.addWidget(QLabel("Theme", lb))
        self.theme_cb = QComboBox(lb)
        self.theme_cb.addItems(["Cyberpunk","Night Hunter","Solar Flare"])
        sl.addWidget(self.theme_cb)
        ml.addWidget(lb)

        # ?? Content area ??
        rc = QWidget(self); rl = QVBoxLayout(rc); rl.setContentsMargins(20,16,20,16); rl.setSpacing(10)

        # Telemetry bar
        tb = QWidget(self); tb.setObjectName("TelemetryBar")
        tbl = QHBoxLayout(tb); tbl.setContentsMargins(12,6,12,6)
        self.telemetry_ind = QLabel("O", tb); self.telemetry_ind.setStyleSheet("color:#00FF96;font-size:18px;")
        self.status_lb = QLabel("Initializing...", tb); self.status_lb.setStyleSheet("color:rgba(255,255,255,200);font-size:13px;")
        self.cam_btn = QPushButton("Camera Preview: OFF", tb)
        self.cam_btn.setStyleSheet("background:rgba(255,255,255,6);border:1px solid rgba(255,255,255,12);border-radius:6px;color:rgba(255,255,255,140);padding:4px 10px;font-size:10px;")
        self.cam_btn.setCursor(Qt.PointingHandCursor)
        cx = QPushButton("X", tb); cx.setFixedSize(22,22)
        cx.setStyleSheet("background:transparent;color:#FF0080;font-size:12px;font-weight:bold;border:none;")
        cx.setCursor(Qt.PointingHandCursor); cx.clicked.connect(self._hide_to_tray_msg)
        tbl.addWidget(self.telemetry_ind); tbl.addWidget(self.status_lb); tbl.addStretch(); tbl.addWidget(self.cam_btn); tbl.addSpacing(8); tbl.addWidget(cx)
        rl.addWidget(tb)

        # Stacked pages
        self.stack = QStackedWidget(self)
        self._build_home(); self._build_matrix(); self._build_calibration(); self._build_settings()
        rl.addWidget(self.stack, 1)

        # Bottom bar
        bb = QHBoxLayout(); bb.setContentsMargins(4,4,4,4)
        save_btn = QPushButton("Save Config", self)
        save_btn.setStyleSheet("background:rgba(0,242,254,10);border:1px solid rgba(0,242,254,40);border-radius:6px;color:#00F2FE;padding:6px 14px;font-size:10px;font-weight:bold;")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.clicked.connect(lambda: (EngineConfig.save_json(), setattr(self,"cfg_lb",None)))
        self.cfg_lb = QLabel("config.json synced", self)
        self.cfg_lb.setStyleSheet("color:rgba(255,255,255,60);font-size:9px;")
        bb.addWidget(save_btn); bb.addStretch(); bb.addWidget(self.cfg_lb)
        rl.addLayout(bb)
        ml.addWidget(rc)

        # Activate first page
        self._switch_page(0)

    def _build_home(self):
        p = QWidget(self); l = QVBoxLayout(p); l.setContentsMargins(0,0,0,0)
        l.addWidget(QLabel("Overview", p))
        l.addSpacing(8)
        mc = QHBoxLayout()
        for title, val, clr in [("Engine","Active","#00FF96"),("Templates","4","#00F2FE"),("Status","Ready","#FFD700")]:
            c = QWidget(p); c.setObjectName("PageCard")
            cl = QVBoxLayout(c); cl.setAlignment(Qt.AlignCenter)
            cl.addWidget(QLabel(val, c)); cl.addWidget(QLabel(title, c))
            c.layout().itemAt(0).widget().setStyleSheet(f"color:{clr};font-size:22px;font-weight:bold;")
            c.layout().itemAt(1).widget().setStyleSheet("color:rgba(255,255,255,100);font-size:10px;")
            mc.addWidget(c)
        l.addLayout(mc); l.addSpacing(12)
        l.addWidget(QLabel("Gesture Matrix", p), 1)
        t = QTableWidget(4,3,p)
        t.setHorizontalHeaderLabels(["Gesture","Action","Status"])
        t.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t.verticalHeader().setVisible(False); t.setSelectionMode(QTableWidget.NoSelection); t.setEditTriggers(QTableWidget.NoEditTriggers)
        for i,(g,a) in enumerate([("Point Up","Move cursor"),("Pinch","Left click"),("V-Sign","Scroll"),("Circle","Macro")]):
            t.setItem(i,0,QTableWidgetItem(g)); t.setItem(i,1,QTableWidgetItem(a))
            cw = QWidget(); cwl = QHBoxLayout(cw); cwl.setContentsMargins(0,0,0,0); cwl.setAlignment(Qt.AlignCenter)
            st = SlateToggle(); st.setChecked(True if i<3 else False); cwl.addWidget(st); t.setCellWidget(i,2,cw)
            t.setRowHeight(i,32)
        l.addWidget(t)
        self.stack.addWidget(p)

    def _build_matrix(self):
        p = QWidget(self); l = QVBoxLayout(p); l.setContentsMargins(0,0,0,0)
        l.addWidget(QLabel("Gesture Workshop", p)); l.addSpacing(8)
        self.matrix_table = QTableWidget(0,4,p)
        self.matrix_table.setHorizontalHeaderLabels(["Gesture","System Action","Status","Action"])
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.setSelectionMode(QTableWidget.NoSelection)
        self.matrix_table.setEditTriggers(QTableWidget.NoEditTriggers)
        for g,a,c,l_ in [("Point Up","Move cursor",True,True),("Pinch","Left click",True,True),("V-Sign","Scroll",True,True),("Circle","Macro [Win+Shift+S]",False,False)]:
            self._matrix_add_row(g,a,c,l_)
        l.addWidget(self.matrix_table, 1)
        rec = QPushButton("+ Record New Gesture Macro", p)
        rec.setStyleSheet("background:rgba(0,242,254,8);border:2px dashed rgba(0,242,254,40);border-radius:12px;color:#00F2FE;padding:12px;font-weight:bold;font-size:12px;")
        rec.setCursor(Qt.PointingHandCursor)
        rec.clicked.connect(self._trigger_recording_wizard)
        l.addWidget(rec)
        self.stack.addWidget(p)

    def _matrix_add_row(self, name, action, checked, locked):
        r = self.matrix_table.rowCount(); self.matrix_table.insertRow(r)
        self.matrix_table.setItem(r,0,QTableWidgetItem(name)); self.matrix_table.setItem(r,1,QTableWidgetItem(action))
        cw = QWidget(); cwl = QHBoxLayout(cw); cwl.setContentsMargins(0,0,0,0); cwl.setAlignment(Qt.AlignCenter)
        st = SlateToggle(); st.setChecked(checked); cwl.addWidget(st); self.matrix_table.setCellWidget(r,2,cw)
        bw = QWidget(); bl = QHBoxLayout(bw); bl.setContentsMargins(0,0,0,0); bl.setAlignment(Qt.AlignCenter)
        if locked:
            lbl = QLabel("Locked",self); lbl.setStyleSheet("color:rgba(255,255,255,70);font-size:10px;"); bl.addWidget(lbl)
        else:
            db = QPushButton("Delete",self)
            db.setStyleSheet("background:rgba(255,0,128,15);border:1px solid rgba(255,0,128,30);border-radius:4px;color:#FF0080;padding:2px 8px;font-size:10px;")
            db.clicked.connect(lambda: self.matrix_table.removeRow(r))
            bl.addWidget(db)
        self.matrix_table.setCellWidget(r,3,bw); self.matrix_table.setRowHeight(r,34)

    def _build_calibration(self):
        p = QWidget(self); l = QVBoxLayout(p); l.setContentsMargins(0,0,0,0)
        l.addWidget(QLabel("Spatial Calibration", p)); l.addSpacing(8)
        cp = QWidget(p); cp.setObjectName("PageCard")
        cl = QVBoxLayout(cp); cl.setContentsMargins(20,16,20,16)
        cl.addWidget(QLabel("Comfort Zone Boundaries", cp))
        for label, attr, lo, hi, div in [("X Min","CALIB_X_MIN",10,50,100),("X Max","CALIB_X_MAX",50,95,100),("Y Min","CALIB_Y_MIN",10,50,100),("Y Max","CALIB_Y_MAX",50,95,100)]:
            r = QHBoxLayout()
            r.addWidget(QLabel(label, cp))
            sv = getattr(EngineConfig, attr, 0.5)
            s = QSlider(Qt.Horizontal, cp); s.setRange(lo,hi); s.setValue(int(sv*div))
            vl = QLabel(f"{sv:.2f}", cp); vl.setFixedWidth(36); vl.setStyleSheet("color:#00F2FE;font-size:11px;")
            s.valueChanged.connect(lambda v, a=attr, d=div, w=vl: (setattr(EngineConfig,a,v/d), w.setText(f"{v/d:.2f}")))
            r.addWidget(s,1); r.addWidget(vl)
            cl.addLayout(r)
        l.addWidget(cp, 1); self.stack.addWidget(p)

    def _build_settings(self):
        p = QWidget(self); l = QVBoxLayout(p); l.setContentsMargins(0,0,0,0)
        l.addWidget(QLabel("Engine Settings", p)); l.addSpacing(8)
        sp = QWidget(p); sp.setObjectName("PageCard")
        sl = QVBoxLayout(sp); sl.setContentsMargins(20,16,20,16)
        sl.addWidget(QLabel("Performance Parameters", sp))
        for label, attr, lo, hi, div in [("Smoothing (Alpha)","ALPHA_MIN",1,30,100),("Pinch Threshold","PINCH_THRESHOLD",2,15,100),("Scroll Sensitivity","SCROLL_SENSITIVITY",5,50,10)]:
            r = QHBoxLayout()
            r.addWidget(QLabel(label, sp))
            sv = getattr(EngineConfig, attr, 0.5)
            s = QSlider(Qt.Horizontal, sp); s.setRange(lo,hi); s.setValue(int(sv*div))
            vl = QLabel(f"{sv*div if div==1 else sv:.2f}", sp); vl.setFixedWidth(40); vl.setStyleSheet("color:#00F2FE;font-size:11px;")
            s.valueChanged.connect(lambda v, a=attr, d=div, w=vl: (setattr(EngineConfig,a,v/d), w.setText(f"{v/d:.2f}")))
            r.addWidget(s,1); r.addWidget(vl)
            sl.addLayout(r)
        sl.addStretch(); sl.addWidget(QLabel(f"AirControl 1.0 | MediaPipe | PyQt5", sp)); sl.addWidget(QLabel(f"DTW Threshold: {EngineConfig.DTW_THRESHOLD}", sp))
        l.addWidget(sp, 1); self.stack.addWidget(p)

    def _switch_page(self, idx):
        self.current_page = idx
        self.stack.setCurrentIndex(idx)
        for i, b in enumerate(self.nav_btns):
            b.setProperty("active","true" if i==idx else "false")
            b.style().unpolish(b); b.style().polish(b)

    def _trigger_recording_wizard(self):
        self.active_dialog = PremiumRecordingWizard(self)
        if self.active_dialog.exec() == QDialog.Accepted:
            n = self.active_dialog.recorded_name; s = self.active_dialog.recorded_shortcut
            t = self.active_dialog.recorded_trajectory
            self._matrix_add_row(f"Custom: {n}", f"Shortcut [{s}]", True, False)
            if self.vision_thread and hasattr(self.vision_thread,"dtw_engine"):
                self.vision_thread.dtw_engine.register_template(f"Custom_{n}", t)
            print(f"[Client] Macro: {n} -> {s} ({len(t)} frames)")
        self.active_dialog = None

    def _toggle_master(self):
        self.engine_on = not self.engine_on; EngineConfig.ENGINE_ACTIVE = self.engine_on
        st = "on" if self.engine_on else "off"
        self.master_btn.setProperty("state",st); self.master_btn.style().unpolish(self.master_btn); self.master_btn.style().polish(self.master_btn)
        self.master_btn.setText("Engine Active" if self.engine_on else "Engine Off")
        if self._ui_shell:
            self._ui_shell.set_glow_active(self.engine_on)
        if self.engine_on: self._start_engine()
        else: self._stop_engine()

    def _hide_to_tray_msg(self):
        self.hide(); self.tray.showMessage("AirControl","Running in system tray.",QSystemTrayIcon.Information,2000)
    def _raise_window(self): self.showNormal(); self.activateWindow(); self.raise_()
    def _on_tray(self, r):
        if r == QSystemTrayIcon.Trigger:
            if self.isVisible(): self.hide()
            else: self._raise_window()
    def _completely_quit(self):
        self._stop_engine(); self.tray.hide(); QApplication.quit(); sys.exit(0)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.drag_pos = e.globalPos() - self.frameGeometry().topLeft(); e.accept()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton: self.move(e.globalPos() - self.drag_pos); e.accept()


if __name__ == "__main__":
    from PyQt5.QtGui import QFont
    QApplication.setFont(QFont("Segoe UI", 10))

    app = QApplication(sys.argv); app.setQuitOnLastWindowClosed(False)
    c = AirControlPremiumApp(); c.show(); sys.exit(app.exec_())