"""Grid generation inside a polygon (SWEREF 99 TM)."""

import math

from qgis.core import QgsGeometry, QgsPointXY


def grid_points(geom: QgsGeometry, spacing: float, limit=None):
    """Regularly spaced points (e, n), ``spacing`` m apart, inside the polygon.

    The grid is anchored at multiples of ``spacing`` so that repeated runs give the
    same points. Stops and returns None if there are more than ``limit`` points.
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
