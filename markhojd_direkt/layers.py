"""Skapa och formatera punktlager (PointZ, SWEREF 99 TM)."""

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsPoint,
    QgsProject,
    QgsSimpleMarkerSymbolLayer,
    QgsMarkerSymbol,
    QgsSingleSymbolRenderer,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor, QFont

PROP = "markhojd_direkt"
CLICK_LAYER_NAME = "Markhöjd – punkter"
MAX_LABELED = 1000


def new_layer(name, extra_fields=None):
    """extra_fields: t.ex. [("avstand", "double")] för extra kolumner efter hojd/e/n."""
    uri = "PointZ?crs=EPSG:3006&field=hojd:double&field=e:double&field=n:double"
    for fname, ftype in extra_fields or []:
        uri += f"&field={fname}:{ftype}"
    layer = QgsVectorLayer(uri, name, "memory")
    layer.setCustomProperty(PROP, True)
    return layer


def add_points(layer, rows):
    """Lägg till (e, n, z, *extra) som 3D-punkter. ``extra`` matchar lagrets extrafält.

    Returnerar antal tillagda. Punkter med z=None (ingen höjddata) hoppas över.
    """
    feats = []
    for e, n, z, *extra in rows:
        if z is None:
            continue
        f = QgsFeature(layer.fields())
        f.setGeometry(QgsGeometry(QgsPoint(e, n, z)))
        f.setAttributes([round(z, 2), round(e, 3), round(n, 3)] + [round(v, 2) for v in extra])
        feats.append(f)
    layer.dataProvider().addFeatures(feats)
    layer.updateExtents()
    layer.triggerRepaint()
    return len(feats)


def style_layer(layer, font_family, font_size, decimals):
    """Kryss som symbol och höjdvärdet som etikett."""
    layer.setRenderer(
        QgsSingleSymbolRenderer(_cross_symbol())
    )
    fmt = QgsTextFormat()
    fmt.setFont(QFont(font_family))
    fmt.setSize(font_size)
    fmt.setColor(QColor("#7a1f00"))
    fmt.buffer().setEnabled(True)
    fmt.buffer().setSize(0.8)
    fmt.buffer().setColor(QColor("white"))
    s = QgsPalLayerSettings()
    s.fieldName = f'format_number("hojd", {int(decimals)})'
    s.isExpression = True
    s.placement = Qgis.LabelPlacement.OverPoint
    s.setFormat(fmt)
    s.quadOffset = Qgis.LabelQuadrantPosition.Right  # texten till höger om punkten, vertikalt centrerad
    s.xOffset = 1.5
    s.yOffset = 0
    s.dist = 0
    layer.setLabeling(QgsVectorLayerSimpleLabeling(s))
    layer.setLabelsEnabled(layer.featureCount() <= MAX_LABELED)
    layer.triggerRepaint()


def _cross_symbol():
    sl = QgsSimpleMarkerSymbolLayer(QgsSimpleMarkerSymbolLayer.Cross, 3.0)
    sl.setColor(QColor("#d94f00"))
    sl.setStrokeColor(QColor("#d94f00"))
    sl.setStrokeWidth(0.5)
    sym = QgsMarkerSymbol()
    sym.changeSymbolLayer(0, sl)
    return sym


def plugin_layers():
    return [
        l for l in QgsProject.instance().mapLayers().values()
        if isinstance(l, QgsVectorLayer) and l.customProperty(PROP)
    ]


def find_click_layer():
    for l in plugin_layers():
        if l.name() == CLICK_LAYER_NAME:
            return l
    return None
