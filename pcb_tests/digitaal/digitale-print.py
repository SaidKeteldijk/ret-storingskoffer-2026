#!/usr/bin/env python3
"""
digitale-print.py - De digitale 48V-uitgangskaarten per pin bedienen.
RET N.V. | Said Keteldijk (1045604)
"""

import sys

import spidev
import RPi.GPIO as GPIO

STANDAARD_ADRESSEN = ("001",)
RESET_PIN = 25
SPI_BUS = 0
SPI_CS = 0
SPI_SPEED = 1_000_000

IODIRA, IODIRB = 0x00, 0x01
IPOLA = 0x02
IOCON = 0x0A
OLATA, OLATB = 0x14, 0x15
HAEN = 0x08

KLEM_HOOG_BIJ_LATCH = 0


def reset_vrijgeven():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(RESET_PIN, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.output(RESET_PIN, GPIO.HIGH)


def latch_voor(hoog):
    return KLEM_HOOG_BIJ_LATCH if hoog else 1 - KLEM_HOOG_BIJ_LATCH


class Kaart:
    def __init__(self, spi, adres):
        self.spi = spi
        self.adres = adres & 0x07
        self.olat = [0x00, 0x00]
        self.iodir = [0xFF, 0xFF]

    def _schrijf(self, register, waarde, adres=None):
        opcode = 0x40 | ((self.adres if adres is None else adres) << 1)
        self.spi.xfer2([opcode, register, waarde & 0xFF])

    def _lees(self, register):
        opcode = 0x40 | (self.adres << 1) | 0x01
        return self.spi.xfer2([opcode, register, 0x00])[2]

    def zet_haen(self):
        for adres in range(8):
            self._schrijf(IOCON, HAEN, adres=adres)

    def antwoordt(self):
        origineel = self._lees(IPOLA)
        goed = True
        for patroon in (0xA5, 0x5A):
            self._schrijf(IPOLA, patroon)
            if self._lees(IPOLA) != patroon:
                goed = False
                break
        self._schrijf(IPOLA, origineel if goed else 0x00)
        if goed:
            self.olat = [self._lees(OLATA), self._lees(OLATB)]
            self.iodir = [self._lees(IODIRA), self._lees(IODIRB)]
        return goed

    @staticmethod
    def _bank_bit(pin):
        return (0, pin) if pin < 8 else (1, pin - 8)

    def zet(self, pin, hoog):
        bank, bit = self._bank_bit(pin)
        if latch_voor(hoog):
            self.olat[bank] |= 1 << bit
        else:
            self.olat[bank] &= ~(1 << bit)
        self._schrijf(OLATA if bank == 0 else OLATB, self.olat[bank])
        if self.iodir[bank] & (1 << bit):
            self.iodir[bank] &= ~(1 << bit)
            self._schrijf(IODIRA if bank == 0 else IODIRB, self.iodir[bank])

    def zet_alles(self, hoog):
        waarde = 0xFF if latch_voor(hoog) else 0x00
        self.olat = [waarde, waarde]
        self._schrijf(OLATA, waarde)
        self._schrijf(OLATB, waarde)
        self.iodir = [0x00, 0x00]
        self._schrijf(IODIRA, 0x00)
        self._schrijf(IODIRB, 0x00)

    def uit(self):
        waarde = 0xFF if latch_voor(False) else 0x00
        self.olat = [waarde, waarde]
        self._schrijf(OLATA, waarde)
        self._schrijf(OLATB, waarde)

    def aangestuurd(self):
        return [p for p in range(16)
                if not self.iodir[self._bank_bit(p)[0]] & (1 << self._bank_bit(p)[1])]

    def actieve_pinnen(self):
        pinnen = []
        for pin in self.aangestuurd():
            bank, bit = self._bank_bit(pin)
            if bool(self.olat[bank] & (1 << bit)) == bool(latch_voor(True)):
                pinnen.append(pin)
        return pinnen


HELP = """
Adres: binair, net als in de scan. Pin: 0 tot en met 15, of 'alles'.
Pin 0-7 is GPIOA0-7, pin 8-15 is GPIOB0-7.

  <adres> <pin> hoog      zet die uitgang op 48V       bv.  001 1 hoog
  <adres> <pin> laag      zet die uitgang op 0V        bv.  001 1 laag
  <adres> alles hoog      alle 16 uitgangen van die kaart tegelijk
  status                  toon per kaart welke uitgangen actief zijn
  uit                     alle uitgangen van alle kaarten op 0V
  help                    dit overzicht
  q                       stoppen, alle uitgangen op 0V
"""


def toon_status(kaarten):
    for adres, kaart in kaarten.items():
        actief = kaart.actieve_pinnen()
        gestuurd = kaart.aangestuurd()
        print(f"  kaart {adres}: 48V op {actief if actief else '-'}   "
              f"(aangestuurd: {gestuurd if gestuurd else 'nog niets'})")


def main():
    adressen = sys.argv[1:] or list(STANDAARD_ADRESSEN)
    for adres in adressen:
        if set(adres) > {"0", "1"} or not 1 <= len(adres) <= 3:
            print(f"Ongeldig adres '{adres}', geef het binair op zoals 001.")
            return 1

    reset_vrijgeven()

    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_CS)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0

    kaarten = {}
    try:
        for adres in adressen:
            kaart = Kaart(spi, int(adres, 2))
            kaart.zet_haen()
            if kaart.antwoordt():
                kaarten[adres] = kaart
                print(f"Kaart {adres} gevonden.")
            else:
                print(f"Kaart {adres} antwoordt niet. Controleer de DIP-stand, "
                      "de 5V-voeding en de SPI-bedrading.")

        if not kaarten:
            return 1

        klem = "laag" if KLEM_HOOG_BIJ_LATCH == 0 else "hoog"
        print(f"RESET is hoog gezet zonder puls. 48V hoort bij latch {klem};")
        print("klopt dat niet, pas dan KLEM_HOOG_BIJ_LATCH boven in dit bestand aan.")
        print("De pinnen blijven ingang tot je ze aanstuurt.")
        print(HELP)

        while True:
            regel = input("> ").strip().lower()
            if not regel:
                continue
            delen = regel.split()

            if delen[0] == "q":
                break
            if delen[0] in ("help", "h", "?"):
                print(HELP)
                continue
            if delen[0] == "status":
                toon_status(kaarten)
                continue
            if delen[0] == "uit":
                for kaart in kaarten.values():
                    kaart.uit()
                print("Alle uitgangen op 0V.")
                continue

            if len(delen) != 3 or delen[2] not in ("hoog", "laag"):
                print("Ongeldige invoer, typ 'help'.")
                continue

            adres, pin, stand = delen
            if adres not in kaarten:
                print(f"Kaart {adres} is niet gevonden. Beschikbaar: {list(kaarten)}")
                continue

            hoog = stand == "hoog"
            if pin == "alles":
                kaarten[adres].zet_alles(hoog)
                print(f"Alle 16 uitgangen van kaart {adres} op "
                      f"{'48V' if hoog else '0V'}.")
                continue

            if not pin.isdigit() or not 0 <= int(pin) <= 15:
                print("Pin moet 0 tot en met 15 zijn, of 'alles'.")
                continue

            nummer = int(pin)
            kaarten[adres].zet(nummer, hoog)
            poort = "A" if nummer < 8 else "B"
            print(f"Kaart {adres} pin {nummer} (GPIO{poort}{nummer % 8}) op "
                  f"{'48V' if hoog else '0V'}.")

    except KeyboardInterrupt:
        print()
    finally:
        try:
            for kaart in kaarten.values():
                kaart.uit()
            print("Alle uitgangen op 0V, programma gestopt.")
        except Exception:
            pass
        spi.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
