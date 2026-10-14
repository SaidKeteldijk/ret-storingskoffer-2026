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
| `digitaal/` | `test_io_board.py` | Losse MCP23S17-kaarten doormeten per pin of poort |
| `knoppen_lampen/` | `lightsout.py` | Zet de lampen op de knoppen/lampen-PCB uit |
| `knoppen_lampen/` | `lampen-test.py` | Lampen Q1..Q8 los aansturen |
| `knoppen_lampen/` | `knoppen-test.py` | Knoppen S1..S8 uitlezen |
| `knoppen_lampen/` | `semi-integratietest-knop-lamp.py` | Knop bedient de bijbehorende lamp |
| `digitaal/` | `digital.py` | De 48V-uitgangskaarten per pin bedienen |
| `digitaal/` | `uitgangen.json` | De kaartvolgorde, de defecte pinnen en de Dx-nummering |
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

> **Let op bij `test_io_board.py`:** dit is gereedschap om een losse kaart per
> pin door te meten, niet om de opgebouwde koffer te bedienen. Het kent de
> defecte uitgangen niet en spreekt ook adres `000` aan, de knoppen- en
> lampenprint. Gebruik voor de 48V-kaarten in de koffer `digital.py`.

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
| GPB0..GPB7 | Q1..Q8, lampen | uitgang | niet geinverteerd: pin hoog = lamp aan |

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

MCP23S17's op CE0 met hardware-adres `001` en hoger. Adres `000` is de
knoppen/lampenprint en wordt nooit aangeraakt; `digital.py` begint bewust bij
`001`, want een schrijfactie naar `000` zou daar alle lampen aanzetten.

Er zijn nu vijf kaarten gebouwd, op `001` tot en met `101`. Het script gaat niet
van een vast aantal uit maar zoekt `001` tot en met `111` af en houdt over wat
antwoordt, zodat een kaart erbij geen aanpassing in de code vraagt.

Pinnummering: 0 tot en met 15, waarbij 0-7 = GPIOA0-7 en 8-15 = GPIOB0-7.
PCB-adressen geef je binair op, net als in de scan: `010` is adres 2.

```console
python3 digitaal/digital.py              # zoekt 001 t/m 111
python3 digitaal/digital.py 001          # alleen die ene kaart
```

Het script zet de RESET-lijn hoog **zonder puls**, zet HAEN aan, en controleert
per adres met een testpatroon of er een kaart antwoordt. Alleen de kaarten die
antwoorden worden gebruikt. Geef je zelf adressen op, dan meldt het script welke
daarvan niet gevonden zijn; bij het automatisch zoeken blijft dat achterwege.

> **Let op:** `scan.py` eindigt met `GPIO.cleanup()`, waarna GPIO25 weer ingang
> wordt. Zonder pull-up zakt RESET dan weg en houden alle MCP23S17's zich stil:
> de schrijfacties komen aan noch gaan fout, er gebeurt alleen niets. Daarom
> zet elk script dat met de kaarten praat die lijn zelf hoog. Een scan die net
> gelukt is, is geen garantie dat het volgende script de kaart nog vindt.

| Commando | Werking |
|---------------------------|---------------------------------------------|
| `<pcb> <pin> hoog` | die uitgang op 48V |
| `<pcb> <pin> laag` | die uitgang op 0V |
| `<pcb> alles hoog\|laag` | alle 16 uitgangen van die kaart tegelijk |
| `aan` | alle uitgangen van alle gevonden kaarten op 48V |
| `uit` | alle uitgangen van alle gevonden kaarten op 0V |
| `status` | leest OLAT terug en toont welke klemmen 48V geven |
| `help`, `exit` | overzicht en afsluiten |

`status` leest de latches terug uit de chip en toont dus niet wat het script
denkt, maar wat de kaart werkelijk vasthoudt.

De polariteit van de uitgangstrap staat als losse constante bovenin:

```python
KLEM_HOOG_BIJ_LATCH = 1
```

Deze is gemeten aan de gebouwde kaarten en niet langer een aanname: de
uitgangstrap is **niet** inverterend. Een latch van 1 geeft 48 V op de klem, een
latch van 0 geeft 0 V. De eerdere aanname in dit project ging uit van het
omgekeerde; die klopte niet. Het script meldt bij het starten welke waarde
actief is.

Voor de bediening maakt het niets uit: `hoog` is altijd 48 V en `laag` altijd
0 V. De constante vertaalt dat naar de latch, zodat de inversie op één plek
staat.

### De uitgangen en hun nummering

Vijf van de zestien uitgangen doen het niet, en dat geldt op elke kaart. In de
telling van de MCP23S17, die bij 0 begint, zijn dat pin 6, 7, 12, 13 en 14; op
de printopdruk, die bij 1 begint, staan ze als 7, 8, 13, 14 en 15. Omdat het op
alle vijf de kaarten dezelfde pinnen zijn, is het geen defect van een losse
kaart maar iets dat in het ontwerp of de print zelf zit. Per kaart blijven er elf
bruikbare uitgangen over, en met vijf kaarten 55 in plaats van 80.

Dat staat samen met de kaartvolgorde in `digitaal/uitgangen.json`:

```json
{
  "kaarten": ["001", "010", "011", "100", "101"],
  "defect_alle_kaarten": [6, 7, 12, 13, 14],
  "defect_per_kaart": {}
}
```

Onder `defect_alle_kaarten` staan de pinnen die op geen enkele kaart werken.
Krijgt een losse kaart er later een eigen probleem bij, dan komt dat onder
`defect_per_kaart` te staan met het binaire kaartadres als sleutel, bijvoorbeeld
`"010": [3]`. De twee lijsten worden bij elkaar opgeteld.

