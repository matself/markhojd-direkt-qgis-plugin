import os

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dock import MarkhojdDock

TITLE = "Markhöjd direkt (Lantmäteriet)"


class MarkhojdPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.dock = None
        self.action = None

    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))
        self.action = QAction(icon, TITLE, self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.toggled.connect(self._toggle)
        self.iface.addPluginToMenu(TITLE, self.action)
        self.iface.addToolBarIcon(self.action)
        self.dock = MarkhojdDock(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.hide()
        self.dock.visibilityChanged.connect(self.action.setChecked)

    def _toggle(self, on):
        self.dock.setVisible(on)

    def unload(self):
        self.iface.removePluginMenu(TITLE, self.action)
        self.iface.removeToolBarIcon(self.action)
        self.dock.cleanup()
        self.iface.removeDockWidget(self.dock)
        self.dock.deleteLater()
