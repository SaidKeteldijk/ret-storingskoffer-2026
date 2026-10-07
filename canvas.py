"""
canvas.py – CircuitCanvas, GPIOConfigDialog, FilePaneel,
            GPIOMonitorPanel en MainWindow.
RET N.V. | Said Keteldijk (1045604)
"""

import json
import math
from pathlib import Path
from dataclasses import asdict
from typing import List, Optional, Tuple, Dict, Set

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QLabel, QFrame, QFileDialog, QInputDialog,
    QMessageBox, QStackedWidget, QScrollArea, QDialog,
    QTableWidget, QTableWidgetItem, QComboBox, QSpinBox,
    QDialogButtonBox, QHeaderView, QCheckBox,
)
from PyQt5.QtGui  import QPainter, QPen, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QPoint, QTimer

from constants import *
from models    import (
    Component, Wire, can_use_contact_start, comp_connections,
    renumber_auto_labels, renumber_contacts,
)
from draw      import (EC_DRAW_BASE, _ec_schakelaar, _ec_schakelaar2p, _ec_spdt, _ec_rspdt, _ec_netlabel,
                       _ec_relaisspoel, _ec_relaiscontact, _ec_motor, _ec_lamp,
                       _ec_voeding, _ec_massa)
from simulator import CircuitSimulator
from gpio_manager import GPIOManager, ON_RPI, GPIO
from koffer_io import KofferIO, SPI_AANWEZIG, is_knop, is_lamp, kanaal_index

#  GPIO CONFIGURATIE DIALOOG
# ═══════════════════════════════════════════════
class GPIOConfigDialog(QDialog):
    """
    Dialoog voor het koppelen van componenten aan de knoppen- en lampenprint.

    Schakelaars en relaiscontacten worden aan een knop S1..S8 gekoppeld,
    lampen, motoren en relaisspoelen aan een lamp Q1..Q8. Het componenttype
    bepaalt zelf of het een ingang of een uitgang is.
    """

    KANAAL_GEEN = "— geen —"

    def __init__(self, components: List[Component], parent=None):
        super().__init__(parent)
        self.setWindowTitle("GPIO Koppeling configureren")
        self.setMinimumWidth(520)
        self.setStyleSheet(f"""
            QDialog, QWidget {{ background:{C_BG}; color:{C_TEXT}; }}
            QTableWidget {{ gridline-color:{C_BORDER}; border:1px solid {C_BORDER};
                            font-family:'Courier New'; font-size:11px; }}
            QHeaderView::section {{ background:{C_SIDE}; color:{C_MUTED};
                                    font-family:'Courier New'; font-size:10px;
                                    padding:4px; border:none;
                                    border-bottom:1px solid {C_BORDER}; }}
            QComboBox {{ background:{C_SIDE}; color:{C_TEXT};
                         border:1px solid {C_BORDER}; border-radius:3px;
                         padding:2px 6px; font-family:'Courier New'; }}
            QComboBox QAbstractItemView {{ background:{C_SIDE}; color:{C_TEXT}; }}
            QPushButton {{ background:{C_BG}; color:{C_TEXT};
                           border:1px solid {C_BORDER}; border-radius:4px;
                           padding:6px 14px; font-family:'Courier New'; }}
            QPushButton:hover {{ background:{C_BORDER}; }}
        """)

        # Filter: alleen koppelbare componenten
        self.comp_indices = [
            i for i, c in enumerate(components)
            if c.type in (GPIO_IN_TYPES | GPIO_OUT_TYPES)
        ]
        self.components = components

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 12)

        # Info
        info = QLabel(
            f"{'✓  RPi.GPIO hardware actief' if ON_RPI else '⚠  MockGPIO actief (geen hardware)'}\n"
            "Koppel hieronder elk component aan een BCM GPIO-pinnummer."
        )
        info.setStyleSheet(
            f"color:{'#a6e3a1' if ON_RPI else C_YELLOW}; "
            f"font-family:'Courier New'; font-size:10px;")
        layout.addWidget(info)

        # Tabel
        self.table = QTableWidget(len(self.comp_indices), 4)
        self.table.setHorizontalHeaderLabels(
            ["Component", "Type", "Soort", "Kanaal op de koffer"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self._kanaal_combos: Dict[int, QComboBox] = {}

        for row, ci in enumerate(self.comp_indices):
            comp = components[ci]

            # Label
            lbl = QTableWidgetItem(comp.label or comp.type)
            lbl.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, lbl)

            # Type
            tp = QTableWidgetItem(comp.type)
            tp.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, tp)

            ingang = comp.type in GPIO_IN_TYPES
            soort = QTableWidgetItem("Knop" if ingang else "Lamp")
            soort.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, soort)

            opties = KOFFER_KNOPPEN if ingang else KOFFER_LAMPEN
            kanaal_cb = QComboBox()
            kanaal_cb.addItems([self.KANAAL_GEEN] + opties)
            if comp.kanaal in opties:
                kanaal_cb.setCurrentText(comp.kanaal)
            else:
                kanaal_cb.setCurrentIndex(0)
            self.table.setCellWidget(row, 3, kanaal_cb)
            self._kanaal_combos[ci] = kanaal_cb

        layout.addWidget(self.table)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btns.setStyleSheet(
            f"QPushButton {{ background:{C_BG}; color:{C_TEXT}; "
            f"border:1px solid {C_BORDER}; border-radius:4px; padding:6px 18px; }}"
            f"QPushButton:hover {{ background:{C_BORDER}; }}")
        layout.addWidget(btns)

    def accept(self):
        """Weiger het sluiten zolang twee componenten hetzelfde kanaal delen."""
        gebruikt = {}
        for ci in self.comp_indices:
            kanaal = self._kanaal_combos[ci].currentText()
            if kanaal == self.KANAAL_GEEN:
                continue
            naam = self.components[ci].label or self.components[ci].type
            if kanaal in gebruikt:
                QMessageBox.warning(
                    self, "Koppeling koffer",
                    f"Kanaal {kanaal} is aan twee componenten gekoppeld: "
                    f"{gebruikt[kanaal]} en {naam}. Elk kanaal hoort bij "
                    "één component. Kies voor één van beide een ander kanaal.")
                return
            gebruikt[kanaal] = naam
        super().accept()

    def apply(self):
        """Schrijf de instellingen terug naar de componentenlijst."""
        for ci in self.comp_indices:
            comp = self.components[ci]
            kanaal = self._kanaal_combos[ci].currentText()
            comp.kanaal = "" if kanaal == self.KANAAL_GEEN else kanaal
            comp.gpio_dir = "IN" if comp.type in GPIO_IN_TYPES else "OUT"
            comp.gpio_pin = -1





# ═══════════════════════════════════════════════
#  STORINGEN DIALOOG
# ═══════════════════════════════════════════════
class FaultConfigDialog(QDialog):
    """
    Dialoog voor het instellen van defecte componenten.

    Toont een tabel met alle relevante componenten.
    Per rij: label | type | omschrijving storing | aan/uit checkbox

    Defectgedrag per type:
      Schakelaar / 2P-schakelaar : altijd open (nooit sluit)
      SPDT-schakelaar            : vast in standaardpositie B
      Relaisspoel                : koppeling spoel→contact verbroken
      Relaiscontact              : contact sluit nooit
      Relaiswisselcontact        : koppeling verbroken, vast op B
      Motor / Lamp               : visueel gemarkeerd als defect
    """

    _FAULT_TYPES = {
        TOOL_SWITCH:    "Altijd open (nooit sluit)",
        TOOL_SW2P_NO:   "Altijd open (nooit sluit)",
        TOOL_SW2P_NC:   "Altijd open (nooit sluit)",
        TOOL_SPDT:      "Vast op positie B",
        TOOL_RCOIL:     "Koppeling spoel↔contact verbroken",
        TOOL_RCONT:     "Contact sluit nooit",
        TOOL_RSPDT:     "Koppeling verbroken, vast op B",
        TOOL_MOTOR:     "Visueel defect (gemarkeerd)",
        TOOL_LAMP:      "Visueel defect (gemarkeerd)",
    }

    def __init__(self, components: List[Component], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Storingen instellen")
        self.setMinimumWidth(600)
        self.setStyleSheet(f"""
            QDialog, QWidget {{ background:{C_BG}; color:{C_TEXT}; }}
            QTableWidget {{ gridline-color:{C_BORDER}; border:1px solid {C_BORDER};
                            font-family:'Courier New'; font-size:11px; }}
            QHeaderView::section {{ background:{C_SIDE}; color:{C_MUTED};
                                    font-family:'Courier New'; font-size:10px;
                                    padding:4px; border:none;
                                    border-bottom:1px solid {C_BORDER}; }}
            QPushButton {{ background:{C_BG}; color:{C_TEXT};
                           border:1px solid {C_BORDER}; border-radius:4px;
                           padding:6px 14px; font-family:'Courier New'; }}
            QPushButton:hover {{ background:{C_BORDER}; }}
        """)

        # Alleen componenten die een zinvolle storing kunnen hebben
        self.comp_indices = [
            i for i, c in enumerate(components)
            if c.type in self._FAULT_TYPES
        ]
        self.components = components

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 12)

        info = QLabel(
            "Vink hieronder componenten aan die tijdens de simulatie defect zijn.\n"
            "Defecte componenten worden in de editor en simulatie gemarkeerd met een rood kruis."
        )
        info.setStyleSheet(
            f"color:{C_YELLOW}; font-family:'Courier New'; font-size:10px;")
        layout.addWidget(info)

        self.table = QTableWidget(len(self.comp_indices), 4)
        self.table.setHorizontalHeaderLabels(
            ["Label", "Type", "Storingsgedrag", "Defect"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)

        self._checkboxes: Dict[int, QCheckBox] = {}

        for row, ci in enumerate(self.comp_indices):
            comp = components[ci]

            lbl = QTableWidgetItem(comp.label or comp.type)
            lbl.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, lbl)

            tp = QTableWidgetItem(TOOL_LABELS.get(comp.type, comp.type))
            tp.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, tp)

            desc = QTableWidgetItem(self._FAULT_TYPES.get(comp.type, "—"))
            desc.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, desc)

            cb = QCheckBox()
            cb.setChecked(getattr(comp, 'defect', False))
            cb.setStyleSheet("margin-left:auto; margin-right:auto;")
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.addWidget(cb)
            cb_layout.setAlignment(Qt.AlignCenter)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            self.table.setCellWidget(row, 3, cb_widget)
            self._checkboxes[ci] = cb

        layout.addWidget(self.table)

        # Selecteer-alles / Geen knoppen
        sel_layout = QHBoxLayout()
        knop_alles = QPushButton("Alles defect")
        knop_geen  = QPushButton("Geen defect")
        knop_alles.clicked.connect(lambda: self._set_all(True))
        knop_geen.clicked.connect(lambda: self._set_all(False))
        sel_layout.addWidget(knop_alles)
        sel_layout.addWidget(knop_geen)
        sel_layout.addStretch()
        layout.addLayout(sel_layout)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        btns.setStyleSheet(
            f"QPushButton {{ background:{C_BG}; color:{C_TEXT}; "
            f"border:1px solid {C_BORDER}; border-radius:4px; padding:6px 18px; }}"
            f"QPushButton:hover {{ background:{C_BORDER}; }}")
        layout.addWidget(btns)

    def _set_all(self, state: bool):
        for cb in self._checkboxes.values():
            cb.setChecked(state)

    def apply(self):
        """Schrijf de defect-vlaggen terug naar de componentenlijst."""
        for ci, cb in self._checkboxes.items():
            self.components[ci].defect = cb.isChecked()


