"""
schermtest.py – Controleert de schermopstelling vóór het starten van de app.
RET N.V. | Said Keteldijk (1045604)

Gebruik op de Raspberry Pi:
    source venv-rpi/bin/activate
    python3 schermtest.py

Toont welke schermen Qt ziet en hoe display.py de vensters zou verdelen.
"""

import os
import sys

if "QT_QPA_PLATFORM" not in os.environ and sys.platform.startswith("linux"):
    os.environ["QT_QPA_PLATFORM"] = "xcb" if os.environ.get("DISPLAY") else "offscreen"

from PyQt5.QtWidgets import QApplication

from display import MONTEUR_BREEDTE, MONTEUR_HOOGTE, bepaal_indeling


def _omgeving():
    print("-- Omgeving -----------------------------------------")
    for naam in ("XDG_SESSION_TYPE", "DISPLAY", "WAYLAND_DISPLAY",
                 "QT_QPA_PLATFORM", "STORINGSKOFFER_LAYOUT",
                 "STORINGSKOFFER_MONTEUR", "STORINGSKOFFER_INSTRUCTEUR"):
        print(f"  {naam:<28} = {os.environ.get(naam, '(niet gezet)')}")

    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        print("\n  LET OP: Qt draait offscreen. Er verschijnt niets op de schermen.")
        print("     Start de app vanaf het bureaublad, niet via SSH zonder DISPLAY.")


def _schermen(app):
    print("\n-- Schermen die Qt ziet -----------------------------")
    schermen = app.screens()
    if not schermen:
        print("  Geen schermen gevonden.")
        return

    primair = app.primaryScreen()
    for i, s in enumerate(schermen):
        g = s.geometry()
        merk = "  (primair)" if s is primair else ""
        print(f"  [{i}] {s.name():<16} {g.width():>5} x {g.height():<5} "
              f"op ({g.x()}, {g.y()}){merk}")

    if len(schermen) < 2:
        print("\n  LET OP: Maar één scherm. Controleer of beide kabels aangesloten zijn")
        print("     en of de schermen uitgebreid staan in plaats van gespiegeld.")
        return

    posities = {(s.geometry().x(), s.geometry().y()) for s in schermen}
    if len(posities) < len(schermen):
        print("\n  LET OP: Schermen staan op dezelfde positie: waarschijnlijk gespiegeld.")
        print("     Zet ze naast elkaar via Beeldscherminstellingen.")


def _verdeling(app):
    print("\n-- Verdeling volgens display.py ---------------------")
    ind = bepaal_indeling(app)
    print(f"  {ind.uitleg}")

    if not ind.fullscreen:
        print("\n  De app start in ontwikkelmodus: beide vensters op één scherm.")
        print("  Forceer de tweeschermopstelling met STORINGSKOFFER_LAYOUT=pi")
        return

    mg = ind.monteur.geometry()
    print(f"  Monteur     : {ind.monteur.name()}  "
          f"({mg.width()} x {mg.height()})")
    print(f"  Instructeur : {ind.instructeur.name()}")

    if (mg.width(), mg.height()) != (MONTEUR_BREEDTE, MONTEUR_HOOGTE):
        print(f"\n  Let op: het monteursscherm is niet {MONTEUR_BREEDTE}x{MONTEUR_HOOGTE}.")
        print("  Controleer of de Touch Display 2 als monteursscherm gekozen is.")

    print("\n  Klopt dit niet? Forceer met bijvoorbeeld:")
    print(f"    STORINGSKOFFER_MONTEUR={ind.instructeur.name()} python3 main.py")


if __name__ == "__main__":
    _omgeving()
    app = QApplication(sys.argv)
    _schermen(app)
    _verdeling(app)
    print()
