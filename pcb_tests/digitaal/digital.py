#!/usr/bin/env python3
"""
digital.py - Bedient de digitale 48V-uitgangen van deelsysteem 6.
RET N.V. | Said Keteldijk (1045604)
"""

import json
import sys
from pathlib import Path

import spidev
import RPi.GPIO as GPIO

PCB_ADRESSEN = tuple(format(a, "03b") for a in range(1, 8))
RESET_PIN = 25
UITGANGEN_BESTAND = Path(__file__).with_name("uitgangen.json")

IODIRA, IODIRB = 0x00, 0x01
IPOLA = 0x02
IOCON = 0x0A
OLATA, OLATB = 0x14, 0x15
HAEN = 0x08

KLEM_HOOG_BIJ_LATCH = 1


def lees_config() -> tuple:
    try:
        ruw = json.loads(UITGANGEN_BESTAND.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return [], [], {}
    except (OSError, ValueError) as fout:
        print(f"Kan {UITGANGEN_BESTAND.name} niet lezen: {fout}")
        return [], [], {}

    def schoon(lijst):
        return sorted({int(p) for p in lijst or [] if 0 <= int(p) <= 15})

    kaarten = [str(k) for k in ruw.get("kaarten") or []]
    algemeen = schoon(ruw.get("defect_alle_kaarten"))
    per_kaart = {adres: schoon(lijst)
                 for adres, lijst in (ruw.get("defect_per_kaart") or {}).items()}
    return kaarten, algemeen, per_kaart


def bouw_d_nummers(kaarten, algemeen, per_kaart) -> dict:
    nummers = {}
    n = 0
    for adres in kaarten:
        defect = set(algemeen) | set(per_kaart.get(adres, []))
        for pin in range(16):
            if pin not in defect:
                n += 1
                nummers[(adres, pin)] = f"D{n}"
    return nummers


def reset_vrijgeven() -> None:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RESET_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.output(RESET_PIN, GPIO.HIGH)


def latch_voor(hoog: bool) -> int:
    return KLEM_HOOG_BIJ_LATCH if hoog else 1 - KLEM_HOOG_BIJ_LATCH


class MCP23S17:
    def __init__(self, spi: spidev.SpiDev, hw_adres: int):
        self.spi = spi
        self.hw_adres = hw_adres & 0x07
        self._olat = [0x00, 0x00]

    def _schrijf(self, register: int, waarde: int, hw_adres: int = None) -> None:
        adres = self.hw_adres if hw_adres is None else hw_adres
        self.spi.xfer2([0x40 | (adres << 1), register, waarde & 0xFF])

    def _lees(self, register: int) -> int:
        return self.spi.xfer2(
            [0x40 | (self.hw_adres << 1) | 0x01, register, 0x00])[2]

    def zet_haen(self) -> None:
        for adres in range(8):
            self._schrijf(IOCON, HAEN, hw_adres=adres)

    def antwoordt(self) -> bool:
        origineel = self._lees(IPOLA)
        goed = True
        for patroon in (0xA5, 0x5A):
            self._schrijf(IPOLA, patroon)
            if self._lees(IPOLA) != patroon:
                goed = False
                break
        self._schrijf(IPOLA, origineel if goed else 0x00)
        return goed

    def init_als_output(self) -> None:
        waarde = 0xFF if latch_voor(False) else 0x00
        self._olat = [waarde, waarde]
        self._schrijf(OLATA, waarde)
        self._schrijf(OLATB, waarde)
        self._schrijf(IODIRA, 0x00)
        self._schrijf(IODIRB, 0x00)

    @staticmethod
    def _bank_bit(pin: int) -> tuple[int, int]:
        if not 0 <= pin <= 15:
            raise ValueError(f"pin moet 0..15 zijn, kreeg {pin}")
        return (0, pin) if pin < 8 else (1, pin - 8)

    def _zet(self, pin: int, hoog: bool) -> None:
        bank, bit = self._bank_bit(pin)
        if latch_voor(hoog):
            self._olat[bank] |= 1 << bit
        else:
            self._olat[bank] &= ~(1 << bit)
        self._schrijf(OLATA if bank == 0 else OLATB, self._olat[bank])

    def set_hoog(self, pin: int) -> None:
        self._zet(pin, True)

    def set_laag(self, pin: int) -> None:
        self._zet(pin, False)

    def alles(self, hoog: bool, overslaan=()) -> None:
        olat = [0x00, 0x00]
        for pin in range(16):
            bank, bit = self._bank_bit(pin)
            aan = hoog and pin not in overslaan
            if latch_voor(aan):
                olat[bank] |= 1 << bit
        self._olat = olat
        self._schrijf(OLATA, olat[0])
        self._schrijf(OLATB, olat[1])

    def status(self) -> list[bool]:
        olat = [self._lees(OLATA), self._lees(OLATB)]
        self._olat = olat
        return [bool(olat[0 if p < 8 else 1] & (1 << (p % 8))) == bool(latch_voor(True))
                for p in range(16)]


class DigitaleUitgangen:
    def __init__(self, adressen=PCB_ADRESSEN, spi_bus: int = 0, spi_ce: int = 0,
                 spi_hz: int = 1_000_000):
        reset_vrijgeven()
        kaarten, self.defect_algemeen, self.defect_kaart = lees_config()
        self.d_nummers = bouw_d_nummers(kaarten, self.defect_algemeen,
                                        self.defect_kaart)

        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_ce)
        self.spi.max_speed_hz = spi_hz
        self.spi.mode = 0

        self.pcbs: dict[str, MCP23S17] = {}
        self.ontbreekt: list[str] = []
        for adres_bin in adressen:
            mcp = MCP23S17(self.spi, int(adres_bin, 2))
            mcp.zet_haen()
            if mcp.antwoordt():
                mcp.init_als_output()
                self.pcbs[adres_bin] = mcp
            else:
                self.ontbreekt.append(adres_bin)

    def _mcp(self, pcb: str) -> MCP23S17:
        if pcb not in self.pcbs:
            raise ValueError(f"PCB '{pcb}' is niet gevonden, beschikbaar: {list(self.pcbs)}")
        return self.pcbs[pcb]

    def _controleer(self, pcb: str, pin: int) -> None:
        if pin in self.defecte_pinnen(pcb):
            raise ValueError(
                f"pin {pin} van PCB {pcb} werkt niet en wordt niet aangestuurd")

    def set_hoog(self, pcb: str, pin: int) -> None:
        self._mcp(pcb)
        self._controleer(pcb, pin)
        self.pcbs[pcb].set_hoog(pin)

    def set_laag(self, pcb: str, pin: int) -> None:
        self._mcp(pcb)
        self._controleer(pcb, pin)
        self.pcbs[pcb].set_laag(pin)

    def kaart_alles(self, pcb: str, hoog: bool) -> None:
        self._mcp(pcb).alles(hoog, overslaan=self.defecte_pinnen(pcb))

    def alles_aan(self) -> None:
        for pcb, mcp in self.pcbs.items():
            mcp.alles(True, overslaan=self.defecte_pinnen(pcb))

    def alles_uit(self) -> None:
        for mcp in self.pcbs.values():
            mcp.alles(False)

    def d_nummer(self, pcb: str, pin: int) -> str:
        naam = self.d_nummers.get((pcb, pin))
        return f" ({naam})" if naam else ""

    def defecte_pinnen(self, pcb: str) -> list:
        return sorted(set(self.defect_algemeen) | set(self.defect_kaart.get(pcb, [])))

    def toon_status(self) -> None:
        for pcb, mcp in self.pcbs.items():
            actief = [i for i, s in enumerate(mcp.status()) if s]
            kapot = self.defecte_pinnen(pcb)
            regel = f"  PCB {pcb}: 48V op {actief if actief else '-'}"
            if kapot:
                regel += f"   defect: {kapot}"
            print(regel)

    def sluit(self) -> None:
        self.spi.close()


