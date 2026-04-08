"""
main.py - Opstartpunt Storingskoffer Dashboard.
RET N.V. | Said Keteldijk (1045604)

Windows: python main.py
Raspberry Pi: python3 main.py

Installatie:
  pip install PyQt5
  pip install RPi.GPIO   (alleen op Raspberry Pi)
"""

import os
import sys

# Qt/GLib startup flags - these must be set before importing PyQt5.
os.environ.setdefault("QT_ACCESSIBILITY", "0")
os.environ.setdefault("G_SLICE", "always-malloc")
os.environ.setdefault("NO_AT_BRIDGE", "1")

# Only force the platform plugin when the OS actually needs it.
if "QT_QPA_PLATFORM" not in os.environ:
    if sys.platform.startswith("linux"):
        os.environ["QT_QPA_PLATFORM"] = "offscreen" if not os.environ.get("DISPLAY") else "xcb"
    elif sys.platform == "win32":
        os.environ["QT_QPA_PLATFORM"] = "windows"

from PyQt5.QtWidgets import QApplication

from canvas import MainWindow
from gpio_manager import gpio_init_startup


if __name__ == "__main__":
    gpio_init_startup()  # alle pins -> OUTPUT LOW
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    venster = MainWindow()
    venster.showMaximized()
    sys.exit(app.exec_())
