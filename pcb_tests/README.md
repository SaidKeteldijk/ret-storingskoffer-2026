# Losse PCB-testen

Deze map bevat testgereedschap waarmee elke printplaat afzonderlijk getoetst
kan worden, los van het dashboard. Dit hoort bij de unittesten uit hoofdstuk 6
van het projectdocument: elk deelsysteem wordt eerst zelfstandig aan zijn
specificaties getoetst voordat het aan de rest gekoppeld wordt.

De scripts zijn bewust losgekoppeld van de app. Zij importeren niets uit
`canvas.py`, `simulator.py` of `gpio_manager.py`, zodat een printplaat ook
getest kan worden als de app zelf nog niet werkt.

## Indeling

Elke unit heeft een eigen map. Wat voor alle kaarten samen geldt, staat in de
hoofdmap van `pcb_tests`.

| Map | Unit | Deelsysteem |
|-------------------|------------------------------------|-------------|
| `knoppen_lampen/` | De knoppen- en lampenprint | 6 |
| `digitaal/` | De vier digitale 48V-uitgangskaarten | 6 |
| `analoog/` | De DAC-print | 7 |
| hoofdmap | Geldt voor alle kaarten op de bus | - |

| Map | Script | Test |
|-------------------|------------------------------------|--------------------------------------------------|
| hoofdmap | `scan.py` | Zoekt MCP23S17's op CE0, adres 0 t/m 7 |
| hoofdmap | `test_io_board.py` | Ouder testgereedschap, zie waarschuwing hieronder |
| `knoppen_lampen/` | `lightsout.py` | Zet de lampen op de knoppen/lampen-PCB uit |
| `knoppen_lampen/` | `lampen-test.py` | Lampen H1..H8 los aansturen |
| `knoppen_lampen/` | `knoppen-test.py` | Knoppen S1..S8 uitlezen |
| `knoppen_lampen/` | `semi-integratietest-knop-lamp.py` | Knop bedient de bijbehorende lamp |
| `digitaal/` | `digital.py` | De vier 48V-uitgangskaarten per pin bedienen |
| `analoog/` | `dac-tester.py` | De twee DAC8564's van een losse print: 4-20 mA en 0-48 V |
| `analoog/` | `koffer-analoog.py` | De acht klemmen U1-U8 en lussen I1-I8 over beide printen |

De scripts staan los van elkaar en importeren niets uit een andere map, dus je
kunt ze vanuit `pcb_tests` aanroepen of eerst naar de map toe gaan:

```console
python3 knoppen_lampen/lampen-test.py
cd digitaal && python3 digital.py
```

Begin altijd met `scan.py`. Dat script raakt geen uitgangen aan en laat zien
welke kaarten de bus ziet en op welk adres.

> **Waarschuwing bij `test_io_board.py`:** dit script doet bij elke aanroep een
> hardware-reset en zet bij het afsluiten alle acht adressen terug naar ingang.
> De RESET-lijn is gedeeld met alle vijf de MCP23S17's, en zwevende ingangen
> laten de 48V-uitgangen aanslaan. Het is geschreven toen er nog één losse
> kaart was. Gebruik voor de opgebouwde koffer `scan.py` en `digital.py`.

## Voorbereiding

De SPI-bus moet op de Raspberry Pi ingeschakeld zijn:

```console
sudo raspi-config
```

Ga naar Interface Options, kies SPI en zet die op Enabled. Controleer daarna
of het apparaat bestaat:

```console
ls /dev/spidev0.*
```

De scripts hebben bibliotheken nodig die de app zelf niet gebruikt:

```console
sudo apt install python3-spidev python3-gpiozero
```

Draai je in de virtuele omgeving, dan zijn deze pakketten alleen zichtbaar als
die met `--system-site-packages` is aangemaakt. Anders installeer je ze in de
omgeving zelf:

```console
source ../venv-rpi/bin/activate
pip install spidev gpiozero
```

## scan.py

Zoekt op CE0 naar MCP23S17's op hardware-adres 0 tot en met 7. Werkwijze:

1. Hardware-reset via de RESET-pin. Zet `RESET_PIN = None` als RESET vast aan
   3V3 hangt, of wanneer je de andere kaarten niet wilt verstoren: de RESET-lijn
   is gedeeld.
2. Het HAEN-bit in IOCON aanzetten, zodat elke chip naar zijn adrespinnen gaat
   luisteren. Direct na een reset staat HAEN uit en reageert elke chip op elk
   adres, dus die ene schrijfactie bereikt de hele keten.
3. Per adres twee testpatronen (0xA5 en 0x5A) naar IPOLA schrijven en
   teruglezen. Twee patronen in plaats van een, omdat een zwevende of
   kortgesloten MISO-lijn altijd 0x00 of 0xFF teruggeeft en anders een
   vals-positief zou opleveren.
4. IPOLA weer op de oorspronkelijke waarde zetten.

Het script raakt geen enkele uitgang aan.

## knoppen_lampen/ - de knoppen- en lampenprint

MCP23S17 op CE0, hardware-adres `000`.

