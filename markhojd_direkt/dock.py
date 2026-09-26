"""Panel och logik för Markhöjd direkt."""

import math
import os

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsAuthMethodConfig,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsMapLayerProxyModel,
    QgsProject,
    QgsSettings,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsAuthConfigSelect, QgsMapLayerComboBox
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import core, layers
from .client import MarkhojdClient, MarkhojdError
from .grid import grid_points
from .map_tools import ClickTool, PolygonTool

CRS_3006 = QgsCoordinateReferenceSystem("EPSG:3006")
SETTINGS = "markhojd_direkt/"
EXACT_COUNT_MAX_CELLS = 200_000  # över detta uppskattas antalet i stället för att räknas exakt
TEST_POINT = (616919.8, 6728782.96)  # exempelpunkt ur Lantmäteriets tekniska beskrivning


class KeyDialog(QDialog):
    """Sparar användarnamn/lösenord (Basic) i QGIS autentiseringsdatabas."""

    def __init__(self, environment, parent=None):
        super().__init__(parent)
        self.environment = environment
        self.authcfg = None
        self.setWindowTitle("Ny anslutning till Lantmäteriet")
        form = QFormLayout(self)
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        form.addRow("Användarnamn", self.user)
        form.addRow("Lösenord", self.password)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def accept(self):
        user, password = self.user.text().strip(), self.password.text()
        if not user or not password:
            return
        cfg = QgsAuthMethodConfig()
        cfg.setName(f"Markhöjd direkt ({self.environment}, {user})")
        cfg.setMethod("Basic")
        cfg.setConfig("username", user)
        cfg.setConfig("password", password)
        am = QgsApplication.authManager()
        am.storeAuthenticationConfig(cfg)
        am.updateConfigAuthMethods()
        self.authcfg = cfg.id()
        super().accept()


