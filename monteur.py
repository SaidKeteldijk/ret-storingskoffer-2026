"""
monteur.py – Examenscherm voor de monteur (Raspberry Pi Touch Display 2).
RET N.V. | Said Keteldijk (1045604)
"""

import copy

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtGui  import QPainter, QPen, QFont, QColor, QBrush
from PyQt5.QtCore import Qt

from canvas    import CircuitCanvas
from constants import (GRID, C_BG, C_SIDE, C_BORDER, C_MUTED,
                       C_GREEN, C_YELLOW, C_RED)
from display   import MONTEUR_BREEDTE, MONTEUR_HOOGTE
from models    import comp_connections


class MonteurCanvas(CircuitCanvas):
    """
    Statische weergave van de schakeling, ingepast op het scherm.

    Erft van CircuitCanvas zodat alle tekenroutines hergebruikt worden, maar
    blijft altijd in "view"-modus. Daardoor vervallen de stroomhighlights
    ([canvas.py] _draw_wires) en de storingsmarkering vanzelf.
    """

    # Een kleine schakeling mag beeldvullend, maar niet grotesk uitvergroot.
    MAX_ZOOM   = 2.0
    BALK_HOOGTE = 64

    def __init__(self):
        super().__init__(gpio=False)
        self.mode     = "view"
        self.toestand = "wacht"          # wacht | examen | einde
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setMinimumSize(320, 240)    # overschrijft de 1200x800 van de editor

    # ── Statische tekening: alle interactie wordt genegeerd ──

    def mousePressEvent(self, e):       pass
    def mouseMoveEvent(self, e):        pass
    def mouseReleaseEvent(self, e):     pass
    def mouseDoubleClickEvent(self, e): pass
    def wheelEvent(self, e):            pass
    def keyPressEvent(self, e):         e.ignore()

    def _draw_defect_overlay(self, p, cx, cy):
        """De storing mag nooit op dit scherm verschijnen."""
        pass

    # ── Circuit overnemen ─────────────────────

    def toon_circuit(self, components, wires):
        """
        Neem een eigen kopie over. Twee redenen: een losse kopie zorgt dat
        latere wijzigingen van de instructeur niet doorlekken, en de
        defect-vlag wordt gewist zodat de storing hier niet eens in het
        geheugen van dit venster staat.
        """
        self.components = copy.deepcopy(list(components))
        self.wires      = copy.deepcopy(list(wires))
        for comp in self.components:
            comp.defect = False
        self.update()

    # ── Inpassen ──────────────────────────────

    def _grens_px(self):
        """Omhullende rechthoek van de schakeling in pixels, of None."""
        cols, rows = [], []
        for comp in self.components:
            cols.append(comp.col); rows.append(comp.row)
            for c, r in comp_connections(comp):
                cols.append(c); rows.append(r)
        for w in self.wires:
            cols += [w.c1, w.c2]; rows += [w.r1, w.r2]
        if not cols:
            return None

        x1, y1 = self._px(min(cols), min(rows))
        x2, y2 = self._px(max(cols), max(rows))
        marge  = int(GRID * 1.5)          # ruimte voor symbolen en labels
        return x1 - marge, y1 - marge, x2 + marge, y2 + marge

    # ── Tekenen ───────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(C_BG))

        if self.toestand == "einde":
            self._teken_midden(p, "EINDE EXAMEN",
                               "De examentijd is verstreken.", C_RED)
            return
        if self.toestand == "wacht":
            self._teken_midden(p, "STORINGSKOFFER",
                               "Wachten op de instructeur…", C_MUTED)
            return

        grens = self._grens_px()
        if grens:
            x1, y1, x2, y2 = grens
            bw = max(1, x2 - x1)
            bh = max(1, y2 - y1)
            beschikbaar_h = max(1, self.height() - self.BALK_HOOGTE)
            schaal = min(self.width() / bw, beschikbaar_h / bh, self.MAX_ZOOM)

            p.save()
            p.translate((self.width() - bw * schaal) / 2,
                        self.BALK_HOOGTE + (beschikbaar_h - bh * schaal) / 2)
            p.scale(schaal, schaal)
            p.translate(-x1, -y1)
            # Geen raster: dit is een tekening, geen editor.
            self._draw_wires(p)
            self._draw_comps(p)
            p.restore()

        self._teken_balk(p)

    def _teken_balk(self, p):
        """Bovenbalk met de resterende examentijd."""
        h = self.BALK_HOOGTE
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(C_SIDE)))
        p.drawRect(0, 0, self.width(), h)
        p.setPen(QPen(QColor(C_BORDER), 1))
        p.drawLine(0, h, self.width(), h)

        p.setFont(QFont("Courier New", 13, QFont.Bold))
        p.setPen(QColor(C_MUTED))
        p.drawText(18, 41, "EXAMEN")

        s   = max(0, self.exam_seconds_left)
        t   = self.exam_total_seconds if self.exam_total_seconds > 0 else 1
        pct = s / t
        kleur = C_GREEN if pct > 0.5 else (C_YELLOW if pct > 0.2 else C_RED)

        txt = f"{s // 60:02d}:{s % 60:02d}"
        p.setFont(QFont("Courier New", 30, QFont.Bold))
        p.setPen(QColor(kleur))
        breedte = p.fontMetrics().horizontalAdvance(txt)
        p.drawText(self.width() - breedte - 18, 46, txt)

    def _teken_midden(self, p, titel, onder, kleur):
        p.setFont(QFont("Courier New", 38, QFont.Bold))
        p.setPen(QColor(kleur))
        breedte = p.fontMetrics().horizontalAdvance(titel)
        p.drawText((self.width() - breedte) // 2, self.height() // 2, titel)

        p.setFont(QFont("Courier New", 15))
        p.setPen(QColor(C_MUTED))
        breedte = p.fontMetrics().horizontalAdvance(onder)
        p.drawText((self.width() - breedte) // 2, self.height() // 2 + 46, onder)


class MonteurWindow(QMainWindow):
    """Kaal venster voor de Touch Display 2: alleen schakeling en tijd."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Storingskoffer – Examen")
        self.setStyleSheet(f"background-color:{C_BG};")
        self.canvas = MonteurCanvas()
        self.setCentralWidget(self.canvas)
        self.resize(MONTEUR_BREEDTE, MONTEUR_HOOGTE)

    # ── Aangestuurd vanuit MainWindow ─────────

    def wachtstand(self):
        self.canvas.toestand   = "wacht"
        self.canvas.components = []
        self.canvas.wires      = []
        self.canvas.update()

    def start_examen(self, components, wires, seconden: int):
        self.canvas.toon_circuit(components, wires)
        self.canvas.exam_total_seconds = seconden
        self.canvas.exam_seconds_left  = seconden
        self.canvas.toestand           = "examen"
        self.canvas.update()

    def update_tijd(self, seconden: int):
        self.canvas.exam_seconds_left = max(0, seconden)
        self.canvas.update()

    def einde_examen(self):
        self.canvas.toestand = "einde"
        self.canvas.update()

    # ── Ontsnappingsroute ─────────────────────

    def keyPressEvent(self, e):
        """Escape verlaat fullscreen – nodig als er op de Pi iets vastloopt."""
        if e.key() == Qt.Key_Escape and self.isFullScreen():
            self.showNormal()
        elif e.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(e)
