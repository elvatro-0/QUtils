## A pyQGIS Module.

### A lightweight, fluent, type-aware processing framework for QGIS map layers.  
  
This module provides a fluent interface for running QGIS Processing algorithms on map layers without the typical boilerplate of resolving layer objects, extracting outputs, or not knowing if something needs the live QgsMapLayer object or the pointer string!  
  
**Wrapper Classes:**  
  
**FlexibleMapLayer** - Creates objects that act as both QGIS layer pointer strings and live QgsMapLayer objects.  
Used as a proxy wrapper for the Processing classes, but, can also be used standalone.  
***requires pointer string as input***  
  
**BaseLayerProcesser** - Proxy Wrapper for the Processing classes handling context, feedback, processing.run() output extraction, and load on completion behaviour.  
  
**Processing API wrappers** - providing easy, seamless chaining of native and custom processing algorithms, including layer type conversion.  
The run method allows any processing algorithm not already implemented within its given Processing class to be easily added in script or in the module itself as its algorithm name and parameter dictionary. Context, feedback, and correct output object return is handled by the method.  
**Current Layer implementations:**  
- QgsVectorLayers via **VectorProcessing**
- QgsRasterLayers via **RasterProcessing**  
***requires pointer string as input***  
  
**FeatureProcessing** - A Wrapper around QgsFeatureiterator providing richer methods. It essentially acts as a cursor over a constructed container (a QgsVectorLayer), allowing multiple cursors over the same container by forwarding the containers reference, when newCursor() is called. FeatureProcessing delegates to QgsFeatureIterator methods acting on the specific cursor, and QgsVectorLayer and VectorProcessing methods acting on the container. Effectively, FeatureProcessing is a cursor, through a QgsFeatureIterator, that can modify it's container.  
**ConnectedFeature** - A class owned by FeatureProcessing that wraps the returned QgsFeature objetcs and automatically updates the same feature in the container when modifications are made.

_Example processing Algorithm Script:_
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
        #Create VectorProcessing object using the input parameter pointer string, context and feedback

        dissolved = Vector.fixGeometries().Dissolve()
        #Chaining VectorProcessing methods

        processingTest = processing.run("native:fixgeometries", {'INPUT': dissolved, 'METHOD':1,'OUTPUT':'TEMPORARY_OUTPUT'}, is_child_algorithm=True, context=context, feedback=feedback)['OUTPUT']
        #With an active QVariant hook, the object itself can be used directly in the parameter dict! (if the hook fails, str(dissolve))

        ReVector = VectorProcessing(processingTest, context, feedback)
        feedback.pushInfo(f"ReVector VectorProcessing Object: {str(ReVector)}")
        #Processing.run output can be used as the Processing class input as it is a pointer string

        ReVectorFeatures = ReVector.getFeatures()
        feedback.pushInfo(f"ReVectorFeatures: {str(ReVectorFeatures)}")
        #All Processing objects contain their given Qgs Layer methods - E.g. VectorProcessing can use QgsVectorLayer and QgsMapLayer methods

        Rasterised = dissolved.RingBuffer(1000, 10).Rasterise("CLASS")
        #Seamless chaining into Raster methods
        #Each time a process algorithm is run, it returns a new Processing object. This allows the use of objects prior to previous processes


        Rasterised.addLayerToLoadOnCompletion("Output_Raster")
        #handles addLayerToLoadOnCompletion so you dont have to deal with extracting layer details
    
        return {"OUTPUT": Rasterised}
```
---

### QGIS Python Console Scripting

Calling **createContextAndFeedback()** creates... well, the context and feedback, which allows the processing wrappers to be run in the QGIS python console.  
When called with showwidget = True (the default), a *Feedback Widget* will appear, which the Feedback object will emit messages to.  
**FeedbackWidget**  
The Feedback Widget is a custom widget that mimics the processing algorithm log, while adding search and highlighting, line numbers and elepsed time, and support for multiple tabs.  
Create the widget or call createContextAndFeedback() withtabs = True (default is False).

_Example QGIS Python Console Script:_
```python
from QUtils import VectorProcessing, RasterProcessing
from QUtils.Console import *
#When scripting in the QGIS Python Console, the Console module needs to be explicitly imported.

context, feedback = createContextAndFeedback(withtabs=True)
#creates the context and feedback (you'd never guess...)

line = VectorProcessing(iface.layerTreeView().selectedLayers()[0].id(), context, feedback)
raster = RasterProcessing(iface.layerTreeView().selectedLayers()[1].id(), context, feedback)

raster.topographicCrossSection(line.Feature().geometry().asPolyline(), 5, tabname="CrossSection")
#Some Processing Wrapper methods (specifically ASCII output methods) can output into a different tab when called with a tab name

raster.GradientMask(2).addLayerToLoadOnCompletion("Gradient")
#addLayerToLoadOnCompletion works the same as when called in Processing Algorithm Scripts

feedback.widget.addTab(QWidget(), "NewWidget")
#Widgets can be added through the Feedback object

feedback.complete()
#At the bottom of a script calling .complete() on the Feedback object signals to the widget and layer loader that processing has finished.
```

---

### QVariant Hook

PyQt converts a Python object to a QString with an exact type == str check and wraps everything else as an opaque PyQt_PyObject. Meaning str subclasses don't get converted to a QString (which is silly if you ask me).  
However! PyQt also exports a C hook that runs BEFORE that check (pyqt5_/pyqt6_register_to_qvariant_convertor).  
The QVariantHook module registers a ctypes callback on that!  
Instances of those str classes can sit directly in a processing parameter dict (or anything
else PyQt turns into a QVariant) and Qt receives a QVariant built from your classes designated converter callable.  
**registering a class:** Call *installQVariantType()* passing the class you want registered and a callable from that class that returns any python object QVariant can convert.  
can be used as installQVariantType(cls, fn), @installQVariantType, or @installQVariantType(converter=fn).  
*installPointerString()* registers classes specifically for QString.  
If a class fails the hook, you must pass the wrapped pointer string itself. For PointerString subclass thats either str(obj), obj._pointer, or if it also subclasses FlexibleMapLayer, simply obj.id(). Within the QUtils framework, in most cases the object is unwrapped before being processed (so long as the class has a \_\_str\_\_, like PointerString subclasses).

---

## License

Copyright (C) 2026 Roxanne Minerals

This project is licensed under the [GNU General Public License v3.0](LICENSE).
