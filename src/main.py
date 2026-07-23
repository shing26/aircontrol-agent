# src/main.py
import sys

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

from src.config import EngineConfig
from src.ui.siri_window import SiriGlowShell
from client_app import AirControlPremiumApp


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    EngineConfig.load_json()

    screen = app.primaryScreen().geometry()
    sw, sh = screen.width(), screen.height()
    print(f"[Engine] Screen: {sw}x{sh}")

    # Fullscreen glow overlay
    ui_shell = SiriGlowShell(sw, sh)
    ui_shell.show()

    # Premium control center (manages its own engine threads)
    dashboard = AirControlPremiumApp(ui_shell=ui_shell)
    dashboard.move((sw - dashboard.width()) // 2, (sh - dashboard.height()) // 2)
    dashboard.show()

    sys.exit(app.exec_())
