# Markhöjd direkt (Lantmäteriet) – QGIS-plugin

Hämtar markhöjd från Lantmäteriets tjänst [Markhöjd Direkt](https://www.lantmateriet.se/sv/geodata/vara-produkter/produktlista/markhojd-direkt/)
(nationella markhöjdmodellen, 1 m grid, höjdsystem RH 2000, rikstäckande).

## Funktioner

1. **Höjd i en punkt** – aktivera *Klicka i kartan för höjd* och klicka. Punkten markeras med ett kryss och höjden
   visas i meter (1 decimal som standard). Typsnitt, textstorlek och antal decimaler kan väljas i panelen.
2. **Höjdgrid i ett område** – rita en polygon (eller använd markerade polygoner i ett lager), välj punktavstånd och
   klicka *Hämta höjder*. Pluginet lägger ett regelbundet grid i området och hämtar höjden i varje gridpunkt.
3. **3D-punkter** – alla resultat är lager av typen PointZ i SWEREF 99 TM (EPSG:3006) med höjden som Z-värde och som
   attributet `hojd`. Spara som GeoPackage, Shapefile eller CSV (X,Y,Z).

## Krav och anslutning

Tjänsten är bara öppen för systemkonto som har beställt Markhöjd Direkt. Anrop görs med HTTP Basic
(användarnamn och lösenord för systemkontot), på samma sätt som i HAJK. Uppgifterna sparas i QGIS
autentiseringsdatabas:

* Välj miljö (produktion / verifiering).
* Klicka *Ny nyckel…* och ange användarnamn och lösenord, eller välj en befintlig Basic-konfiguration.
* *Testa* anropar `/health` och hämtar höjden i en testpunkt.

## Begränsningar i tjänsten

Enligt teknisk beskrivning v1.0.1 och produktbeskrivning v1.6:

| Begränsning | Värde |
|---|---|
| Punkter i en MultiPoint per anrop | 1 000 |
| Brytpunkter i LineString/Polygon per anrop | 1 000 |
| Yta per anrop (enligt felmeddelandet i dokumentationen) | 1 000 000 m² |
| Antal anrop per tidsenhet | **Ej dokumenterat** – styrs av API-portalens prenumerationsplan |

Pluginet delar därför upp ett grid i anrop om högst 1 000 punkter inom en ruta på högst 900 × 900 m, hämtar dem
efter varandra med kort paus och gör om anropet med väntetid vid HTTP 429/503 (respekterar `Retry-After`).
Om ert avtal har en lägre kvot: sänk *Max antal punkter*.

## Hur tätt ska gridet vara?

Underlaget är ett 1 m-grid, så tätare än 1 m ger ingen ny information. Du kan styra antingen med
**punktavstånd** (m) eller med **max antal punkter** – knappen *Anpassa punktavstånd till max antal* räknar ut
minsta avstånd som håller sig under maxgränsen. Panelen visar hela tiden uppskattat antal punkter och anrop.
Tumregel: 1 ha ger 100 punkter vid 10 m, 10 000 punkter vid 1 m. Standard är 10 m och max 20 000 punkter.

## Installation

Bygg zip och installera via *Plugins → Hantera och installera insticksmoduler → Installera från ZIP*:

```bash
python package.py
```

## Utveckling

```bash
pytest tests/test_core.py   # ren logik
```

`tests/test_grid.py` kräver QGIS Python (`python-qgis.bat`).

Licens: GPL-2.0-or-later (se `LICENSE`).