# ═══════════════════════════════════════════════
#  CIRCUIT CANVAS  (edit / view / sim)
# ═══════════════════════════════════════════════
class CircuitCanvas(QWidget):
    """
    Drie modi:
      "edit" – volledige editor (selecteren, slepen, draaien, draden)
      "view" – alleen weergave, geen interactie
      "sim"  – simulatie: schakelaar klikken, draden oplichten
    """

    def __init__(self, gpio: bool = True):
        super().__init__()
        # Circuit data
        self.components: List[Component] = []
        self.wires:      List[Wire]      = []

        # Modus
        self.mode: str = "edit"

        # Edit state
        self.tool:         str                       = TOOL_SELECT
        self.selected:     Optional[Component]       = None
        self.drag_active:  bool                      = False
        self.drag_start_px:Optional[Tuple[int,int]]  = None
        self.drag_orig:    Optional[Tuple[int,int]]  = None
        self.wire_start:   Optional[Tuple[int,int]]  = None
        self.muis_grid:    Optional[Tuple[int,int]]  = None
        self.snap_hl:      Optional[Tuple[int,int]]  = None

        # Sim state
        self.sim = CircuitSimulator()

        # Examen
        self.exam_active        = False   # storingen verborgen, timer loopt
        self.exam_seconds_left  = 0       # resterende seconden (door MainWindow beheerd)
        self.exam_total_seconds = 0       # totale examenduur in seconden

        # Twee managers op dezelfde pinnen botsen; het monteursscherm krijgt er geen.
        self.gpio_mgr = GPIOManager() if gpio else None
        self.koffer = KofferIO() if gpio else None
        self._gpio_timer = QTimer(self)
        self._gpio_timer.setInterval(50)
        self._gpio_timer.timeout.connect(self._gpio_poll)
        self._on_gpio_update = None

        self.setMouseTracking(True)
        self.setMinimumSize(1200, 800)
        self.setStyleSheet(f"background-color:{C_BG};")
        self.setFocusPolicy(Qt.StrongFocus)

    # ── Modus wisselen ────────────────────────

    def set_mode(self, mode: str):
        prev = self.mode
        self.mode = mode
        if mode == "sim":
            self.sim.load(self.components, self.wires)
            if self.koffer:
                self.koffer.init()
            if self.gpio_mgr:
                self.gpio_mgr.configure_pins(self.components)
            if self.koffer or self.gpio_mgr:
                self._gpio_timer.start()
        else:
            self._gpio_timer.stop()
            if prev == "sim":
                if self.koffer:
                    self.koffer.cleanup()
                if self.gpio_mgr:
                    self.gpio_mgr.cleanup()
        self.wire_start = None
        self.selected   = None
        self.update()

    # ── GPIO polling ─────────────────────────

    def _gpio_poll(self):
        """
        Wordt elke 50 ms aangeroepen tijdens simulatie.
        1. Lees de knoppen van de koffer en werk de schakelaarstanden bij
        2. Bereken de nieuwe simulatietoestand
        3. Schrijf de lampen van de koffer op basis van actieve componenten
        """
        changed = False

        if self.koffer and self.koffer.actief:
            knoppen = self.koffer.lees_knoppen()
            for idx, comp in enumerate(self.components):
                if not is_knop(comp.kanaal):
                    continue
                k = kanaal_index(comp.kanaal)
                if k < 0 or k not in knoppen:
                    continue
                if self.sim.sw_states.get(idx, False) != knoppen[k]:
                    self.sim.set_switch_from_gpio(idx, knoppen[k])
                    changed = True

        if self.gpio_mgr:
            for idx, stand in self.gpio_mgr.read_inputs(self.components).items():
                if self.sim.sw_states.get(idx, False) != stand:
                    self.sim.set_switch_from_gpio(idx, stand)
                    changed = True

        active = self.sim.comp_active_states()

        # Examen: een defecte lamp of motor blijft uit, ook al staat er spanning
        # op. De storing is daarmee niet aan de uitgang af te lezen.
        if self.exam_active:
            for i, comp in enumerate(self.components):
                if getattr(comp, 'defect', False) and comp.type in (TOOL_LAMP, TOOL_MOTOR):
                    active[i] = False

        if self.koffer and self.koffer.actief:
            standen = {}
            for i, comp in enumerate(self.components):
                if is_lamp(comp.kanaal):
                    k = kanaal_index(comp.kanaal)
                    if k >= 0:
                        standen[k] = active.get(i, False)
            self.koffer.schrijf_lampen(standen)

        if self.gpio_mgr:
            self.gpio_mgr.write_outputs(self.components, active)

        if self._on_gpio_update:
            self._on_gpio_update()

        if changed:
            self.update()

    def open_fault_dialog(self):
        """Open het storingen-configuratievenster."""
        dlg = FaultConfigDialog(self.components, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.apply()
            if self.mode == "sim":
                self.sim.load(self.components, self.wires)
        self.update()

    def open_gpio_dialog(self):
        """Open het GPIO-configuratievenster."""
        dlg = GPIOConfigDialog(self.components, parent=self)
        if dlg.exec_() == QDialog.Accepted:
            dlg.apply()
            # Herconfigureer pins als simulatie actief is
            if self.mode == "sim":
                self.gpio_mgr.configure_pins(self.components)
        self.update()

    def load_circuit(self, data: dict):
        # Veilig laden: ontbrekende velden krijgen standaardwaarden
        comp_defaults = {"label": "", "rotation": 0, "contact_start": 1,
                         "manual_contact_start": False,
                         "gpio_pin": -1, "gpio_dir": "IN", "kanaal": "",
                         "defect": False, "manual_label": False}
        comps = []
        for c in data.get("components", []):
            merged = {**comp_defaults, **c}
            comps.append(Component(**merged))
        self.components = comps
        self.wires           = [Wire(**w) for w in data.get("wires", [])]
        self.exam_time_minutes = data.get("exam_time_minutes", 10)
        # Altijd hernummeren na laden zodat nummering altijd klopt
        renumber_contacts(self.components)
        renumber_auto_labels(self.components)
        self.wire_start = None
        self.selected   = None
        self.sim.load(self.components, self.wires)
        self.update()

    def naar_dict(self) -> dict:
        # next_contact hoeft niet meer opgeslagen te worden —
        # renumber_contacts berekent het altijd opnieuw bij laden
        return {
            "components":       [asdict(c) for c in self.components],
            "wires":            [asdict(w) for w in self.wires],
            "exam_time_minutes": getattr(self, '_exam_time_minutes', 10),
        }

    @property
    def exam_time_minutes(self) -> int:
        return getattr(self, '_exam_time_minutes', 10)

    @exam_time_minutes.setter
    def exam_time_minutes(self, v: int):
        self._exam_time_minutes = max(1, int(v))

    def leegmaken(self):
        self.components = []
        self.wires      = []
        self.wire_start = None
        self.selected   = None
        self.update()

    # ── Gereedschap (edit) ────────────────────

    def set_tool(self, t: str):
        self.tool       = t
        self.wire_start = None
        if t != TOOL_SELECT:
            self.selected = None
        self.update()

    # ── Raster hulpfuncties ───────────────────

    def _px(self, col, row) -> Tuple[int, int]:
        return CANVAS_OX + col * GRID, CANVAS_OY + row * GRID

    def _grid(self, px, py) -> Tuple[int, int]:
        return (max(0, round((px - CANVAS_OX) / GRID)),
                max(0, round((py - CANVAS_OY) / GRID)))

    def _all_snap_points(self) -> Set[Tuple[int, int]]:
        """
        Alle snap-doelen:
        - aansluitpunten van componenten
        - eindpunten van bestaande draden
        - elk rasterpunt op een bestaande draad (T-verbindingen)
        """
        pts: Set[Tuple[int, int]] = set()
        for comp in self.components:
            for cp in comp_connections(comp):
                pts.add(cp)
        for w in self.wires:
            pts.add((w.c1, w.r1))
            pts.add((w.c2, w.r2))
            if w.c1 == w.c2:                    # verticaal
                for r in range(min(w.r1, w.r2), max(w.r1, w.r2) + 1):
                    pts.add((w.c1, r))
            elif w.r1 == w.r2:                  # horizontaal
                for c in range(min(w.c1, w.c2), max(w.c1, w.c2) + 1):
                    pts.add((c, w.r1))
        return pts

    def _nearest_snap(self, px, py) -> Optional[Tuple[int, int]]:
        """
        Geeft het dichtstbijzijnde snap-doel.
        Als het grid-punt zelf een snap-doel is: altijd snappen (afstand 0).
        Anders: zoek binnen SNAP_R pixels.
        """
        grid_pt = self._grid(px, py)
        all_pts = self._all_snap_points()
        if grid_pt in all_pts:          # grid-punt IS een snap-doel
            return grid_pt
        best_d, best = float("inf"), None
        for cp in all_pts:
            cpx, cpy = self._px(*cp)
            d = math.hypot(px - cpx, py - cpy)
            if d < best_d:
                best_d, best = d, cp
        return best if best_d < SNAP_R else None

    def _snap_ortho(self, c1, r1, c2, r2):
        if abs(c2-c1) >= abs(r2-r1): return c2, r1
        return c1, r2

    def _comp_at(self, col, row) -> Optional[Component]:
        """
        Het dichtstbijzijnde component binnen één rastercel. Bij gelijke
        afstand wint het laatst geplaatste component (dat ligt bovenop).
        """
        beste, beste_d = None, None
        for c in self.components:
            dc, dr = abs(c.col - col), abs(c.row - row)
            if dc > 1 or dr > 1:
                continue
            d = dc * dc + dr * dr
            if beste_d is None or d <= beste_d:
                beste, beste_d = c, d
        return beste

    # ── Muisgebeurtenissen ────────────────────

    def mousePressEvent(self, event):
        px, py = event.x(), event.y()
        col, row = self._grid(px, py)

        # ── SIM modus ────────────────────────
        if self.mode == "sim":
            if event.button() == Qt.LeftButton:
                comp = self._comp_at(col, row)
                if comp and comp.type in (TOOL_SWITCH, TOOL_SW2P_NO,
                                          TOOL_SW2P_NC, TOOL_SPDT):
                    idx = self.components.index(comp)
                    self.sim.toggle_switch(idx)
                    self.update()
            return

        # ── EDIT modus ───────────────────────
        if event.button() == Qt.LeftButton:
            if self.tool == TOOL_SELECT:
                comp = self._comp_at(col, row)
                if comp:
                    self.selected      = comp
                    self.drag_active   = True
                    self.drag_start_px = (px, py)
                    self.drag_orig     = (comp.col, comp.row)
                else:
                    self.selected    = None
                    self.drag_active = False

            elif self.tool == TOOL_DELETE:
                self._verwijder(col, row)

            elif self.tool == TOOL_WIRE:
                snapped = self._nearest_snap(px, py)
                if snapped:
                    col, row = snapped
                elif self.wire_start:
                    col, row = self._snap_ortho(*self.wire_start, col, row)
                if self.wire_start is None:
                    self.wire_start = (col, row)
                else:
                    c1, r1 = self.wire_start
                    if not snapped:
                        col, row = self._snap_ortho(c1, r1, col, row)
                    if (c1, r1) != (col, row):
                        self.wires.append(Wire(c1, r1, col, row))
                    self.wire_start = None

            elif self.tool == TOOL_NETLABEL:
                snapped = self._nearest_snap(px, py)
                if not snapped:
                    QMessageBox.information(
                        self,
                        "Net Label",
                        "Plaats een net label op een draad of aansluitpunt.",
                    )
                    return
                col, row = snapped
                label = self._auto_label(self.tool)
                self.components.append(Component(self.tool, col, row, label, 0, 0))
                renumber_contacts(self.components)
                renumber_auto_labels(self.components)

            else:
                label = self._auto_label(self.tool)
                # contact_start tijdelijk 1; renumber_contacts stelt de juiste waarde in
                rotation = 0 if self.tool == TOOL_RCOIL else 90
                self.components.append(Component(self.tool, col, row, label, rotation, 1))
                renumber_contacts(self.components)   # herbereken ÁLle nummers
                renumber_auto_labels(self.components)

        elif event.button() == Qt.RightButton:
            self._verwijder(col, row)

        self.update()

    def mouseMoveEvent(self, event):
        px, py = event.x(), event.y()
        col, row = self._grid(px, py)

        if (self.mode == "edit" and self.tool == TOOL_SELECT
                and self.drag_active and self.selected):
            dx = px - self.drag_start_px[0]
            dy = py - self.drag_start_px[1]
            self.selected.col = max(1, self.drag_orig[0] + round(dx / GRID))
            self.selected.row = max(1, self.drag_orig[1] + round(dy / GRID))
            self.update()
            return

        if self.mode == "edit" and self.tool == TOOL_WIRE:
            snapped = self._nearest_snap(px, py)
            if snapped:
                col, row = snapped
                self.snap_hl = snapped
            else:
                self.snap_hl = None
                if self.wire_start:
                    col, row = self._snap_ortho(*self.wire_start, col, row)

        self.muis_grid = (col, row)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_active    = False
            self.drag_start_px  = None
            self.drag_orig      = None

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key_Escape:
            self.wire_start  = None
            self.selected    = None
        elif k == Qt.Key_R and self.selected and self.tool == TOOL_SELECT:
            self.selected.rotation = (self.selected.rotation + 90) % 360
        elif k == Qt.Key_N and self.selected and self.tool == TOOL_SELECT:
            self._hernoem_component(self.selected)
        elif k == Qt.Key_F and self.selected and self.tool == TOOL_SELECT:
            self.selected.defect = not self.selected.defect
        elif k == Qt.Key_C and self.selected and self.tool == TOOL_SELECT:
            self._wijzig_contactnummers(self.selected)
        elif k in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.selected and self.tool == TOOL_SELECT:
                if self.selected in self.components:
                    self.components.remove(self.selected)
                    renumber_contacts(self.components)   # hernummer na verwijderen
                    renumber_auto_labels(self.components)
                self.selected = None
        self.update()

    def _verwijder(self, col, row):
        # Gebruik dezelfde keuze als bij het selecteren, anders verwijder je
        # een ander component dan je aangeklikt hebt.
        comp = self._comp_at(col, row)
        if comp is not None:
            if comp is self.selected:
                self.selected = None
            self.components.remove(comp)
            renumber_contacts(self.components)   # hernummer na verwijderen
            renumber_auto_labels(self.components)
            self.update(); return
        for i, w in enumerate(self.wires):
            on_h = w.r1==w.r2==row and min(w.c1,w.c2)<=col<=max(w.c1,w.c2)
            on_v = w.c1==w.c2==col and min(w.r1,w.r2)<=row<=max(w.r1,w.r2)
            near = ((abs(w.c1-col)<=1 and abs(w.r1-row)<=1) or
                    (abs(w.c2-col)<=1 and abs(w.r2-row)<=1))
            if on_h or on_v or near:
                self.wires.pop(i); self.update(); return

    def _auto_label(self, t):
        # Eerste vrije nummer per type, zodat er geen dubbel label ontstaat.
        prefix   = LABEL_PREFIX.get(t, 'X')
        bestaand = {c.label for c in self.components if c.type == t}
        n = 1
        while f"{prefix}{n}" in bestaand:
            n += 1
        return f"{prefix}{n}"

    def _hernoem_component(self, comp: Component):
        oud_label = comp.label or ""
        nieuw_label, ok = QInputDialog.getText(
            self,
            "Symbool hernoemen",
            f"Nieuwe naam voor {oud_label or comp.type}:",
            text=oud_label,
        )
        if not ok:
            return

        nieuw_label = nieuw_label.strip()
        if not nieuw_label:
            QMessageBox.warning(
                self,
                "Symbool hernoemen",
                "De naam mag niet leeg zijn.",
            )
            return

        comp.label        = nieuw_label
        comp.manual_label = True   # niet meer automatisch hernummeren

        # Alleen bij een spoel geldt de hernoeming voor de hele relaisgroep.
        # Een contact hernoemen is juist de manier om het aan een andere
        # spoel te koppelen; dan mag de spoel niet meeveranderen.
        if comp.type == TOOL_RCOIL and oud_label:
            for ander in self.components:
                if ander is comp:
                    continue
                if ander.type in (TOOL_RCONT, TOOL_RSPDT) and ander.label == oud_label:
                    ander.label        = nieuw_label
                    ander.manual_label = True

        self.update()

    def _wijzig_contactnummers(self, comp: Component):
        aantal = CONTACTS_PER_TYPE.get(comp.type, 2)
        if aantal <= 0:
            QMessageBox.information(
                self,
                "Contactnummers",
                "Dit component heeft geen instelbare contactnummers.",
            )
            return

        waarde, ok = QInputDialog.getInt(
            self,
            "Contactnummers wijzigen",
            f"Startnummer voor {comp.label or comp.type} ({aantal} contacten)\n"
            "0 = automatisch laten nummeren",
            comp.contact_start if comp.manual_contact_start else 0,
            0,
            9999,
            1,
        )
        if not ok:
            return

        if waarde == 0:
            comp.manual_contact_start = False
            renumber_contacts(self.components)
            self.update()
            return

        oud_start = comp.contact_start
        oud_manual = comp.manual_contact_start
        comp.contact_start = waarde
        comp.manual_contact_start = True

        if not can_use_contact_start(self.components, comp, waarde):
            comp.contact_start = oud_start
            comp.manual_contact_start = oud_manual
            QMessageBox.warning(
                self,
                "Contactnummers",
                "Dit contactbereik overlapt met een ander component.",
            )
            return

        renumber_contacts(self.components)
        self.update()

    # ══════════════════════════════════════════
    #  TEKENEN
    # ══════════════════════════════════════════

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._draw_grid(p)
        self._draw_wires(p)
        self._draw_snap_pts(p)
        self._draw_comps(p)
        if self.mode == "edit":
            self._draw_selection(p)
            self._draw_wire_preview(p)
        if self.mode == "sim":
            self._draw_sim_legend(p)
        if self.mode == "sim" and self.exam_active:
            self._draw_exam_overlay(p)

    def _draw_grid(self, p):
        p.setPen(QPen(QColor(C_BORDER), 1))
        col = 0
        while CANVAS_OX + col*GRID < self.width():
            row = 0
            while CANVAS_OY + row*GRID < self.height():
                px, py = self._px(col, row)
                p.drawPoint(px, py)
                row += 1
            col += 1

    def _draw_wires(self, p):
        for w in self.wires:
            x1, y1 = self._px(w.c1, w.r1)
            x2, y2 = self._px(w.c2, w.r2)
            if self.mode == "sim" and self.sim.wire_is_live(w):
                p.setPen(QPen(QColor(C_LIVE), 3))
            else:
                p.setPen(QPen(QColor(C_BLUE), 2))
            p.drawLine(x1, y1, x2, y2)

        # ── Verbindingspunten (junction dots) ──────────────────────
        # Teken een dot waar 3+ draden samenkomen of een draad-eindpunt
        # op een andere draad aansluit (T-verbinding).
        if self.mode in ("edit", "view", "sim"):
            from collections import Counter
            node_count: Counter = Counter()
            for w in self.wires:
                node_count[(w.c1, w.r1)] += 1
                node_count[(w.c2, w.r2)] += 1
            for (col, row), cnt in node_count.items():
                if cnt >= 2:        # verbindingspunt (T of kruis)
                    px2, py2 = self._px(col, row)
                    kleur = C_LIVE if (self.mode == "sim" and
                                       (col, row) in self.sim.live_nodes) else C_BLUE
                    p.setPen(QPen(QColor(kleur), 1))
                    p.setBrush(QBrush(QColor(kleur)))
                    p.drawEllipse(px2-4, py2-4, 8, 8)

    def _draw_snap_pts(self, p):
        """
        Toont snap-doelen als het Draad-gereedschap actief is.
        - Componentaansluitpunten: vierkant symbool (□)
        - Draad-eindpunten: kleine cirkel
        - Actief snap-doel (snap_hl): groot groen kruis + ring
        """
        if self.mode != "edit" or self.tool != TOOL_WIRE:
            return

        all_pts   = self._all_snap_points()
        comp_pts  = {cp for comp in self.components for cp in comp_connections(comp)}
        wire_ends = {(w.c1,w.r1) for w in self.wires} | {(w.c2,w.r2) for w in self.wires}

        for cp in all_pts:
            cpx, cpy = self._px(*cp)

            if cp == self.snap_hl:
                # ── Actieve snap: grote groene ring + kruis ───────
                p.setPen(QPen(QColor(C_GREEN), 2))
                p.setBrush(QBrush(Qt.transparent))
                p.drawEllipse(cpx-10, cpy-10, 20, 20)
                p.setPen(QPen(QColor(C_GREEN), 2))
                p.drawLine(cpx-6, cpy, cpx+6, cpy)
                p.drawLine(cpx, cpy-6, cpx, cpy+6)
                # Label "SNAP"
                p.setPen(QColor(C_GREEN))
                p.setFont(QFont("Courier New", 7))
                p.drawText(cpx+12, cpy+4, "SNAP")

            elif cp in comp_pts:
                # ── Component aansluitpunt: klein vierkantje ───────
                p.setPen(QPen(QColor(C_PEACH), 1))
                p.setBrush(QBrush(Qt.transparent))
                p.drawRect(cpx-4, cpy-4, 8, 8)

            elif cp in wire_ends:
                # ── Draad eindpunt: kleine stip ────────────────────
                p.setPen(QPen(QColor(C_MUTED), 1))
                p.setBrush(QBrush(QColor(C_MUTED)))
                p.drawEllipse(cpx-3, cpy-3, 6, 6)

    def _draw_comps(self, p):
        for i, comp in enumerate(self.components):
            cx, cy = self._px(comp.col, comp.row)
            p.save()
            p.translate(cx, cy)
            p.rotate(comp.rotation)
            self._draw_one_comp(p, i, comp)
            p.restore()
            # Defect-overlay: rood kruis over component (buiten rotatie)
            # Verborgen tijdens examen zodat de monteur ze zelf moet vinden.
            if getattr(comp, 'defect', False) and self.mode in ("edit", "sim") and not self.exam_active:
                self._draw_defect_overlay(p, cx, cy)
            # GPIO pin badge (buiten rotatie, altijd leesbaar)
            if (comp.kanaal or comp.gpio_pin >= 0) and self.mode in ("sim", "edit"):
                self._draw_gpio_badge(p, cx, cy, comp)

    def _draw_gpio_badge(self, p, cx, cy, comp):
        """Klein badge boven elk component dat een GPIO-koppeling heeft."""
        txt   = comp.kanaal if comp.kanaal else f"GPIO{comp.gpio_pin}"
        dir_k = C_GREEN if comp.gpio_dir == "IN" else C_PEACH
        p.setFont(QFont("Courier New", 7, QFont.Bold))
        fm    = p.fontMetrics()
        tw    = fm.horizontalAdvance(txt)
        bx    = cx - tw//2 - 4
        by    = cy - CONN - 10    # boven het component (CONN = 40px = 1 rastercel)
        p.setPen(QPen(QColor(dir_k), 1))
        p.setBrush(QBrush(QColor(dir_k + "44")))
        p.drawRoundedRect(bx, by, tw + 8, 14, 3, 3)
        p.setPen(QColor(dir_k))
        p.drawText(bx + 4, by + 11, txt)

    def _draw_defect_overlay(self, p, cx, cy):
        """Rood X-kruis over een defect component."""
        s = HW + 4   # halve grootte van het kruis
        p.setPen(QPen(QColor(C_RED), 3))
        p.drawLine(cx - s, cy - s, cx + s, cy + s)
        p.drawLine(cx + s, cy - s, cx - s, cy + s)
        # Kleine rode tekst "STORING"
        p.setFont(QFont("Courier New", 7, QFont.Bold))
        p.setPen(QColor(C_RED))
        fm = p.fontMetrics()
        txt = "STORING"
        tw = fm.horizontalAdvance(txt)
        p.drawText(cx - tw // 2, cy + s + 12, txt)

    def _draw_one_comp(self, p, idx, comp):
        """Tekent één component, rekening houdend met sim-toestand."""
        cs = comp.contact_start
        l  = comp.label

        if self.mode == "sim":
            active    = self.sim.comp_is_active(idx)
            closed    = self.sim.switch_closed(idx)
            energized = self.sim.coil_energized(l)
            rc_closed = self.sim.contact_closed(l)

            # Examen: defecte loads zijn visueel inactief (storing verborgen).
            # - LAMP/MOTOR: gaat niet aan ook al staat er spanning op.
            # - RCOIL: al afgehandeld via relay_states=False → energized=False.
            # - Schakelaars/contacten: visuele stand blijft (klik werkt), maar
            #   circuit reageert niet → dit IS de verborgen fout.
            if self.exam_active and getattr(comp, 'defect', False):
                if comp.type in (TOOL_MOTOR, TOOL_LAMP):
                    active = False

            if comp.type == TOOL_SWITCH:
                _ec_schakelaar(p, l, cs, gesloten=closed)
            elif comp.type == TOOL_SW2P_NO:
                _ec_schakelaar2p(p, l, cs, gesloten=closed, nc=False)
            elif comp.type == TOOL_SW2P_NC:
                _ec_schakelaar2p(p, l, cs, gesloten=closed, nc=True)
            elif comp.type == TOOL_SPDT:
                _ec_spdt(p, l, cs, positie_c=closed, flipped=True)
            elif comp.type == TOOL_RCOIL:
                _ec_relaisspoel(p, l, cs, actief=energized)
            elif comp.type == TOOL_RCONT:
                _ec_relaiscontact(p, l, cs, gesloten=rc_closed)
            elif comp.type == TOOL_RSPDT:
                _ec_rspdt(p, l, cs, positie_c=rc_closed, flipped=True)
            elif comp.type == TOOL_MOTOR:
                _ec_motor(p, l, cs, actief=active)
            elif comp.type == TOOL_LAMP:
                _ec_lamp(p, l, cs, actief=active)
            elif comp.type == TOOL_POWER:
                _ec_voeding(p, l, cs)
            elif comp.type == TOOL_GND:
                _ec_massa(p, l, cs)
            elif comp.type == TOOL_NETLABEL:
                _ec_netlabel(p, l, cs)
        else:
            fn = EC_DRAW_BASE.get(comp.type)
            if fn:
                fn(p, l, cs)

    def _draw_selection(self, p):
        if not self.selected or self.tool != TOOL_SELECT:
            return
        cx, cy = self._px(self.selected.col, self.selected.row)
        t = self.selected.type
        if t in FOUR_TERMINAL:
            # 2P: pools op ±CONN → selectiebox van -CONN tot +CONN
            top, h = -CONN - 6, CONN * 2 + 12
        elif t in THREE_TERMINAL:
            # SPDT: A links, B/C op ±CONN rechts
            top, h = -CONN - 6, CONN * 2 + 12
        else:
            top, h = -HW - 6, HW * 2 + 12
        p.save()
        p.translate(cx, cy)
        p.rotate(self.selected.rotation)
        p.setPen(QPen(QColor(C_BLUE), 1, Qt.DashLine))
        p.setBrush(QBrush(Qt.transparent))
        p.drawRoundedRect(-CONN - 6, top, CONN * 2 + 12, h, 4, 4)
        p.restore()
        p.setPen(QColor(C_MUTED))
        p.setFont(QFont("Courier New", 8))
        p.drawText(cx + CONN + 4, cy - HW // 2, "[R] draaien  [Del] wissen  [F] storing")

    def _draw_wire_preview(self, p):
        if not (self.wire_start and self.muis_grid):
            return
        x1, y1 = self._px(*self.wire_start)
        x2, y2 = self._px(*self.muis_grid)
        p.setPen(QPen(QColor(C_BLUE), 1, Qt.DashLine))
        p.drawLine(x1, y1, x2, y2)
        p.setPen(QPen(QColor(C_BLUE), 2))
        p.setBrush(QBrush(QColor(C_BLUE)))
        p.drawEllipse(x1-5, y1-5, 10, 10)

    def _draw_sim_legend(self, p):
        """Kleine legenda rechtsonder in sim-modus."""
        hw_txt = "Hardware RPi" if ON_RPI else "MockGPIO (geen hardware)"
        x, y = self.width() - 230, self.height() - 92
        p.setPen(QColor(C_MUTED))
        p.setFont(QFont("Courier New", 9))
        p.drawText(x, y,      f"GPIO: {hw_txt}")
        p.drawText(x, y + 16, "● Draden oranje = onder spanning")
        p.drawText(x, y + 32, "⚡ Klik schakelaar om te sluiten")
        p.setPen(QColor(C_GREEN))
        p.drawText(x, y + 48, "■ GPIO IN")
        p.setPen(QColor(C_PEACH))
        p.drawText(x + 80, y + 48, "■ GPIO OUT")
        p.setPen(QColor(C_RED))
        p.drawText(x, y + 64, "✕ Rood kruis = storing actief")

    def _draw_exam_overlay(self, p):
        """Grote examentimer rechtsbovenin de canvas."""
        from PyQt5.QtCore import QRect
        s = self.exam_seconds_left
        t = self.exam_total_seconds if self.exam_total_seconds > 0 else 1
        pct = s / t
        if pct > 0.5:
            kleur = QColor(C_GREEN)
        elif pct > 0.2:
            kleur = QColor(C_YELLOW)
        else:
            kleur = QColor(C_RED)

        bw, bh = 200, 90
        bx = self.width() - bw - 12
        by = 12

        # Achtergrond – halftransparant
        p.setPen(Qt.NoPen)
        bg = QColor(17, 17, 27, 220)       # C_SIDE (#11111b) + alpha 220
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(bx, by, bw, bh, 10, 10)

        # Border in timerkleur
        p.setPen(QPen(kleur, 2))
        p.setBrush(QBrush(Qt.transparent))
        p.drawRoundedRect(bx, by, bw, bh, 10, 10)

        # Label "EXAMEN"
        p.setFont(QFont("Courier New", 9, QFont.Bold))
        p.setPen(QColor(C_MUTED))
        p.drawText(QRect(bx, by + 6, bw, 18), Qt.AlignCenter, "EXAMEN")

        # MM:SS groot
        mins = s // 60
        secs = s % 60
        p.setFont(QFont("Courier New", 32, QFont.Bold))
        p.setPen(kleur)
        p.drawText(QRect(bx, by + 22, bw, 58), Qt.AlignCenter, f"{mins:02d}:{secs:02d}")


# ═══════════════════════════════════════════════
#  BESTANDSPANEEL  (linkerkant Bekijken-modus)
# ═══════════════════════════════════════════════
class FilePaneel(QWidget):
    """
    Toont JSON-circuits uit een map als klikbare knoppen.
    Signaleert welk circuit geselecteerd is via callback.
    """

    def __init__(self, on_select, on_sim):
        super().__init__()
        self.on_select  = on_select   # callback(data: dict, naam: str)
        self.on_sim     = on_sim      # callback()
        self.map_pad    = DEFAULT_DIR
        self._geselecteerd = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Map-keuze
        layout.addWidget(self._sec("MAP"))
        self.map_lbl = QLabel(str(self.map_pad))
        self.map_lbl.setWordWrap(True)
        self.map_lbl.setStyleSheet(
            f"color:{C_MUTED}; font-size:9px; font-family:'Courier New';")
        layout.addWidget(self.map_lbl)

        knop_map = QPushButton("📂  Map kiezen")
        knop_map.setStyleSheet(_knop_stijl(C_TEAL))
        knop_map.clicked.connect(self._kies_map)
        layout.addWidget(knop_map)

        knop_ververs = QPushButton("↻  Verversen")
        knop_ververs.setStyleSheet(_knop_stijl(C_BLUE))
        knop_ververs.clicked.connect(self.ververs)
        layout.addWidget(knop_ververs)

        layout.addWidget(self._sec("OPGESLAGEN CIRCUITS"))

        # Scrollbaar gebied voor bestandslijst
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"border:none; background:{C_SIDE};")
        self.lijst_widget = QWidget()
        self.lijst_layout = QVBoxLayout(self.lijst_widget)
        self.lijst_layout.setContentsMargins(0, 0, 0, 0)
        self.lijst_layout.setSpacing(3)
        self.lijst_layout.addStretch()
        scroll.setWidget(self.lijst_widget)
        layout.addWidget(scroll)

        # Simuleer-knop (verborgen tot circuit geladen)
        self.sim_knop = QPushButton("▶  Simuleren")
        self.sim_knop.setStyleSheet(_knop_stijl("#a6e3a1"))
        self.sim_knop.setVisible(False)
        self.sim_knop.clicked.connect(self.on_sim)
        layout.addWidget(self.sim_knop)

        self.ververs()

    def ververs(self):
        """Herlaad bestandslijst uit de huidige map."""
        # Verwijder oude knoppen
        while self.lijst_layout.count() > 1:
            item = self.lijst_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.map_lbl.setText(str(self.map_pad))
        self.map_pad.mkdir(parents=True, exist_ok=True)

        bestanden = sorted(self.map_pad.glob("*.json"))
        if not bestanden:
            lbl = QLabel("Geen circuits gevonden.\nMaak een circuit en sla het op.")
            lbl.setWordWrap(True)
            lbl.setStyleSheet(f"color:{C_MUTED}; font-size:10px; font-family:'Courier New';")
            self.lijst_layout.insertWidget(0, lbl)
            return

        for pad in bestanden:
            naam = pad.stem
            k = QPushButton(f"📄  {naam}")
            k.setCheckable(True)
            k.setStyleSheet(_knop_stijl(C_BLUE))
            k.clicked.connect(lambda _, p=pad, n=naam: self._laad(p, n))
            self.lijst_layout.insertWidget(
                self.lijst_layout.count() - 1, k)

    def _kies_map(self):
        pad = QFileDialog.getExistingDirectory(
            self, "Kies map met circuits", str(self.map_pad))
        if pad:
            self.map_pad = Path(pad)
            self.ververs()

    def _laad(self, pad: Path, naam: str):
        # Alle knoppen deselecteren
        for i in range(self.lijst_layout.count() - 1):
            w = self.lijst_layout.itemAt(i).widget()
            if isinstance(w, QPushButton):
                w.setChecked(w.text() == f"📄  {naam}")
        try:
            with open(pad, encoding="utf-8") as f:
                data = json.load(f)
            self._geselecteerd = data
            self.sim_knop.setVisible(True)
            self.on_select(data, naam)
        except Exception as e:
            QMessageBox.critical(self, "Fout", f"Kan bestand niet laden:\n{e}")

    def _sec(self, t):
        l = QLabel(t)
        l.setStyleSheet(
            f"color:{C_MUTED}; font-size:10px; font-weight:bold;"
            f"font-family:'Courier New'; letter-spacing:1px; margin-top:6px;")
        return l


# ═══════════════════════════════════════════════
#  GPIO MONITOR PANEEL
# ═══════════════════════════════════════════════
class GPIOMonitorPanel(QWidget):
    """
    Live overzicht van alle GPIO-koppelingen en hun huidige staat.

    Bovenste rij  : samenvatting + hardware-indicator
    Middelste rij : één kaartje per geconfigureerde pin
                    groen  = HIGH  (actief)
                    rood   = LOW   (inactief)
                    grijs  = niet geconfigureerd
    Onderste rij  : op MockGPIO: toggle-knoppen voor INPUT-pins (test)
    """

    def __init__(self, koffer, on_mock_toggle, parent=None):
        super().__init__(parent)
        self.koffer         = koffer
        self.on_mock_toggle = on_mock_toggle   # callback(pin)
        self._components: List[Component] = []
        self._kaartjes: Dict[str, dict]   = {}  # pin → {frame, lbl_state, lbl_comp}

        self.setStyleSheet(
            f"background-color:{C_SIDE}; "
            f"border-top: 1px solid {C_BORDER};")
        self.setFixedHeight(130)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 6)
        root.setSpacing(4)

        # ── Kopregel ──────────────────────────────────────────────
        kop = QHBoxLayout()
        self.lbl_hw = QLabel(
            "🟢  Koffer via SPI" if SPI_AANWEZIG else "🟡  Mockkoffer (geen hardware)")
        self.lbl_hw.setStyleSheet(
            f"color:{'#a6e3a1' if SPI_AANWEZIG else C_YELLOW}; "
            f"font-family:'Courier New'; font-size:10px; font-weight:bold;")
        kop.addWidget(self.lbl_hw)
        kop.addStretch()
        self.lbl_sum = QLabel("Geen pins geconfigureerd")
        self.lbl_sum.setStyleSheet(
            f"color:{C_MUTED}; font-family:'Courier New'; font-size:10px;")
        kop.addWidget(self.lbl_sum)
        root.addLayout(kop)

        # ── Scrollbaar kaartjes-gebied ─────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"border:none; background:{C_SIDE};"
            f"QScrollBar:horizontal {{ height:6px; background:{C_BORDER}; }}"
            f"QScrollBar::handle:horizontal {{ background:{C_MUTED}; border-radius:3px; }}")

        self._kaart_widget = QWidget()
        self._kaart_widget.setStyleSheet(f"background:{C_SIDE};")
        self._kaart_layout = QHBoxLayout(self._kaart_widget)
        self._kaart_layout.setContentsMargins(0, 0, 0, 0)
        self._kaart_layout.setSpacing(6)
        self._kaart_layout.addStretch()

        scroll.setWidget(self._kaart_widget)
        root.addWidget(scroll)

    # ── Kaartjes opbouwen ─────────────────────────────────────────

    def _maak_kaartje(self, kanaal: str, comp: Component) -> dict:
        """Bouw één kanaalkaartje en geef de verwijzingen terug."""
        frame = QFrame()
        frame.setFixedSize(90, 72)
        frame.setStyleSheet(
            f"background:{C_BG}; border:1px solid {C_BORDER}; border-radius:6px;")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(4, 4, 4, 4)
        fl.setSpacing(2)

        # Pin-nummer
        lbl_pin = QLabel(kanaal)
        lbl_pin.setAlignment(Qt.AlignCenter)
        lbl_pin.setStyleSheet(
            f"color:{C_MUTED}; font-family:'Courier New'; font-size:9px; font-weight:bold;")
        fl.addWidget(lbl_pin)

        # Status-indicator (gekleurde cirkel + HIGH/LOW tekst)
        lbl_state = QLabel("UIT")
        lbl_state.setAlignment(Qt.AlignCenter)
        lbl_state.setStyleSheet(
            f"color:{C_RED}; font-family:'Courier New'; font-size:11px; font-weight:bold; "
            f"background:{C_RED}22; border-radius:4px; padding:1px 6px;")
        fl.addWidget(lbl_state)

        # Component-label + richting
        dir_kleur = C_GREEN if is_knop(kanaal) else C_PEACH
        lbl_comp = QLabel(f"{comp.label}  [{'knop' if is_knop(kanaal) else 'lamp'}]")
        lbl_comp.setAlignment(Qt.AlignCenter)
        lbl_comp.setStyleSheet(
            f"color:{dir_kleur}; font-family:'Courier New'; font-size:8px;")
        fl.addWidget(lbl_comp)

        # Toggle-knop (alleen MockGPIO + INPUT pins)
        knop = None
        if not SPI_AANWEZIG and is_knop(kanaal):
            knop = QPushButton("⚡ Test")
            knop.setFixedHeight(18)
            knop.setStyleSheet(
                f"background:{C_BORDER}; color:{C_TEXT}; border:none; "
                f"border-radius:3px; font-family:'Courier New'; font-size:8px;")
            knop.clicked.connect(lambda _, k=kanaal: self.on_mock_toggle(k))
            fl.addWidget(knop)

        return {
            "frame":     frame,
            "lbl_state": lbl_state,
            "lbl_comp":  lbl_comp,
            "toggle":    knop,
        }

    def refresh_layout(self, components: List[Component]):
        """Herbouw de kaartjes op basis van de huidige componentlijst."""
        self._components = components

        # Verwijder oude kaartjes
        while self._kaart_layout.count() > 1:
            item = self._kaart_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._kaartjes.clear()

        geconfigureerd = [
            (i, c) for i, c in enumerate(components) if c.kanaal
        ]

        if not geconfigureerd:
            lbl = QLabel("Geen kanalen gekoppeld  ·  "
                         "Klik ⚙ GPIO om Q1..Q8 en S1..S8 te koppelen")
            lbl.setStyleSheet(
                f"color:{C_MUTED}; font-family:'Courier New'; font-size:10px;")
            self._kaart_layout.insertWidget(0, lbl)
            self.lbl_sum.setText("Geen kanalen gekoppeld")
            return

        for _, comp in geconfigureerd:
            kaartje = self._maak_kaartje(comp.kanaal, comp)
            self._kaartjes[comp.kanaal] = kaartje
            # Voeg vóór de stretch in
            self._kaart_layout.insertWidget(
                self._kaart_layout.count() - 1, kaartje["frame"])

        n_knop = sum(1 for _, c in geconfigureerd if is_knop(c.kanaal))
        n_lamp = sum(1 for _, c in geconfigureerd if is_lamp(c.kanaal))
        self.lbl_sum.setText(f"{n_knop} knoppen  |  {n_lamp} lampen")

    def update_states(self, components: List[Component]):
        """Ververs de kaartjes op basis van de actuele stand van de koffer."""
        if self.koffer is None or not self.koffer.actief:
            return

        knoppen = self.koffer.lees_knoppen()
        lampen = self.koffer.lamp_standen()

        for comp in components:
            kaartje = self._kaartjes.get(comp.kanaal)
            if kaartje is None:
                continue
            i = kanaal_index(comp.kanaal)
            if i < 0:
                continue

            aan = knoppen.get(i, False) if is_knop(comp.kanaal) else lampen.get(i, False)
            kleur = C_GREEN if aan else C_RED
            kaartje["lbl_state"].setText("AAN" if aan else "UIT")
            kaartje["lbl_state"].setStyleSheet(
                f"color:{kleur}; font-family:'Courier New'; font-size:11px; "
                f"font-weight:bold; background:{kleur}22; "
                f"border-radius:4px; padding:1px 6px;")
            rand = kleur if aan else C_BORDER
            kaartje["frame"].setStyleSheet(
                f"background:{C_BG}; border:1px solid {rand}; "
                f"border-radius:6px;")


