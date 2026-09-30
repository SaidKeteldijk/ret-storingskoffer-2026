"""
display.py – Verdeelt het instructeurs- en monteursvenster over de schermen.
RET N.V. | Said Keteldijk (1045604)
"""

import os
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication

# Exacte afmeting van de Raspberry Pi Touch Display 2.
MONTEUR_BREEDTE = 1280
MONTEUR_HOOGTE  = 720

_MONTEUR_NAMEN     = ("DSI", "DPI")
_INSTRUCTEUR_NAMEN = ("HDMI",)


@dataclass
class SchermIndeling:
    instructeur: Optional[object]   # QScreen of None
    monteur:     Optional[object]   # QScreen of None
    fullscreen:  bool
    uitleg:      str


def _kies(schermen, spec):
    """Zoek een scherm op index ('1') of op naamfragment ('DSI')."""
    if not spec:
        return None
    spec = spec.strip()
    if spec.isdigit():
        i = int(spec)
        return schermen[i] if 0 <= i < len(schermen) else None
    for s in schermen:
        if spec.lower() in s.name().lower():
            return s
    return None


def _zoek_naam(schermen, fragmenten, negeer=None):
    for frag in fragmenten:
        for s in schermen:
            if s is not negeer and frag.lower() in s.name().lower():
                return s
    return None


def _kleinste(schermen, negeer=None):
    kandidaten = [s for s in schermen if s is not negeer]
    if not kandidaten:
        return None
    return min(kandidaten,
               key=lambda s: s.geometry().width() * s.geometry().height())


def bepaal_indeling(app) -> SchermIndeling:
    """Kies welk scherm welk venster krijgt."""
    schermen = app.screens()
    modus    = os.environ.get("STORINGSKOFFER_LAYOUT", "auto").lower()

    if modus == "dev" or (modus == "auto" and len(schermen) < 2):
        reden = ("handmatig ingesteld" if modus == "dev"
                 else f"{len(schermen)} scherm gevonden")
        return SchermIndeling(
            None, None, False,
            f"Ontwikkelmodus – beide vensters op één scherm ({reden}).")

    # Een expliciete keuze via omgevingsvariabelen wint altijd.
    monteur     = _kies(schermen, os.environ.get("STORINGSKOFFER_MONTEUR"))
    instructeur = _kies(schermen, os.environ.get("STORINGSKOFFER_INSTRUCTEUR"))

    if monteur is None:
        monteur = _zoek_naam(schermen, _MONTEUR_NAMEN, negeer=instructeur)
    if instructeur is None:
        instructeur = _zoek_naam(schermen, _INSTRUCTEUR_NAMEN, negeer=monteur)

    # Onder XWayland heten schermen soms XWAYLAND0/1 in plaats van DSI/HDMI.
    # Val dan terug op afmeting: de Touch Display 2 is het kleinste scherm.
    if monteur is None:
        monteur = _kleinste(schermen, negeer=instructeur)
    if instructeur is None:
        instructeur = next((s for s in schermen if s is not monteur), None)

    if monteur is None or instructeur is None or monteur is instructeur:
        return SchermIndeling(
            None, None, False,
            "Kon twee schermen niet onderscheiden – terug naar ontwikkelmodus.")

    return SchermIndeling(
        instructeur, monteur, True,
        f"Instructeur op '{instructeur.name()}', monteur op '{monteur.name()}'.")


# Controles van toon_op: samen maximaal anderhalve seconde.
_POGINGEN  = 6
_WACHTTIJD = 250   # ms


def toon_op(venster, scherm):
    """
    Zet een venster schermvullend op een specifiek scherm en blijf dat
    controleren tot het er echt staat.

    Een compositor mag een plaatsingsverzoek negeren of pas later uitvoeren.
    Dat gebeurt bijvoorbeeld als de schermindeling een gat heeft, of nadat er
    een andere monitor is aangesloten: een nieuw venster begint op (0, 0), en
    als daar geen scherm staat kiest de compositor er zelf een. Daarom wordt
    na het plaatsen gecontroleerd waar het venster terecht is gekomen, en
    wordt het zo nodig opnieuw geplaatst.
    """
    venster.setGeometry(scherm.geometry())
    venster.show()                       # nu pas bestaat het native venster
    _plaats(venster, scherm)
    _controleer(venster, scherm, poging=1)


def _plaats(venster, scherm):
    geo = scherm.geometry()

    # Een compositor verplaatst geen venster dat al schermvullend is.
    if venster.isFullScreen():
        venster.showNormal()

    handle = venster.windowHandle()
    if handle is not None:
        handle.setScreen(scherm)

    venster.setGeometry(geo)
    venster.move(geo.x(), geo.y())
    QApplication.processEvents()         # laat de compositor de verplaatsing verwerken

    venster.showFullScreen()
    QApplication.processEvents()


def _staat_op(venster, scherm) -> bool:
    """
    Staat het venster echt op dit scherm? Twee onafhankelijke controles: het
    midden van het venster moet binnen het scherm liggen, en Qt moet het
    venster zelf ook aan dit scherm toekennen.
    """
    midden_ok = scherm.geometry().contains(venster.frameGeometry().center())
    return midden_ok and huidig_scherm(venster) == scherm.name()


def _controleer(venster, scherm, poging):
    def stap():
        if not venster.isVisible():      # app wordt al afgesloten
            return
        naam = venster.windowTitle()
        if _staat_op(venster, scherm):
            extra = f" (na {poging} pogingen)" if poging > 1 else ""
            print(f"[SCHERM] '{naam}' staat op {scherm.name()}{extra}")
            return
        if poging >= _POGINGEN:
            print(f"[SCHERM] LET OP: '{naam}' staat op {huidig_scherm(venster)} "
                  f"in plaats van {scherm.name()}. Controleer de schermindeling "
                  "via Voorkeuren > Schermconfiguratie.")
            return
        _plaats(venster, scherm)
        _controleer(venster, scherm, poging + 1)

    QTimer.singleShot(_WACHTTIJD, stap)


def huidig_scherm(venster) -> str:
    """Naam van het scherm waar het venster daadwerkelijk op staat."""
    handle = venster.windowHandle()
    if handle is not None and handle.screen() is not None:
        return handle.screen().name()
    return "(onbekend)"
