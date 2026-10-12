"""
koffer_dac.py - Analoge spanningsuitgangen U1 t/m U8 op de DAC-printen.
RET N.V. | Said Keteldijk (1045604)
"""

from typing import Dict

from constants import SPANNING_MAX

SPI_BUS = 0
SPI_CS = 1
SPI_SPEED = 1_000_000
SPI_MODE = 1

VFS = 2.5
BOOSTER = 19.2
DAC_MAX = 2.5

ADRES_SPANNING = {1: 0b01, 2: 0b10}

try:
    import spidev
    DAC_SPI_AANWEZIG = True
except ImportError:
    DAC_SPI_AANWEZIG = False


def klem_naar_dac(index: int):
    """Klemindex 0..7 naar (adres van de DAC, kanaalnummer 0..3)."""
    if not 0 <= index <= 7:
        return None
    print_nr = 1 if index < 4 else 2
    return ADRES_SPANNING[print_nr], index % 4


def volt_naar_code(volt: float) -> int:
    volt = max(0.0, min(SPANNING_MAX, volt))
    dac_volt = min(volt / BOOSTER, DAC_MAX)
    return round(dac_volt / VFS * 0xFFFF)


class KofferDAC:
    """
    De acht spanningsklemmen U1 t/m U8, verdeeld over twee DAC-printen.

    U1 t/m U4 zitten op de spannings-DAC van print 1 (adres 01), U5 t/m U8 op
    die van print 2 (adres 10). Beide printen delen CE1 en draaien in SPI-mode
    1. De stroomlussen blijven hier buiten; die worden niet aangestuurd.

    De DAC8564 heeft geen data-uitgang, dus er is geen manier om te
    controleren of de print aangesloten is. Zonder print gebeurt er stil
    niets; de fout komt pas aan het licht bij het meten.
    """

    def __init__(self):
        self.spi = None
        self.actief = False
        self.fout = ""
        self._waarden: Dict[int, float] = {i: 0.0 for i in range(8)}

    def init(self) -> bool:
        self.fout = ""
        self._waarden = {i: 0.0 for i in range(8)}

        if not DAC_SPI_AANWEZIG:
            self.actief = True
            print("[DAC] spidev niet gevonden - MockDAC actief (Windows/Mac)")
            return True

        try:
            self.spi = spidev.SpiDev()
            self.spi.open(SPI_BUS, SPI_CS)
            self.spi.max_speed_hz = SPI_SPEED
            self.spi.mode = SPI_MODE
        except Exception as e:
            self.fout = f"DAC-print niet te openen op CE{SPI_CS}: {e}"
            self.actief = False
            print(f"[DAC] {self.fout}")
            return False

        self.actief = True
        self.alles_uit()
        print(f"[DAC] CE{SPI_CS} mode {SPI_MODE}: U1-U8 op 0 V "
              "(aanwezigheid van de print is niet te controleren)")
        return True

    def _schrijf_kanaal(self, index: int, volt: float):
        doel = klem_naar_dac(index)
        if doel is None:
            return
        adres, kanaal = doel
        code = volt_naar_code(volt)
        if self.spi is None:
            return
        byte0 = (adres << 6) | (1 << 4) | ((kanaal & 0x03) << 1)
        self.spi.xfer2([byte0, (code >> 8) & 0xFF, code & 0xFF])

    def schrijf(self, waarden: Dict[int, float]):
        """Zet de klemmen die in waarden staan; de rest gaat naar 0 V."""
        if not self.actief:
            return
        for i in range(8):
            volt = max(0.0, min(SPANNING_MAX, float(waarden.get(i, 0.0))))
            if abs(volt - self._waarden[i]) < 0.01:
                continue
            self._schrijf_kanaal(i, volt)
            self._waarden[i] = volt

    def standen(self) -> Dict[int, float]:
        return dict(self._waarden)

    def alles_uit(self):
        if not self.actief:
            return
        for i in range(8):
            self._schrijf_kanaal(i, 0.0)
            self._waarden[i] = 0.0

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
        print("[DAC] U1-U8 op 0 V, SPI gesloten")
