from qgis.core import QgsProcessingProvider
from QUtils.Scripts.ProcessingAlgorithms import PolygonCutter, RingBuffer, GradientMask
from QUtils import QUtilsIcon

__author__ = "Roxanne Minerals"
__version__ = 1.1


class QUtilsProvider(QgsProcessingProvider):
    def id(self): return "qutils"
    def name(self): return "QUtils Tools"
    def icon(self): return QUtilsIcon
    def loadAlgorithms(self):
        self.addAlgorithm(PolygonCutter("PolygonCutter", "Polygon Cutter"))
        self.addAlgorithm(GradientMask("GradientMask", "Gradient Mask"))