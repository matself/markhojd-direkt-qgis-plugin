# Användarhandledning – Markhöjd direkt (Lantmäteriet)

> **Observera:** Pluginet är fristående och har inget samband med, och är inte godkänt eller
> tillhandahållet av, Lantmäteriet. Namnet *Lantmäteriet* används endast för att ange varifrån
> höjddata hämtas.

## 1. Vad pluginet gör

Pluginet hämtar markhöjd (höjd över havet i RH 2000) från tjänsten Markhöjd Direkt, som bygger på
nationella markhöjdmodellen med 1 m upplösning. Du kan:

* klicka i kartan och få höjden markerad med ett kryss och ett höjdvärde,
* rita ett område och hämta höjder i ett regelbundet grid,
* spara resultatet som 3D-punkter.

## 2. Förutsättningar

* QGIS 3.34 eller senare.
* Ett användarkonto (systemkonto) som har beställt tjänsten Markhöjd Direkt hos Lantmäteriet.
  Pluginet fungerar inte utan ett sådant konto.
* Internetanslutning. Tjänsten täcker hela Sverige.

## 3. Installation

1. Ladda ner `markhojd_direkt.zip` från [Releases](https://github.com/matself/markhojd-direkt-qgis-plugin/releases).
2. I QGIS: *Plugins → Hantera och installera insticksmoduler → Installera från ZIP*.
3. Välj filen och klicka *Installera insticksmodul*.
4. Klicka på ikonen i verktygsfältet, eller välj pluginet i menyn *Plugins*, för att öppna panelen
   **Markhöjd direkt (Lantmäteriet)**.

## 4. Anslutning

Överst i panelen finns gruppen **Anslutning**.

1. **Miljö** – välj *Produktion*. *Verifiering* är en testmiljö som kräver att kontot har beställt tjänsten där.
2. **Ny nyckel…** – ange användarnamn och lösenord för kontot. Uppgifterna sparas i QGIS
   autentiseringsdatabas (du kan behöva ange QGIS huvudlösenord första gången).
3. Välj den nya konfigurationen i listan **Autentisering**.
4. Klicka **Testa**. Meddelandet ska visa att tjänsten är uppe och ange en höjd för en testpunkt.

Du behöver bara göra detta en gång. Valen kommer ihåg till nästa gång du startar QGIS.

## 5. Höjd i en punkt

1. Klicka **Klicka i kartan för höjd** (knappen blir intryckt).
2. Klicka i kartan. Punkten får ett kryss och höjden visas i meter till höger om krysset.
3. Fortsätt klicka för fler punkter. De läggs i lagret **Markhöjd – punkter**.
4. Klicka på knappen igen för att stänga av verktyget.

Under **Höjd i en punkt** kan du ändra:

* **Typsnitt** och **Textstorlek** (punkter, pt) på höjdvärdet,
* **Decimaler** (0–3, standard 1). Lantmäteriet rekommenderar att antalet decimaler begränsas,
  eftersom tjänsten ger svar med många decimaler men inte har den noggrannheten.

Ändringarna slår igenom direkt på alla lager som pluginet har skapat. Du kan också ändra
utseendet som vanligt i lagrets egenskaper (*Symbologi* och *Etiketter*).

Om ingen höjddata finns på platsen visas ett meddelande och ingen punkt läggs till.

## 6. Höjdgrid i ett område

### Välja område

* **Rita område** – klicka ut polygonens hörn i kartan. Högerklick eller Enter avslutar,
  Esc börjar om.
* **Markerad polygon** – markera en eller flera polygoner i ett polygonlager, gör lagret aktivt och
  klicka på knappen. Flera markerade polygoner slås ihop.
* **Rensa** – tar bort området.

Området kan ligga i vilket koordinatsystem som helst. Pluginet räknar om det till SWEREF 99 TM (EPSG:3006).

### Välja hur tätt gridet ska vara

Två inställningar styr:

| Inställning | Betydelse |
|---|---|
| **Punktavstånd** | Avstånd i meter mellan gridpunkterna (1–5 000 m). Standard 10 m. |
| **Max antal punkter** | Övre gräns som skydd mot att du hämtar för mycket av misstag. Standard 20 000. |

Panelen visar hela tiden yta, exakt antal punkter och antal anrop, till exempel
*"Yta 0.36 ha: 49 punkter i 1 anrop."* Är antalet större än maxgränsen blir knappen
**Hämta höjder** avstängd tills du ökar punktavståndet eller maxgränsen.

**Anpassa punktavstånd till max antal** räknar ut det tätaste avståndet (hela meter) som ryms inom maxgränsen.

Tumregler:

* Underlaget är ett 1 m-grid. Tätare än 1 m ger ingen ny information.
* 1 ha ger ca 100 punkter vid 10 m avstånd, ca 2 500 vid 2 m och ca 10 000 vid 1 m.
* Gridpunkterna ligger på jämna multiplar av punktavståndet i SWEREF 99 TM, så upprepade körningar
  med samma avstånd ger samma punkter.
* Punkter på områdets kant räknas med.
* För mycket stora områden räknar panelen inte exakt utan anger "ca".

### Hämta höjderna

1. Klicka **Hämta höjder**. En förloppsindikator visas, och du kan avbryta med **Avbryt**.
   Punkter som redan hämtats behålls.
2. Resultatet läggs i ett nytt lager, till exempel **Markhöjd – grid 10 m**.
3. Meddelandet anger antal hämtade punkter och eventuella punkter utan höjddata.

Etiketter med höjdvärde visas för lager med högst 1 000 punkter. Större lager ritas utan etiketter för att kartan ska vara läsbar;
slå på etiketter i lagrets egenskaper om du vill ha dem.

### Om begränsningar i tjänsten

* Högst 1 000 punkter per anrop. Pluginet delar automatiskt upp större grid i flera anrop
  inom rutor om högst 900 × 900 m (tjänsten har en gräns för ytan per anrop).
* Någon gräns för antal anrop per tidsenhet finns inte angiven i dokumentationen. Den kan bero på
  kontots avtal. Vid HTTP 429 eller 503 väntar pluginet och försöker igen. Om du blir strypt kan du
  sänka **Max antal punkter**.

## 7. Spara som 3D-punkter

Alla lager som pluginet skapar är av typen **PointZ** i SWEREF 99 TM (EPSG:3006). Höjden ligger både som Z-värde i
geometrin och som attributet `hojd`. Övriga attribut är `e` och `n` (koordinater).

Lagren är tillfälliga (minneslager) tills du sparar dem:

1. Välj lager i listan under **Spara som 3D-punkter**. Det senast hämtade gridet är förvalt.
2. Klicka **Spara lager…** och välj format:
   * **GeoPackage** (`.gpkg`) – rekommenderas, behåller 3D-geometri och attribut.
   * **Shapefile** (`.shp`) – behåller Z-värdet.
   * **CSV med X,Y,Z** (`.csv`) – textfil med kolumnerna X, Y, Z, hojd, e, n.

Om du stänger projektet utan att spara försvinner minneslagren (QGIS varnar om detta).

## 8. Felsökning

| Meddelande | Trolig orsak och åtgärd |
|---|---|
| *Åtkomst nekad (401)* | Fel användarnamn eller lösenord. Skapa nyckeln på nytt med *Ny nyckel…* och kontrollera inmatningen. |
| *Åtkomst nekad (403)* | Kontot saknar behörighet till tjänsten i vald miljö. Kontrollera beställningen och att rätt miljö är vald. |
| *Välj eller skapa en autentiseringskonfiguration först* | Ingen konfiguration vald under **Autentisering**. |
| *HTTP 400 …* | Anropet avvisades, till exempel för stor yta. Använd ett mindre område eller större punktavstånd. |
| *Nätverksfel* | Ingen kontakt med tjänsten. Kontrollera internetanslutning och proxy. |
| *Ingen höjddata för den punkten* | Punkten ligger utanför modellens täckning (t.ex. till havs). |
| *N saknade höjddata* efter grid | Vissa gridpunkter ligger utanför täckningen och har hoppats över. |

Felmeddelanden visas i QGIS meddelandefält. Vid felrapport, bifoga texten och gärna QGIS-versionen.

## 9. Datainnehåll och noggrannhet

* Källa: nationella markhöjdmodellen, grid med 1 m upplösning.
* Plan: SWEREF 99 TM. Höjd: RH 2000.
* Höjdvärdet anger markens höjd över havet (RH 2000) enligt modellen, inte höjden på byggnader eller träd.
* Kvalitet, tillkomst och uppdateringsfrekvens beskrivs av tjänstens leverantör i dokumentet
  *Kvalitetsbeskrivning nationell markhöjdmodell*. Kontrollera att kvaliteten räcker för ditt ändamål.

## 10. Ansvarsfriskrivning

Pluginet är ett fristående verktyg som tillhandahålls i befintligt skick, utan garantier.
Det är inte utvecklat av, godkänt av eller kopplat till Lantmäteriet. Namnet *Lantmäteriet* används bara som
namn på datakällan. Användning av tjänsten regleras av dina villkor och ditt avtal med Lantmäteriet.
Kontrollera alltid resultat som ska användas som underlag för beslut.

Pluginet licensieras under GPL-3.0, se `LICENSE`.
