"""Gridgenerering inom en polygon (SWEREF 99 TM)."""

import math

from qgis.core import QgsGeometry, QgsPointXY


def grid_points(geom: QgsGeometry, spacing: float, limit=None):
    """Regelbundna punkter (e, n) med ``spacing`` m mellan sig inom polygonen.

    Gridet är förankrat i multiplar av ``spacing`` så att upprepade körningar
    ger samma punkter. Avbryter och returnerar None om fler än ``limit`` punkter.
    """
    engine = QgsGeometry.createGeometryEngine(geom.constGet())
    engine.prepareGeometry()
    bb = geom.boundingBox()
    x0 = math.ceil(bb.xMinimum() / spacing) * spacing
    y0 = math.ceil(bb.yMinimum() / spacing) * spacing
    points = []
    y = y0
    while y <= bb.yMaximum():
        x = x0
        while x <= bb.xMaximum():
            if engine.intersects(QgsGeometry.fromPointXY(QgsPointXY(x, y)).constGet()):
                points.append((x, y))
                if limit and len(points) > limit:
                    return None
            x += spacing
        y += spacing
    return points