**De Dx-nummering.** Op de koffer zijn alleen de werkende uitgangen
doorverbonden, en die zijn doorlopend genummerd als `D1` tot en met `D55`. De
volgorde volgt de kaarten uit `kaarten` en per kaart de pinnummers oplopend,
waarbij de defecte pinnen worden overgeslagen:

| Kaart | MCP-pin | Klem |
|-------|---------|------|
| 001 | 5 | D6 |
| 001 | 8 | D7 |
| 001 | 15 | D11 |
| 010 | 0 | D12 |
| 101 | 15 | D55 |

Daarom staat de kaartvolgorde in hetzelfde bestand: zonder vaste volgorde zou de
Dx-nummering verschuiven zodra er een kaart niet antwoordt. Dit bestand is de
enige plek waar die verdeling vastligt; `digital.py` en `koffer_digitaal.py` in
de hoofdmap lezen het allebei.

`digital.py` werkt met de kaart en het MCP-pinnummer en zet het klemnummer erbij:

```console
> 001 8 hoog
PCB 001, pin 8 (D7) -> 48V
```

De defecte pinnen worden niet aangestuurd. Een poging wordt geweigerd:

```console
> 001 6 hoog
Fout: pin 6 van PCB 001 werkt niet en wordt niet aangestuurd
```

Ook `<pcb> alles hoog` en `aan` slaan ze over; die zetten alleen de werkende
uitgangen op 48 V en melden welke overgeslagen zijn. `aan` telt daarbij de
werkelijk aangestuurde uitgangen, dus 55 en niet 80. In `status` staan de
defecte pinnen achteraan de regel als geheugensteun. Let op dat `status` de
latch van de chip teruggeeft en niet de klemspanning: een defecte pin zou daar
als actief kunnen staan terwijl er niets uit komt.

### test_io_board.py

Gereedschap om een enkele MCP23S17 per pin of per poort door te meten, los van
de koffer. Het werkt op elk adres van 0 tot en met 7 en kent de defecte
uitgangen uit `uitgangen.json` niet; daarvoor is `digital.py` er.
De aansluiting op de Raspberry Pi header is:

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
Het script zet bij het opstarten hardware-adressering (HAEN) aan op alle acht
adressen, en zet de RESET-lijn hoog **zonder puls**, zodat de knoppen- en
lampenprint er niet van in reset gaat.

De beschikbare commando's:

```console
python3 digitaal/test_io_board.py scan              # zoek kaarten op adres 0 t/m 7
python3 digitaal/test_io_board.py walk 0            # loop 1 bit langs GPA0..GPB7
python3 digitaal/test_io_board.py write 0 A 0x0F    # schrijf een byte naar poort A
python3 digitaal/test_io_board.py read 0            # lees beide poorten als ingang
python3 digitaal/test_io_board.py read 0 --continu  # blijf lezen tot Ctrl-C
python3 digitaal/test_io_board.py blink 0 A 3       # knipper alleen GPA3
python3 digitaal/test_io_board.py blink 0 A         # knipper de hele poort A
python3 digitaal/test_io_board.py blink 0 AB --delay 2   # alle 16 pinnen, 2 s aan / 2 s uit
python3 digitaal/test_io_board.py allon 0           # alle 16 pinnen hoog, vasthouden
python3 digitaal/test_io_board.py allon --alle      # idem op alle gevonden kaarten
```

Begin altijd met `scan`. Worden er geen kaarten gevonden, controleer dan de
voeding, de RESET-lijn en de DIP-standen voordat je verder zoekt.

#### Uitgangen blijven alleen staan zolang het script draait

Bij het afsluiten zet het script de pinnen terug naar ingang van de kaarten die
het zelf heeft aangestuurd. Dat is bewust zo: een testtool mag geen uitgangen
laten staan waar niemand meer zicht op heeft. Kaarten die het niet heeft
aangeraakt blijven ongemoeid.

Het gevolg is wel dat `write` geen blijvend effect heeft. Dat commando zet de
byte weg en sluit meteen daarna af, waardoor de uitgang direct weer wegvalt.
Gebruik `write` dus alleen samen met een oscilloscoop, en gebruik `allon`,
`walk` of `blink` wanneer je rustig met een multimeter wilt meten: die blijven
lopen tot je Ctrl-C geeft.

> **Voorzichtig:** `walk`, `write`, `blink` en `allon` zetten de pinnen van de gekozen
> kaart als uitgang. Doe dat niet op een kaart waar iets op de ingangen is
> aangesloten: twee uitgangen die elkaar tegenwerken beschadigen de MCP23S17.
> Het script zet bij het afsluiten de gebruikte pinnen terug naar ingang, ook na
> Ctrl-C.

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
| 2 | DAC 1 (U1) | 11 | XTR117 stroomlus | 4 tot 20 mA |
| 2 | DAC 2 (U3) | 10 | MCP6002 + 2N7002 booster | 0 tot 48 V |

Het adreswoord is `(A1 << 1) | A0`. Op print 2 staan de twee DAC's in de
omgekeerde volgorde van print 1; dat is zo gebouwd en staat zo in
`koffer-analoog.py`. Verwissel je de printen, dan klopt de tabel niet meer.

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

## Meetresultaten

Noteer de uitkomst van elke test in het unittestformulier van het betreffende
deelsysteem in het projectdocument, zodat de resultaten herleidbaar blijven bij
de acceptatietest.
