"""
display.py – Bepaalt op welk scherm het instructeurs- en monteursvenster komen.
RET N.V. | Said Keteldijk (1045604)

Twee schermen (Raspberry Pi):
    Instructeur -> HDMI0              volledig dashboard
    Monteur     -> DSI / Touch 2      statische schakeling + examentijd

Eén scherm (laptop tijdens ontwikkeling):
    Beide vensters op hetzelfde scherm; het monteursvenster krijgt exact
    1280x720 zodat je meteen tegen de echte afmeting van de Touch Display 2
    ontwikkelt in plaats van het inpasprobleem pas op de Pi te ontdekken.

Omgevingsvariabelen – noodrem als de automatische detectie verkeerd kiest:
    STORINGSKOFFER_LAYOUT       auto (standaard) | dev | pi
    STORINGSKOFFER_MONTEUR      schermnaam of index, bv. "DSI-1" of "1"
    STORINGSKOFFER_INSTRUCTEUR  schermnaam of index
"""

import os
from dataclasses import dataclass
from typing import Optional

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


def toon_op(venster, scherm):
    """
    Zet een venster fullscreen op een specifiek scherm.
    De volgorde is essentieel: showFullScreen() kiest het scherm waar het
    venster op dat moment staat, dus eerst verplaatsen, dan pas fullscreen.
    """
    venster.setGeometry(scherm.geometry())
    venster.showFullScreen()
