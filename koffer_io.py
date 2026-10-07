"""
koffer_io.py - Knoppen- en lampenprint op de SPI-bus.
RET N.V. | Said Keteldijk (1045604)
"""

from typing import Dict

MCP_ADDR = 0b000
SPI_BUS = 0
SPI_CS = 0
SPI_SPEED = 1_000_000

IODIRA, IODIRB = 0x00, 0x01
IOCON = 0x0A
GPPUA = 0x0C
GPIOA = 0x12
OLATB = 0x15
HAEN = 0x08

try:
    import spidev
    SPI_AANWEZIG = True
    print("[KOFFER] spidev geladen - hardware modus actief")
except ImportError:
    SPI_AANWEZIG = False
    print("[KOFFER] spidev niet gevonden - MockKoffer actief (Windows/Mac)")


def kanaal_index(kanaal: str) -> int:
    """Geeft de index 0..7 van een kanaalnaam als Q3 of S1, of -1."""
    if not kanaal or len(kanaal) < 2:
        return -1
    try:
        nummer = int(kanaal[1:])
    except ValueError:
        return -1
    return nummer - 1 if 1 <= nummer <= 8 else -1


def is_lamp(kanaal: str) -> bool:
    return bool(kanaal) and kanaal[0].upper() == "Q"


def is_knop(kanaal: str) -> bool:
    return bool(kanaal) and kanaal[0].upper() == "S"


class KofferIO:
    """
    Knoppen- en lampenprint op hardware-adres 000.

    Lampen Q1..Q8 op GPB0..GPB7, niet geinverteerd: bit hoog is lamp aan.
    Knoppen S1..S8 op GPA0..GPA7, actief laag met externe pull-up R20.

    Er wordt bewust geen hardware-reset gedaan: de RESET-lijn is gedeeld met
    de digitale 48V-kaarten en zou hun uitgangen laten zweven.
    """

    def __init__(self):
        self.spi = None
        self.actief = False
        self.fout = ""
        self._lampen = 0x00
        self._mock_knoppen = 0xFF

    def _opcode(self, lezen: bool) -> int:
        return 0x40 | ((MCP_ADDR & 0x07) << 1) | (1 if lezen else 0)

    def _schrijf(self, register: int, waarde: int):
        if self.spi is None:
            if register == OLATB:
                self._lampen = waarde & 0xFF
            return
        self.spi.xfer2([self._opcode(False), register, waarde & 0xFF])

    def _lees(self, register: int) -> int:
        if self.spi is None:
            if register == GPIOA:
                return self._mock_knoppen
            if register == OLATB:
                return self._lampen
            if register == IODIRB:
                return 0x00
            return 0xFF
        return self.spi.xfer2([self._opcode(True), register, 0x00])[2]

    def init(self) -> bool:
        """Zet de print klaar. Geeft True terug als dat gelukt is."""
        self.fout = ""
        if SPI_AANWEZIG:
            try:
                self.spi = spidev.SpiDev()
                self.spi.open(SPI_BUS, SPI_CS)
                self.spi.max_speed_hz = SPI_SPEED
                self.spi.mode = 0
            except Exception as e:
                self.spi = None
                self.actief = False
                self.fout = f"SPI openen mislukt: {e}"
                print(f"[KOFFER] {self.fout}")
                return False

        self._schrijf(IOCON, HAEN)
        self._schrijf(OLATB, 0x00)
        self._schrijf(IODIRB, 0x00)
        self._schrijf(IODIRA, 0xFF)
        self._schrijf(GPPUA, 0x00)
        self._lampen = 0x00

        if self._lees(IODIRB) != 0x00:
            self.actief = False
            self.fout = "print op adres 000 reageert niet zoals verwacht"
            print(f"[KOFFER] {self.fout}")
            return False

        self.actief = True
        bron = "hardware" if self.spi is not None else "mock"
        print(f"[KOFFER] print 000 klaar ({bron}): 8 lampen, 8 knoppen")
        return True

    def lees_knoppen(self) -> Dict[int, bool]:
        """Index 0..7 naar ingedrukt. Actief laag, dus omgekeerd gelezen."""
        if not self.actief:
            return {}
        rauw = self._lees(GPIOA)
        return {i: not bool(rauw & (1 << i)) for i in range(8)}

    def schrijf_lampen(self, standen: Dict[int, bool]):
        """Index 0..7 naar aan of uit."""
        if not self.actief:
            return
        masker = 0
        for i in range(8):
            if standen.get(i, False):
                masker |= 1 << i
        if masker != self._lampen:
            self._schrijf(OLATB, masker)
        self._lampen = masker

    def lamp_standen(self) -> Dict[int, bool]:
        return {i: bool(self._lampen & (1 << i)) for i in range(8)}

    def mock_toggle(self, index: int) -> bool:
        """Zet in mockmodus een knop om, voor testen zonder hardware."""
        if SPI_AANWEZIG or not 0 <= index <= 7:
            return False
        self._mock_knoppen ^= 1 << index
        return True

    def cleanup(self):
        """Alle lampen uit en de bus vrijgeven."""
        try:
            self._schrijf(OLATB, 0x00)
        except Exception:
            pass
        self._lampen = 0x00
        if self.spi is not None:
            try:
                self.spi.close()
            except Exception:
                pass
            self.spi = None
        self.actief = False
        print("[KOFFER] lampen uit, SPI gesloten")
