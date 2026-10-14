"""
koffer_digitaal.py - De digitale 48V-uitgangen D1 t/m D55 op de MCP23S17-kaarten.
RET N.V. | Said Keteldijk (1045604)
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

from koffer_io import reset_vrijgeven

CONFIG = Path(__file__).parent / "pcb_tests" / "digitaal" / "uitgangen.json"

SPI_BUS = 0
SPI_CS = 0
SPI_SPEED = 1_000_000

IODIRA, IODIRB = 0x00, 0x01
IPOLA = 0x02
IOCON = 0x0A
OLATA, OLATB = 0x14, 0x15
HAEN = 0x08

# Gemeten aan de gebouwde kaarten: de uitgangstrap is niet inverterend.
KLEM_HOOG_BIJ_LATCH = 1

try:
    import spidev
    DIG_SPI_AANWEZIG = True
except ImportError:
    DIG_SPI_AANWEZIG = False


def _lees_config() -> Tuple[List[str], set, Dict[str, set]]:
    try:
        ruw = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError) as fout:
        print(f"[DIG] {CONFIG.name} niet te lezen ({fout}); geen uitgangen beschikbaar")
        return [], set(), {}

    def schoon(lijst):
        return {int(p) for p in lijst or [] if 0 <= int(p) <= 15}

    kaarten = [str(k) for k in ruw.get("kaarten") or []]
    algemeen = schoon(ruw.get("defect_alle_kaarten"))
    per_kaart = {k: schoon(v) for k, v in (ruw.get("defect_per_kaart") or {}).items()}
    return kaarten, algemeen, per_kaart


def _bouw_kaart() -> List[Tuple[str, int]]:
    """
    De volgorde van D1 tot en met Dn: per kaart de werkende pinnen oplopend.

    De defecte uitgangen worden overgeslagen, want die zijn op de koffer niet
    doorverbonden. De nummering volgt daardoor de bedrading en niet de
    pinnummers van de MCP23S17.
    """
    kaarten, algemeen, per_kaart = _lees_config()
    plekken = []
    for adres in kaarten:
        defect = algemeen | per_kaart.get(adres, set())
        for pin in range(16):
            if pin not in defect:
                plekken.append((adres, pin))
    return plekken


UITGANG_PLEK = _bouw_kaart()
KOFFER_UITGANGEN = [f"D{i + 1}" for i in range(len(UITGANG_PLEK))]


def is_uitgang(kanaal: str) -> bool:
    return bool(kanaal) and kanaal[0].upper() == "D"


def uitgang_index(kanaal: str) -> int:
    if not is_uitgang(kanaal):
        return -1
    try:
        nummer = int(kanaal[1:])
    except ValueError:
        return -1
    return nummer - 1 if 1 <= nummer <= len(UITGANG_PLEK) else -1


def kanaal_omschrijving(kanaal: str) -> str:
    i = uitgang_index(kanaal)
    if i < 0:
        return kanaal
    adres, pin = UITGANG_PLEK[i]
    return f"{kanaal} (kaart {adres}, pin {pin})"


class KofferDigitaal:
    """
    De digitale 48V-uitgangskaarten op CE0, hardware-adres 001 en hoger.

    Een latch van 1 geeft 48 V op de klem; dat is aan de kaarten gemeten. Er
    wordt geen hardware-reset gegeven, alleen de RESET-lijn hoog gezet: die
    lijn is gedeeld met de knoppen- en lampenprint.
    """

    def __init__(self):
        self.spi = None
        self.actief = False
        self.fout = ""
        self.kaarten: Dict[str, bool] = {}
        self._olat: Dict[str, List[int]] = {}
        self._standen: Dict[int, bool] = {}

    def _schrijf(self, adres: int, register: int, waarde: int):
        self.spi.xfer2([0x40 | (adres << 1), register, waarde & 0xFF])

    def _lees(self, adres: int, register: int) -> int:
        return self.spi.xfer2([0x40 | (adres << 1) | 0x01, register, 0x00])[2]

    def _antwoordt(self, adres: int) -> bool:
        origineel = self._lees(adres, IPOLA)
        goed = True
        for patroon in (0xA5, 0x5A):
            self._schrijf(adres, IPOLA, patroon)
            if self._lees(adres, IPOLA) != patroon:
                goed = False
                break
        self._schrijf(adres, IPOLA, origineel if goed else 0x00)
        return goed

    def init(self) -> bool:
        self.fout = ""
        self.kaarten = {}
        self._olat = {}
        self._standen = {i: False for i in range(len(UITGANG_PLEK))}

        if not UITGANG_PLEK:
            self.fout = "geen uitgangen geconfigureerd"
            self.actief = False
            return False

        if not DIG_SPI_AANWEZIG:
            self.actief = True
            self.kaarten = {a: True for a, _ in UITGANG_PLEK}
            print(f"[DIG] spidev niet gevonden - MockDigitaal actief "
                  f"({len(UITGANG_PLEK)} uitgangen)")
            return True

        reset_vrijgeven()
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(SPI_BUS, SPI_CS)
            self.spi.max_speed_hz = SPI_SPEED
            self.spi.mode = 0
        except Exception as e:
            self.fout = f"SPI niet te openen: {e}"
            self.actief = False
            print(f"[DIG] {self.fout}")
            return False

        adressen = []
        for adres, _ in UITGANG_PLEK:
            if adres not in adressen:
                adressen.append(adres)

        for adres in range(8):
            self._schrijf(adres, IOCON, HAEN)

        uit = 0xFF if KLEM_HOOG_BIJ_LATCH == 0 else 0x00
        for adres in adressen:
            nummer = int(adres, 2)
            if not self._antwoordt(nummer):
                self.kaarten[adres] = False
                continue
            # Eerst de latch op uit, pas daarna de richting op uitgang, zodat
            # er bij het omschakelen geen uitgang kort aanslaat.
            self._schrijf(nummer, OLATA, uit)
            self._schrijf(nummer, OLATB, uit)
            self._schrijf(nummer, IODIRA, 0x00)
            self._schrijf(nummer, IODIRB, 0x00)
            self._olat[adres] = [uit, uit]
            self.kaarten[adres] = True

        self.actief = any(self.kaarten.values())
        gevonden = [a for a, ok in self.kaarten.items() if ok]
        ontbreekt = [a for a, ok in self.kaarten.items() if not ok]
        print(f"[DIG] kaarten {gevonden} klaar, {self.beschikbaar()} uitgangen")
        if ontbreekt:
            print(f"[DIG] geen antwoord van {ontbreekt}; die uitgangen blijven dood")
        if not self.actief:
            self.fout = "geen enkele uitgangskaart antwoordt"
        return self.actief

    def beschikbaar(self) -> int:
        return sum(1 for adres, _ in UITGANG_PLEK if self.kaarten.get(adres))

    def schrijf(self, standen: Dict[int, bool]):
        """Zet de uitgangen die in standen staan; de rest gaat uit."""
        if not self.actief:
            return
        nieuw = {i: bool(standen.get(i, False)) for i in range(len(UITGANG_PLEK))}
        if nieuw == self._standen:
            return
        self._standen = nieuw

        if self.spi is None:
            return

        for adres, banken in self._olat.items():
            opnieuw = [0x00, 0x00]
            for i, (plek_adres, pin) in enumerate(UITGANG_PLEK):
                if plek_adres != adres or not nieuw[i]:
                    continue
                if KLEM_HOOG_BIJ_LATCH:
                    opnieuw[0 if pin < 8 else 1] |= 1 << (pin % 8)
            if KLEM_HOOG_BIJ_LATCH == 0:
                opnieuw = [0xFF & ~opnieuw[0], 0xFF & ~opnieuw[1]]
            nummer = int(adres, 2)
            if opnieuw[0] != banken[0]:
                self._schrijf(nummer, OLATA, opnieuw[0])
            if opnieuw[1] != banken[1]:
                self._schrijf(nummer, OLATB, opnieuw[1])
            self._olat[adres] = opnieuw

    def standen(self) -> Dict[int, bool]:
        return dict(self._standen)

    def alles_uit(self):
        self.schrijf({})

    def cleanup(self):
        try:
            self.alles_uit()
        except Exception:
            pass
        if self.spi is not None:
            try:
                self.spi.close()
            except Exception:
                pass
            self.spi = None
        self.actief = False
        print("[DIG] alle uitgangen uit, SPI gesloten")