class MarkhojdDock(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__("Markhöjd direkt (Lantmäteriet)", parent)
        self.setObjectName("MarkhojdDirektDock")
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.geom = None  # område i EPSG:3006
        self._cancel = False
        self._running = False

        self.click_tool = ClickTool(self.canvas)
        self.click_tool.clicked.connect(self.on_click)
        self.poly_tool = PolygonTool(self.canvas)
        self.poly_tool.finished.connect(self.on_polygon)

        self._loading = True
        self._build_ui()
        self._load_settings()
        self._loading = False
        self._update_info()

    # ---------------------------------------------------------------- UI
    def _build_ui(self):
        body = QWidget()
        lay = QVBoxLayout(body)

        # Anslutning
        g = QGroupBox("Anslutning")
        f = QFormLayout(g)
        self.env = QComboBox()
        self.env.addItem("Produktion", "production")
        self.env.addItem("Verifiering", "verification")
        self.auth = QgsAuthConfigSelect()
        row = QHBoxLayout()
        b_new = QPushButton("Ny nyckel…")
        b_test = QPushButton("Testa")
        b_new.clicked.connect(self.new_key)
        b_test.clicked.connect(self.test_connection)
        row.addWidget(b_new)
        row.addWidget(b_test)
        f.addRow("Miljö", self.env)
        f.addRow("Autentisering", self.auth)
        f.addRow(row)
        lay.addWidget(g)

        # Höjd i punkt
        g = QGroupBox("Höjd i en punkt")
        f = QFormLayout(g)
        self.btn_click = QPushButton("Klicka i kartan för höjd")
        self.btn_click.setCheckable(True)
        self.btn_click.toggled.connect(self.toggle_click_tool)
        self.font = QFontComboBox()
        self.size = QDoubleSpinBox()
        self.size.setRange(5, 60)
        self.size.setSuffix(" pt")
        self.decimals = QSpinBox()
        self.decimals.setRange(0, 3)
        self.font.currentFontChanged.connect(self._style_changed)
        self.size.valueChanged.connect(self._style_changed)
        self.decimals.valueChanged.connect(self._style_changed)
        f.addRow(self.btn_click)
        f.addRow("Typsnitt", self.font)
        f.addRow("Textstorlek", self.size)
        f.addRow("Decimaler", self.decimals)
        lay.addWidget(g)

        # Grid
        g = QGroupBox("Höjdgrid i ett område")
        v = QVBoxLayout(g)
        row = QHBoxLayout()
        self.btn_draw = QPushButton("Rita område")
        self.btn_draw.setCheckable(True)
        self.btn_draw.toggled.connect(self.toggle_poly_tool)
        b_sel = QPushButton("Markerad polygon")
        b_sel.setToolTip("Använd de markerade polygonerna i aktivt lager")
        b_sel.clicked.connect(self.use_selection)
        b_clear = QPushButton("Rensa")
        b_clear.clicked.connect(self.clear_area)
        for b in (self.btn_draw, b_sel, b_clear):
            row.addWidget(b)
        v.addLayout(row)
        hint = QLabel("Vänsterklick = hörn, högerklick/Enter = klar, Esc = börja om.")
        hint.setWordWrap(True)
        v.addWidget(hint)
        f = QFormLayout()
        self.spacing = QDoubleSpinBox()
        self.spacing.setRange(1, 5000)
        self.spacing.setDecimals(0)
        self.spacing.setSuffix(" m")
        self.maxpts = QSpinBox()
        self.maxpts.setRange(1, 1_000_000)
        self.maxpts.setSingleStep(1000)
        self.spacing.valueChanged.connect(self._update_info)
        self.maxpts.valueChanged.connect(self._update_info)
        b_auto = QPushButton("Anpassa punktavstånd till max antal")
        b_auto.clicked.connect(self.auto_spacing)
        f.addRow("Punktavstånd", self.spacing)
        f.addRow("Max antal punkter", self.maxpts)
        v.addLayout(f)
        v.addWidget(b_auto)
        self.info = QLabel()
        self.info.setWordWrap(True)
        v.addWidget(self.info)
        self.btn_fetch = QPushButton("Hämta höjder")
        self.btn_fetch.clicked.connect(self.fetch_grid)
        self.btn_cancel = QPushButton("Avbryt")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        v.addWidget(self.btn_fetch)
        v.addWidget(self.progress)
        v.addWidget(self.btn_cancel)
        lay.addWidget(g)

        # Spara
        g = QGroupBox("Spara som 3D-punkter")
        v = QVBoxLayout(g)
        self.save_layer = QgsMapLayerComboBox()
        self.save_layer.setFilters(QgsMapLayerProxyModel.PointLayer)
        b_save = QPushButton("Spara lager…")
        b_save.clicked.connect(self.save)
        v.addWidget(self.save_layer)
        v.addWidget(b_save)
        lay.addWidget(g)
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        self.setWidget(scroll)

    # ------------------------------------------------------- settings
    def _load_settings(self):
        s = QgsSettings()
        self.env.setCurrentIndex(max(0, self.env.findData(s.value(SETTINGS + "env", "production"))))
        self.auth.setConfigId(s.value(SETTINGS + "authcfg", ""))
        self.font.setCurrentFont(QFont(s.value(SETTINGS + "font", "Arial")))
        self.size.setValue(float(s.value(SETTINGS + "size", 10)))
        self.decimals.setValue(int(s.value(SETTINGS + "decimals", 1)))
        self.spacing.setValue(float(s.value(SETTINGS + "spacing", 10)))
        self.maxpts.setValue(int(s.value(SETTINGS + "maxpts", 20000)))

    def _save_settings(self):
        s = QgsSettings()
        s.setValue(SETTINGS + "env", self.env.currentData())
        s.setValue(SETTINGS + "authcfg", self.auth.configId())
        s.setValue(SETTINGS + "font", self.font.currentFont().family())
        s.setValue(SETTINGS + "size", self.size.value())
        s.setValue(SETTINGS + "decimals", self.decimals.value())
        s.setValue(SETTINGS + "spacing", self.spacing.value())
        s.setValue(SETTINGS + "maxpts", self.maxpts.value())

    def _style_changed(self, *_):
        if self._loading:
            return
        self._save_settings()
        for layer in layers.plugin_layers():
            self._style(layer)

    def _style(self, layer):
        layers.style_layer(layer, self.font.currentFont().family(), self.size.value(), self.decimals.value())

    def closeEvent(self, event):
        self._save_settings()
        self.btn_click.setChecked(False)
        self.btn_draw.setChecked(False)
        super().closeEvent(event)

    # ------------------------------------------------------ helpers
    def msg(self, text, level=Qgis.Info, duration=6):
        self.iface.messageBar().pushMessage("Markhöjd direkt", text, level, duration)

    def client(self):
        cfg = self.auth.configId()
        if not cfg:
            self.msg("Välj eller skapa en autentiseringskonfiguration först.", Qgis.Warning)
            return None
        self._save_settings()
        return MarkhojdClient(cfg, self.env.currentData())

    def new_key(self):
        dlg = KeyDialog(self.env.currentData(), self)
        if dlg.exec() and dlg.authcfg:
            self.auth.setConfigId(dlg.authcfg)
            self._save_settings()

    def test_connection(self):
        c = self.client()
        if not c:
            return
        try:
            up = c.health()
            z = c.get_height(*TEST_POINT)
            self.msg(f"Tjänsten är {'uppe' if up else 'nere'}. Testpunkt: {z} m.", Qgis.Success)
        except MarkhojdError as e:
            self.msg(str(e), Qgis.Critical, 12)

    # ---------------------------------------------------- click tool
    def toggle_click_tool(self, on):
        if on:
            self.btn_draw.setChecked(False)
            self.canvas.setMapTool(self.click_tool)
        elif self.canvas.mapTool() is self.click_tool:
            self.canvas.unsetMapTool(self.click_tool)

    def on_click(self, pt):
        c = self.client()
        if not c:
            return
        xf = QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), CRS_3006, QgsProject.instance())
        p = xf.transform(pt)
        try:
            z = c.get_height(p.x(), p.y())
        except MarkhojdError as e:
            self.msg(str(e), Qgis.Critical, 12)
            return
        if z is None:
            self.msg("Ingen höjddata för den punkten.", Qgis.Warning)
            return
        layer = layers.find_click_layer()
        if layer is None:
            layer = layers.new_layer(layers.CLICK_LAYER_NAME)
            QgsProject.instance().addMapLayer(layer)
        layers.add_points(layer, [(p.x(), p.y(), z)])
        self._style(layer)

    # ------------------------------------------------------- area
    def toggle_poly_tool(self, on):
        if on:
            self.btn_click.setChecked(False)
            self.poly_tool.reset()
            self.canvas.setMapTool(self.poly_tool)
        elif self.canvas.mapTool() is self.poly_tool:
            self.canvas.unsetMapTool(self.poly_tool)

    def on_polygon(self, geom):
        self.geom = QgsGeometry(geom)
        self.geom.transform(
            QgsCoordinateTransform(self.canvas.mapSettings().destinationCrs(), CRS_3006, QgsProject.instance())
        )
        self.btn_draw.setChecked(False)
        self._update_info()

    def use_selection(self):
        layer = self.iface.activeLayer()
        if not isinstance(layer, QgsVectorLayer) or layer.geometryType() != QgsWkbTypes.PolygonGeometry:
            self.msg("Markera ett polygonlager som aktivt lager.", Qgis.Warning)
            return
        feats = layer.selectedFeatures()
        if not feats:
            self.msg("Inga polygoner är markerade i det aktiva lagret.", Qgis.Warning)
            return
        geom = QgsGeometry.unaryUnion([f.geometry() for f in feats])
        geom.transform(QgsCoordinateTransform(layer.crs(), CRS_3006, QgsProject.instance()))
        self.geom = geom
        self.poly_tool.reset()
        self.poly_tool.band.setToGeometry(geom, CRS_3006)
        self._update_info()

    def clear_area(self):
        self.geom = None
        self.poly_tool.reset()
        self._update_info()

    def _update_info(self, *_):
        if not self.geom or self.geom.isEmpty():
            self.info.setText("Inget område valt.")
            self.btn_fetch.setEnabled(False)
            return
        area = self.geom.area()
        spacing, maxpts = self.spacing.value(), self.maxpts.value()
        bb = self.geom.boundingBox()
        if bb.area() / (spacing * spacing) <= EXACT_COUNT_MAX_CELLS:
            pts = grid_points(self.geom, spacing, limit=maxpts)
            n = maxpts + 1 if pts is None else len(pts)  # None = över maxgränsen
            exact = pts is not None
        else:
            n, exact = core.estimate_grid(area, spacing)[0], False
        req = max(1, math.ceil(n / core.MAX_POINTS_PER_REQUEST)) if n else 0
        head = f"Yta {area / 10000:,.2f} ha: "
        if exact:
            txt = head + f"{n:,} punkter i {req} anrop."
        elif n > maxpts and bb.area() / (spacing * spacing) <= EXACT_COUNT_MAX_CELLS:
            txt = head + f"fler än max ({maxpts:,}) punkter; öka punktavståndet."
        else:
            txt = head + f"ca {n:,} punkter i ca {req} anrop."
            if n > maxpts:
                txt += " Över max; öka punktavståndet."
        self.info.setText(txt.replace(",", " "))
        self.btn_fetch.setEnabled(0 < n <= maxpts and not self._running)

    def auto_spacing(self):
        if self.geom:
            self.spacing.setValue(core.spacing_for_max_points(self.geom.area(), self.maxpts.value()))

    # ------------------------------------------------------- fetch
    def _on_cancel(self):
        self._cancel = True

    def fetch_grid(self):
        c = self.client()
        if not c or not self.geom:
            return
        spacing = self.spacing.value()
        pts = grid_points(self.geom, spacing, limit=self.maxpts.value())
        if pts is None:
            self._update_info()
            return
        if not pts:
            self.msg("Inga gridpunkter föll inom området – minska punktavståndet.", Qgis.Warning)
            return
        self._chunks = core.chunk_points(pts)
        self._layer = layers.new_layer(f"Markhöjd – grid {spacing:g} m")
        QgsProject.instance().addMapLayer(self._layer)
        self._done = 0
        self._total = len(pts)
        self._client = c
        self._nodata = 0
        self._cancel = False
        self._running = True
        self.btn_fetch.setEnabled(False)
        self.btn_cancel.setVisible(True)
        self.progress.setRange(0, self._total)
        self.progress.setValue(0)
        self.progress.setVisible(True)
        QTimer.singleShot(0, self._step)

    def _step(self):
        if self._cancel or not self._chunks:
            return self._finish()
        chunk = self._chunks.pop(0)
        try:
            res = self._client.get_heights(chunk)
        except MarkhojdError as e:
            self.msg(str(e), Qgis.Critical, 15)
            return self._finish(failed=True)
        self._nodata += sum(1 for r in res if r[2] is None)
        layers.add_points(self._layer, res)
        self._done += len(chunk)
        self.progress.setValue(self._done)
        QTimer.singleShot(0, self._step)

    def _finish(self, failed=False):
        self._running = False
        self.btn_cancel.setVisible(False)
        self.progress.setVisible(False)
        n = self._layer.featureCount()
        self._style(self._layer)
        text = f"{n} höjdpunkter hämtade"
        if self._nodata:
            text += f" ({self._nodata} saknade höjddata)"
        if self._cancel:
            text += " – avbrutet"
        self.msg(text + ".", Qgis.Warning if (failed or self._cancel) else Qgis.Success)
        self.save_layer.setLayer(self._layer)
        self._update_info()

    # -------------------------------------------------------- save
    def save(self):
        layer = self.save_layer.currentLayer()
        if not layer:
            self.msg("Välj ett punktlager att spara.", Qgis.Warning)
            return
        path, flt = QFileDialog.getSaveFileName(
            self,
            "Spara 3D-punkter",
            "",
            "GeoPackage (*.gpkg);;Shapefile (*.shp);;CSV med X,Y,Z (*.csv)",
        )
        if not path:
            return
        ext = {"GeoPackage": ".gpkg", "Shapefile": ".shp", "CSV": ".csv"}[flt.split(" ")[0]]
        if not path.lower().endswith(ext):
            path += ext
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.fileEncoding = "UTF-8"
        opts.driverName = {".gpkg": "GPKG", ".shp": "ESRI Shapefile", ".csv": "CSV"}[ext]
        if ext == ".csv":
            opts.layerOptions = ["GEOMETRY=AS_XYZ"]
        res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, QgsProject.instance().transformContext(), opts)
        if res[0] == QgsVectorFileWriter.NoError:
            self.msg(f"Sparade {layer.featureCount()} punkter till {os.path.basename(path)}.", Qgis.Success)
        else:
            self.msg(f"Kunde inte spara: {res[1]}", Qgis.Critical, 12)
