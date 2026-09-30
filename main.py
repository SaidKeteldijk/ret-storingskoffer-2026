"""
main.py - Opstartpunt Storingskoffer Dashboard.
RET N.V. | Said Keteldijk (1045604)
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
from display import MONTEUR_BREEDTE, MONTEUR_HOOGTE, bepaal_indeling, toon_op
from gpio_manager import gpio_init_startup
from monteur import MonteurWindow


if __name__ == "__main__":
    gpio_init_startup()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    indeling = bepaal_indeling(app)
    print(f"[SCHERM] {indeling.uitleg}")

    instructeur = MainWindow()
    monteur     = MonteurWindow()
    instructeur.monteur = monteur
    monteur.wachtstand()

    if indeling.fullscreen:
        toon_op(monteur, indeling.monteur)
        toon_op(instructeur, indeling.instructeur)
    else:
        # Ontwikkelmodus: monteursvenster op de echte afmeting van de Touch Display 2.
        beschikbaar = app.primaryScreen().availableGeometry()
        instructeur.showMaximized()
        monteur.setGeometry(
            max(beschikbaar.left(), beschikbaar.right() - MONTEUR_BREEDTE - 20),
            max(beschikbaar.top(),  beschikbaar.bottom() - MONTEUR_HOOGTE - 20),
            MONTEUR_BREEDTE, MONTEUR_HOOGTE)
        monteur.show()
        monteur.raise_()

    sys.exit(app.exec_())
