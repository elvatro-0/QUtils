from qgis.core import(
    Qgis,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingAlgorithm,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsApplication,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterBand,
    QgsProcessingParameterRasterDestination
)
from qgis.PyQt.QtGui import QIcon
from QUtils.Scripts.ScriptHelper import ProcessingSourceType, NumberType
from QUtils.Processing import VectorProcessing, RasterProcessing

__author__ = "Roxanne Minerals"
__version__ = 1.1


defaulticon = QgsApplication.getThemeIcon("/processingAlgorithm.svg")

class AlgorithmFactory(QgsProcessingAlgorithm):
    def __init__(self, name: str, displayname: str, icon: QIcon = defaulticon):
        super().__init__()
        self._name = name
        self._displayname = displayname
        self._icon = icon
    def name(self):
        return self._name
    def displayName(self):
        return self._displayname
    def icon(self):
        return self._icon

class PolygonCutter(AlgorithmFactory):
    def shortHelpString(self):
        return """
        Cuts overlapping polygons hierarchically within a single layer.\n
        For every features geometry, minus all overlapping feature's geometries, that have a higher hierarchy value, from the current features geometry.\n
        Hierarchy Field: the numerical layer field which is used as the hierarchy values. Higher value -> higher cutting priority.
        """
    def createInstance(self):
        return PolygonCutter("PolygonCutter", "Polygon Cutter")

    def initAlgorithm(self, configuration = None):
        self.addParameter(QgsProcessingParameterVectorLayer("VECTOR", "Polygon Layer", [ProcessingSourceType.VectorPolygon]))
        self.addParameter(QgsProcessingParameterField("FIELD", "Hierarchy Field", parentLayerParameterName="VECTOR", type=Qgis.ProcessingFieldParameterDataType.Numeric))
        self.addParameter(QgsProcessingParameterVectorDestination("OUTPUT", "output"))

    def processAlgorithm(self, parameters, context, feedback):
        output = self.parameterAsOutputLayer(parameters, "OUTPUT", context)
        field = self.parameterAsFields(parameters, "FIELD", context)[0]
        vector = VectorProcessing(parameters["VECTOR"], context, feedback).PolygonCutter(field).saveFeatures(output, "Cut Polygon")

        return {"OUTPUT": str(vector)}

#Basically already exists as multi-ring buffer...
#that doesnt add a CLASS field tho, which is useful for MCAs and suitability mapping...
class RingBuffer(AlgorithmFactory):
    def shortHelpString(self):
        return """
        Creates a multi-ring buffer with overlap logic based on a generated Class field \n
        NOTE: Does not preserve attributes. Creates new CLASS Field. \n
        Diameter: Total Diameter (map units)
        Invert:\n
        True = Increasing class value inwards (inner ring as highest value) \n
        False = increases class value outwards (Outer ring as highest value)
        Segments: Number of line segments to approximate a quarter circle when creating rounded offsets
        """
    def createInstance(self):
        return RingBuffer("RingBuffer", "Ring Buffer")

    def initAlgorithm(self, configuration = None):
        self.addParameter(QgsProcessingParameterVectorLayer("VECTOR", "Vector Layer"))
        self.addParameter(QgsProcessingParameterNumber("DIAMETER", "Diameter", NumberType.Double, 100))
        self.addParameter(QgsProcessingParameterNumber("RINGS", "Number of Rings", NumberType.Integer, 10))
        self.addParameter(QgsProcessingParameterBoolean("INVERT", "Invert", False))
        self.addParameter(QgsProcessingParameterNumber("SEGMENTS", "Segments", NumberType.Integer, 16))
        self.addParameter(QgsProcessingParameterVectorDestination("OUTPUT", "output"))

    def processAlgorithm(self, parameters, context, feedback):
        diameter = self.parameterAsDouble(parameters, "DIAMETER", context)
        rings = self.parameterAsInt(parameters, "RINGS", context)
        invert = self.parameterAsBool(parameters, "INVERT", context)
        segments = self.parameterAsInt(parameters, "SEGMENTS", context)
        output = self.parameterAsOutputLayer(parameters, "OUTPUT", context)
        vector = VectorProcessing(parameters["VECTOR"], context, feedback).RingBuffer(diameter, rings, invert, segments).saveFeatures(output, "Ring Buffer")

        return {"OUTPUT": str(vector)}

class GradientMask(AlgorithmFactory):
    def shortHelpString(self):
        return """
        Creates a descending gradient from a specified elevation.
        """
    def createInstance(self):
        return GradientMask("GradientMask", "Gradient Mask")
    
    def initAlgorithm(self, configuration = None):
        self.addParameter(QgsProcessingParameterRasterLayer("RASTER", "Raster Layer"))
        self.addParameter(QgsProcessingParameterBand("BAND", "Band", 1))
        self.addParameter(QgsProcessingParameterNumber("MASKVALUE", "Mask Elevation", NumberType.Double))
        self.addParameter(QgsProcessingParameterNumber("ANGLE", "Slope Angle", NumberType.Double, 0.5))
        self.addParameter(QgsProcessingParameterRasterDestination("OUTPUT", "Output"))

    def processAlgorithm(self, parameters, context, feedback):
        band = self.parameterAsInt(parameters, "BAND", context)
        value = self.parameterAsDouble(parameters, "MASKVALUE", context)
        angle = self.parameterAsDouble(parameters, "ANGLE", context)
        output = self.parameterAsOutputLayer(parameters, "OUTPUT", context)
        raster = RasterProcessing(parameters["RASTER"], context, feedback).GradientMask(value, band, angle).save(output, "Gradient Mask")

        return {"OUTPUT": str(raster)}