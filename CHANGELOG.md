# Changelog

## 1.0.0
- First stable release. Renamed to "Geodata: Markhöjd direkt (Lantmäteriet)" with a new icon, part of a shared naming and icon scheme for the four Lantmäteriet plugins.
- Code comments, docstrings, metadata and documentation translated to English; the user interface remains in Swedish and is explained in the README.
- Qt6-compatible enum usage; marked as QGIS 4 ready.

## 0.1.6
- "Adjust point spacing" now aims for about 100 points (the same limit as the warning text), not for "Max number of points". The maximum is only a safeguard and is used as the target only if it is set lower.

## 0.1.5
- The grid warns (orange text) when there are more than 100 points, suggesting a larger point spacing. The grid is meant for e.g. a plot map, not for building a custom elevation model from the points.
- New optional "Show profile" button for a fetched line: opens a panel in QGIS with distance/height as a graph, built on the QGIS elevation profile component. It is not shown automatically.

## 0.1.4
- A MultiLineString (several line parts, mixed order/direction) is automatically merged into one continuous line for heights along a line. A truly disconnected line (gap) is rejected with a clear message instead of giving wrong distances.

## 0.1.3
- New mode: heights along a line, with a draw-line tool or an existing line feature. The points get an attribute avstand (meters from the start of the line), suitable for an elevation profile.

## 0.1.2
- Installation via plugin repository (plugins.xml) and updated README.

## 0.1.1
- Login with username/password (Basic) instead of OAuth2; own network manager (no crashes or login dialogs on 401).
- The height value is placed to the right of the point.
- Exact number of grid points in the panel.
- Disclaimer (independent plugin) and user guide in docs.
- LICENSE (GPL-3.0) included in the ZIP package.

## 0.1.0
- First version: click for height, height grid in a drawn/selected area, save as 3D points.
