#!/usr/bin/env python3
"""
digitale-print.py - Een enkele digitale 48V-uitgangskaart, standaard op adres 001.
RET N.V. | Said Keteldijk (1045604)
"""

import sys

import spidev

MCP_ADDR = 0b001
SPI_BUS = 0
SPI_CS = 0
SPI_SPEED = 1_000_000

IODIRA, IODIRB = 0x00, 0x01
IPOLA = 0x02
IOCON = 0x0A
GPIOA, GPIOB = 0x12, 0x13
OLATA, OLATB = 0x14, 0x15
HAEN = 0x08


class Kaart:
    def __init__(self, spi, adres):
        self.spi = spi
        self.adres = adres & 0x07
        self.rust = 1
        self.olat = [0xFF, 0xFF]

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
        return goed

    def lees_latches(self):
        self.olat = [self._lees(OLATA), self._lees(OLATB)]
        return self.olat

    def toestand(self):
        return {
            "iodir": (self._lees(IODIRA), self._lees(IODIRB)),
            "olat": (self._lees(OLATA), self._lees(OLATB)),
            "gpio": (self._lees(GPIOA), self._lees(GPIOB)),
        }

    def latch(self, pin, bit):
        bank, bitnr = (0, pin) if pin < 8 else (1, pin - 8)
        if bit:
            self.olat[bank] |= 1 << bitnr
        else:
            self.olat[bank] &= ~(1 << bitnr)
        self._schrijf(OLATA if bank == 0 else OLATB, self.olat[bank])

    def alle_latches(self, bit):
        waarde = 0xFF if bit else 0x00
        self.olat = [waarde, waarde]
        self._schrijf(OLATA, waarde)
        self._schrijf(OLATB, waarde)

    def alles_uitgang(self):
        self.alle_latches(self.rust)
        self._schrijf(IODIRA, 0x00)
        self._schrijf(IODIRB, 0x00)

    def enkel_uitgang(self, pin):
        self.alle_latches(self.rust)
        masker = [0xFF, 0xFF]
        bank, bitnr = (0, pin) if pin < 8 else (1, pin - 8)
        masker[bank] &= ~(1 << bitnr)
        self._schrijf(IODIRA, masker[0])
        self._schrijf(IODIRB, masker[1])

    def alles_ingang(self):
        self._schrijf(IODIRA, 0xFF)
        self._schrijf(IODIRB, 0xFF)


def toon(kaart):
    t = kaart.toestand()
    for naam, (a, b) in t.items():
        print(f"  {naam.upper():5s} A={a:08b}  B={b:08b}")
    uitgangen = [p for p in range(16)
                 if not (t["iodir"][0] if p < 8 else t["iodir"][1]) & (1 << (p % 8))]
    print(f"  pinnen als uitgang: {uitgangen if uitgangen else '-'}")
    if uitgangen:
        afwijkend = [p for p in uitgangen
                     if bool((t["olat"][0] if p < 8 else t["olat"][1]) & (1 << (p % 8)))
                     != bool(kaart.rust)]
        print(f"  latch afwijkend van rust ({kaart.rust}): "
              f"{afwijkend if afwijkend else '-'}")


def help_tekst(kaart):
    print(f"""
Kaart op adres {kaart.adres:03b}, CE{SPI_CS}.

De polariteit van de uitgangstrap staat nog niet vast. Daarom werkt dit script
met de latchwaarde van de MCP23S17 en niet met 'aan' en 'uit': je zet een bit
en meet zelf wat er op de klem gebeurt.

Stap 1, bepaal de polariteit met 48V aangesloten en de voeding stroombegrensd:
  enkel 0        alleen pin 0 wordt uitgang, de rest blijft ingang
  l 0 0          latch van pin 0 op 0, meet de klem
  l 0 1          latch van pin 0 op 1, meet de klem
  rust 0|1       leg vast welke latchwaarde de uitgang uit zet

Stap 2, daarna pas de hele kaart:
  uitgang        alle 16 pinnen uitgang, latches op de rustwaarde
  l <pin> 0|1    latch van een pin zetten, 0..15
  alles 0|1      alle latches tegelijk
  ingang         alle pinnen terug naar ingang
  status         IODIR, OLAT en GPIO zoals de kaart ze teruggeeft
  help           dit overzicht
  q              stoppen, latches naar de rustwaarde
""")


def main():
    adres = MCP_ADDR
    if len(sys.argv) > 1:
        adres = int(sys.argv[1], 2) if set(sys.argv[1]) <= {"0", "1"} else int(sys.argv[1])

    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_CS)
    spi.max_speed_hz = SPI_SPEED
    spi.mode = 0

    kaart = Kaart(spi, adres)
    try:
        kaart.zet_haen()
        if not kaart.antwoordt():
            print(f"Geen antwoord van een kaart op adres {adres:03b}.")
            print("Controleer de DIP-stand, de 5V-voeding, de SPI-bedrading en")
            print("of de RESET-lijn hoog staat.")
            return 1

        kaart.lees_latches()
        print(f"Kaart op adres {adres:03b} antwoordt. Er is geen reset gegeven,")
        print("dus de knoppen- en lampenprint blijft ongemoeid.")
        toon(kaart)
        help_tekst(kaart)

        while True:
            regel = input("> ").strip().lower()
            if not regel:
                continue
            delen = regel.split()

            if delen[0] == "q":
                break
            if delen[0] in ("help", "h", "?"):
                help_tekst(kaart)
                continue
            if delen[0] == "status":
                toon(kaart)
                continue
            if delen[0] == "uitgang":
                kaart.alles_uitgang()
                print(f"Alle 16 pinnen zijn uitgang, latches op {kaart.rust}.")
                continue
            if delen[0] == "ingang":
                kaart.alles_ingang()
                print("Alle pinnen staan weer als ingang.")
                continue
            if delen[0] == "rust" and len(delen) == 2 and delen[1] in ("0", "1"):
                kaart.rust = int(delen[1])
                print(f"Rustwaarde van de latch staat nu op {kaart.rust}.")
                continue
            if delen[0] == "enkel" and len(delen) == 2 and delen[1].isdigit():
                pin = int(delen[1])
                if not 0 <= pin <= 15:
                    print("Pin moet 0 tot en met 15 zijn.")
                    continue
                kaart.enkel_uitgang(pin)
                print(f"Alleen pin {pin} is uitgang, de overige 15 blijven ingang.")
                continue
            if delen[0] == "alles" and len(delen) == 2 and delen[1] in ("0", "1"):
                kaart.alle_latches(int(delen[1]))
                print(f"Alle latches op {delen[1]}.")
                continue
            if delen[0] == "l" and len(delen) == 3 and delen[1].isdigit() \
                    and delen[2] in ("0", "1"):
                pin = int(delen[1])
                if not 0 <= pin <= 15:
                    print("Pin moet 0 tot en met 15 zijn.")
                    continue
                kaart.latch(pin, int(delen[2]))
                poort = "A" if pin < 8 else "B"
                print(f"Latch van pin {pin} (GPIO{poort}{pin % 8}) op {delen[2]}. "
                      f"OLAT A={kaart.olat[0]:08b} B={kaart.olat[1]:08b}")
                continue

            print("Onbekend commando, typ 'help'.")

    except KeyboardInterrupt:
        print()
    finally:
        try:
            kaart.alle_latches(kaart.rust)
            print(f"Latches op de rustwaarde {kaart.rust} gezet.")
        except Exception:
            pass
        spi.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
