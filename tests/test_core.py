import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "markhojd_direkt"))
import core  # noqa: E402


def test_chunks_respect_limits():
    pts = [(600000 + x, 6700000 + y) for x in range(0, 2000, 10) for y in range(0, 2000, 10)]
    chunks = core.chunk_points(pts)
    assert sum(len(c) for c in chunks) == len(pts)
    for c in chunks:
        assert len(c) <= 1000
        w = max(p[0] for p in c) - min(p[0] for p in c)
        h = max(p[1] for p in c) - min(p[1] for p in c)
        assert w * h < core.MAX_AREA_M2


def test_body_is_multipoint_sweref():
    b = json.loads(core.build_multipoint_body([(1.0, 2.0), (3.0, 4.0)]))
    assert b["type"] == "MultiPoint" and b["crs"]["properties"]["name"].endswith("3006")
    assert b["coordinates"] == [[1.0, 2.0], [3.0, 4.0]]


def test_parse_point_and_nodata():
    r = core.parse_heights({"geometry": {"type": "Point", "coordinates": [1, 2, 7.23]}, "properties": {"nodatavalue": -9999}})
    assert r == [(1.0, 2.0, 7.23)]
    r = core.parse_heights({"geometry": {"type": "MultiPoint", "coordinates": [[1, 2, -9999], [3, 4, 5]]}, "properties": {"nodatavalue": -9999}})
    assert r == [(1.0, 2.0, None), (3.0, 4.0, 5.0)]


def test_fault_text():
    t = core.parse_fault('{"code":400,"reason":"Bad Request","errors":["Area is too large!"]}')
    assert "400" in t and "Area is too large" in t


def test_estimates():
    assert core.estimate_grid(1_000_000, 10) == (10000, 10)
    assert core.spacing_for_max_points(1_000_000, 10000) == 10


def test_chunk_sequential_preserves_order():
    pts = [(i, i, i * 2) for i in range(2500)]
    chunks = core.chunk_sequential(pts, max_points=1000)
    assert [len(c) for c in chunks] == [1000, 1000, 500]
    flat = [p for c in chunks for p in c]
    assert flat == pts
