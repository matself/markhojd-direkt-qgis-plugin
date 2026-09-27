"""Punkter med jämnt intervall längs en linje (SWEREF 99 TM)."""


def line_points(geom, spacing, limit=None):
    """Punkter (e, n, avstånd) med ``spacing`` m mellan sig längs linjen.

    Första punkten ligger vid avstånd 0 och sista alltid vid linjens slut, även om
    slutet inte råkar ligga på ett jämnt multipel av ``spacing``. Avbryter och
    returnerar None om fler än ``limit`` punkter skulle skapas.
    """
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
