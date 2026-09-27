"""Kräver QGIS Python (python-qgis)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "markhojd_direkt"))
from qgis.core import QgsGeometry  # noqa: E402

from line import line_points  # noqa: E402


def test_line_points_endpoints_and_spacing():
    geom = QgsGeometry.fromPolylineXY(
        [__import__("qgis.core", fromlist=["QgsPointXY"]).QgsPointXY(x, 0) for x in (0, 100)]
    )
    pts = line_points(geom, 30)
    dists = [p[2] for p in pts]
    assert dists[0] == 0
    assert dists[-1] == 100  # slutpunkten kommer alltid med
    assert dists == [0, 30, 60, 90, 100]
    assert pts[0][:2] == (0, 0) and pts[-1][:2] == (100, 0)


def test_line_points_exact_multiple_no_duplicate_end():
    geom = QgsGeometry.fromPolylineXY(
        [__import__("qgis.core", fromlist=["QgsPointXY"]).QgsPointXY(x, 0) for x in (0, 90)]
    )
    pts = line_points(geom, 30)
    assert [p[2] for p in pts] == [0, 30, 60, 90]


def test_line_points_limit():
    geom = QgsGeometry.fromPolylineXY(
        [__import__("qgis.core", fromlist=["QgsPointXY"]).QgsPointXY(x, 0) for x in (0, 1000)]
    )
    assert line_points(geom, 1, limit=50) is None
