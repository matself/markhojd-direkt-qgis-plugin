"""Evenly spaced points along a line (SWEREF 99 TM)."""


def line_points(geom, spacing, limit=None):
    """Points (e, n, distance), ``spacing`` m apart, along the line.

    The first point is at distance 0 and the last is always at the end of the line, even if
    the end is not an even multiple of ``spacing``. Stops and returns None if more than
    ``limit`` points would be created.

    If ``geom`` is a MultiLineString (for example several selected line features or a line
    with several parts) the parts are merged and the direction is unified with
    ``mergeLines()``, which joins parts regardless of the order or direction they are stored
    in. If the parts are not connected (a gap), distance and interpolation would silently
    skip the gap, so ``ValueError`` is raised instead.
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