HELP = """
PCB-adres: binair, net als in de scan. Zonder argument wordt 001 t/m 111
afgezocht; 000 is de knoppen- en lampenprint en blijft buiten schot.
Pin: 0..15  (0-7 = GPIOA0-7, 8-15 = GPIOB0-7)

Commando's:
  <pcb> <pin> hoog      zet die uitgang op 48V
  <pcb> <pin> laag      zet die uitgang op 0V
  <pcb> alles hoog      alle 16 uitgangen van die kaart op 48V
  <pcb> alles laag      alle 16 uitgangen van die kaart op 0V
  aan                   alle uitgangen van alle kaarten op 48V
  uit                   alle uitgangen van alle kaarten op 0V
  status                toon welke uitgangen nu actief zijn
  help                  dit overzicht
  exit                  script afsluiten

Voorbeeld:  010 5 hoog     -> PCB "010" (adres 2), pin 5, naar 48V
"""


def main() -> None:
    gevraagd = tuple(sys.argv[1:])
    du = DigitaleUitgangen(gevraagd or PCB_ADRESSEN)

    if not du.pcbs:
        print("Geen enkele kaart antwoordt. Controleer de DIP-standen, de")
        print("5V-voeding en de SPI-bedrading. De RESET-lijn is hoog gezet.")
        du.sluit()
        return

    print(f"Gevonden kaarten: {list(du.pcbs)}")
    if du.defect_algemeen:
        print(f"  pin {du.defect_algemeen} werkt op geen enkele kaart "
              "en wordt niet aangestuurd")
    for pcb in du.pcbs:
        extra = du.defect_kaart.get(pcb, [])
        if extra:
            print(f"  kaart {pcb}: daarnaast pin {extra} defect")
    if du.ontbreekt and gevraagd:
        print(f"Geen kaart op: {du.ontbreekt}")
    klem = "laag" if KLEM_HOOG_BIJ_LATCH == 0 else "hoog"
    print(f"RESET hoog gezet zonder puls. 48V op de klem hoort bij latch {klem}.")
    print("Alle uitgangen staan op 0V.")
    print(HELP)

    try:
        while True:
            regel = input("> ").strip().lower()
            if not regel:
                continue
            if regel in ("exit", "quit"):
                break
            if regel == "help":
                print(HELP)
                continue
            if regel == "status":
                du.toon_status()
                continue
            if regel == "uit":
                du.alles_uit()
                print("Alle uitgangen op 0V.")
                continue
            if regel == "aan":
                du.alles_aan()
                aantal = sum(16 - len(du.defecte_pinnen(pcb)) for pcb in du.pcbs)
                print(f"{aantal} werkende uitgangen op 48V. "
                      "Let op de stroomopname.")
                continue

            delen = regel.split()
            if len(delen) != 3 or delen[2] not in ("hoog", "laag"):
                print("Onbekend commando. Typ 'help' voor het overzicht.")
                continue
            try:
                pcb, pin, stand = delen
                hoog = stand == "hoog"
                if pin == "alles":
                    du.kaart_alles(pcb, hoog)
                    kapot = du.defecte_pinnen(pcb)
                    staart = f"  (behalve {kapot}, werkt niet)" if kapot and hoog else ""
                    print(f"PCB {pcb}, alle 16 uitgangen -> "
                          f"{'48V' if hoog else '0V'}{staart}")
                else:
                    nummer = int(pin)
                    if hoog:
                        du.set_hoog(pcb, nummer)
                    else:
                        du.set_laag(pcb, nummer)
                    print(f"PCB {pcb}, pin {nummer}{du.d_nummer(pcb, nummer)} -> "
                          f"{'48V' if hoog else '0V'}")
            except ValueError as e:
                print(f"Fout: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        du.alles_uit()
        du.sluit()
        print("\nAlle uitgangen op 0V gezet en SPI gesloten. Tot ziens.")


if __name__ == "__main__":
    main()