# ═══════════════════════════════════════════════
def _knop_stijl(actief=C_BLUE) -> str:
    return f"""
        QPushButton {{
            background-color:{C_BG}; color:{C_TEXT};
            border:1px solid {C_BORDER}; border-radius:6px;
            padding:8px 8px; text-align:left;
            font-family:'Courier New'; font-size:12px;
        }}
        QPushButton:hover   {{ background-color:{C_BORDER}; }}
        QPushButton:checked {{ background-color:{actief};
                               color:{C_SIDE}; font-weight:bold; border:none; }}
    """


# ═══════════════════════════════════════════════
#  HOOFDVENSTER
# ═══════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Storingskoffer Dashboard – RET N.V.")
        self.setMinimumSize(1400, 800)
        self.setStyleSheet(f"background-color:{C_SIDE}; color:{C_TEXT};")

        central = QWidget()
        self.setCentralWidget(central)
        hoofd = QHBoxLayout(central)
        hoofd.setSpacing(0); hoofd.setContentsMargins(0, 0, 0, 0)

        # ── Linkerpaneel ──────────────────────
        zij = QFrame()
        zij.setFixedWidth(235)
        zij.setStyleSheet(f"background-color:{C_SIDE}; border-right:1px solid {C_BORDER};")
        zij_l = QVBoxLayout(zij)
        zij_l.setContentsMargins(10, 14, 10, 14); zij_l.setSpacing(5)

        # Mode toggle
        mf = QFrame(); mf.setStyleSheet(f"background-color:{C_BG}; border-radius:6px;")
        ml = QHBoxLayout(mf); ml.setContentsMargins(4, 4, 4, 4); ml.setSpacing(4)
        ts = f"""QPushButton {{ background:transparent; color:{C_MUTED}; border:none;
                border-radius:4px; padding:6px; font-family:'Courier New';
                font-size:12px; font-weight:bold; }}
             QPushButton:checked {{ background:{C_BORDER}; color:{C_TEXT}; }}"""
        self.kb = QPushButton("Bekijken"); self.kb.setCheckable(True); self.kb.setChecked(True)
        self.ke = QPushButton("Bewerken"); self.ke.setCheckable(True)
        self.kx = QPushButton("Examen");   self.kx.setCheckable(True)
        for k in (self.kb, self.ke, self.kx): k.setStyleSheet(ts)
        self.kb.clicked.connect(lambda: self._modus("bekijk"))
        self.ke.clicked.connect(lambda: self._modus("bewerk"))
        self.kx.clicked.connect(lambda: self._modus("examen"))
        ml.addWidget(self.kb); ml.addWidget(self.ke); ml.addWidget(self.kx)
        zij_l.addWidget(mf)

        self.zij_stack = QStackedWidget()
        zij_l.addWidget(self.zij_stack)

        # ── Zijbalk p0: Bekijken ──────────────
        self.file_paneel = FilePaneel(
            on_select=self._circuit_geladen,
            on_sim=self._start_sim
        )
        self.zij_stack.addWidget(self.file_paneel)

        # ── Zijbalk p1: Bewerken ──────────────
        p1 = QWidget(); p1l = QVBoxLayout(p1)
        p1l.setContentsMargins(0, 0, 0, 0); p1l.setSpacing(4)
        p1l.addWidget(self._sec("GEREEDSCHAP"))
        self.tknoppen = {}
        alle_tools = [
            TOOL_SELECT, TOOL_WIRE, TOOL_NETLABEL,
            TOOL_SWITCH, TOOL_SW2P_NO, TOOL_SW2P_NC, TOOL_SPDT,
            TOOL_RCOIL, TOOL_RCONT, TOOL_RSPDT, TOOL_MOTOR, TOOL_LAMP,
            TOOL_POWER, TOOL_GND,
            TOOL_DELETE,
        ]
        for t in alle_tools:
            k = QPushButton(TOOL_LABELS[t]); k.setCheckable(True)
            k.setStyleSheet(_knop_stijl(TOOL_KLEUREN[t]))
            k.clicked.connect(lambda _, tool=t: self._sel_tool(tool))
            p1l.addWidget(k); self.tknoppen[t] = k

        p1l.addWidget(self._lijn())
        p1l.addWidget(self._sec("CIRCUIT"))
        for tekst, slot in [("🗋  Nieuw",   self._nieuw),
                             ("💾  Opslaan", self._opslaan),
                             ("📂  Laden",   self._laden)]:
            k = QPushButton(tekst); k.setStyleSheet(_knop_stijl(C_TEAL))
            k.clicked.connect(slot); p1l.addWidget(k)

        p1l.addStretch()
        tip = QLabel("Sleep → verplaatsen\nR → roteren\n"
                     "Del → verwijderen\nEsc → annuleer\n\n"
                     "🔗 Koppelen:\n"
                     "  klik A → klik B\n"
                     "  klik A zelf → ontkoppel\n"
                     "  schakelaar→schakelaar\n"
                     "  schakelaar→relaisspoel\n\n"
                     "⊕ Voeding + ⏚ Massa\nnodig voor simulatie")
        tip.setStyleSheet(f"color:{C_MUTED}; font-size:10px; font-family:'Courier New';")
        p1l.addWidget(tip)
        self.zij_stack.addWidget(p1)

        # ── Zijbalk p2: Examen ────────────────
        p2 = QWidget(); p2l = QVBoxLayout(p2)
        p2l.setContentsMargins(0, 0, 0, 0); p2l.setSpacing(4)
        p2l.addWidget(self._sec("EXAMEN VOORBEREIDEN"))

        k_gpio2 = QPushButton("⚙  GPIO koppeling")
        k_gpio2.setStyleSheet(_knop_stijl(C_PEACH))
        k_gpio2.clicked.connect(self._gpio_config)
        p2l.addWidget(k_gpio2)

        k_str2 = QPushButton("✕  Storingen instellen")
        k_str2.setStyleSheet(_knop_stijl(C_RED))
        k_str2.clicked.connect(self._storing_config)
        p2l.addWidget(k_str2)

        p2l.addWidget(self._lijn())
        p2l.addWidget(self._sec("TIJDSLIMIET"))

        tijd_rij = QHBoxLayout()
        self.exam_spin = QSpinBox()
        self.exam_spin.setRange(1, 180)
        self.exam_spin.setValue(10)
        self.exam_spin.setSuffix("  min")
        self.exam_spin.setStyleSheet(
            f"background:{C_BG}; color:{C_TEXT}; border:1px solid {C_BORDER};"
            f"border-radius:4px; padding:4px; font-family:'Courier New'; font-size:12px;")
        tijd_rij.addWidget(self.exam_spin)
        tijd_rij.addStretch()
        p2l.addLayout(tijd_rij)

        p2l.addWidget(self._lijn())

        self.start_examen_knop = QPushButton("▶  Start Examen")
        self.start_examen_knop.setStyleSheet(_knop_stijl(C_GREEN))
        self.start_examen_knop.clicked.connect(self._start_examen)
        p2l.addWidget(self.start_examen_knop)

        # Timer + stop (alleen zichtbaar tijdens examen)
        self.exam_sidebar_timer = QLabel("00:00")
        self.exam_sidebar_timer.setAlignment(Qt.AlignCenter)
        self.exam_sidebar_timer.setStyleSheet(
            f"color:{C_GREEN}; font-family:'Courier New'; font-size:28px;"
            f"font-weight:bold; padding:6px 0;")
        self.exam_sidebar_timer.setVisible(False)
        p2l.addWidget(self.exam_sidebar_timer)

        self.stop_examen_knop = QPushButton("■  Stop Examen")
        self.stop_examen_knop.setStyleSheet(_knop_stijl(C_RED))
        self.stop_examen_knop.clicked.connect(self._stop_examen_clicked)
        self.stop_examen_knop.setVisible(False)
        p2l.addWidget(self.stop_examen_knop)

        p2l.addStretch()
        tip2 = QLabel(
            "Werkwijze:\n"
            "1. Bouw circuit (Bewerken)\n"
            "2. Koppel GPIO-pinnen\n"
            "3. Stel storingen in\n"
            "4. Kies tijdslimiet\n"
            "5. Klik Start Examen\n\n"
            "De monteur ziet geen\nvisuele aanwijzingen\nover defecte onderdelen."
        )
        tip2.setStyleSheet(f"color:{C_MUTED}; font-size:10px; font-family:'Courier New';")
        p2l.addWidget(tip2)
        self.zij_stack.addWidget(p2)

        # Status
        self.status = QLabel("Geen circuit geladen")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            f"color:{C_MUTED}; font-size:10px; font-family:'Courier New'; padding:4px;")
        zij_l.addWidget(self.status)

        # ── Rechterpaneel ─────────────────────
        rechts = QWidget(); rechts.setStyleSheet(f"background-color:{C_BG};")
        rl = QVBoxLayout(rechts); rl.setContentsMargins(0, 0, 0, 0); rl.setSpacing(0)

        # Titelbalk + stop-sim knop
        titel_frame = QFrame()
        titel_frame.setFixedHeight(42)
        titel_frame.setStyleSheet(
            f"background-color:{C_BG}; border-bottom:1px solid {C_BORDER};")
        tf_l = QHBoxLayout(titel_frame)
        tf_l.setContentsMargins(12, 0, 8, 0)

        self.titel = QLabel("Selecteer een circuit")
        self.titel.setStyleSheet(
            f"color:{C_BLUE}; font-size:14px; font-weight:bold; font-family:'Courier New';")
        tf_l.addWidget(self.titel, stretch=1)

        self.stop_sim_knop = QPushButton("■  Stop simulatie")
        self.stop_sim_knop.setVisible(False)
        self.stop_sim_knop.setStyleSheet(
            f"background:{C_RED}; color:{C_SIDE}; font-weight:bold; "
            f"font-family:'Courier New'; border:none; border-radius:4px; padding:4px 10px;")
        self.stop_sim_knop.clicked.connect(self._stop_sim)
        tf_l.addWidget(self.stop_sim_knop)

        # Examentimer in titelbalk (zichtbaar tijdens examen)
        self.examen_timer_lbl = QLabel("00:00")
        self.examen_timer_lbl.setVisible(False)
        self.examen_timer_lbl.setStyleSheet(
            f"color:{C_GREEN}; font-family:'Courier New'; font-size:20px;"
            f"font-weight:bold; padding:0 10px; letter-spacing:2px;")
        tf_l.addWidget(self.examen_timer_lbl)

        self.storing_knop = QPushButton("✕  Storingen")
        self.storing_knop.setVisible(False)
        self.storing_knop.setStyleSheet(
            f"background:{C_RED}; color:{C_SIDE}; font-weight:bold; "
            f"font-family:'Courier New'; border:none; border-radius:4px; padding:4px 10px;")
        self.storing_knop.clicked.connect(self._storing_config)
        tf_l.addWidget(self.storing_knop)

        self.gpio_knop = QPushButton("⚙  GPIO")
        self.gpio_knop.setVisible(False)
        self.gpio_knop.setStyleSheet(
            f"background:{C_PEACH}; color:{C_SIDE}; font-weight:bold; "
            f"font-family:'Courier New'; border:none; border-radius:4px; padding:4px 10px;")
        self.gpio_knop.clicked.connect(self._gpio_config)
        tf_l.addWidget(self.gpio_knop)

        rl.addWidget(titel_frame)

        # Canvas in scrollbaar gebied — tekenruimte is groter dan scherm
        self.canvas = CircuitCanvas()
        self.canvas.setMinimumSize(3000, 2400)   # grote virtuele canvas

        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)         # canvas behoudt eigen maat
        scroll.setStyleSheet(
            f"border:none; background:{C_BG};"
            f"QScrollBar:vertical   {{ background:{C_BORDER}; width:12px; }}"
            f"QScrollBar:horizontal {{ background:{C_BORDER}; height:12px; }}"
            f"QScrollBar::handle:vertical, QScrollBar::handle:horizontal"
            f"  {{ background:{C_MUTED}; border-radius:4px; min-height:20px; }}")
        rl.addWidget(scroll)

        # ── GPIO Monitor paneel (onderaan, verborgen tot sim start) ─
        self.gpio_monitor = GPIOMonitorPanel(
            koffer          = self.canvas.koffer,
            on_mock_toggle  = self._mock_toggle,
        )
        self.gpio_monitor.setVisible(False)
        rl.addWidget(self.gpio_monitor)

        hoofd.addWidget(zij); hoofd.addWidget(rechts)

        self.monteur = None   # monteursvenster, door main.py gekoppeld

        # Examentimer (MainWindow beheert de countdown)
        self._exam_timer = QTimer(self)
        self._exam_timer.setInterval(1000)
        self._exam_timer.timeout.connect(self._examen_tick)

        # Standaard gereedschap
        self._sel_tool(TOOL_SELECT)

    # ── Helpers ───────────────────────────────

    def _sec(self, t):
        l = QLabel(t)
        l.setStyleSheet(
            f"color:{C_MUTED}; font-size:10px; font-weight:bold;"
            f"font-family:'Courier New'; letter-spacing:1px; margin-top:6px;")
        return l

    def _lijn(self):
        l = QFrame(); l.setFrameShape(QFrame.HLine)
        l.setStyleSheet(f"color:{C_BORDER};"); return l

    # ── Modus ─────────────────────────────────

    def _modus(self, m):
        # Blokkeer moduswisseling tijdens actief examen
        if self.canvas.exam_active:
            QMessageBox.warning(self, "Examen actief",
                "Stop het examen eerst via '■ Stop Examen'.")
            self.kb.setChecked(False)
            self.ke.setChecked(False)
            self.kx.setChecked(True)
            return

        bekijk = m == "bekijk"
        bewerk = m == "bewerk"
        examen = m == "examen"
        self.kb.setChecked(bekijk)
        self.ke.setChecked(bewerk)
        self.kx.setChecked(examen)
        self.zij_stack.setCurrentIndex(0 if bekijk else (1 if bewerk else 2))

        if bekijk:
            self.canvas.set_mode("view")
            self.stop_sim_knop.setVisible(False)
            self.storing_knop.setVisible(False)
            self.gpio_knop.setVisible(False)
            self.gpio_monitor.setVisible(False)
            self.canvas.setFocus()
        elif bewerk:
            self.canvas.set_mode("edit")
            self.stop_sim_knop.setVisible(False)
            self.storing_knop.setVisible(True)
            self.gpio_knop.setVisible(False)
            self.canvas.setFocus()
        elif examen:
            # Schakel naar view-modus zodat de instructeur niets per ongeluk wijzigt
            self.canvas.set_mode("view")
            self.stop_sim_knop.setVisible(False)
            self.storing_knop.setVisible(False)
            self.gpio_knop.setVisible(False)
            # Sync tijdspinner met opgeslagen waarde in canvas
            self.exam_spin.setValue(self.canvas.exam_time_minutes)
            self.canvas.setFocus()

    # ── Viewer callbacks ──────────────────────

    def _circuit_geladen(self, data: dict, naam: str):
        self.canvas.load_circuit(data)
        self.canvas.set_mode("view")
        self.stop_sim_knop.setVisible(False)
        self.storing_knop.setVisible(False)
        self.gpio_knop.setVisible(False)
        self.gpio_monitor.setVisible(False)
        self.titel.setText(f"  {naam}")
        self.status.setText(f"Geladen: {naam}")
        # Haal een blijven staande "Einde examen" van het monteursscherm.
        if self.monteur:
            self.monteur.wachtstand()

    def _start_sim(self):
        self.canvas.set_mode("sim")
        self.stop_sim_knop.setVisible(True)
        self.storing_knop.setVisible(True)
        self.gpio_knop.setVisible(True)
        self.examen_timer_lbl.setVisible(False)   # geen examentimer in gewone sim
        self.gpio_monitor.setVisible(True)
        self.gpio_monitor.refresh_layout(self.canvas.components)
        self.gpio_monitor.update_states(self.canvas.components)
        self.titel.setText(f"  ▶  {self.titel.text().strip()} — SIMULATIE")
        gpio_txt = "Hardware RPi" if ON_RPI else "MockGPIO"
        self.status.setText(
            f"Simulatie actief  [{gpio_txt}]\n"
            "⚙ GPIO = pin-koppelingen instellen")
        self.canvas.setFocus()
        # Koppel canvas poll-callback aan monitor update
        self.canvas._on_gpio_update = self._on_gpio_update

    def _stop_sim(self):
        self.canvas.set_mode("view")
        self.stop_sim_knop.setVisible(False)
        self.storing_knop.setVisible(False)
        self.gpio_knop.setVisible(False)
        self.gpio_monitor.setVisible(False)
        naam = self.titel.text().replace("  ▶  ", "  ").replace(" — SIMULATIE", "")
        self.titel.setText(naam)
        self.status.setText("Simulatie gestopt")

    def _storing_config(self):
        """Open storingen-configuratiedialoog."""
        self.canvas.open_fault_dialog()

    def _gpio_config(self):
        """Open GPIO-configuratiedialoog en ververs de monitor erna."""
        self.canvas.open_gpio_dialog()
        self.gpio_monitor.refresh_layout(self.canvas.components)
        self.gpio_monitor.update_states(self.canvas.components)

    def _on_gpio_update(self):
        """Callback vanuit de GPIO-poll: ververs de monitor."""
        self.gpio_monitor.update_states(self.canvas.components)

    def _mock_toggle(self, kanaal: str):
        """Zet zonder hardware een knop om, voor testdoeleinden."""
        if self.canvas.koffer:
            self.canvas.koffer.mock_toggle(kanaal_index(kanaal))
        self.gpio_monitor.update_states(self.canvas.components)

    # ── Examen ────────────────────────────────

    def _start_examen(self):
        """Start het examen: sim-modus aan, storingen verborgen, timer start."""
        if not self.canvas.components:
            QMessageBox.warning(self, "Examen starten",
                "Er is geen circuit geladen.\n"
                "Bouw eerst een schakeling in de Bewerken-modus.")
            return

        minuten = self.exam_spin.value()
        self.canvas.exam_time_minutes = minuten
        totaal = minuten * 60

        # Stel canvas-toestand in
        self.canvas.exam_total_seconds = totaal
        self.canvas.exam_seconds_left  = totaal
        self.canvas.set_mode("sim")
        self.canvas.exam_active = True

        # Koppel GPIO-monitor (niet zichtbaar in examen)
        self.gpio_monitor.setVisible(False)
        self.gpio_knop.setVisible(False)

        # Zet de schakeling op het monteursscherm. Dit gebeurt bewust één keer:
        # de monteur krijgt een statische tekening van de opgave.
        if self.monteur:
            self.monteur.start_examen(self.canvas.components,
                                      self.canvas.wires, totaal)

        # Start countdown
        self._exam_timer.start(1000)

        # UI bijwerken
        self._update_examen_ui(running=True)
        self.titel.setText(
            f"  ▶ EXAMEN  —  {self.canvas.exam_time_minutes} minuten  —  "
            + self.titel.text().strip()
        )
        self.canvas.setFocus()

    def _stop_examen_clicked(self):
        """Stopknop ingedrukt: bevestig en onthul storingen."""
        antwoord = QMessageBox.question(
            self, "Examen stoppen",
            "Wilt u het examen stoppen?\n\nNa het stoppen worden de ingestelde storingen onthuld.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if antwoord == QMessageBox.Yes:
            self._stop_examen(reveal=True)

    def _stop_examen(self, reveal: bool = True):
        """Beëindig examen, stop timer, herstel UI."""
        self._exam_timer.stop()
        elapsed = self.canvas.exam_total_seconds - self.canvas.exam_seconds_left
        self.canvas.exam_active = False
        self.canvas.set_mode("view")
        self._update_examen_ui(running=False)

        # Het monteursscherm toont "Einde examen" – ook als de instructeur
        # handmatig stopt. De onthulling hieronder blijft op dít scherm.
        if self.monteur:
            self.monteur.einde_examen()

        # Titelbalk opschonen
        naam = self.titel.text()
        if "▶ EXAMEN" in naam:
            # Haal de originele naam er achter vandaan
            try:
                origineel = naam.split("—")[-1].strip()
            except Exception:
                origineel = ""
            self.titel.setText(f"  {origineel}" if origineel else "  Selecteer een circuit")

        if reveal:
            defecten = [
                f"{c.label or c.type}  [{TOOL_LABELS.get(c.type, c.type)}]"
                for c in self.canvas.components
                if getattr(c, 'defect', False)
            ]
            mins_v = elapsed // 60
            secs_v = elapsed % 60
            tijd_txt = f"{mins_v:02d}:{secs_v:02d}"

            if defecten:
                bericht = (
                    f"Examen beëindigd  –  gebruikte tijd: {tijd_txt}\n\n"
                    "Defecte componenten:\n"
                    + "\n".join(f"  •  {d}" for d in defecten)
                )
            else:
                bericht = (
                    f"Examen beëindigd  –  gebruikte tijd: {tijd_txt}\n\n"
                    "Er waren geen defecte componenten ingesteld."
                )
            QMessageBox.information(self, "Examen resultaat", bericht)

    def _examen_tick(self):
        """Elke seconde: timer aftellen en canvas hertekenen."""
        self.canvas.exam_seconds_left -= 1
        self.canvas.update()

        if self.canvas.exam_seconds_left <= 0:
            self.canvas.exam_seconds_left = 0
            self._exam_timer.stop()
            # Eerst het monteursscherm bijwerken, dan pas de dialoog: die
            # blokkeert, en de monteur zou anders naar een stilstaande
            # timer op 00:00 blijven kijken.
            if self.monteur:
                self.monteur.einde_examen()
                QApplication.processEvents()
            QMessageBox.warning(
                self, "Tijd is om!",
                "De examentijd is verstreken.\n\nHet examen wordt nu beëindigd."
            )
            self._stop_examen(reveal=True)
        else:
            self._update_examen_timer_display()
            if self.monteur:
                self.monteur.update_tijd(self.canvas.exam_seconds_left)

    def _update_examen_ui(self, running: bool):
        """Schakel tussen setup-weergave en lopende-examen-weergave."""
        self.start_examen_knop.setVisible(not running)
        self.exam_spin.setEnabled(not running)
        self.stop_examen_knop.setVisible(running)
        self.exam_sidebar_timer.setVisible(running)
        self.examen_timer_lbl.setVisible(running)
        if not running:
            self.examen_timer_lbl.setText("00:00")
            self.exam_sidebar_timer.setText("00:00")
        else:
            self._update_examen_timer_display()

    def _update_examen_timer_display(self):
        """Ververs de timer-weergave in titelbalk en sidebar."""
        s = self.canvas.exam_seconds_left
        t = self.canvas.exam_total_seconds if self.canvas.exam_total_seconds > 0 else 1
        pct = s / t
        kleur = C_GREEN if pct > 0.5 else (C_YELLOW if pct > 0.2 else C_RED)

        txt = f"{s // 60:02d}:{s % 60:02d}"

        # Titelbalk label
        self.examen_timer_lbl.setText(txt)
        self.examen_timer_lbl.setStyleSheet(
            f"color:{kleur}; font-family:'Courier New'; font-size:20px;"
            f"font-weight:bold; padding:0 10px; letter-spacing:2px;")

        # Sidebar label
        self.exam_sidebar_timer.setText(txt)
        self.exam_sidebar_timer.setStyleSheet(
            f"color:{kleur}; font-family:'Courier New'; font-size:28px;"
            f"font-weight:bold; padding:6px 0;")

    # ── Editor acties ─────────────────────────

    def _sel_tool(self, tool):
        for t, k in self.tknoppen.items(): k.setChecked(t == tool)
        self.canvas.set_tool(tool)
        self.status.setText(f"Gereedschap:\n{TOOL_LABELS[tool]}")
        self.canvas.setFocus()

    def _nieuw(self):
        if QMessageBox.question(self, "Nieuw", "Huidig circuit wissen?",
                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.canvas.leegmaken()
            self.canvas.set_mode("edit")
            self.titel.setText("  ✏  Nieuw circuit")

    def _opslaan(self):
        naam, ok = QInputDialog.getText(self, "Opslaan", "Naam van de schakeling:")
        if not ok or not naam.strip():
            return
        # Sla op in de circuits-map (ook zichtbaar in viewer)
        DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
        pad, _ = QFileDialog.getSaveFileName(
            self, "Opslaan als",
            str(DEFAULT_DIR / f"{naam.strip()}.json"),
            "JSON (*.json)")
        if not pad:
            return
        data = self.canvas.naar_dict(); data["naam"] = naam.strip()
        with open(pad, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.titel.setText(f"  ✏  {naam.strip()} (opgeslagen)")
        self.file_paneel.ververs()   # ververs de bestandslijst
        QMessageBox.information(self, "Opgeslagen", f"Opgeslagen als:\n{pad}")

    def _laden(self):
        pad, _ = QFileDialog.getOpenFileName(
            self, "Laden", str(DEFAULT_DIR), "JSON (*.json)")
        if not pad:
            return
        try:
            with open(pad, encoding="utf-8") as f:
                data = json.load(f)
            self.canvas.load_circuit(data)
            self.canvas.set_mode("edit")
            naam = data.get("naam", Path(pad).stem)
            self.titel.setText(f"  ✏  {naam}")
            self._modus("bewerk")
        except Exception as e:
            QMessageBox.critical(self, "Fout", f"Kan circuit niet laden:\n{e}")

    def keyPressEvent(self, event):
        """F11 wisselt fullscreen – ontsnappingsroute op de Raspberry Pi."""
        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """GPIO-pins vrijgeven bij afsluiten — alle pins naar LOW."""
        if self.canvas.exam_active:
            self._exam_timer.stop()
            self.canvas.exam_active = False
        if self.canvas.koffer:
            self.canvas.koffer.cleanup()
        if self.canvas.gpio_mgr:
            self.canvas.gpio_mgr.cleanup()
        self.canvas._gpio_timer.stop()
        # Sluit het monteursvenster mee, anders blijft de app draaien.
        if self.monteur:
            self.monteur.close()
        event.accept()


# ═══════════════════════════════════════════════
