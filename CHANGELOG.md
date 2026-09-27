# Ändringslogg

## 0.1.5
- Gridet varnar (orange text) när antalet punkter blir fler än 100, med förslag att öka punktavståndet - gridet är tänkt för t.ex. en tomtkarta, inte för att bygga en egen höjdmodell av punkterna.
- Ny, frivillig knapp Visa profil för en hämtad linje: öppnar en panel i QGIS med avstånd/höjd som en graf, byggd på QGIS egen höjdprofilkomponent. Visas inte automatiskt.

## 0.1.4
- En MultiLineString (flera linjedelar, blandad ordning/riktning) slås automatiskt ihop till en sammanhängande linje för höjder längs en linje. En verkligt osammanhängande linje (lucka) avvisas med ett tydligt meddelande i stället för att ge felaktiga avstånd.

## 0.1.3
- Nytt läge: höjder längs en linje, med rita-linje-verktyg eller befintligt linjeobjekt. Punkterna får ett attribut avstand (meter från linjens början), lämpligt för en höjdprofil.

## 0.1.2
- Installation via plugin-arkiv (plugins.xml) och uppdaterad README.

## 0.1.1
- Inloggning med användarnamn/lösenord (Basic) i stället för OAuth2; egen nätverkshanterare (inga krascher eller inloggningsrutor vid 401).
- Höjdvärdet placeras till höger om punkten.
- Exakt antal gridpunkter i panelen.
- Disclaimer (fristående plugin) och användarhandledning i docs.
- LICENSE (GPL-3.0) följer med i ZIP-paketet.

## 0.1.0
- Första version: klicka för höjd, höjdgrid i ritat/markerat område, spara som 3D-punkter.

