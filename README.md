##QGIS Utility Module.

###A lightweight, fluent, type-aware processing framework for QGIS map layers. \n
This module provides a unified, fluent interface for running QGIS Processing algorithms on map layers without the typical boilerplate of resolving layer objects, extracting outputs, or not knowing if something needs the live Qgs object or the pointer a string! \n
\n
**Wrapper Classes:** \n
\n
FlexibleMapLayer - Creates objects that act as both QGIS layer pointer strings and live QgsMapLayer objects. \n
Used as a proxy wrapper for the Processing classes, but, can also be used standalone. \n
***requires pointer string as input*** \n
\n
BaseLayerProcesser - Proxy Wrapper for the Processing classes handling context, feedback, processing.run() output extraction, and load on completion behaviour. \n
\n
Processing API wrappers - providing easy, seamless chaining of native and custom processing algorithms, including layer type conversion. \n
The run method allows any processing algorithm not already implemented within its given Processing class to be easily added in script or in the module itself as its algorithm name and parameter dictionary. Context, feedback, and correct output object return is handled by the method. \n
**Current Layer implementations:** \n
- QgsVectorLayers via VectorProcessing \n
- QgsRasterLayers via RasterProcessing \n
***requires pointer string as input*** \n
\n
```python
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingFeatureSource,
    QgsProcessing,
    QgsProcessingParameterRasterDestination
)
from qgis import processing
from QUtils import(
    VectorProcessing,
    RasterProcessing
)

class Example(QgsProcessingAlgorithm):
    def name(self):
        return "Example"
    
    def displayName(self):
        return "Example"
    
    def group(self):
        return "Custom Tools"
    
    def groupId(self):
        return "custom_tools"

    def createInstance(self):
        return Example()
    
    def initAlgorithm(self, configuration = None):
        self.addParameter(QgsProcessingParameterFeatureSource("INPUT", "Input Polygon", [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterRasterDestination("OUTPUT", "Output Destination"))

    def processAlgorithm(self, parameters, context, feedback):
        Vector = VectorProcessing(parameters["INPUT"], context, feedback)
        #Create VectorProcessing object using the input parameter pointer string

        dissolved = Vector.fixGeometries().Dissolve()
        #Chaining VectorProcessing methods

        processingTest = processing.run("native:fixgeometries", {'INPUT': str(dissolved), 'METHOD':1,'OUTPUT':'TEMPORARY_OUTPUT'}, is_child_algorithm=True, context=context, feedback=feedback)['OUTPUT']
        #as long as the Processing object is within a str(), it will return the pointer string of the object

        ReVector = VectorProcessing(processingTest, context, feedback)
        feedback.pushInfo(f"ReVector VectorProcessing Object: {str(ReVector)}")
        #Processing.run output can be used as the Processing class input as it is a pointer string

        ReVectorFeatures = ReVector.getFeatures()
        feedback.pushInfo(f"ReVectorFeatures: {str(ReVectorFeatures)}")
        #All Processing objects contain their given Qgs Layer methods - E.g. VectorProcessing can use QgsVectorLayer and QgsMapLayer methods

        Rasterised = dissolved.RingBuffer(1000, 10).Rasterise("CLASS")
        #Seamless chaining into Raster methods


        Rasterised.addLayerToLoadOnCompletion("Output_Raster")
        #handles addLayerToLoadOnCompletion to you dont have to deal with extracting layer details
    
        return {"OUTPUT": Rasterised}
```
