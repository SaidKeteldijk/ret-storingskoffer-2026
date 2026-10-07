"""
models.py – Component, Wire dataklassen + hulpfuncties.
RET N.V. | Said Keteldijk (1045604)
"""

import re

from dataclasses import dataclass, asdict
from typing import List, Tuple

from constants import (
    CONN,
    CONTACTS_PER_TYPE,
    FOUR_TERMINAL,
    LABEL_PREFIX,
    SINGLE_TERMINAL,
    THREE_TERMINAL,
)


@dataclass
class Component:
    type:          str
    col:           int
    row:           int
    label:         str = ""
    rotation:      int = 0
    contact_start: int = 1
    manual_contact_start: bool = False
    gpio_pin:      int = -1
    gpio_dir:      str = "IN"
    defect:        bool = False
    manual_label:  bool = False
    kanaal:        str = ""


@dataclass
class Wire:
    c1: int; r1: int
    c2: int; r2: int


def renumber_contacts(components: List["Component"]):
    """Herbereken contact_start en respecteer handmatig vastgezette startnummers."""
    locked_ranges = []
    for comp in components:
        n = CONTACTS_PER_TYPE.get(comp.type, 2)
        if n > 0 and comp.manual_contact_start:
            start = max(1, comp.contact_start)
            comp.contact_start = start
            locked_ranges.append((start, start + n - 1, comp))

    teller = 1
    for comp in components:
        n = CONTACTS_PER_TYPE.get(comp.type, 2)
        if n <= 0:
            comp.contact_start = 0
            continue

        if comp.manual_contact_start:
            teller = max(teller, comp.contact_start + n)
            continue

        start = max(1, teller)
        while True:
            overlap = next(
                (
                    eind
                    for begin, eind, other in locked_ranges
                    if other is not comp and not (start + n - 1 < begin or start > eind)
                ),
                None,
            )
            if overlap is None:
                break
            start = overlap + 1

        comp.contact_start = start
        teller = start + n


def can_use_contact_start(components: List["Component"], target: "Component", start: int) -> bool:
    n = CONTACTS_PER_TYPE.get(target.type, 2)
    if n <= 0:
        return start == 0
    if start < 1:
        return False

    target_begin = start
    target_end = start + n - 1

    for comp in components:
        if comp is target or not comp.manual_contact_start:
            continue
        other_n = CONTACTS_PER_TYPE.get(comp.type, 2)
        if other_n <= 0:
            continue
        other_begin = comp.contact_start
        other_end = comp.contact_start + other_n - 1
        if not (target_end < other_begin or target_begin > other_end):
            return False

    return True


def renumber_auto_labels(components: List["Component"]):
    """
    Hernummer alleen standaard auto-labels zoals S1/K2/H3.
    Aangepaste labels blijven onaangeraakt.
    """
    counters = {}

    # Labels die de gebruiker zelf heeft gezet blijven staan. Hun nummers
    # worden overgeslagen zodat er geen dubbele labels ontstaan.
    vast = {}
    for comp in components:
        if comp.manual_label and comp.label:
            vast.setdefault(comp.type, set()).add(comp.label)

    for comp in components:
        prefix = LABEL_PREFIX.get(comp.type)
        if not prefix:
            continue

        if comp.manual_label:
            continue

        bezet  = vast.get(comp.type, set())
        nummer = counters.get(comp.type, 0) + 1
        while f"{prefix}{nummer}" in bezet:
            nummer += 1
        counters[comp.type] = nummer

        if re.fullmatch(rf"{re.escape(prefix)}\d+", comp.label or ""):
            comp.label = f"{prefix}{nummer}"


def comp_connections(comp: "Component") -> List[Tuple[int, int]]:
    """
    Aansluitpunten in rastercoodinaten.
    SINGLE → 1 pt | standaard → 2 pt | FOUR → 4 pt | THREE(SPDT) → 3 pt
    """
    c, r = comp.col, comp.row

    if comp.type in SINGLE_TERMINAL:
        return [(c, r)]

    if comp.type in THREE_TERMINAL:
        # Rotatiematrix consistent met QPainter.rotate()
        rot = comp.rotation % 360
        if rot == 0:   return [(c-1,r), (c+1,r-1), (c+1,r+1)]
        elif rot == 90: return [(c,r+1), (c-1,r-1), (c+1,r-1)]
        elif rot == 180: return [(c+1,r), (c-1,r+1), (c-1,r-1)]
        else:           return [(c,r-1), (c+1,r+1), (c-1,r+1)]

    if comp.type in FOUR_TERMINAL:
        if comp.rotation % 180 == 0:
            return [(c-1,r-1),(c+1,r-1),(c-1,r+1),(c+1,r+1)]
        else:
            return [(c-1,r-1),(c-1,r+1),(c+1,r-1),(c+1,r+1)]

    if comp.rotation % 180 == 0:
        return [(c-1, r), (c+1, r)]
    else:
        return [(c, r-1), (c, r+1)]
