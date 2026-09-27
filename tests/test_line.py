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


def test_multilinestring_mixed_order_and_direction_is_merged():
    from qgis.core import QgsPointXY

    seg1 = [QgsPointXY(0, 0), QgsPointXY(10, 0)]
    seg2 = [QgsPointXY(30, 0), QgsPointXY(20, 0)]  # omvänd riktning
    seg3 = [QgsPointXY(20, 0), QgsPointXY(10, 0)]  # kopplar ihop seg1 och seg2, omvänd riktning
    geom = QgsGeometry.fromMultiPolylineXY([seg2, seg3, seg1])  # blandad ordning
    pts = line_points(geom, 10)
    # mergeLines() väljer själv vilken ände som blir start; det viktiga är att punkterna
    # ligger i en enda konsekvent riktning längs den sammanhängande linjen, jämnt fördelade.
    xs = [p[0] for p in pts]
    assert {p[1] for p in pts} == {0}
    assert sorted(xs) == [0, 10, 20, 30]
    assert xs == sorted(xs) or xs == sorted(xs, reverse=True)
    assert [p[2] for p in pts] == [0, 10, 20, 30]


def test_multilinestring_with_gap_raises():
    from qgis.core import QgsPointXY

    seg1 = [QgsPointXY(0, 0), QgsPointXY(10, 0)]
    seg2 = [QgsPointXY(20, 0), QgsPointXY(30, 0)]  # lucka mellan 10 och 20
    geom = QgsGeometry.fromMultiPolylineXY([seg1, seg2])
    try:
        line_points(geom, 10)
        assert False, "skulle ha höjt ValueError"
    except ValueError:
        pass