| Poort | Signaal | Richting | Werking |
|------------|------------------|----------|-----------------------------------------|
| GPA0..GPA7 | S1..S8, knoppen | ingang | actief laag, externe pull-up R20 (10 k) |
| GPB0..GPB7 | H1..H8, lampen | uitgang | niet geinverteerd: pin hoog = lamp aan |

De lampen hangen via een 2N7002 aan 12 V. Interne pull-ups zijn niet nodig, R20
doet dat al; daarom staat `USE_PULLUP = False`.

Bij het instellen wordt eerst de latch laag gezet en pas daarna de richting op
uitgang. Andersom flitst elke lamp kort aan op het moment van omschakelen.

`lightsout.py` doet bewust **geen** hardware-reset: de RESET-lijn is gedeeld met
de andere kaarten op CE0 en zou hun uitgangen ook wissen. Na het opstarten van
de Pi staan de pinnen als ingang en zweven de MOSFET-gates, waardoor lampen
kunnen aanstaan; dit script maakt er uitgangen van en zet ze laag.

`knoppen-test.py` meet bij het starten de rusttoestand, met alle knoppen los.
Een knop telt als ingedrukt zodra zijn pin daarvan afwijkt, dus het script werkt
zowel voor knoppen naar GND als naar 3V3.

`lampen-test.py` bedien je met `0`..`7` (aan), `u0`..`u7` (uit), `x` (alles uit)
en `q` (stoppen).

`semi-integratietest-knop-lamp.py` koppelt S*n* aan Q*n*. Met
`MODE = "momentary"` brandt de lamp zolang de knop ingedrukt is, met
`MODE = "toggle"` schakelt elke druk de lamp om.

### Het adres van de kaart

`knoppen-test.py`, `lampen-test.py` en `semi-integratietest-knop-lamp.py` werken
standaard op adres `000`, het adres van de knoppen- en lampenprint. Een ander
adres geef je als argument mee, decimaal of binair:

```console
python3 knoppen_lampen/lampen-test.py          # adres 000
python3 knoppen_lampen/lampen-test.py 1        # adres 001
python3 knoppen_lampen/lampen-test.py 0b010    # adres 010
```

Elk van deze drie scripts toont bij het starten op welk adres het werkt, zodat je
kunt controleren dat je de juiste kaart aanspreekt. `lightsout.py` staat vast op
adres `000`.

## digitaal/ - de 48V-uitgangskaarten

Vier MCP23S17's op CE0, hardware-adres `001` tot en met `100`. Adres `000` is de
knoppen/lampenprint en wordt door `digital.py` niet aangeraakt.

Pinnummering: 0 tot en met 15, waarbij 0-7 = GPIOA0-7 en 8-15 = GPIOB0-7.
PCB-adressen geef je binair op, net als in de scan: `010` is adres 2.

`digital.py` gaat uit van een geinverteerde open-drain levelshifter:

| MCP-pin | Uitgang |
|-----------|----------------|
| 1 (3,3 V) | 0 V, inactief |
| 0 (0 V) | 48 V, actief |

Die inversie wordt verborgen: `set_hoog()` zet de uitgang op 48 V.

> **Let op:** deze polariteit is nog niet definitief. Uit de metingen aan de
> kaarten kwam de omgekeerde conclusie (latch 1 = 48 V). Controleer dit voordat
> je het script op een opgebouwde koffer gebruikt: bij de verkeerde aanname zet
> `init_als_output()` juist alle 64 uitgangen op 48 V in plaats van uit.

Commando's: `<pcb> <pin> hoog`, `<pcb> <pin> laag`, `status`, `uit`, `help`,
`exit`.

## analoog/ - de DAC-print

Elke DAC-print draagt twee DAC8564's. De !SYNC van beide printen gaat naar CE1
(GPIO7, fysieke pin 26). De DAC8564 heeft geen data-uitgang, dus MISO blijft
ongebruikt en de bus draait in SPI-mode 1.

Omdat beide printen dezelfde chip-select delen, moeten alle vier de adressen
uniek zijn. De DAC8564 heeft alleen A0 en A1, dus er zijn precies vier
adressen beschikbaar:

| Print | DAC | Adres | Keten | Bereik |
|-------|------------|-------|--------------------------|-------------|
| 1 | DAC 1 (U1) | 00 | XTR117 stroomlus | 4 tot 20 mA |
| 1 | DAC 2 (U3) | 01 | MCP6002 + 2N7002 booster | 0 tot 48 V |
| 2 | DAC 1 (U1) | 10 | XTR117 stroomlus | 4 tot 20 mA |
| 2 | DAC 2 (U3) | 11 | MCP6002 + 2N7002 booster | 0 tot 48 V |

`dac-tester.py` kent alleen de adressen 00 en 01 en test dus een losse print.
`koffer-analoog.py` kent alle vier de adressen en spreekt de uitgangen aan met
de klemnummers van de koffer: U1 tot en met U8 voor de spanningsuitgangen en
I1 tot en met I8 voor de stroomlussen. U1-U4 en I1-I4 zitten op print 1,
U5-U8 en I5-I8 op print 2, in de kanaalvolgorde A, B, C, D.

