"""
main.py - Opstartpunt Storingskoffer Dashboard.
RET N.V. | Said Keteldijk (1045604)

Windows: python main.py
Raspberry Pi: python3 main.py

Twee vensters:
  Instructeur (HDMI0)      – volledig dashboard: ontwerpen, storing, examen
  Monteur (Touch Display 2) – statische schakeling + examentijd

Op één scherm (laptop) komen beide vensters naast elkaar; zie display.py
voor de omgevingsvariabelen waarmee je die indeling kunt forceren.

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
from display import MONTEUR_BREEDTE, MONTEUR_HOOGTE, bepaal_indeling, toon_op
from gpio_manager import gpio_init_startup
from monteur import MonteurWindow


if __name__ == "__main__":
    gpio_init_startup()  # alle pins -> OUTPUT LOW
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    indeling = bepaal_indeling(app)
    print(f"[SCHERM] {indeling.uitleg}")

    instructeur = MainWindow()
    monteur     = MonteurWindow()
    instructeur.monteur = monteur
    monteur.wachtstand()

    if indeling.fullscreen:
        # toon_op controleert zelf waar de vensters terechtkomen, plaatst ze
        # zo nodig opnieuw en meldt het resultaat.
        toon_op(monteur, indeling.monteur)
        toon_op(instructeur, indeling.instructeur)
    else:
        # Ontwikkelmodus: het monteursvenster krijgt exact de afmeting van de
        # Touch Display 2, zodat het inpassen nu al realistisch is.
        beschikbaar = app.primaryScreen().availableGeometry()
        instructeur.showMaximized()
        monteur.setGeometry(
            max(beschikbaar.left(), beschikbaar.right() - MONTEUR_BREEDTE - 20),
            max(beschikbaar.top(),  beschikbaar.bottom() - MONTEUR_HOOGTE - 20),
            MONTEUR_BREEDTE, MONTEUR_HOOGTE)
        monteur.show()
        monteur.raise_()

    sys.exit(app.exec_())
