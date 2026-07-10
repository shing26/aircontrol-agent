# src/main.py
import sys
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication
from src.config import EngineConfig
from src.control.os_mapper import InputMapper
from src.ui.siri_window import SiriGlowShell
from src.ui.main_dashboard import AirControlMainDashboard
from src.ui.settings_window import SettingsDashboard
from src.vision.pipeline import FramePipeline, VisionAgentThread


class CameraProducer(QThread):
    frame_signal = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.running = True

    def run(self):
        print("[Thread] Camera producer started.")
        cap = cv2.VideoCapture(EngineConfig.CAMERA_INDEX)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, EngineConfig.FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, EngineConfig.FRAME_HEIGHT)
        while self.running:
            ret, frame = cap.read()
            if not ret:
                break
            if self.running:
                self.frame_signal.emit(frame)
        cap.release()
        print("[Thread] Camera producer exited.")

    def stop(self):
        self.running = False


class AirControlEngine:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        EngineConfig.load_json()

        screen = self.app.primaryScreen()
        geo = screen.geometry()
        sw, sh = geo.width(), geo.height()
        print(f"[Engine] Primary screen: {sw}x{sh}")

        # Permanent core components
        self.pipeline = FramePipeline()
        self.ui_shell = SiriGlowShell(sw, sh)
        self.mapper = InputMapper(sw, sh)

        # Main dashboard
        self.dashboard = AirControlMainDashboard(
            self.ui_shell, on_master_toggle=self._handle_master_switch
        )
        self.dashboard.on_macro_recorded_callback = self._on_ui_macro_registered_success

        # Dynamic thread lifecycle pointers
        self.camera_thread = None
        self.vision_thread = None

        # Auto-start on boot
        self._start_backend_agents()

        # Show UI
        self.ui_shell.show()
        self.dashboard.move(
            (sw - self.dashboard.width()) // 2,
            (sh - self.dashboard.height()) // 2
        )
        self.dashboard.show()

    def _start_backend_agents(self):
        """Assemble and launch fresh backend threads."""
        print("[Engine] Starting backend agents...")
        self.camera_thread = CameraProducer()
        self.vision_thread = VisionAgentThread(self.pipeline)

        # Wire cross-thread signal topology
        self.camera_thread.frame_signal.connect(self.pipeline.push)
        self.vision_thread.gesture_signal.connect(
            self.mapper.on_gesture_received
        )
        self.vision_thread.ui_signal.connect(
            self.ui_shell.update_ui_state
        )
        self.vision_thread.ui_signal.connect(
            self.dashboard.update_status
        )
        self.vision_thread.gesture_signal.connect(
            self._relay_coordinates_to_wizard
        )

        # Launch
        self.vision_thread.start()
        self.camera_thread.start()
        self.ui_shell.update_ui_state("RELEASE", 0.15)

    def _stop_backend_agents(self):
        """Kill all backend threads with poison pill, clean up resources."""
        print("[Engine] Stopping backend agents...")

        # 1. Disconnect signals to prevent stale emissions
        if self.camera_thread:
            try:
                self.camera_thread.frame_signal.disconnect()
            except TypeError:
                pass
        if self.vision_thread:
            try:
                self.vision_thread.gesture_signal.disconnect()
                self.vision_thread.ui_signal.disconnect()
            except TypeError:
                pass

        # 2. Send stop signals
        if self.camera_thread:
            self.camera_thread.stop()
        if self.vision_thread:
            self.vision_thread.stop()

        # 3. Poison pill: unblock the consumer queue
        self.pipeline.push(None)

        # 4. Wait for clean thread exit
        if self.camera_thread:
            self.camera_thread.wait()
        if self.vision_thread:
            self.vision_thread.wait()

        # 5. Destroy references
        self.camera_thread = None
        self.vision_thread = None

        self.ui_shell.update_ui_state("RELEASE", 0.0)
        print("[Engine] Backend agents fully stopped.")

    def _handle_master_switch(self, active):
        """Central router for the dashboard master toggle."""
        EngineConfig.ENGINE_ACTIVE = active
        if active:
            self._start_backend_agents()
            self.ui_shell.show()
            print("[Engine] Master ON")
        else:
            self._stop_backend_agents()
            self.ui_shell.hide()
            print("[Engine] Master OFF")

    def _relay_coordinates_to_wizard(self, state, nx, ny):
        if self.dashboard.active_dialog and self.dashboard.active_dialog.is_recording:
            if nx > 0.001:
                self.dashboard.active_dialog.collect_coordinate(nx, ny)

    def _on_ui_macro_registered_success(self, macro_name, shortcut_keys, trajectory_data):
        print(f"[Engine] Recording complete: {macro_name} -> {shortcut_keys}")
        if self.vision_thread and hasattr(self.vision_thread, "dtw_engine"):
            self.vision_thread.dtw_engine.register_template(
                f"Custom_{macro_name}", trajectory_data
            )

    def run(self):
        print("[Engine] AirControl 1.0 is now fully operational.")
        sys.exit(self.app.exec_())


if __name__ == "__main__":
    engine = AirControlEngine()
    engine.run()