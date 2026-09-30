"""
simulator.py – BFS-gebaseerde elektrische circuit simulator.
RET N.V. | Said Keteldijk (1045604)
"""

from typing import List, Dict, Set, Tuple
from constants import (
    TOOL_SWITCH, TOOL_SW2P_NO, TOOL_SW2P_NC, TOOL_SPDT,
    TOOL_RCOIL, TOOL_RCONT, TOOL_RSPDT, TOOL_MOTOR, TOOL_LAMP, TOOL_POWER, TOOL_GND,
    TOOL_NETLABEL,
    FOUR_TERMINAL, THREE_TERMINAL,
)
from models import Component, Wire, comp_connections

# ═══════════════════════════════════════════════
#  CIRCUIT SIMULATOR
# ═══════════════════════════════════════════════
class CircuitSimulator:
    """
    Vereenvoudigd aan/uit-simulatiemodel.
    Stroomvoering: BFS vanuit Voeding(+V) en Massa(GND) componenten.
    Schakelaar: user-gestuurd (klik om te sluiten/openen).
    Relaiscontact: volgt automatisch de relaisspoel met hetzelfde label.
    """

    def __init__(self):
        self.components:  List[Component]       = []
        self.wires:       List[Wire]             = []
        self.sw_states:   Dict[int, bool]        = {}   # comp_idx → gesloten?
        self.relay_states:Dict[str, bool]        = {}   # spoel label → bekrachtigd?
        self.live_nodes:  Set[Tuple[int, int]]   = set()
        self.gnd_nodes:   Set[Tuple[int, int]]   = set()

    def load(self, components: List[Component], wires: List[Wire]):
        self.components  = components
        self.wires       = wires
        # Alle schakelbare types opnemen in sw_states
        self.sw_states   = {
            i: False for i, c in enumerate(components)
            if c.type in (TOOL_SWITCH, TOOL_SW2P_NO, TOOL_SW2P_NC,
                          TOOL_SPDT, TOOL_RCONT)
        }
        self.relay_states = {}
        self.solve()

    def toggle_switch(self, idx: int):
        if idx in self.sw_states:
            self.sw_states[idx] = not self.sw_states[idx]
            self.solve()

    def set_switch_from_gpio(self, idx: int, state: bool):
        """Stel schakelaar in vanuit een GPIO-input."""
        if self.components[idx].type in (
                TOOL_SWITCH, TOOL_SW2P_NO, TOOL_SW2P_NC,
                TOOL_SPDT, TOOL_RCONT):
            self.sw_states[idx] = state
            self.solve()

    def comp_active_states(self) -> Dict[int, bool]:
        """Geeft voor elk component terug of het actief is (voor GPIO output)."""
        result = {}
        for i in range(len(self.components)):
            result[i] = self.comp_is_active(i)
        return result

    def solve(self):
        """Iteratief oplossen tot stabiele toestand (max 20 stappen)."""
        for _ in range(20):
            old = dict(self.relay_states)
            self._step()
            if self.relay_states == old:
                break

    def _build_adj(self) -> Dict:
        adj: Dict[Tuple, Set] = {}

        def add(p1, p2):
            adj.setdefault(p1, set()).add(p2)
            adj.setdefault(p2, set()).add(p1)

        # ── Draden: voeg een knooppunt toe voor elk rasterpunt op de draad.
        # Dit zorgt dat T-verbindingen correct werken: een draad van A naar B
        # die door punt C loopt, maakt C bereikbaar voor andere draden die
        # op C aansluiten.
        for w in self.wires:
            if w.c1 == w.c2:                        # verticale draad
                c = w.c1
                for r in range(min(w.r1, w.r2), max(w.r1, w.r2)):
                    add((c, r), (c, r + 1))
            elif w.r1 == w.r2:                      # horizontale draad
                r = w.r1
                for c in range(min(w.c1, w.c2), max(w.c1, w.c2)):
                    add((c, r), (c + 1, r))
            else:                                   # schuine draad (edge case)
                add((w.c1, w.r1), (w.c2, w.r2))

        for i, c in enumerate(self.components):
            pts = comp_connections(c)
            if len(pts) < 2:
                continue

            defect = getattr(c, 'defect', False)

            if c.type == TOOL_SWITCH:
                # 1-polig NO: sluit als gesloten. Defect → altijd open.
                if not defect and self.sw_states.get(i, False):
                    add(pts[0], pts[1])

            elif c.type in (TOOL_SW2P_NO, TOOL_SW2P_NC):
                # 2-polig: pts = [p1L, p1R, p2L, p2R]. Defect → altijd open.
                if not defect:
                    p1L, p1R, p2L, p2R = pts[0], pts[1], pts[2], pts[3]
                    gesloten = self.sw_states.get(i, False)
                    nc = (c.type == TOOL_SW2P_NC)
                    actief = gesloten if not nc else not gesloten
                    if actief:
                        add(p1L, p1R)
                        add(p2L, p2R)

            elif c.type == TOOL_SPDT:
                # SPDT: pts = [A (common), B, C]. Defect → vast op B (open).
                if len(pts) >= 3:
                    a, b, cv = pts[0], pts[1], pts[2]
                    if defect:
                        add(a, b)   # vast in standaardpositie B
                    else:
                        positie_c = self.sw_states.get(i, False)
                        if positie_c:
                            add(a, cv)
                        else:
                            add(a, b)

            elif c.type == TOOL_RSPDT:
                # Relaiswisselcontact. Defect → koppeling verbroken, vast op B.
                if len(pts) >= 3:
                    a, b, cv = pts[0], pts[1], pts[2]
                    if defect:
                        add(a, b)   # koppeling spoel↔contact verbroken
                    else:
                        positie_c = self.relay_states.get(c.label, False)
                        if positie_c:
                            add(a, cv)
                        else:
                            add(a, b)

            elif c.type == TOOL_RCOIL:
                # Spoel geleidt stroom ongeacht defect, maar koppeling wordt
                # in _step() geblokkeerd als defect=True.
                add(pts[0], pts[1])

            elif c.type == TOOL_RCONT:
                # Defect → contact sluit nooit (koppeling verbroken).
                if not defect and self.relay_states.get(c.label, False):
                    add(pts[0], pts[1])

            elif c.type in (TOOL_MOTOR, TOOL_LAMP):
                # Defect = onderbroken, zoals een doorgebrande lamp of wikkeling.
                if not defect:
                    add(pts[0], pts[1])

        label_groups: Dict[str, List[Tuple[int, int]]] = {}
        for c in self.components:
            if c.type != TOOL_NETLABEL or not c.label:
                continue
            pts = comp_connections(c)
            if pts:
                label_groups.setdefault(c.label.strip().upper(), []).append(pts[0])

        for nodes in label_groups.values():
            if len(nodes) < 2:
                continue
            basis = nodes[0]
            for node in nodes[1:]:
                add(basis, node)

        return adj

    @staticmethod
    def _bfs(adj: Dict, starts: Set) -> Set:
        visited = set(starts)
        q = list(starts)
        while q:
            n = q.pop(0)
            for nb in adj.get(n, set()):
                if nb not in visited:
                    visited.add(nb)
                    q.append(nb)
        return visited

    def _step(self):
        adj = self._build_adj()

        power_nodes: Set = set()
        gnd_nodes:   Set = set()
        for c in self.components:
            pts = comp_connections(c)
            if not pts:
                continue
            if c.type == TOOL_POWER:
                power_nodes.add(pts[0])
            elif c.type == TOOL_GND:
                gnd_nodes.add(pts[0])

        self.live_nodes = self._bfs(adj, power_nodes)
        self.gnd_nodes  = self._bfs(adj, gnd_nodes)

        for c in self.components:
            if c.type != TOOL_RCOIL:
                continue
            pts = comp_connections(c)
            if len(pts) < 2:
                continue
            p1, p2 = pts
            energized = (
                (p1 in self.live_nodes and p2 in self.gnd_nodes) or
                (p2 in self.live_nodes and p1 in self.gnd_nodes)
            )
            # Defecte spoel: stroom loopt wel, maar koppeling naar
            # relaiscontacten is verbroken → relay_states blijft False.
            if getattr(c, 'defect', False):
                self.relay_states[c.label] = False
            else:
                self.relay_states[c.label] = energized

    # ── Query methoden ────────────────────────

    def wire_is_live(self, w: Wire) -> bool:
        """
        Een draad licht op als minstens één punt erop onder spanning staat.
        Controleert eindpunten EN tussenliggende rasterpunten.
        """
        if w.c1 == w.c2:                            # verticaal
            return any((w.c1, r) in self.live_nodes
                       for r in range(min(w.r1, w.r2), max(w.r1, w.r2) + 1))
        elif w.r1 == w.r2:                          # horizontaal
            return any((c, w.r1) in self.live_nodes
                       for c in range(min(w.c1, w.c2), max(w.c1, w.c2) + 1))
        return (w.c1, w.r1) in self.live_nodes or (w.c2, w.r2) in self.live_nodes

    def comp_is_active(self, idx: int) -> bool:
        if idx >= len(self.components):
            return False
        c = self.components[idx]
        pts = comp_connections(c)
        if len(pts) < 2:
            return False
        if c.type in FOUR_TERMINAL:
            # 2P: actief als minstens één pool stroomvoerend is
            p1L, p1R, p2L, p2R = pts[0], pts[1], pts[2], pts[3]
            pole1 = ((p1L in self.live_nodes and p1R in self.gnd_nodes) or
                     (p1R in self.live_nodes and p1L in self.gnd_nodes))
            pole2 = ((p2L in self.live_nodes and p2R in self.gnd_nodes) or
                     (p2R in self.live_nodes and p2L in self.gnd_nodes))
            return pole1 or pole2
        if c.type in THREE_TERMINAL:
            # SPDT/relaiswisselcontact: actief als het actieve pad stroomvoert
            if len(pts) >= 3:
                a, b, cv = pts[0], pts[1], pts[2]
                if c.type == TOOL_RSPDT:
                    positie_c = self.relay_states.get(c.label, False)
                else:
                    positie_c = self.sw_states.get(idx, False)
                actief_pt = cv if positie_c else b
                return (
                    (a in self.live_nodes and actief_pt in self.gnd_nodes) or
                    (actief_pt in self.live_nodes and a in self.gnd_nodes)
                )
            return False
        # Standaard 2-aansluitpunt
        p1, p2 = pts[0], pts[1]
        return (
            (p1 in self.live_nodes and p2 in self.gnd_nodes) or
            (p2 in self.live_nodes and p1 in self.gnd_nodes)
        )

    def switch_closed(self, idx: int) -> bool:
        return self.sw_states.get(idx, False)

    def contact_closed(self, label: str) -> bool:
        return self.relay_states.get(label, False)

    def coil_energized(self, label: str) -> bool:
        return self.relay_states.get(label, False)


# ═══════════════════════════════════════════════
#  CIRCUIT CANVAS  (edit / view / sim)