> **Let op:** de aanduiding U komt twee keer voor. U1 en U3 zijn de
> componentnummers van de twee DAC8564's op de print; U1 tot en met U8 zijn de
> klemnummers van de koffer. In `koffer-analoog.py` wordt daarom consequent
> DAC 1 en DAC 2 gebruikt voor de IC's.

**XTR117.** R3 van 10 k tussen VOUT en IIN, stroomversterking 100x:

```
IIN  = V_dac / 10k
Iuit = 100 x IIN   ->   Iuit [mA] = 10 x V_dac
4 mA bij 0,40 V DAC, 20 mA bij 2,00 V DAC
```

**Booster.** De DAC gaat naar de min-ingang, de deler R18 (1,82 M) / R19 (100 k)
vanaf VOUT3 naar de plus-ingang. De 2N7002 keert om, dus de lus is negatief
teruggekoppeld en regelt tot V+ = V-:

```
V_dac = Vuit x 100k / 1,92M   ->   Vuit = 19,2 x V_dac
48 V bij 2,50 V DAC
```

Beide schakelingen gebruiken maar een deel van het DAC-bereik. Per uitgang staat
daarom een harde begrenzing (`v_max`), zodat een typefout de XTR117 niet in
overstroom drijft.

> **Openstaand:** `VFS` staat op 2,5 terwijl de afleiding uitgaat van een volle
> schaal van 5,0 V. Dat hangt samen met de meting waarbij DAC 2 de halve
> spanning gaf. Meet VOUTA van U3: 1,25 V betekent dat `VFS = 2.5` klopt,
> 2,50 V betekent dat de fout in de booster zit en dat `scale` en R18 nagerekend
> moeten worden.

## test_io_board.py

Test de MCP23S17 I/O-expanders van deelsysteem 6. De aansluiting op de
Raspberry Pi header is:

| Signaal | Header | GPIO |
|-----------|--------|--------|
| SCK | pin 23 | GPIO11 |
| SI (MOSI) | pin 19 | GPIO10 |
| SO (MISO) | pin 21 | GPIO9 |
| CS (CE0) | pin 24 | GPIO8 |
| RESET | pin 22 | GPIO25 |
| INT-NET | pin 18 | GPIO24 |
| 3V3 | pin 17 | - |
| GND | pin 20 | - |

Elke kaart krijgt met de DIP-schakelaars een eigen adres van 0 tot en met 7.
Het script zet bij het opstarten hardware-adressering (HAEN) aan; direct na een
reset luistert elke kaart namelijk nog naar elk adres, waardoor die ene
schrijfactie de hele keten bereikt.

De beschikbare commando's:

```console
python3 test_io_board.py scan              # zoek kaarten op adres 0 t/m 7
python3 test_io_board.py walk 0            # loop 1 bit langs GPA0..GPB7
python3 test_io_board.py write 0 A 0x0F    # schrijf een byte naar poort A
python3 test_io_board.py read 0            # lees beide poorten als ingang
python3 test_io_board.py read 0 --continu  # blijf lezen tot Ctrl-C
python3 test_io_board.py blink 0 A 3       # knipper alleen GPA3
python3 test_io_board.py blink 0 A         # knipper de hele poort A
python3 test_io_board.py blink 0 AB --delay 2   # alle 16 pinnen, 2 s aan / 2 s uit
python3 test_io_board.py allon 0           # alle 16 pinnen hoog, vasthouden
python3 test_io_board.py allon --alle      # idem op alle gevonden kaarten
```

Begin altijd met `scan`. Worden er geen kaarten gevonden, controleer dan de
voeding, de RESET-lijn en de DIP-standen voordat je verder zoekt.

### Uitgangen blijven alleen staan zolang het script draait

Bij het afsluiten zet het script alle pinnen van alle acht adressen terug naar
ingang. Dat is bewust zo: een testtool mag geen uitgangen laten staan waar
niemand meer zicht op heeft.

Het gevolg is wel dat `write` geen blijvend effect heeft. Dat commando zet de
byte weg en sluit meteen daarna af, waardoor de uitgang direct weer wegvalt.
Gebruik `write` dus alleen samen met een oscilloscoop, en gebruik `allon`,
`walk` of `blink` wanneer je rustig met een multimeter wilt meten: die blijven
lopen tot je Ctrl-C geeft.

> **Voorzichtig:** `walk`, `write`, `blink` en `allon` zetten de pinnen van de gekozen
> kaart als uitgang. Doe dat niet op een kaart waar iets op de ingangen is
> aangesloten: twee uitgangen die elkaar tegenwerken beschadigen de MCP23S17.
> Het script zet bij het afsluiten alle pinnen terug naar ingang, ook na Ctrl-C.

## Meetresultaten

Noteer de uitkomst van elke test in het unittestformulier van het betreffende
deelsysteem in het projectdocument, zodat de resultaten herleidbaar blijven bij
de acceptatietest.
