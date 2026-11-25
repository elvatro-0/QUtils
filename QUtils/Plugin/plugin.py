from qgis.core import QgsApplication, QgsSettings
from qgis.gui import QgisInterface
from qgis.PyQt.QtWidgets import QAction, QMenu
from .provider import QUtilsProvider
from .ui import AsciiWidgetButton
from QUtils import QUtilsIcon

__author__ = "Roxanne Minerals"
__version__ = 1.1


class QUtilsPlugin:
    def __init__(self, iface: QgisInterface):
        self.iface = iface
        self.provider = None

    def initProvider(self):
        self.provideraction = QAction("QUtils Tools")
        self.provideraction.setCheckable(True)
        self.provideraction.toggled.connect(self.toggleprovider)
        self.provideraction.setChecked(QgsSettings().value("QUtils/Provider_Toggle", True, bool))

    def initGui(self):
        self.initProvider()
        self.widgetbutton = AsciiWidgetButton(self.iface)
        self.menu = QMenu("QUtils")
        self.menu.setIcon(QUtilsIcon)
        self.menu.addActions([self.provideraction, self.widgetbutton.action])
        self.iface.pluginMenu().addMenu(self.menu)

    def toggleprovider(self, toggled: bool):
        if toggled:
            self.provider = QUtilsProvider()
            QgsApplication.processingRegistry().addProvider(self.provider)
            QgsSettings().setValue("QUtils/Provider_Toggle", True)
        else:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            QgsSettings().setValue("QUtils/Provider_Toggle", False)
            self.provider = None

    def unload(self):
        self.widgetbutton.unload()
        if self.provider is not None:
            QgsApplication.processingRegistry().removeProvider(self.provider)
        self.iface.pluginMenu().removeAction(self.menu.menuAction())
        self.menu.deleteLater()
