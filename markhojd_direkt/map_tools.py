"""Map tools: click for height, draw polygon and draw line."""

from qgis.core import Qgis, QgsGeometry, QgsPointXY
from qgis.gui import QgsMapTool, QgsMapToolEmitPoint, QgsRubberBand
from qgis.PyQt.QtCore import Qt, QTimer, pyqtSignal
from qgis.PyQt.QtGui import QColor


class ClickTool(QgsMapToolEmitPoint):
    clicked = pyqtSignal(QgsPointXY)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pt = self.toMapCoordinates(event.pos())
            # the network request runs after the event has been fully handled
            QTimer.singleShot(0, lambda: self.clicked.emit(pt))


class PolygonTool(QgsMapTool):
    """Left click adds a vertex, right click/double click finishes, Esc cancels."""

    finished = pyqtSignal(QgsGeometry)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.points = []
        self.band = QgsRubberBand(canvas, Qgis.GeometryType.Polygon)
        self._style(self.band)

    @staticmethod
    def _style(band):
        band.setColor(QColor(217, 79, 0, 200))
        band.setFillColor(QColor(217, 79, 0, 40))
        band.setWidth(2)

    def reset(self):
        self.points = []
        self.band.reset(Qgis.GeometryType.Polygon)

    def canvasMoveEvent(self, event):
        if self.points:
            self._draw(self.points + [self.toMapCoordinates(event.pos())])

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.points.append(self.toMapCoordinates(event.pos()))
            self._draw(self.points)
        elif event.button() == Qt.MouseButton.RightButton:
            self._finish()

    def canvasDoubleClickEvent(self, event):
        self._finish()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reset()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._finish()

    def _draw(self, pts):
        self.band.reset(Qgis.GeometryType.Polygon)
        if len(pts) >= 2:
            self.band.setToGeometry(QgsGeometry.fromPolygonXY([pts]), None)

    def _finish(self):
        if len(self.points) < 3:
            return
        geom = QgsGeometry.fromPolygonXY([self.points])
        self._draw(self.points)
        self.points = []
        self.finished.emit(geom)  # the rubber band stays until the user clears it

    def deactivate(self):
        self.points = []
        super().deactivate()


class LineTool(QgsMapTool):
    """Left click adds a point, right click/double click finishes, Esc cancels."""

    finished = pyqtSignal(QgsGeometry)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.points = []
        self.band = QgsRubberBand(canvas, Qgis.GeometryType.Line)
        self.band.setColor(QColor(217, 79, 0, 200))
        self.band.setWidth(2)

    def reset(self):
        self.points = []
        self.band.reset(Qgis.GeometryType.Line)

    def canvasMoveEvent(self, event):
        if self.points:
            self._draw(self.points + [self.toMapCoordinates(event.pos())])

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.points.append(self.toMapCoordinates(event.pos()))
            self._draw(self.points)
        elif event.button() == Qt.MouseButton.RightButton:
            self._finish()

    def canvasDoubleClickEvent(self, event):
        self._finish()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reset()
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._finish()

    def _draw(self, pts):
        self.band.reset(Qgis.GeometryType.Line)
        if len(pts) >= 2:
            self.band.setToGeometry(QgsGeometry.fromPolylineXY(pts), None)

    def _finish(self):
        if len(self.points) < 2:
            return
        geom = QgsGeometry.fromPolylineXY(self.points)
        self._draw(self.points)
        self.points = []
        self.finished.emit(geom)  # the rubber band stays until the user clears it

    def deactivate(self):
        self.points = []
        super().deactivate()
