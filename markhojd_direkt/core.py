"""Ren logik utan QGIS-beroenden: begränsningar, uppdelning i anrop och tolkning av svar."""

import json
import math

SRID = 3006
CRS_URN = "urn:ogc:def:crs:EPSG::3006"

# Begränsningar enligt teknisk beskrivning v1.0.1 (GeometriRequest)
MAX_POINTS_PER_REQUEST = 1000
# Felmeddelandet i den tekniska beskrivningen visar att en yta får vara högst 1 000 000 m2.
# Vi håller varje anrop inom en ruta på 900 x 900 m så att gränsen inte kan slå till.
MAX_AREA_M2 = 1_000_000
TILE_SIZE_M = 900.0

DEFAULT_NODATA = -9999.0


def chunk_points(points, max_points=MAX_POINTS_PER_REQUEST, tile=TILE_SIZE_M):
    """Dela punkter i anrop om högst ``max_points`` punkter inom en ruta på ``tile`` m.

    Punkterna sorteras rutvis så att varje anrop blir geografiskt kompakt.
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
    """Dela punkter i anrop om högst ``max_points`` punkter, utan att ändra ordningen.

    Används för linjer, där ordningen behövs för att avståndet längs linjen ska stämma.
    Ingen yt-baserad uppdelning behövs, eftersom tjänstens enda dokumenterade begränsning
    för LineString/MultiLineString är antalet brytpunkter.
    """
    return [points[i : i + max_points] for i in range(0, len(points), max_points)]


def build_multipoint_body(points):
    """JSON-kropp (bytes) för POST /hojd med en MultiPoint i SWEREF 99 TM."""
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
    """Tolka ett HojdResponse (dict). Returnerar lista av (e, n, z eller None)."""
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
    """Läsbar text ur ett Fault-svar (code/reason/errors)."""
    try:
        data = json.loads(text)
        parts = [f"{data.get('code', '')} {data.get('reason', '')}".strip()]
        parts += [str(e) for e in data.get("errors") or []]
        return ": ".join(p for p in parts if p)
    except (ValueError, AttributeError, TypeError):
        return (text or "").strip()[:300]


def estimate_grid(area_m2, spacing):
    """Uppskattat antal gridpunkter och antal anrop för en yta."""
    if spacing <= 0:
        return 0, 0
    n = int(area_m2 / (spacing * spacing))
    return n, max(1, math.ceil(n / MAX_POINTS_PER_REQUEST)) if n else 0


def spacing_for_max_points(area_m2, max_points):
    """Minsta glesning (m, avrundad uppåt till helt meter) som ger högst ``max_points`` punkter."""
    if max_points <= 0 or area_m2 <= 0:
        return 1
    return max(1, math.ceil(math.sqrt(area_m2 / max_points)))
