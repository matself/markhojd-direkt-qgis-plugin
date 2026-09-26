"""Kartverktyg: klicka för höjd och rita polygon."""

from qgis.core import QgsGeometry, QgsPointXY, QgsWkbTypes
from qgis.gui import QgsMapTool, QgsMapToolEmitPoint, QgsRubberBand
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor


class ClickTool(QgsMapToolEmitPoint):
    clicked = pyqtSignal(QgsPointXY)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.toMapCoordinates(event.pos()))


class PolygonTool(QgsMapTool):
    """Vänsterklick lägger till hörn, högerklick/dubbelklick avslutar, Esc avbryter."""

    finished = pyqtSignal(QgsGeometry)

    def __init__(self, canvas):
        super().__init__(canvas)
        self.setCursor(Qt.CrossCursor)
        self.points = []
        self.band = QgsRubberBand(canvas, QgsWkbTypes.PolygonGeometry)
        self._style(self.band)

    @staticmethod
    def _style(band):
        band.setColor(QColor(217, 79, 0, 200))
        band.setFillColor(QColor(217, 79, 0, 40))
        band.setWidth(2)

    def reset(self):
        self.points = []
        self.band.reset(QgsWkbTypes.PolygonGeometry)

    def canvasMoveEvent(self, event):
        if self.points:
            self._draw(self.points + [self.toMapCoordinates(event.pos())])

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.points.append(self.toMapCoordinates(event.pos()))
            self._draw(self.points)
        elif event.button() == Qt.RightButton:
            self._finish()

    def canvasDoubleClickEvent(self, event):
        self._finish()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reset()
            event.accept()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._finish()

    def _draw(self, pts):
        self.band.reset(QgsWkbTypes.PolygonGeometry)
        if len(pts) >= 2:
            self.band.setToGeometry(QgsGeometry.fromPolygonXY([pts]), None)

    def _finish(self):
        if len(self.points) < 3:
            return
        geom = QgsGeometry.fromPolygonXY([self.points])
        self._draw(self.points)
        self.points = []
        self.finished.emit(geom)  # bandet blir kvar tills användaren rensar

    def deactivate(self):
        self.points = []
        super().deactivate()
