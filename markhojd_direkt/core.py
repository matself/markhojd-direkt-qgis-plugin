"""Pure logic without QGIS dependencies: limits, splitting into requests and parsing responses."""

import json
import math

SRID = 3006
CRS_URN = "urn:ogc:def:crs:EPSG::3006"

# Limits according to the technical description v1.0.1 (GeometriRequest)
MAX_POINTS_PER_REQUEST = 1000
# The error message in the technical description shows that an area may be at most 1,000,000 m2.
# Each request is kept within a 900 x 900 m tile so that the limit cannot be hit.
MAX_AREA_M2 = 1_000_000
TILE_SIZE_M = 900.0

DEFAULT_NODATA = -9999.0


def chunk_points(points, max_points=MAX_POINTS_PER_REQUEST, tile=TILE_SIZE_M):
    """Split points into requests of at most ``max_points`` points within a ``tile`` m square.

    The points are grouped per tile so that each request is geographically compact.
    """
    tiles = {}
    for p in points:
        key = (math.floor(p[0] / tile), math.floor(p[1] / tile))
        tiles.setdefault(key, []).append(p)
    chunks = []
    for key in sorted(tiles):
        pts = tiles[key]
        for i in range(0, len(pts), max_points):
            chunks.append(pts[i : i + max_points])
    return chunks


def chunk_sequential(points, max_points=MAX_POINTS_PER_REQUEST):
    """Split points into requests of at most ``max_points`` points, keeping the order.

    Used for lines, where the order is needed for the distance along the line to be correct.
    No area-based splitting is needed, since the only documented limit of the service for
    LineString/MultiLineString is the number of vertices.
    """
    return [points[i : i + max_points] for i in range(0, len(points), max_points)]


def build_multipoint_body(points):
    """JSON body (bytes) for POST /hojd with a MultiPoint in SWEREF 99 TM."""
    body = {
        "type": "MultiPoint",
        "crs": {"type": "name", "properties": {"name": CRS_URN}},
        "coordinates": [[round(e, 3), round(n, 3)] for e, n in points],
    }
    return json.dumps(body).encode("utf-8")


def _z_or_none(z, nodata):
    if z is None or (nodata is not None and abs(z - nodata) < 1e-6):
        return None
    return float(z)


def parse_heights(payload, ignore_nodata=True):
    """Parse a HojdResponse (dict). Returns a list of (e, n, z or None)."""
    nodata = (payload.get("properties") or {}).get("nodatavalue", DEFAULT_NODATA)
    geom = payload.get("geometry") or {}
    coords = geom.get("coordinates") or []
    if geom.get("type") == "Point":
        coords = [coords]
    out = []
    for c in coords:
        z = c[2] if len(c) > 2 else None
        out.append((float(c[0]), float(c[1]), _z_or_none(z, nodata)))
    return out


def parse_fault(text):
    """Readable text from a Fault response (code/reason/errors)."""
    try:
        data = json.loads(text)
        parts = [f"{data.get('code', '')} {data.get('reason', '')}".strip()]
        parts += [str(e) for e in data.get("errors") or []]
        return ": ".join(p for p in parts if p)
    except (ValueError, AttributeError, TypeError):
        return (text or "").strip()[:300]


def estimate_grid(area_m2, spacing):
    """Estimated number of grid points and number of requests for an area."""
    if spacing <= 0:
        return 0, 0
    n = int(area_m2 / (spacing * spacing))
    return n, max(1, math.ceil(n / MAX_POINTS_PER_REQUEST)) if n else 0


def spacing_for_max_points(area_m2, max_points):
    """Smallest spacing (m, rounded up to whole meters) that gives at most ``max_points`` points."""
    if max_points <= 0 or area_m2 <= 0:
        return 1
    return max(1, math.ceil(math.sqrt(area_m2 / max_points)))
