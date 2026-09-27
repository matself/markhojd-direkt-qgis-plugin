"""Punkter med jämnt intervall längs en linje (SWEREF 99 TM)."""


def line_points(geom, spacing, limit=None):
    """Punkter (e, n, avstånd) med ``spacing`` m mellan sig längs linjen.

    Första punkten ligger vid avstånd 0 och sista alltid vid linjens slut, även om
    slutet inte råkar ligga på ett jämnt multipel av ``spacing``. Avbryter och
    returnerar None om fler än ``limit`` punkter skulle skapas.

    Är ``geom`` en MultiLineString (t.ex. flera markerade linjeobjekt eller en linje med
    flera delar) slås delarna ihop och riktningen ensas med ``mergeLines()``, som kopplar
    ihop delar oavsett i vilken ordning eller riktning de är lagrade. Hänger delarna inte
    ihop (en lucka) skulle avstånd och interpolering annars tyst hoppa över luckan, så då
    höjs ``ValueError`` i stället.
    """
    if geom.isMultipart():
        merged = geom.mergeLines()
        if merged.isMultipart():
            raise ValueError(
                "Linjen har osammanhängande delar (en lucka) och kan inte användas för en "
                "sammanhängande höjdprofil. Välj eller rita en sammanhängande linje."
            )
        geom = merged
    length = geom.length()
    if length <= 0 or spacing <= 0:
        return []
    n_steps = int(length // spacing)
    distances = [i * spacing for i in range(n_steps + 1)]
    if not distances or length - distances[-1] > 1e-6:
        distances.append(length)
    if limit and len(distances) > limit:
        return None
    points = []
    for d in distances:
        pt = geom.interpolate(d)
        if pt.isEmpty():
            continue
        p = pt.asPoint()
        points.append((p.x(), p.y(), d))
    return points
