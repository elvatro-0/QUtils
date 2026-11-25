from qgis.gui import QgsMapLayerComboBox, QgsDoubleSpinBox, QgsRasterBandComboBox, QgsCollapsibleGroupBox, QgisInterface
from qgis.core import Qgis, QgsRasterLayer, QgsSettings, QgsProcessingContext
from qgis.PyQt.QtWidgets import QAction, QFormLayout, QCheckBox, QTabBar, QComboBox

from QUtils import QUtilsIcon
from QUtils.Widgets import *
from QUtils.Console import Feedback, createContextAndFeedback
from QUtils.Processing import RasterProcessing, VectorProcessing

__author__ = "Roxanne Minerals"
__version__ = 1.1


def ReportError(message: str, feedback: Feedback):
    feedback.reportError(message)
    feedback.finished.emit(False)

class SpinBox(QgsDoubleSpinBox):
    def __init__(self, value: float = None, minimum: float = None, maximum: float = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if minimum is not None:
            self.setMinimum(minimum)
        if maximum is not None:
            self.setMaximum(maximum)
        if value is not None:
            self.setValue(value)
        self.setDecimals(3)

class ToMinMax(QVBoxLayout):
    def __init__(self, buttonsize: QSize, tomin: Callable[[], Any], tomax: Callable[[], Any], disable = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tomin = ToolButton(buttonsize, tooltip="To Min", autoraise=False)
        self.tomin.setArrowType(Qt.ArrowType.DownArrow)
        self.tomin.setDisabled(disable)
        self.tomin.clicked.connect(tomin)
        self.tomax = ToolButton(buttonsize, tooltip="To Max", autoraise=False)
        self.tomax.setArrowType(Qt.ArrowType.UpArrow)
        self.tomax.setDisabled(disable)
        self.tomax.clicked.connect(tomax)
        self.addWidget(self.tomax)
        self.addWidget(self.tomin)

class ParameterWidget(QWidget):
    def __init__(self, layername: str, tabname: str, feedback: Feedback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.feedback = feedback
        self.box = QFormLayout(self)
        self.box.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        self.layer = QgsMapLayerComboBox()
        self.layer.setExcludedProviders(["wms"])
        self.box.addRow(layername, self.layer)
        self.tabname = SimpleLineEdit()
        self.tabname.setPlaceholderText(tabname)
        self.collapsebox = QgsCollapsibleGroupBox("Error Log")
        self.collapsebox.setCollapsed(True)
        self.logbox = QVBoxLayout(self.collapsebox)
        self.log = SimpleTextEdit(readOnly=True)
        self.logbox.addWidget(self.log)

class rasterParmeterWidget(ParameterWidget):
    def __init__(self, tabname, synclayer: Callable[[], Any], *args, **kwargs):
        super().__init__("Raster Layer", tabname, *args, **kwargs)
        self.synclayer = synclayer
        self.layer.setFilters(Qgis.LayerFilter.RasterLayer)
        self.band = QgsRasterBandComboBox()
        self.band.setLayer(self.layer.currentLayer())
        self.band.setBand(1)
        QgsProject.instance().layersAdded.connect(lambda layers: QTimer.singleShot(0, self._sync))
        QgsProject.instance().layersRemoved.connect(lambda ids: QTimer.singleShot(0, self._sync))

    def _sync(self):
        self.band.setLayer(self.layer.currentLayer())
        self.synclayer()

    

class PeakWidget(rasterParmeterWidget):
    def __init__(self, *args, **kwargs):
        super().__init__("Histogram", self._syncLayer, *args, **kwargs)
        self._setLayerMinMax()
        self.band.bandChanged.connect(lambda band: self._setLayerMinMax())
        self.layer.layerChanged.connect(self.band.setLayer)
        self.layer.layerChanged.connect(self._layerChanged)
        self.bins = SpinBox(200, 1, 9999)
        self.bins.setDecimals(0)
        self.y_truncpercent = SpinBox(100, 0, 999)
        self.minmax = QHBoxLayout()
        self.minimum = SpinBox(0, 0)
        disable = self.layer.currentLayer() is None
        smallbutton = QSize(int(self.size().width() * 0.04), int(self.size().height() * 0.02))
        self.min_tominmax = ToMinMax(smallbutton, lambda: self._min_tominmax(0), lambda: self._min_tominmax(1), disable)
        self.minimum.textChanged.connect(lambda text: self._check_minmaxbuttons())
        self.maximum = SpinBox(100, maximum=100)
        self.max_tominmax = ToMinMax(smallbutton, lambda: self._max_tominmax(0), lambda: self._max_tominmax(1), disable)
        self.maximum.textChanged.connect(lambda text: self._check_minmaxbuttons())
        self.minmax.addWidget(self.minimum)
        self.minmax.addLayout(self.min_tominmax)
        self.minmax.addWidget(self.maximum)
        self.minmax.addLayout(self.max_tominmax)
        self.minimum.setMaximum(self.maximum.value())
        self.minimum.valueChanged.connect(self.maximum.setMinimum)
        self.maximum.setMinimum(self.minimum.value())
        self.maximum.valueChanged.connect(self.minimum.setMaximum)
        self.showtable = QCheckBox()
        self.showtable.setChecked(True)
        self.box.addRow("Band", self.band)
        self.box.addRow("Number of Bins", self.bins)
        self.box.addRow("X-Axis Min and Max", self.minmax)
        self.box.addRow("Y-Axis Truncate (%)", self.y_truncpercent)
        self.box.addRow("Tab Name", self.tabname)
        self.box.addRow("Show Table", self.showtable)
        self.box.addRow(self.collapsebox)

    def _check_minmaxbuttons(self):
        if self.layer.currentLayer() is None:
            return None
        def check(spinboxtext: str, _min: str, _max: str, tominmax: ToMinMax):
            if spinboxtext == _min:
                tominmax.tomin.setDisabled(True)
            else: tominmax.tomin.setDisabled(False)
            if spinboxtext == _max:
                tominmax.tomax.setDisabled(True)
            else: tominmax.tomax.setDisabled(False)

        _min = str(round(self.layermin, 3))
        _max = str(round(float(self.maximum.text()), 3))
        spinboxtext = str(round(float(self.minimum.text()), 3))
        check(spinboxtext, _min, _max, self.min_tominmax)

        _min = str(round(float(self.minimum.text()), 3))
        _max = str(round(self.layermax, 3))
        spinboxtext = str(round(float(self.maximum.text()), 3))
        check(spinboxtext, _min, _max, self.max_tominmax)

    def _min_tominmax(self, to: Literal[0, 1]):
        if to == 0:
            self.minimum.setValue(self.layermin)
        elif to == 1:
            self.minimum.setValue(self.maximum.value())
    def _max_tominmax(self, to: Literal[0, 1]):
        if to == 0:
            self.maximum.setValue(self.minimum.value())
        elif to == 1:
            self.maximum.setValue(self.layermax)

    def _layerChanged(self, layer: QgsRasterLayer):
        if layer is None:
            return None
        self._setLayerMinMax()
        self._check_minmaxbuttons()
        self.maximum.setMaximum(self.layermax)
        self.minimum.setMinimum(self.layermin)

    def _syncLayer(self):
        layer = self.layer.currentLayer()
        self._layerChanged(layer)

    def _setLayerMinMax(self):
        if self.layer.currentLayer() is None:
            return None
        stats = self.layer.currentLayer().dataProvider().bandStatistics(self.band.currentBand())
        self.layermin = stats.minimumValue
        self.layermax = stats.maximumValue

    def run(self, context):
        if self.layer.currentLayer() is None:
            return ReportError("No Raster Layer Selected", self.feedback)
        layer = self.layer.currentLayer()
        bins = int(self.bins.value())
        y_truncpercent = self.y_truncpercent.value()
        minValue = self.minimum.value()
        maxValue = self.maximum.value()
        if minValue == maxValue:
            return ReportError("Min and Max value are the same.", self.feedback)
        band = self.band.currentBand()
        showTable = self.showtable.isChecked()
        tabname = self.tabname.text()
        if not tabname: tabname = "Histogram"
        RasterProcessing(layer.id(), context, self.feedback).peak(bins, y_truncpercent, minValue, maxValue, band, showTable, tabname)

class CrossSectionWidget(rasterParmeterWidget):
    def __init__(self, *args, **kwargs):
        super().__init__("Cross Section", self._syncLayer, *args, **kwargs)
        self.layer.layerChanged.connect(lambda layer: (self.band.setLayer(layer), self._syncLayer()))
        self.transect = QgsMapLayerComboBox()
        self.transect.setExcludedProviders(["wms"])
        self.transect.setFilters(Qgis.LayerFilter.LineLayer)
        self.transect.setToolTip("Takes first feature")
        self.autoformat = QHBoxLayout()
        buttonsize = QSize(int(self.size().width() * 0.035), int(self.size().width() * 0.035))
        self.autoformat_button = PushButton(buttonsize, icon=QgsApplication.getThemeIcon("/mActionElevationProfile.svg"), tooltip="Auto Scale (set 1:1)")
        self.autoformat_button.pressed.connect(self._autoFormat)
        self.resolution = SpinBox(2, 1, 999999)
        self.resolution.setDecimals(0)
        self.resolution.setToolTip("Size of each Step (map units)")
        self.autoformat.addWidget(self.resolution)
        self.autoformat.addWidget(self.autoformat_button)
        self.graphheight = SpinBox(29, 1, 999999)
        self.graphheight.setDecimals(0)
        self.minybox = QHBoxLayout()
        self.miny = SpinBox(0, -999999, 999999)
        self.miny.setToolTip("Minimum Elevation")
        self.miny.textChanged.connect(self._disableMinYButtons)
        smallbuttonsize = QSize(int(self.size().width() * 0.04), int(self.size().height() * 0.02))
        disable = self.layer.currentLayer() is None
        self.miny_button = ToMinMax(smallbuttonsize, lambda: (self.miny.setValue(0), self._disableMinYButtons()), self._syncLayer, disable)
        self.miny_button.tomax.setToolTip("To Layer Min")
        self.miny_button.tomin.setToolTip("To Zero")
        self.minybox.addWidget(self.miny)
        self.minybox.addLayout(self.miny_button)
        self.box.addRow("Band", self.band)
        self.box.addRow("Transect", self.transect)
        self.box.addRow("Resolution", self.autoformat)
        self.box.addRow("Graph Height", self.graphheight)
        self.box.addRow("Minimum Elevation", self.minybox)
        self.box.addRow("Tab Name", self.tabname)
        self.box.addRow(self.collapsebox)
        self._syncLayer()

    def _syncLayer(self):
        self.miny.setValue(0)
        if self.layer.currentLayer() is not None:
            self.miny.setValue(self.layer.currentLayer().dataProvider().bandStatistics(self.band.currentBand()).minimumValue)
            self._disableMinYButtons()

    def _disableMinYButtons(self):
        if self.layer.currentLayer() is None:
            self.miny_button.tomin.setDisabled(True)
            self.miny_button.tomax.setDisabled(True)
            return None
        self.miny_button.tomin.setDisabled(self.miny.value() == 0)
        self.miny_button.tomax.setDisabled(self.miny.value() == round(self.layer.currentLayer().dataProvider().bandStatistics(self.band.currentBand()).minimumValue, 3))

    def _autoFormat(self):
        context = QgsProcessingContext()
        context.setProject(QgsProject.instance())
        self.run(context, True)

    def run(self, context, autoformat = False):
        if self.layer.currentLayer() is None:
            return ReportError("No Raster Layer Selected", self.feedback)
        if self.transect.currentLayer() is None:
            return ReportError("No Transect Layer Selected", self.feedback)
        layer = self.layer.currentLayer()
        transectfeature = VectorProcessing(self.transect.currentLayer().id(), context, self.feedback).Feature()
        if not transectfeature:
            return ReportError("Transect is empty", self.feedback)
        geom = transectfeature.geometry()
        geom.convertToSingleType()
        transect = geom.asPolyline()
        resolution = self.resolution.value()
        band = self.band.currentBand()
        graphheight = int(self.graphheight.value())
        miny = self.miny.value()
        tabname = self.tabname.text()
        if not tabname: tabname = "Cross Section"
        feedback = self.feedback
        if autoformat:
            feedback = QgsProcessingFeedback()
        topodict = RasterProcessing(layer.id(), context, feedback).topographicCrossSection(transect, resolution, band, graphheight, miny, autoformat, tabname)
        if autoformat:
            maxsum = max(topodict.values())
            size = (maxsum - miny) / self.resolution.value()
            self.graphheight.setValue(size)



class AsciiWidget(FeedbackWidget):
    closed = pyqtSignal()

    def __init__(self, iface):
        self.context, self.feedback = createContextAndFeedback(False)
        super().__init__(self.feedback, withtabs=True, tabname="Parmeters")
        self.setWindowTitle("QUtils Ascii Viewer")
        self.setWindowIcon(QUtilsIcon)
        self.iface = iface
        self.log.hide()
        self.elapsedappendbutton.hide()
        self.linenumberappendbutton.hide()
        self.savelog.hide()
        self.copytext.hide()
        self.clearlog.hide()
        self.keybinds.hide()
        self.wrapbutton.hide()
        self.runbutton = PushButton(QSize(int(self.size().width() * 0.07), int(self.size().height() * 0.04)), "Run")
        self.runbutton.clicked.connect(self.run)

        self.peakwidget = PeakWidget(self.feedback)
        self.crosssectionwidget = CrossSectionWidget(self.feedback)
        self.asciiwidgets = [self.crosssectionwidget, self.peakwidget]
        self.currentasciiwidget = self.crosssectionwidget
        self.log = self.crosssectionwidget.log
        self.log.show()
        self.logpage.addWidget(self.peakwidget)
        self.peakwidget.hide()
        self.logpage.addWidget(self.crosssectionwidget)

        self.asciipicker = QComboBox()
        self.asciipicker.addItems(["Cross Section", "Histogram"])
        self.asciipicker.currentIndexChanged.connect(self._switchAscii)
        self.rendering = QLabel("Rendering...")
        self.rendering.hide()
        self._bottom.addWidget(self.rendering)
        self._bottom.addWidget(self.asciipicker)
        self._bottom.addWidget(self.runbutton)
        
        self.setObjectName("QUtilsAsciiWidget")
        self.tabs.setTabsClosable(True)
        tabbar = self.tabs.tabBar()
        tabbar.setTabButton(0, QTabBar.ButtonPosition.RightSide, None)
        tabbar.setTabButton(0, QTabBar.ButtonPosition.LeftSide, None)
        self.tabs.tabCloseRequested.connect(self.tabs.removeTab)
        self.tostartbuffer = SimpleInfoWidget(self, flags=Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.tostartbuffer.setWindowOpacity(0)
        self.toendbuffer = paintedSimpleInfoWidget(self, flags=Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.toendbuffer.setWindowOpacity(0)

        self.cancelButton.clicked.connect(lambda: QTimer.singleShot(0, self._cancel))
        self.feedback.finished.connect(lambda success: QTimer.singleShot(0, lambda: self.newFeedback() if not success else None))
        sys.excepthook = self.sysexcepthook
        self.running = False

    def _cancel(self):
        if not self.running:
            return None
        self._setProgress(100, True, True)
        print("Canceled")
        self.feedback.reportError("Canceled", True)
        self.newFeedback()

    def newFeedback(self):
        self.feedback = Feedback()
        self.feedback.widget = self
        self.context.setFeedback(self.feedback)
        for widget in self.asciiwidgets:
            widget.feedback = self.feedback
        self.feedback.messageLogged.connect(self.appendMessage)
        self.feedback.progressChanged.connect(self._setProgress)
        self.feedback.finished.connect(lambda complete: self._setProgress(100, True, not complete))
        self.cancelButton.clicked.connect(self.feedback.cancel)

    def _switchAscii(self, index: int):
        for asciiwidget in self.asciiwidgets: asciiwidget.hide()
        self.asciiwidgets[index].show()
        self.currentasciiwidget = self.asciiwidgets[index]
        self.log.hide()
        self.log = self.currentasciiwidget.log

    def run(self):
        self.running = True
        self.rendering.show()
        self.currentasciiwidget.run(self.context)
        self.rendering.hide()
        self.running = False

    def addTab(self, tab, name = None):
        super().addTab(tab, name)
        colour = self.palette().color(QPalette.ColorRole.Text).name()
        buttonsize = int(self.tabs.tabBar().height() * 0.5)
        closebutton = ToolButton(QSize(buttonsize, buttonsize), icon=closeIcon(colour))
        self.tabs.tabBar().setTabButton(self.tabs.indexOf(tab), QTabBar.ButtonPosition.RightSide, closebutton)
        closebutton.clicked.connect(lambda: self.tabs.removeTab(self.tabs.indexOf(tab)))
        QTimer.singleShot(0, lambda: self.tabs.setCurrentIndex(self.tabs.indexOf(tab)))

    def _updatetabs(self):
        super()._updatetabs()
        if self.tabi == self.tabs.indexOf(self.tabwidget):
            self._closefind()
    def _appendTextToggle(self, appendobj):
        if self.tabi == self.tabs.indexOf(self.tabwidget):
            return None
        super()._appendTextToggle(appendobj)
    def closeEvent(self, a0):
        self.feedback.complete()
        self.closed.emit()
        super().closeEvent(a0)

class AsciiWidgetButton(QAction):
    def __init__(self, iface: QgisInterface):
        super().__init__(QUtilsIcon, "<b>QUtils Ascii Viewer</b>")
        self.iface = iface
        self.widget = None
        self.triggered.connect(self.hideShowWidget)
        self.action = QAction("QUtils Ascii Viewer")
        self.action.setCheckable(True)
        self.action.toggled.connect(self.toggle)
        self.action.setChecked(QgsSettings().value("QUtils/Ascii_Viewer_Toggle", True, bool))
        self.hidden = True
    
    def hideShowWidget(self):
        if self.widget is not None and self.widget.isMinimized():
            self.widget.showNormal()
        elif self.hidden:
            if self.widget is None:
                self.widget = AsciiWidget(self.iface)
                self.widget.closed.connect(lambda: (setattr(self, "widget", None), setattr(self, "hidden", True)))
                self._setpeakminmax()
            self.widget.show()
            self.hidden = False
            self.widget.raise_()
            self.widget.activateWindow()
        else:
            self.widget.hide()
            self.hidden = True

    def _setpeakminmax(self):
        if self.widget.peakwidget.layer.currentLayer() is None:
            return None
        self.widget.peakwidget._layerChanged(self.widget.peakwidget.layer.currentLayer())
        QTimer.singleShot(0, lambda: self.widget.peakwidget.maximum.setValue(self.widget.peakwidget.layer.currentLayer().dataProvider().bandStatistics(self.widget.peakwidget.band.currentBand()).maximumValue))
        QTimer.singleShot(0, lambda: self.widget.peakwidget.minimum.setValue(self.widget.peakwidget.layer.currentLayer().dataProvider().bandStatistics(self.widget.peakwidget.band.currentBand()).minimumValue))

    def toggle(self, toggled: bool):
        if toggled:
            self.iface.addToolBarIcon(self)
            QgsSettings().setValue("QUtils/Ascii_Viewer_Toggle", True)
        else:
            self.iface.removeToolBarIcon(self)
            if self.widget is not None:
                self.widget.hide()
                self.hidden = True
            QgsSettings().setValue("QUtils/Ascii_Viewer_Toggle", False)

    def unload(self):
        if self.widget is not None:
            self.widget.deleteLater()
        self.iface.removeToolBarIcon(self)
        self.widget = None