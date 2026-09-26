"""Kräver QGIS Python (python-qgis)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "markhojd_direkt"))
from qgis.core import QgsGeometry, QgsPointXY  # noqa: E402

import grid  # noqa: E402


def test_grid_square_and_hole():
    sq = QgsGeometry.fromPolygonXY([[QgsPointXY(0, 0), QgsPointXY(100, 0), QgsPointXY(100, 100), QgsPointXY(0, 100)]])
    pts = grid.grid_points(sq, 10)
    assert len(pts) == 121  # kanten räknas med
    assert grid.grid_points(sq, 10, limit=50) is None
