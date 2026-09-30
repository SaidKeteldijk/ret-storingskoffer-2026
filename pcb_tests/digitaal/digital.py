#!/usr/bin/env python3
"""
digital.py - Bedient de digitale 48V-uitgangen van deelsysteem 6.
RET N.V. | Said Keteldijk (1045604)
"""

import sys
import spidev

IODIRA, IODIRB = 0x00, 0x01
GPIOA,  GPIOB  = 0x12, 0x13
OLATA,  OLATB  = 0x14, 0x15

PCB_ADRESSEN = ("001", "010", "011", "100")


class MCP23S17:
    """Een enkele I/O-expander op een vast hardware-adres (A2A1A0)."""

    def __init__(self, spi: spidev.SpiDev, hw_adres: int):
        self.spi = spi
        self.opcode_write = 0x40 | (hw_adres << 1)
        self.opcode_read = self.opcode_write | 0x01
        self._olat = [0xFF, 0xFF]

    def _schrijf(self, register: int, waarde: int) -> None:
        self.spi.xfer2([self.opcode_write, register, waarde & 0xFF])

    def _lees(self, register: int) -> int:
        return self.spi.xfer2([self.opcode_read, register, 0x00])[2]

    def init_als_output(self) -> None:
        """Alle 16 pinnen als output, en meteen alles inactief (48V uit)."""
        self._schrijf(IODIRA, 0x00)
        self._schrijf(IODIRB, 0x00)
        self._olat = [0xFF, 0xFF]
        self._schrijf(OLATA, self._olat[0])
        self._schrijf(OLATB, self._olat[1])

    def _bank_bit(self, pin: int) -> tuple[int, int]:
        """pin 0..15  ->  (bank-index 0=A/1=B, bitpositie 0..7)"""
        if not 0 <= pin <= 15:
            raise ValueError(f"pin moet 0..15 zijn, kreeg {pin}")
        return (0, pin) if pin < 8 else (1, pin - 8)

    def set_hoog(self, pin: int) -> None:
        """Zet de uitgang actief: 48V op de klemmenstrook."""
        bank, bit = self._bank_bit(pin)
        self._olat[bank] &= ~(1 << bit)
        self._schrijf(OLATA if bank == 0 else OLATB, self._olat[bank])

    def set_laag(self, pin: int) -> None:
        """Zet de uitgang inactief: 0V op de klemmenstrook."""
        bank, bit = self._bank_bit(pin)
        self._olat[bank] |= (1 << bit)
        self._schrijf(OLATA if bank == 0 else OLATB, self._olat[bank])

    def alles_laag(self) -> None:
        self._olat = [0xFF, 0xFF]
        self._schrijf(OLATA, self._olat[0])
        self._schrijf(OLATB, self._olat[1])

    def status(self) -> list[bool]:
        """True = uitgang actief (48V), voor pin 0..15, gebaseerd op de cache."""
        return [not bool((self._olat[0] if p < 8 else self._olat[1]) & (1 << (p % 8)))
                for p in range(16)]


class DigitaleUitgangen:
    """Verzamelt de vier PCB's (binair adres 001..100) achter een simpele interface."""

    def __init__(self, spi_bus: int = 0, spi_ce: int = 0, spi_hz: int = 1_000_000):
        self.spi = spidev.SpiDev()
        self.spi.open(spi_bus, spi_ce)
        self.spi.max_speed_hz = spi_hz
        self.spi.mode = 0

        self.pcbs: dict[str, MCP23S17] = {}
        for adres_bin in PCB_ADRESSEN:
            mcp = MCP23S17(self.spi, int(adres_bin, 2))
            mcp.init_als_output()
            self.pcbs[adres_bin] = mcp

    def _mcp(self, pcb: str) -> MCP23S17:
        if pcb not in self.pcbs:
            raise ValueError(f"onbekend PCB-adres '{pcb}', geldig zijn: {list(self.pcbs)}")
        return self.pcbs[pcb]

    def set_hoog(self, pcb: str, pin: int) -> None:
        self._mcp(pcb).set_hoog(pin)

    def set_laag(self, pcb: str, pin: int) -> None:
        self._mcp(pcb).set_laag(pin)

    def alles_uit(self) -> None:
        for mcp in self.pcbs.values():
            mcp.alles_laag()

    def toon_status(self) -> None:
        for pcb, mcp in self.pcbs.items():
            actief = [i for i, s in enumerate(mcp.status()) if s]
            print(f"  PCB {pcb}: actief = {actief if actief else '-'}")

    def sluit(self) -> None:
        self.spi.close()


HELP = """
PCB-adres: binair, net als de scan  ("001", "010", "011", "100")
Pin: 0..15  (0-7 = GPIOA0-7, 8-15 = GPIOB0-7)

Commando's:
  <pcb_binair> <pin> hoog     zet die uitgang op 48V
  <pcb_binair> <pin> laag     zet die uitgang op 0V
  status                       toon welke uitgangen nu actief zijn
  uit                           zet alle uitgangen van alle PCB's op 0V
  help                           dit overzicht
  exit                           script afsluiten

Voorbeeld:  010 5 hoog     -> PCB "010" (adres 2), pin 5, naar 48V
"""


def main() -> None:
    du = DigitaleUitgangen()
    print("Digitale uitgangen geinitialiseerd (PCB 001 t/m 100, alles op 0V).")
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

            delen = regel.split()
            if len(delen) != 3 or delen[2] not in ("hoog", "laag"):
                print("Onbekend commando. Typ 'help' voor het overzicht.")
                continue
            try:
                pcb = delen[0]
                pin = int(delen[1])
                if delen[2] == "hoog":
                    du.set_hoog(pcb, pin)
                    print(f"PCB {pcb}, pin {pin} -> 48V")
                else:
                    du.set_laag(pcb, pin)
                    print(f"PCB {pcb}, pin {pin} -> 0V")
            except ValueError as e:
                print(f"Fout: {e}")
    except KeyboardInterrupt:
        pass
    finally:
        du.alles_uit()
        du.sluit()
        print("\nAlle uitgangen op 0V gezet en SPI gesloten. Tot ziens.")


if __name__ == "__main__":
    sys.exit(main())
