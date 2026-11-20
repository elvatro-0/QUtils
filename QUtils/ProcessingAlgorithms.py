"""
Boilerplate generation for processing algorithm scripts.
"""

from qgis.core import Qgis, QgsProcessingParameterNumber
from pathlib import Path
from typing import TYPE_CHECKING
import inspect

__author__ = "Roxanne Minerals"
__version__ = 1.0

#========================================================================================================#
#----------------------------------------------InstaScript-----------------------------------------------#
#===============================================>      <=================================================#

def InstaScript(name: str):
    file = Path(inspect.stack()[1].filename)
    script = f"""from qgis.core import(
    QgsProcessingAlgorithm
)
import QUtils
QUtils.reload()
from QUtils import *

_InstaImports({repr(str(file))})

class InstaScript(QgsProcessingAlgorithm):
    QUtils.reload()

    def name(self):
        return "{name}"

    def displayName(self):
        return "{name}"

    def group(self):
        return "Custom Tools"

    def groupId(self):
        return "custom_tools"

    def createInstance(self):
        return InstaScript()

    def initAlgorithm(self, configuration = None):
        QUtils.reload()
        self.addParameter()


    def processAlgorithm(self, parameters, context, feedback):
        QUtils.reload()




        return {{}}
"""
    with open(file, "w") as f:
        f.write(script)

def InstaImports(file):
    with open(file, "r") as fr:
        all_lines = fr.readlines()

    for line_no, line in enumerate(all_lines):
        if line.startswith("from qgis.core import("):
            importline_start = line_no
            in_imports = True
        if line.startswith(")") and in_imports:
            importline_stop = line_no
            in_imports = False
        if line.startswith("    def initAlgorithm("):
            initline_start = line_no
        if line.startswith("    def processAlgorithm("):
            initline_stop = line_no
            break
    imports = set()
    for importline in all_lines[importline_start + 1:importline_stop]:
        imports.add(importline.strip(", \n"))

    proc_params = []
    for initline in all_lines[initline_start + 1:initline_stop]:
        if initline.strip().startswith("self.addParameter(Qgs") or initline.strip().startswith("Qgs"):
            _proc = ""
            for letter in initline.strip().removeprefix("self.addParameter("):
                if letter == "(": break
                _proc += letter
            proc_params.append(_proc)

    for _import in proc_params:
        if _import not in imports:
            all_lines.insert(importline_stop - 1, f"    {_import},\n")

    with open(file, "w") as fw:
        fw.writelines(all_lines)

#========================================================================================================#
#---------------------------------------------TYPE CHECKING----------------------------------------------#
#===============================================>      <=================================================#

class ProcessingSourceType:
    MapLayer = Qgis.ProcessingSourceType.MapLayer
    VectorAnyGeometry = Qgis.ProcessingSourceType.VectorAnyGeometry
    VectorPoint = Qgis.ProcessingSourceType.VectorPoint
    VectorLine = Qgis.ProcessingSourceType.VectorLine
    VectorPolygon = Qgis.ProcessingSourceType.VectorPolygon
    Raster = Qgis.ProcessingSourceType.Raster
    File = Qgis.ProcessingSourceType.File
    Vector = Qgis.ProcessingSourceType.Vector
    Mesh = Qgis.ProcessingSourceType.Mesh
    Plugin = Qgis.ProcessingSourceType.Plugin
    PointCloud = Qgis.ProcessingSourceType.PointCloud
    Annotation = Qgis.ProcessingSourceType.Annotation
    VectorTile = Qgis.ProcessingSourceType.VectorTile
    TiledScene = Qgis.ProcessingSourceType.TiledScene

class NumberType:
    Integer = QgsProcessingParameterNumber.Integer
    Double = QgsProcessingParameterNumber.Double

if TYPE_CHECKING:
    from qgis.core import(
        QgsProcessingParameterDefinition,
        QgsProcessingParameterAggregate,
        QgsProcessingParameterDxfLayers,
        QgsProcessingParameterFieldMapping,
        QgsProcessingParameterMeshDatasetGroups,
        QgsProcessingParameterMeshDatasetTime,
        QgsProcessingParameters,
        QgsProcessingParameterBoolean,
        QgsProcessingParameterCrs,
        QgsProcessingParameterExtent,
        QgsProcessingParameterPoint,
        QgsProcessingParameterGeometry,
        QgsProcessingParameterFile,
        QgsProcessingParameterMatrix,
        QgsProcessingParameterMultipleLayers,
        QgsProcessingParameterNumber,
        QgsProcessingParameterDistance,
        QgsProcessingParameterArea,
        QgsProcessingParameterVolume,
        QgsProcessingParameterDuration,
        QgsProcessingParameterScale,
        QgsProcessingParameterRange,
        QgsProcessingParameterRasterLayer,
        QgsProcessingParameterEnum,
        QgsProcessingParameterString,
        QgsProcessingParameterAuthConfig,
        QgsProcessingParameterExpression,
        QgsProcessingParameterLimitedDataTypes,
        QgsProcessingParameterVectorLayer,
        QgsProcessingParameterLimitedDataTypes,
        QgsProcessingParameterMeshLayer,
        QgsProcessingParameterMapLayer,
        QgsProcessingParameterField,
        QgsProcessingParameterFeatureSource,
        QgsProcessingDestinationParameter,
        QgsProcessingParameterFeatureSink,
        QgsProcessingParameterVectorDestination,
        QgsProcessingParameterRasterDestination,
        QgsProcessingParameterFileDestination,
        QgsProcessingParameterFolderDestination,
        QgsProcessingParameterBand,
        QgsProcessingParameterLayout,
        QgsProcessingParameterLayoutItem,
        QgsProcessingParameterColor,
        QgsProcessingParameterCoordinateOperation,
        QgsProcessingParameterMapTheme,
        QgsProcessingParameterDateTime,
        QgsProcessingParameterProviderConnection,
        QgsProcessingParameterDatabaseSchema,
        QgsProcessingParameterDatabaseTable,
        QgsProcessingParameterPointCloudLayer,
        QgsProcessingParameterAnnotationLayer,
        QgsProcessingParameterPointCloudDestination,
        QgsProcessingParameterPointCloudAttribute,
        QgsProcessingParameterVectorTileDestination,
        QgsProcessingParameterTinInputLayers,
        QgsProcessingParameterType,
        QgsProcessingParameterVectorTileWriterLayers,
        QgsProcessingParameterAlignRasterLayers
    )