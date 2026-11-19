"""Where the magic happens"""
"""            lllll                              Aqua <3
         llll lllllll        ll‡                     
         lllllllllllll‡l     l‡ll‡l                  
         lllllllll¯`````l‡ll ll¯`*‡                  
         l‡ll`"lll¯````````"l*`````ll                
         ll````````````````````````l‡               
       ‡l"```````````````````¯ll‡"`ll               
 ‡ll   l‡"```````````````````¯‡l l‡l‡               
 l‡l‡l ‡l"```````````````"l3gü`` ll                 
ll```¯l¯``````````````lll‡gggggü‡l                  
ll``````````````¯l6ggggggggggggl`*‡ll‡l````         
 ‡l*````````````lggggg‡llll3gggl``````¯ggg3````     
 l‡*`````*l``gggÇllllllll‡gggÇl¯`````gggggggl``     
   l‡ll‡l‡ l‡l3ggggg3llll‡gggü```‡ügggggggggl``     
       l‡l ll```lggggggggÞ`````ügggggggggggggg"`    
           ‡l`````````ÞggGl*`‡gggggggggggggggg¯`    
     ll‡lll`````````*llllllllllÇgggggü3`````````    
       l‡"````````3g6ülllll3gggl`‡ü``````           
         l‡ll```lgggggggggggggggg*`                 
           l‡`¯ggg3`6gggggggggggg6ü``               
         ````ggggg3`6gggggggggggggg"`````           
     ````‡ügggggÞü*`6ggggggggggggggggü3``````       
     ``üggggggggü`*üÞggggggggggggggüü`"lll¯``       
       ``Çgggggg6`3gggggggggggggggg"`lllll¯``       
       ````GggGül`3gggggggggggggg6ü``lll¯``         
         ````gÞ`lggggggggggggggl```  ``````         
             `````*üÞggggGü‡``````                  
                  ````````````                      
                    ````gggÇ``                      
                      ``lll*``                      
                    ``*llll*``                      
                    ````````                            """
#=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=

import qgis.core as core
from qgis.core import(
    Qgis,
    QgsMessageLog,
    QgsFeature,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingUtils,
    QgsProcessingAlgorithm,
    QgsMapLayer,
    QgsFields,
    QgsField,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsFeatureIterator,
    QgsFeatureRequest,
    QgsProcessingException,
    QgsRasterBandStats,
    QgsRasterDataProvider,
    QgsVectorDataProvider,
    QgsDataProvider,
    QgsWkbTypes,
    QgsRectangle,
    QgsSpatialIndex,
    QgsFeatureStore,
    QgsPointXY,
    QgsPoint
)
from qgis.PyQt.QtGui import QPalette
from qgis.PyQt import QtCore
from qgis import processing
from typing import TYPE_CHECKING, Union, overload, Iterator, Iterable
import math

from .ErrorHandling import QUtilsExceptions
from .Console import Feedback
from .Widgets import FeedbackWidget
from .QVariantHook import installPointerString
from .Legacy import ListSlicer
from .Storage import *


__author__ = "Roxanne Minerals"

#========================================================================================================#
#----------------------------------------------Functions-------------------------------------------------#
#===============================================>      <=================================================#

def NewVectorLayer(type: Qgis.WkbType | str, context: QgsProcessingContext, name: str = "new_Vector", uri: str | None = None, provider: str = "memory") -> QgsVectorLayer:
    wkbtype = QgsWkbTypes().parseType(type) if isinstance(type, str) else type
    if uri:
        fulluri = uri if uri.__contains__("?") else f"{QgsWkbTypes().displayString(wkbtype)}?{uri}"
    else: fulluri = QgsWkbTypes().displayString(wkbtype)
    return context.temporaryLayerStore().addMapLayer(QgsVectorLayer(fulluri, name, provider))

def is_pointerStr(input, context: QgsProcessingContext) -> bool:
    _string = QgsProcessingUtils.mapLayerFromString(str(input), context)
    return isinstance(_string, QgsMapLayer)

def NewFields(fields: tuple[str, str | QtCore.QMetaType.Type] | list[tuple[str, str | QtCore.QMetaType.Type]], extend: QgsFields = None, extendfrom: bool = False):
    """
    Generates a populated QgsFields object\n
    :param fields: Tuple or list of tuples containing the name of the field and it's field type.\n
        ("*name*", *FieldType*)\n
        Field type can be a QMetaType.Type (E.g. QgsField.type() return), QVariant.*Type*, or a string representation:\n
            - "string" -> QVariant.String
            - "int" -> QVariant.Int
            - "int64" -> QVariant.LongLong
            - "double" -> QVariant.Double
            - "date" -> QVariant.Date
            - "time" -> QVariant.Time
            - "datetime" -> QVariant.DateTime
            - "bool" -> QVariant.Bool
            - "bytearray" -> QVariant.ByteArray
            - "json" -> QVariant.Map
            - "array" -> QVariant.List
            - "unset" -> QVariant.Invalid
    :param extend: A QgsFields object to append the new fields to.
    :param extendfrom: if true, the extend QgsFields param will extend from the list of new fields, instead of the new fields appending.
    :return: QgsFields object.
    """
    fields = [fields] if isinstance(fields, tuple) else fields
    _qgsfields = QgsFields() if not extend or extendfrom else QgsFields(extend)
    for field in fields:
        field = (field[0], getattr(FieldType, field[1])) if isinstance(field[1], str) else field
        _qgsfields.append(QgsField(field[0], field[1]))
    if extendfrom: _qgsfields.extend(extend)
    return _qgsfields

#if deep layer cloning already existed, this would be much simpler... ~⪖ ‸⪕~
@QUtilsExceptions.ErrorHandling
def CloneLayer(layer: QgsMapLayer | QgsVectorLayer | QgsRasterLayer | str, context: QgsProcessingContext, feedback: QgsProcessingFeedback, printfeedback: bool = True):
    """Deep cloning returning a new layer"""
    if isinstance(layer, str):
        layer = QgsProcessingUtils().mapLayerFromString(str(layer), context) if is_pointerStr(layer, context) else QUtilsExceptions.CriticalError("input layer str is not layer pointer string.")
    if isinstance(layer.dataProvider(), QgsRasterDataProvider):
        clone = QgsProcessingUtils().mapLayerFromString(
            processing.run(
                "gdal:translate", {
                    'INPUT':layer.id(),
                    'TARGET_CRS':None,
                    'NODATA':None,
                    'COPY_SUBDATASETS':False,
                    'CREATION_OPTIONS':None,
                    'EXTRA':'',
                    'DATA_TYPE':0,
                    'OUTPUT':'TEMPORARY_OUTPUT'
                },
                is_child_algorithm=True,
                context=context,
                feedback=QgsProcessingFeedback()
            )['OUTPUT'],
            context
        )
        clone.setName(f"{layer.name()}_clone")
        feedback.pushInfo(f"Result: {clone.name()}_{clone.id()}") if printfeedback else None
    elif isinstance(layer.dataProvider(), QgsVectorDataProvider):
        clone = NewVectorLayer(layer.wkbType(), context, f"{layer.name()}_clone", "disable_id_generation=true")
        clone.startEditing()
        clone.setCrs(layer.crs())
        clone.dataProvider().addAttributes(layer.fields())
        clone.dataProvider().addFeatures(layer.dataProvider().getFeatures())
        clone.setAbstract(layer.abstract())
        clone.setCustomProperties(layer.customProperties())
        clone.setBlendMode(layer.blendMode())
        clone.setKeywordList(layer.keywordList())
        clone.setRenderer(layer.renderer().clone())
        clone.setMaximumScale(layer.maximumScale())
        clone.setMetadata(layer.metadata())
        clone.setMetadataUrl(layer.metadataUrl())
        clone.setMinimumScale(layer.minimumScale())
        clone.setOpacity(layer.opacity())
        clone.setScaleBasedVisibility(layer.hasScaleBasedVisibility())
        clone.commitChanges()
        feedback.pushInfo(f"Result: {clone.id()}") if printfeedback else None

    return clone

def PrettyNumber(number: int | float, ndigits: int = 3) -> str:
    number = round(number) + 0.0 if abs(number) >= (1000 - 5 * 10 ** (2 - ndigits)) else number + 0.0
    letter = ("", 1)
    letter = ("k", 10 ** 3) if abs(number) >= 1000 else letter
    letter = ("m", 10 ** 6) if abs(number) >= 1_000_000 else letter
    letter = ("G", 10 ** 9) if abs(number) >= 1_000_000_000 else letter
    letter = ("T", 10 ** 12) if abs(number) >= 10 ** 12 else letter
    trunc_numb: float = (
        round(number / letter[1], ndigits - len(str(int(abs(number) / letter[1]))))
        if len(str(int(abs(number)))) >= ndigits else round(number, ndigits - len(str(int(abs(number)))))
        )
    trunc_numb = int(trunc_numb) if trunc_numb.is_integer() and len(str(int(abs(trunc_numb)))) >= ndigits else trunc_numb
    return f"{number:.{ndigits - 1}e}" if abs(number) >= 10 ** 15 else f'{trunc_numb}{"0" * (ndigits - len(str(abs(trunc_numb)).replace(".", "")))}{letter[0]}'

def renderGraph(graphdict: dict[tuple[float, float], float], y_bins: int = 29, y_truncpercent: int = 100, minY: float = None, minValue: float | None = None, maxValue: float | None = None, feedback: QgsProcessingFeedback = QgsProcessingFeedback()):
    if minValue is None or maxValue is None:
        _min = next(iter(graphdict.keys()))[0]
        _max = next(iter(graphdict.keys()))[1]
        for bin in graphdict.keys():
            _min = bin[0] if bin[0] < _min else _min
            _max = bin[1] if bin[1] > _max else _max
        minValue = _min if minValue is None else minValue
        maxValue = _max if maxValue is None else maxValue
    minY = min(graphdict.values()) if minY is None else minY

    maxsum: float = max(graphdict.values()) * (y_truncpercent / 100)
    y_bins = int(maxsum - minY) if (maxsum - minY) < y_bins else y_bins
    y_bins += 1 if y_bins == 0 else 0
    y_Sizes = (maxsum - minY) / y_bins
    next_min = maxsum - y_Sizes
    extrapad = 1 if min(graphdict.values()) < -999 else 0
    linestring = ""
    linestring += f"{'·' * (5 + extrapad - len(PrettyNumber(maxsum + y_Sizes)))}{PrettyNumber(maxsum + y_Sizes)}│" + "".join(["#" if value >= (maxsum + y_Sizes) else "·" for value in graphdict.values()]) + f"\n"
    linestring += f"{'·' * (5 + extrapad - len(PrettyNumber(maxsum)))}{PrettyNumber(maxsum)}│" + "".join(["#" if value >= maxsum else "·" for value in graphdict.values()]) + f"\n"
    for y_i in range(y_bins):
        y_min = next_min if next_min > minY else minY
        next_min = y_min - y_Sizes
        linestring += f"{'·' * (5 + extrapad - len(PrettyNumber(y_min)))}{PrettyNumber(y_min)}│"
        linestring += "".join(["#" if value > y_min else "·" for value in graphdict.values()]) + f"\n"
        feedback.setProgress((100 / y_bins) * (y_i + 1))
    
    #All this.. just for the x-axis ~>.<~
    x_pad = len(graphdict.keys()) + 1 + (len(PrettyNumber(minValue, 3)) % 2) - len(PrettyNumber(minValue, 3) + PrettyNumber(maxValue)) + (len(PrettyNumber(maxValue, 3)) // 2)
    x_list = [minValue, maxValue]
    for x_i in range(x_pad):
        hold_list = []
        for v_i in range(len(x_list) - 1):
            pad_remain = (x_pad - (5 * len(ListSlicer(x_list, (None, None, [0, len(x_list) - 1]), feedback)))) // (len(x_list) - 1)
            if pad_remain < 13: # 8(4 spaces between labels) + 5(max width of labels)
                _break = True
                break
            _break = False
            hold_list.append((x_list[v_i] + x_list[v_i + 1]) / 2)
        x_list.extend(hold_list)
        x_list.sort()
        if _break:
            break
    mid_list = ListSlicer(x_list, (None, None, [0, len(x_list) - 1]), feedback)
    pad_subtraction = ((x_pad - (len(mid_list)) * 5) // (len(mid_list) + 1))
    remainder = (x_pad - 5 * len(mid_list)) % (len(mid_list) + 1)
    rem_binlist = [1 for i in range(remainder)]
    for i in range(1, len(mid_list) - remainder + 1, 2):
        rem_binlist.insert(i, 0) if len(mid_list) > 1 else None
    rem_binlist.extend([0 for i in range(len(mid_list) - len(rem_binlist))])
    rem_binlist.reverse()
    mid_labels = "".join(
        [f"{'·' * pad_subtraction}{'·' * ((5 - (len(PrettyNumber(value, 3)))) // 2)}{PrettyNumber(value, 3)}{'·' * ((5 - len(PrettyNumber(value, 3))) // ((len(PrettyNumber(value, 3)) % 2) + 1))}{'·' * rem_binlist[i]}"
            for i, value in enumerate(mid_list)]
        )
    mid_labels = f"{'·' * (x_pad - pad_subtraction)}" if len(mid_list) == 0 else mid_labels
    linestring += f"{'·' * (5 + extrapad - (len(PrettyNumber(minValue, 3)) % 2))}{PrettyNumber(minValue, 3)}{mid_labels}{'·' * pad_subtraction}{PrettyNumber(maxValue, 3)}"

    return linestring

#========================================================================================================#
#------------------------------------------Proxy Base Wrappers-------------------------------------------#
#===============================================>      <=================================================#

class PointerString(str):
    def __new__(cls, pointer: str, *args, **kwargs):
        return super().__new__(cls, pointer)
    def __init__(self, pointer: str):
        self._pointer = pointer

    def __str__(self):
        return str(self._pointer)

    def __repr__(self):
        return f"PointerString - {self._pointer!r}"

class FlexibleMapLayer(PointerString):     #this is my baby ♡
    def __init__(self, input_pointer: str, context: QgsProcessingContext):
        if not is_pointerStr(input_pointer, context):
            raise TypeError(f"FlexibleMapLayer Received {repr(input_pointer)} - Requires Pointer String")
        super().__init__(input_pointer)
        self.context = context

    def __repr__(self):
        return f"FlexibleMapLayer({self._pointer!r})"

    @property
    def __class__(self):
        return QgsProcessingUtils.mapLayerFromString(self, self.context).__class__
        
    def __getattr__(self, name):
        _return = getattr(QgsProcessingUtils.mapLayerFromString(self, self.context), name)
        if callable(_return): return _methodCaller(_return)
        return _return

class _methodCaller(MethodCaller):
    def __call__(self, *args, **kwargs):
        args = tuple([arg.__param__() if hasattr(arg, "__param__") else arg for arg in args])
        for key, val in kwargs.items():
            kwargs[key] = val.__param__() if hasattr(val, "__param__") else val
        _return = self.method(*args, **kwargs)
        if isinstance(_return, QgsDataProvider):
            return self.datawrapper(_return, _methodCaller)
        return _return

class BaseLayerProcesser(FlexibleMapLayer):
    def __init__(self, input_pointer: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        super().__init__(input_pointer, context)
        self.feedback = feedback
        self.RETURN_CLS: tuple[type, int] = (None, -1)
        self.CUSTOM_PARAMETERS = ()

    #output can be specified by the position of the layer pointer str in the processing output dict, or by the spcefic keys name.
    @QUtilsExceptions.ErrorHandling
    def ProcessingOutput(self, processdict: dict, output: str | int = 0) -> str | Carrier | None:
        if isinstance(output, str):
            if output not in processdict.keys():
                QUtilsExceptions.CriticalError(f"output {output} does not exist", self.feedback)
            elif not is_pointerStr(processdict[output], self.context):
                self.feedback.pushWarning(f"output {output} is not pointer string.")
                self.feedback.pushInfo(f"{output}: {processdict[output]}")
                return Carrier(processdict[output], key={"output": 0})
            return processdict[output]
        if isinstance(output, int):
            _return = []
            for _value in processdict.values():
                if is_pointerStr(_value, self.context):
                    _return.append(_value)
            if len(_return) == 0:
                self.feedback.pushWarning(f"Process did not return pointer string.")
                return None
            return _return[output]

    def ProcessingInput(self, parameters: dict[str, object]):
        for key, val in parameters.items():
            if val == "__self__":
                parameters[key] = str(self)
            elif isinstance(val, list):
                _list = []
                for _val in val:
                    _val = str(self) if _val == "__self__" else _val
                    _val = str(_val) if is_pointerStr(_val, self.context) else _val
                    _list.append(_val)
                parameters[key] = _list
            elif is_pointerStr(val, self.context):
                parameters[key] = str(val)
        return parameters

    def forceMapLayer(self):
        return QgsProcessingUtils.mapLayerFromString(self, self.context)
    
    #roses are red, I like mantle wedge depletion-
    def addLayerToLoadOnCompletion(self, output_name: str):
        self.context.addLayerToLoadOnCompletion(self, QgsProcessingContext.LayerDetails(output_name, self.context.project()))

    def setRETURN_CLS(self, cls: type, for_runs: int = -1):
        self.RETURN_CLS = (cls, for_runs)
        return self

    def newLayerObject(self, input_pointer: str, *args, **kwargs):
        argslist = list(args)
        forruns = self.RETURN_CLS[1] if self.RETURN_CLS[0] is not None else -1
        cls = self.RETURN_CLS[0]
        if self.RETURN_CLS[0] is None or forruns == 0:
            cls = type(self)
            argslist.extend(self.CUSTOM_PARAMETERS)
        if forruns > 0: self.RETURN_CLS = (self.RETURN_CLS[0], forruns - 1)
        return cls(input_pointer, self.context, self.feedback, *tuple(argslist), **kwargs)

    def run(self, algorname:str | QgsProcessingAlgorithm, parameters: dict[str, object], output: str | int = 0, printfeedback: bool = True, chain = False, *args, **kwargs):
        if self.feedback.isCanceled(): raise QgsProcessingException("Cancelled")
        _output = self.ProcessingOutput(
            processing.run(
                algorname,
                self.ProcessingInput(parameters),
                is_child_algorithm=True,
                context=self.context,
                feedback=self.feedback if printfeedback else SilentFeedback(self.feedback)
            ),
            output=output
        )

        if _output is None:
            return self
        elif isinstance(_output, Carrier):
            if chain:
                return self
            return _output["output"]
        return self.newLayerObject(_output, *args, **kwargs)

    def Clone(self, printfeedback: bool = True):
        return self.newLayerObject(CloneLayer(self, self.context, self.feedback, printfeedback).id())

#========================================================================================================#
#--------------------------------------Direction AND MAGNITUDE!------------------------------------------#
#==========================================> OH YEAH!!! <================================================#

class VectorProcessing(BaseLayerProcesser):

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>     Debug Methods     <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def peak(self, rows: int = 5, start: int = 1, min_colwidth: int = 6):
        stop = start + rows - 1 if self.featureCount() >= start + rows - 1 else self.featureCount()
        self.feedback.pushInfo(f"\n{'=♡' * 35}=\n Attribute table for {str(self)}\n rows {start}-{stop}")
        min_colwidth += 1 if min_colwidth & 1 == 1 else 0
        name_string = ""
        for name in self.fields().names():
            name_Length = min_colwidth if len(str(name)) < min_colwidth else len(str(name))
            name_string += f"{'·' * ((name_Length - len(str(name))) // 2)}{name}{('·' * ((name_Length - len(str(name))) // 2)) + ('·' if len(str(name)) & 1 == 1 else '')}|"        #big padding >.<
        self.feedback.pushCommandInfo(name_string)
        for row, feature in enumerate(self.getFeatures()):
            if row < start - 1: continue
            if row > stop - 1: break
            row_string = ""
            for name in self.fields().names():
                name_Length = min_colwidth if len(str(name)) < min_colwidth else len(str(name))
                name_Length += 1 if name_Length & 1 == 1 else 0
                cell = feature[name]
                if len(str(cell)) > name_Length:
                    word = ""
                    letter_count = 0
                    for letter in str(cell):
                        letter_count += 1
                        if letter_count > name_Length: break
                        word += letter
                    cell = word
                cell_Length = len(str(cell))
                row_string += f"{'·' * ((name_Length - cell_Length) // 2)}{cell}{('·' * ((name_Length - cell_Length) // 2)) + ('·' if cell_Length & 1 == 1 else '')}|"
            self.feedback.pushCommandInfo(row_string)
        self.feedback.pushInfo(f"{'=♡' * 35}=\n")                                 #Chonky </3

        return self
# ⋅ >.<
# · 
# · <<
# ∙ 

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>     Layer Methods     <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#

    def layer_Slicer(self, input_slice: tuple[Union[list[int], None], Union[tuple[int, int], list[tuple[int, int]], None], Union[list[int], list[tuple[int, int]], None]], printfeedback=True):
        self.feedback.pushInfo(f"Result: layerFeatures_Slicer: {str(self)}") if printfeedback else None
        return self.newLayerObject(ListSlicer(self, input_slice, self.feedback, self.context))

    def requestedFeatures(self, request: QgsFeatureRequest | str | list[int], name: str = "Selected_Features_Layer"):
        features = self.Features(request)
        layer = self.newLayerObject(NewVectorLayer(self.wkbType(), self.context, name).id())
        layer.startEditing()
        layer.setCrs(self.crs())
        layer.dataProvider().addAttributes(features.fields())
        layer.dataProvider().addFeatures(features)
        layer.commitChanges()
        return layer

    def wktType(self):
        return QgsWkbTypes.displayString(self.wkbType())

    def simpleWktType(self):
        if self.wktType().__contains__("Polygon"): return "Polygon"
        if self.wktType().__contains__("Point"): return "Point"
        if self.wktType().__contains__("Line"): return "Line"
        return self.wktType()

    def changeAttributeValuesV2(self, fid: int, newValues: list) -> bool:
        attrmap = {}
        for i, attr in enumerate(newValues):
            attrmap[i] = attr

        return self.changeAttributeValues(fid, attrmap)

    #I look at myself and I think... sometimes she knows what she's doing ~>.o~

    def addFields(self, fields: QgsFields, positions: list[int] = None):
        """
        An extension of addAttributes() which also adds the new fields to the layers features, while allowing positional field insertion.\n
        *only crashes QGIS sometimes...*\n
        NOTE: Needs to be run in an edit session.\n
        :param fields: A QgsFields object of all the new fields to be added.
        :param positions: A list of integers whos index position relates to the fields position in the fields param.
            The integer refers to the position at which the relating field will be inserted into the layers field list.
            If less positions are given then the number of fields, the remaining fields will all be appended to the end.
        :return: self
        """
        checkedfields = QgsFields()
        for field in fields.toList():
            if field.name() in self.fields().names():
                field.setName(f"{field.name()}_")
            checkedfields.append(field)

        features = self.Features()
        features.setConnectFeatures(False)
        features.setFeatureIdReturn(True)

        if positions != None:
            fieldlist: list = self.fields().toList()
            for i, pos in enumerate(positions):
                fieldlist.insert(pos, checkedfields.toList()[i])
            if len(positions) < checkedfields.count():
                fieldlist.extend([checkedfields.toList()[i] for i in range(len(positions), checkedfields.count())])
            self.dataProvider().deleteAttributes(self.fields().allAttributesList())
            self.dataProvider().addAttributes(fieldlist)
        else:
            self.dataProvider().addAttributes(checkedfields)
        self.updateFields()

        for feature in self.getFeatures():
            feature: QgsFeature
            attrs: list = features[feature.id()].attributes()
            attrs.pop(0) #FeatureProcessings _fid_ field
            if positions != None:
                for pos in positions: attrs.insert(pos, None)
            self.changeAttributeValuesV2(feature.id(), attrs)

        return self

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Native Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def fixGeometries(self, method: int = 1, output="TEMPORARY_OUTPUT", printfeedback=True):
        """
        Native Fix geometries Process \n
        :param method: Repair method: \n
                       0 = Linework
                       1 = Structure
        :param output: Output file path string | Default Temporary Memory Output
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        return self.run(
            "native:fixgeometries", {
                'INPUT': "__self__",
                'METHOD': method,
                'OUTPUT': output
            },
            printfeedback=printfeedback
        )
    def Dissolve(self, field: QgsFields = [], separate_disjoint: bool = False, output="TEMPORARY_OUTPUT", printfeedback=True):
        """
        Native Dissolve Process \n
        :param field: QgsFields list of attributes | Blank list will dissolve all atrtibute fields
        :param separateDisJoint: If True, features and parts that do not overlap or touch will be exported as separate features
        :param output: Output file path string | Default Temporary Memory Output
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        return self.run(
            "native:dissolve", {
                'INPUT':"__self__",
                'FIELD': field,
                'SEPARATE_DISJOINT': separate_disjoint,
                'OUTPUT': output
            },
            printfeedback=printfeedback
        )
    def Smooth(self, iterations:int = 1, offset: float = 0.5, max_angle: float = 180, output="TEMPORARY_OUTPUT", printfeedback=True):
        """
        Native Smooth geometry process
        """
        return self.run(
            "native:smoothgeometry", {
                'INPUT':"__self__",
                'ITERATIONS':iterations,
                'OFFSET':offset,
                'MAX_ANGLE':max_angle,
                'OUTPUT':output
            },
            printfeedback=printfeedback
        )
    def FieldCalculator(self, field_name: str, field_type: int, formula: str, field_length: int = 0, field_precision: int = 0, output="TEMPORARY_OUTPUT", printfeedback=True):
        return  self.run(
            "native:fieldcalculator", {
                'INPUT':"__self__",
                'FIELD_NAME':field_name,'FIELD_TYPE':field_type,
                'FIELD_LENGTH':field_length,
                'FIELD_PRECISION':field_precision,
                'FORMULA':formula,
                'OUTPUT':output
            },
            printfeedback=printfeedback
        )

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Custom Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def RingBuffer(self, diameter: float, rings: int, invert: bool = False, segments: int = 16, printfeedback=True):
        """
        Creates a multi-ring buffer with overlap logic based on a generated Class field \n
        NOTE: Does not preserve attributes. Creates new CLASS Field. \n
        :param diameter: Total Diameter (map units)
        :param rings: Number of donut rings
        :param invert: True = Increasing class value inwards (inner ring as highest value) \n
                       False = increases class value outwards (Outer ring as highest value)
        :param segments: Number of line segments to approximate a quarter circle when creating rounded offsets
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """

        ringsize = diameter / 2 / rings
        geomlist = []
        for buffer_i in range(1, rings + 1):
            for i, feature in enumerate(self.Features()):
                buffer: QgsGeometry = feature.geometry().buffer(ringsize * buffer_i, segments)
                buffer_combined = buffer if i == 0 else buffer_combined.combine(buffer)
                if self.feedback.isCanceled(): raise QgsProcessingException("Cancelled")
            self.feedback.setProgress((100 / rings) * buffer_i / 2) if printfeedback else None
            geomlist.append((buffer_combined, rings - buffer_i + 1 if invert else buffer_i))
        
        fields = NewFields(("CLASS", FieldType.int))
        layer = NewVectorLayer("MultiPolygon" , self.context, "Ring_Buffer")
        layer.startEditing()
        layer.setCrs(self.crs())
        layer.dataProvider().addAttributes(fields)

        geomlist.reverse()
        for geom_i in range(rings):
            ring = geomlist[geom_i][0].difference(geomlist[geom_i + 1][0]) if geom_i != rings - 1 else geomlist[geom_i][0]
            feature = QgsFeature()
            feature.setGeometry(ring)
            feature.setFields(fields)
            feature.setAttribute("CLASS", geomlist[geom_i][1])
            layer.dataProvider().addFeature(feature)
            self.feedback.setProgress(((100 / rings) * (geom_i + 1) / 2) + 50) if printfeedback else None
        layer.commitChanges()

        self.feedback.pushInfo(f"Results: {layer.id()}") if printfeedback else None
        return self.newLayerObject(layer.id())

    def PolygonCutter(self, hierarchyfield: str | QgsField):
        """
        Cuts overlapping polygons hierarchically within a single layer.\n
        For every features geometry, minus all overlapping feature's geometries, that have a higher hierarchy value, from the current features geometry.\n
        :param hierarchyfield: the numerical layer field which are used as the hierarchy values. Higher value -> higher cutting priority.
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """

        field = hierarchyfield.name() if isinstance(hierarchyfield, QgsField) else hierarchyfield
        featureindex = QgsSpatialIndex(self.getFeatures())
        cutlayer = NewVectorLayer("MultiPolygon", self.context, "Cut_Layer")
        cutlayer.startEditing()
        cutlayer.dataProvider().addAttributes(self.fields())
        cutlayer.setCrs(self.crs())

        for feature in self.getFeatures():
            geom: QgsGeometry = feature.geometry()
            for fid_intersected in featureindex.intersects(geom.boundingBox()):
                fid_feature: QgsFeature = self.getFeature(fid_intersected)
                if geom.intersects(fid_feature.geometry()):
                    geom = geom.difference(fid_feature.geometry()) if fid_feature[field] > feature[field] else geom
            cutfeature = QgsFeature()
            cutfeature.setGeometry(geom)
            cutfeature.setFields(self.fields())
            cutfeature.setAttributes(feature.attributes())
            cutlayer.dataProvider().addFeature(cutfeature)
        cutlayer.commitChanges()

        return self.newLayerObject(cutlayer.id())

    @QUtilsExceptions.ErrorHandling
    def geometryCenter(self):
        """
        Creates a new layer containing point features representing the geometric centre of each feature.\n
        NOTE: polygon features call controid(), the midpoint may not be within the geometry.\n
        The point features will maintain the attributes of the input layers features.\n
        An "fid" field will be added or overridden representing the input feature's id.\n
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        self.feedback.setProgress(0)
        fields = NewFields(("fid", FieldType.int), self.fields(), True)
        layer = NewVectorLayer("MultiPoint", self.context, f"{self.name()}_CenterPoints")
        layer.startEditing()
        layer.dataProvider().addAttributes(fields)
        layer.setCrs(self.crs())

        for i, feature in enumerate(self.getFeatures()):
            feature: QgsFeature
            pointfeature = QgsFeature()
            if self.simpleWktType() == "Point": point = feature.geometry()
            elif self.simpleWktType() == "Line": point = feature.geometry().interpolate(feature.geometry().length() / 2)
            elif self.simpleWktType() == "Polygon": point = feature.geometry().centroid()
            else: QUtilsExceptions.CriticalError(f"Geometry of {self.id()} does not support center locating operation", self.feedback)
            pointfeature.setGeometry(point)
            pointfeature.setFields(fields)
            pointfeature.setAttributes(feature.attributes())
            pointfeature.setAttribute("fid", feature.id())
            layer.dataProvider().addFeature(pointfeature)
            self.feedback.setProgress((100 / self.featureCount()) * (i + 1))
        layer.commitChanges()

        return self.newLayerObject(layer.id())

    #-------------------------------------------------------#
    #>>>>>>>>>>>>    Layer Type Conversion    <<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def Rasterise(self, field:str, burn:float = 0, use_Z:bool = False, units:int = 1, width:float = 30, height:float = 30, extent:str = None, nodata:float = 0, creation_options:str = None, data_type:int = 5, init:float = None, invert:bool = False, extra:str = '', output = "TEMPORARY_OUTPUT", printfeedback=True):
        """
        GDAL rasterize Process \n
        :param field: Attribute field used to assign pixel values.
        :param burn: Constant value to burn into all pixels.
        :param use_Z: Uses Z-values from geometry as pixel values, if True.
        :param units: Pixel size units: \n
                  0 = Pixels per map unit
                  1 = Georeferenced units per pixel
        :param width: Pixel width.
        :param height: Pixel height.
        :param extent: Extent string "xmin,xmax,ymin,ymax" defining raster bounds. Uses layer extent if None.
        :param nodata: NoData value assigned to empty pixels.
        :param Creation_Options: GDAL creation options string.
        :param data_type: Output raster data type: \n
                      0 = Byte, 1 = Int16, 2 = UInt16, 3 = Int32, 4 = UInt32, 5 = Float32, 6 = Float64
        :param init: Initial value for all pixels before burning geometry.
        :param invert: inverts the burn mask.
        :param extra: Additional GDAL command-line arguments.
        :param output: Output file path string | Default Temporary Memory Output
        :return: RasterProcessing(FlexibleRasterLayer) Object
        """
        _return: RasterProcessing = self.setRETURN_CLS(RasterProcessing, 1).run(
                "gdal:rasterize", {
                    'INPUT':"__self__",
                    'FIELD':field,
                    'BURN':burn,
                    'USE_Z':use_Z,
                    'UNITS':units,
                    'WIDTH':width,
                    'HEIGHT':height,
                    'EXTENT':extent,
                    'NODATA':nodata,
                    'CREATION_OPTIONS':creation_options,
                    'DATA_TYPE':data_type,
                    'INIT':init,
                    'INVERT':invert,
                    'EXTRA':extra,
                    'OUTPUT':output
                },
                printfeedback=printfeedback
            )
        return _return

    #-------------------------------------------------------#
    #>>>>>>>>>>>  Vector to Feature Conversion  <<<<<<<<<<<<#
    #-------------------------------------------------------#
    def Features(self, request: QgsFeatureRequest | str | list[int] = NO_REQUEST, maintaincontainer = False):
        """
        :param maintaincontainer: dictates if this layer should be the container FeatureProcessing iterates over (if True),
        or if the features should be iterated over separately in a new container (if False)
        """
        if maintaincontainer:
            return FeatureProcessing(self, self.context, self.feedback, request=request)
        return FeatureProcessing(self.getFeatures(), self.context, self.feedback, request=request)

    def Feature(self):
        return self.Features()._firstfeature

    #======================================================#

class VectorProcessing_Buffer(VectorProcessing):
    pass

if TYPE_CHECKING:
    class VectorProcessing(VectorProcessing_Buffer, QgsMapLayer, QgsVectorLayer):
        def dataProvider(self) -> QgsVectorDataProvider:
            pass

#I studied geology not english language, of course theres spelling mistakes ~>.<~

#========================================================================================================#
#-------------------------------------------Feature Processing-------------------------------------------#
#===============================================>      <=================================================#
#she kinda cooked with this one...
class FeatureProcessing:
    """
    A QgsFeatureIterator equivilent with richer methods.\n
    To fully grasp the usecases of this class, treat every FeatureProcessing object as a cursor.\n
    NOTE: If you addFeature(s) directly on the container, bypassing the FeatureProcessing objects addFeature(s) methods or getattr,
    it is HIGHLY recommended to call updatemNextFeatureId() on a FeatureProcessing object that traverses that container.\n
    Second NOTE: Creating the container with an empty features input and/or with an empty geometry param, the containers
    geometry will default to MultiPolygon.\n
    Third NOTE: The container is a memory layer, and as with all memory layers the fids aren't preserved.
    If the original fids are needed, an "\_fid_" field is added to all featues, attributing their original fids.
    _*This is always set to the FIRST field index.*_ I advise against trying to change the name or position of "\_fid_",
    there are some safeguards, but it's best not to in the first place.\n
    If featureIdReturn is True, any feature retrieved will return with its "\_fid_" value as its id.\n
    The flag is stored with the container, so new cursors will maintain it, and new containers created with the newContainer() method will copy
    the flag forward. Importantly, the flag is only passed forwards to new cursors. Cursors created prior to toggling
    the flag won't be affected by the change.\n
    \_\_getitem__, \_\_delitem__, \_\_setitem__ and \_\_contains__ will all also work by "\_fid_" instead of by layerFid if True.
    featureIdReturn is False by default, and can be toggled with toggleFidReturn(), set with setFeatureIdReturn() and checked with isFeatureIdReturn().\n
    Fourth NOTE: The request is stored separatley per cursor and not forwarded to new ones. Any Cursor/Iterator level operation
    returns the filtered view of the specific cursor, while Container level operations returns the entire containers collection.\n
    **ConnectedFeatures**: When True, any feature retrieved through \_\_getitem__ and iteration will remain connected to the container,
    meaning any opertaion and mutation to that QgsFeature will be auto-updated on the container at method call. Modification can be buffered
    on two levels: per feature (by the ConnectedFeature flag, bufferupdate) updates the container per single feature after you have finished feature
    mutation; and bulk feature (by the flag, bulkbufferupdate) which stores all modified features in a BufferStore and updates the container all at once.\n
    Both container update operations can be done manually with the updateContainer() ConnectedFeature method.\n
    NOTE: The connectfeatures flag is stored per cursor and not forwarded to new ones. Likewise with both buffer flags,
    it is per cursor and newCursors are set to the default value: connectfeatures: False; both buffers: False.
    """
    @overload
    def __init__(self, features: QgsFeatureIterator | Iterable[QgsFeature], context: QgsProcessingContext, feedback: QgsProcessingFeedback, geometry: Qgis.WkbType | str = "MultiPolygon", request: QgsFeatureRequest | str | list[int] = ...):
        ...
    @overload
    def __init__(self, context: QgsProcessingContext, feedback: QgsProcessingFeedback, geometry: Qgis.WkbType | str = "MultiPolygon"):
        ...

    @QUtilsExceptions.ErrorHandling
    def __init__(self, features_context, context_feedback, feedback_geometry = "MultiPolygon", geometry: Qgis.WkbType | str = None, request: QgsFeatureRequest | str | list[int] = NO_REQUEST):
        if isinstance(features_context, QgsProcessingContext):
            self.context = features_context
            self.feedback = context_feedback
            self.featurestore = VectorProcessing(NewVectorLayer(feedback_geometry, self.context, "_FEATUREPROCESSING_ITERATOR_CONTAINER_", "index=yes").id(), self.context, self.feedback)
            self.featurestore.startEditing()
            self.featurestore.setCrs(self.context.project().crs())
            self.featurestore.dataProvider().addAttributes(NewFields(("_fid_", FieldType.int64)))
            self.featurestore.commitChanges()
            self.cursor = self.featurestore.getFeatures()
            self._featureidreturn = False
        else:
            self.context: QgsProcessingContext = context_feedback
            self.feedback: QgsProcessingFeedback = feedback_geometry
            if isinstance(features_context, (QgsVectorLayer, VectorProcessing, BaseLayerProcesser, FlexibleMapLayer)) and not isinstance(features_context, FeatureProcessing):
                if isinstance(features_context.dataProvider(), QgsVectorDataProvider):
                    features_context.startEditing()
                    features_context = VectorProcessing(features_context.id(), self.context, self.feedback)
                    features_context.addFields(NewFields(("_fid_", FieldType.int64)), [0])
                    fieldid = features_context.fields().lookupField("_fid_")
                    for fid in features_context.allFeatureIds():
                        features_context.changeAttributeValue(fid, fieldid, fid)
                    features_context.commitChanges()
                    features_context = Carrier(features_context, False, key={"featurestore": 0, "featureidreturn": 1})
                else:
                    QUtilsExceptions.CriticalError(f"{features_context} is unsupported as features input. If you meant to input a QgsVectorLayer, you did it wrong.", self.feedback)
            if isinstance(features_context, Carrier):
                self._featureidreturn: bool = features_context["featureidreturn"]
                self.featurestore: VectorProcessing = features_context["featurestore"]
                self.cursor = self.featurestore.getFeatures(request)
            else:
                _qgsfeaturestor = QgsFeatureStore()
                if hasattr(features_context, "__next__"):   # wish there was an easier way to test between iterator and iterable ~⪖ ˰⪕~
                    feature = next(features_context, None)
                    if feature != None:
                        _qgsfeaturestor.setFields(feature.fields())
                        _qgsfeaturestor.addFeature(feature)
                else:
                    _qgsfeaturestor.setFields(next(iter(features_context), QgsFeature()).fields())
                _qgsfeaturestor.addFeatures(features_context)
                if geometry is None:
                    geometry = _qgsfeaturestor.features()[0].geometry().wkbType() if _qgsfeaturestor.features() else "MultiPolygon"
                featurestore = VectorProcessing(NewVectorLayer(geometry, self.context, "_FEATUREPROCESSING_ITERATOR_CONTAINER_", "index=yes").id(), self.context, self.feedback)
                featurestore.startEditing()
                featurestore.setCrs(self.context.project().crs())
                if _qgsfeaturestor.features():
                    featurestore.dataProvider().addAttributes(NewFields(("_fid_", FieldType.int64), _qgsfeaturestor.features()[0].fields(), True))
                    for fid in range(_qgsfeaturestor.count()):
                        feature = _qgsfeaturestor.features()[fid]
                        self._fid_(feature, feature.id())
                        featurestore.dataProvider().addFeature(feature)
                else: featurestore.dataProvider().addAttributes(NewFields(("_fid_", FieldType.int64)))
                featurestore.commitChanges()
                self.featurestore = featurestore
                self.cursor = self.featurestore.getFeatures(request)
                self._featureidreturn = False
        self.request = request
        self._bulkbuffer: FeatureProcessing._BufferStore | None = None
        self._bulkbufferupdate = False
        self.connectfeatures = False
        if self:
            self._firstfeature = next(self.featurestore.getFeatures())
            self.cursorposition = self._firstfeature
        else:
            self._firstfeature = None
            self.cursorposition = None
        if self.featurestore.id() not in mNextFeatureId.keys():
            self.updatemNextFeatureId()
        self.RETURN_CLS: tuple[type, int] = (None, -1)

    def __iter__(self):
        return self

    def __next__(self) -> QgsFeature:
        feature: QgsFeature = next(self.cursor)
        self.cursorposition = feature
        if self._featureidreturn:
            feature.setId(feature["_fid_"])
        if self.connectfeatures:
            return self.ConnectedFeature(self, feature, self._featureidreturn)
        return feature

    def getFeatures(self, request: QgsFeatureRequest | str | list[int] = NO_REQUEST):
        return self.newCursor(request)

    def getFeature(self, id: int):
        return self[id]

    def __getitem__(self, id: int):
        if self._featureidreturn:
            for feature in self(QgsFeatureRequest().setFilterExpression(f'"_fid_" =  {id}')):
                feature.setId(id)
                _return = feature
                break
            else: raise IndexError()
        else:
            _return = self.featurestore.getFeature(id)
            if not _return.isValid(): raise IndexError()
        if self.connectfeatures:
            return self.ConnectedFeature(self, _return, self._featureidreturn)
        return _return

    def __setitem__(self, id: int, feature: QgsFeature):
        feature = QgsFeature(feature)
        self._fid_(feature)
        feature["_fid_"] = id
        self.featurestore.startEditing()
        if self._featureidreturn and self.fidExists(id):
            feature.setId(self.featureIdToLayerFid(id))
            self.featurestore.updateFeature(feature)
        elif self.featurestore.getFeature(id).isValid() and not self._featureidreturn:
            feature.setId(id)
            self.featurestore.updateFeature(feature)
        else:
            if self.featurestore.dataProvider().addFeature(feature):
                mNextFeatureId[self.featurestore.id()] += 1
        self.featurestore.commitChanges()

    def __delitem__(self, id: int | list[int]):
        id = [id] if isinstance(id, int) else id
        self.featurestore.startEditing()
        if self._featureidreturn:
            for _id in id:
                self.featurestore.dataProvider().deleteFeatures([self.featureIdToLayerFid(_id)])
        else:
            self.featurestore.dataProvider().deleteFeatures(id)
        self.featurestore.commitChanges()

    def __len__(self):
        return len(self.allFids())

    def __bool__(self):
        if self.featurestore.featureCount() > 0:
            return True
        return False

    def __contains__(self, id):
        if self._featureidreturn:
            return self.fidExists(id)
        return self.featurestore.getFeature(id).isValid()

    def __call__(self, request: QgsFeatureRequest | str | list[int] = NO_REQUEST):
        return self.newCursor(request)

    def __repr__(self):
        fid = self.cursorposition.id() if self else None
        return f"FeatureProcessing: {{Cursor at: {self.cursorposition}, Layer Fid: {fid}, Container: {self.featurestore}}}"

    def newCursor(self, request: QgsFeatureRequest | str | list[int] = NO_REQUEST):
        return self.newFeaturesObject(Carrier(self.featurestore, self._featureidreturn, key={"featurestore": 0, "featureidreturn": 1}), request=request)

    def _fid_(self, feature: QgsFeature, value: int = None):
        if "_fid_" not in feature.fields().names():
            attr: list = feature.attributes()
            attr.insert(0, value)
            feature.setFields(NewFields(("_fid_", FieldType.int64), feature.fields(), True), False)
            feature.setAttributes(attr)
        else:
            feature["_fid_"] = value

    def setRETURN_CLS(self, cls: type, for_runs: int = -1):
        self.RETURN_CLS = (cls, for_runs)
        return self

    def newFeaturesObject(self, features: QgsFeatureIterator | Iterable[QgsFeature] | Carrier, request: QgsFeatureRequest | str | list[int] = NO_REQUEST, *args, **kwargs):
        forruns = self.RETURN_CLS[1] if self.RETURN_CLS[0] is not None else -1
        cls = type(self) if self.RETURN_CLS[0] is None or forruns == 0 else self.RETURN_CLS[0]
        if forruns > 0: self.RETURN_CLS = (self.RETURN_CLS[0], forruns - 1)
        return cls(features, self.context, self.feedback, request=request, *args, **kwargs)

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>   Feature Methods     <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def newContainer(self, request: QgsFeatureRequest | str | list[int] = NO_REQUEST):
        fidreturn = self.isFeatureIdReturn()
        self.setFeatureIdReturn(True)
        _return = self.newFeaturesObject(self(request))
        _return.setFeatureIdReturn(fidreturn)
        _return.featurestore.setCrs(self.featurestore.crs())
        self.setFeatureIdReturn(fidreturn)
        return _return

    def setConnectFeatures(self, set_bool: bool):
        self.connectfeatures = set_bool
        return self.connectfeatures

    def isConnectFeatures(self):
        return self.connectfeatures

    def isFeatureIdReturn(self) -> bool:
        return self._featureidreturn

    def setFeatureIdReturn(self, set_bool: bool):
        self._featureidreturn = set_bool
        return self._featureidreturn

    def toggleFeatureIdReturn(self) -> bool:
        if self._featureidreturn:
            self._featureidreturn = False
        else:
            self._featureidreturn = True
        return self._featureidreturn

    def allFids(self) -> list[int]:
        return [feature["_fid_"] for feature in self(self.request)]

    def fidExists(self, fid):
        for f in self(QgsFeatureRequest().setFilterExpression(f'"_fid_" =  {fid}')):
            return True
        else: return False

    def featureIdToLayerFid(self, id) -> int:
        for feature in self.featurestore.getFeatures(QgsFeatureRequest().setFilterExpression(f'"_fid_" =  {id}')):
            return feature.id()

    def layerFidToFeatureId(self, fid) -> int:
        return self.featurestore.getFeature(fid)["_fid_"]

    @QUtilsExceptions.ErrorHandling
    def addFeature(self, feature, id: int = None):
        feature = QgsFeature(feature)
        if id is not None and self.fidExists(id):
            QUtilsExceptions.CriticalError(f"fid {id} already exists in container.", self.feedback)
        elif id is None and self.fidExists(feature.id()):
            QUtilsExceptions.CriticalError(f"fid {feature.id()} already exists in container.", self.feedback)
        self._fid_(feature)
        feature["_fid_"] = feature.id() if id is None else id
        self.featurestore.startEditing()
        _return = self.featurestore.dataProvider().addFeature(feature)
        if _return:
            mNextFeatureId[self.featurestore.id()] += 1
        self.featurestore.commitChanges()
        if self._firstfeature is None:
            self._firstfeature: QgsFeature = next(self.newCursor())
        return _return

    @QUtilsExceptions.ErrorHandling
    def addFeatures(self, features: Iterable[QgsFeature], maintainfid = False):
        _qgsfeaturestore = QgsFeatureStore()
        if hasattr(features, "__next__"):
            feature = next(features, None)
            if feature != None:
                _qgsfeaturestore.setFields(feature.fields())
                _qgsfeaturestore.addFeature(feature)
        else:
            _qgsfeaturestore.setFields(next(iter(features), QgsFeature()).fields())
        _qgsfeaturestore.addFeatures(features)
        if _qgsfeaturestore.count() == 0:
            return False
        self.featurestore.startEditing()
        for fid in range(_qgsfeaturestore.count()):
            feature = _qgsfeaturestore.features()[fid]
            if self.fidExists(feature.id()):
                if maintainfid:
                    QUtilsExceptions.CriticalError(f"fid {feature.id()} already exists in container.", self.feedback)
                featureid = mNextFeatureId[self.featurestore.id()] + 1
            else:
                featureid = feature.id()
            self._fid_(feature, featureid)
            _return = self.featurestore.dataProvider().addFeature(feature)
            if not _return:
                self.featurestore.rollBack()
                return _return
            mNextFeatureId[self.featurestore.id()] += 1
        self.featurestore.commitChanges()
        if self._firstfeature is None:
            self._firstfeature: QgsFeature = next(self.newCursor())
        return _return

    def addFields(self, fields: QgsFields, positions: list[int] = None):
        if positions is None:
            newpositions = None
        elif 0 in positions:
            changepos = []
            for i, pos in enumerate(sorted(positions)):
                if pos == i:
                    changepos.append(pos)
                    continue
                break
            newpositions = [pos + 1 if pos in changepos else pos for pos in positions]
        else:
            newpositions = positions
        self.featurestore.addFields(fields, newpositions)
        if self._bulkbuffer != None:
            self._bulkbuffer.updateFields()

    def deleteContainerFromContext(self):
        """This is permanent"""
        self.context.temporaryLayerStore().removeMapLayer(self.featurestore.id())

    def updatemNextFeatureId(self):
        self.featurestore.startEditing()
        self.featurestore.dataProvider().addFeature(QgsFeature())
        self.featurestore.commitChanges()
        mNextFeatureId[self.featurestore.id()] = max(self.featurestore.allFeatureIds())
        self.featurestore.startEditing()
        self.featurestore.dataProvider().deleteFeatures([max(self.featurestore.allFeatureIds())])
        self.featurestore.commitChanges()

    #-------------------------------------------------------#
    #>>>>>>>>>  Feature List to Vector Conversion  <<<<<<<<<#
    #-------------------------------------------------------#

    def FeaturesToLayer(self, request = NO_REQUEST):
        _layer = NewVectorLayer(self.wkbType(), self.context, "_FeatureToLayer_MEM_LAYER_")
        _layer.startEditing()
        _layer.setCrs(self.featurestore.crs())
        _layer.dataProvider().addAttributes(self.fields())
        _layer.dataProvider().addFeatures(self(request).cursor)
        _layer.commitChanges()

        self.feedback.pushInfo(f"Result: FeaturesToLayer: {_layer.id()}")
        return VectorProcessing(_layer.id(), self.context, self.feedback)

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>   Feature Connection   <<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    class ConnectedFeature(QgsFeature):
        def __init__(self, instance, feature, featureidreturn):
            super().__init__(feature)
            self._instance: FeatureProcessing = instance
            self._featureidreturn = featureidreturn
            self.bufferupdate = False
            self.backup = QgsFeature(self)

        def __setitem__(self, key, value):
            super().__setitem__(key, value)
            self._update()
        def __delitem__(self, key):
            super().__delitem__(key)
            self._update()

        def __getitem__(self, key): return super().__getitem__(key)
        def __iter__(self): return super().__iter__()
        def __ne__(self, value): return super().__ne__(value)
        def __eq__(self, value): return super().__eq__(value)
        def __hash__(self): return super().__hash__()

        @QUtilsExceptions.ErrorHandling
        def setId(self, id):
            """only updates the \_fid_"""
            if self._instance.fidExists(id):
                QUtilsExceptions.CriticalError(f"id {id} already exists", self._instance.feedback)
            self["_fid_"] = id
            self._update_both()
            super().setId(id)

        def setBufferUpdate(self, set_bool: bool):
            self.bufferupdate = set_bool
            return self.bufferupdate

        def setBulkBufferUpdate(self, set_bool: bool, update: bool = True):
            if not set_bool and update and self._instance._bulkbufferupdate:
                self.updateContainer()
            self._instance._bulkbufferupdate = set_bool

        def isBufferUpdate(self):
            return self.bufferupdate

        def isBulkBufferUpdate(self):
            return self._instance._bulkbufferupdate

        @QUtilsExceptions.ErrorHandling
        def updateContainer(self):
            if self._instance._bulkbufferupdate:
                if self._instance._bulkbuffer is None:
                    QUtilsExceptions.CriticalError("Buffer Store is not initialised on this cursor", self._instance.feedback)
                for feature in self._instance._bulkbuffer:
                    feature = QgsFeature(feature) #_bulkbuffer always returns features with _fid_ as the id
                    feature.setId(self._instance.featureIdToLayerFid(feature.id()))
                    self._instance.featurestore.updateFeature(feature)
                self._instance.context.temporaryLayerStore().removeMapLayer(self._instance._bulkbuffer.store.featurestore.id())
                self._instance._bulkbuffer = None
            else:
                feature = QgsFeature(self)
                if self._featureidreturn:
                    feature.setId(self._instance.featureIdToLayerFid(feature.id()))
                return self._instance.featurestore.updateFeature(feature)

        def _update(self):
            if not self.bufferupdate and not self._instance._bulkbufferupdate:
                return self.updateContainer()
            elif self._instance._bulkbufferupdate:
                self._updateBufferStore()

        def _update_both(self):
            _return = self._update()
            if self._instance._bulkbufferupdate:
                feature = QgsFeature(self)
                if self._featureidreturn:
                    feature.setId(self._instance.featureIdToLayerFid(feature.id()))
                return self._instance.featurestore.updateFeature(feature)
            return _return

        def _updateBufferStore(self):
            if self._instance._bulkbuffer is None:
                self._instance._bulkbuffer = self._instance._BufferStore(self._instance)
            self._instance._bulkbuffer.add_update_Feature(self)

        class _methodCaller(MethodCaller):
            @QUtilsExceptions.ErrorHandling
            def __call__(self, *args, **kwargs):
                self.instance: FeatureProcessing.ConnectedFeature
                if self.method.__name__ == "setAttribute":
                    if args[0] == "_fid_" or args[0] == 0:
                        QUtilsExceptions.CriticalError("Cannot change \_fid_ attribute. Call setId() instead.", self.instance._instance.feedback)
                elif self.method.__name__ == "setAttributes":
                    if args[0][0] != self.instance["_fid_"]:
                        QUtilsExceptions.CriticalError("Cannot change \_fid_ attribute. Call setId() instead.", self.instance._instance.feedback)
                elif self.method.__name__ == "deleteAttribute":
                    if args[0] == 0 or args[0] == "_fid_":
                        QUtilsExceptions.CriticalError("Cannot delete \_fid_ attribute", self.instance._instance.feedback)
                _return = self.method(*args, **kwargs)
                self.instance._update()
                return _return

        @QUtilsExceptions.ErrorHandling
        def __getattribute__(self, name: str):
            _return = super().__getattribute__(name)
            if callable(_return) and name not in object.__getattribute__(self, "__dict__") and name not in vars(FeatureProcessing.ConnectedFeature) and not name.startswith("__"):
                if _return.__name__ == "setFields":
                    QUtilsExceptions.CriticalError("Cannot setFields on individual connected features. addFields on the container.", self._instance.feedback)
                return FeatureProcessing.ConnectedFeature._methodCaller(_return, self)
            return _return
    class ConnectedFeature_Buffer(ConnectedFeature):
        pass
    if TYPE_CHECKING:
        class ConnectedFeature(ConnectedFeature_Buffer, QgsFeature):
            pass

    class _BufferStore:
        def __init__(self, instance):
            self.instance: FeatureProcessing = instance
            self.store = FeatureProcessing(self.instance.context, self.instance.feedback, self.instance.wkbType())
            self.store.startEditing()
            self.store.featurestore.dataProvider().addAttributes(self.instance.fields().toList()[1:])
            self.store.commitChanges()
            self.store.setFeatureIdReturn(True)

        def __iter__(self):
            return self

        def __next__(self) -> QgsFeature:
            return next(self.store)

        def add_update_Feature(self, feature):
            feature = QgsFeature(feature)
            if not self.instance._featureidreturn:
                feature.setId(self.instance.layerFidToFeatureId(feature.id()))
            self.store[feature.id()] = feature

        def updateFields(self):
            deleted: list[int] = []
            for name in self.store.featurestore.fields().names():
                if name not in self.instance.featurestore.fields().names():
                    deleted.append(self.store.featurestore.fields().indexFromName(name))
            added: list[tuple[QgsField, int]] = []
            for i, field in enumerate(self.instance.featurestore.fields().toList()):
                if field.name() not in self.store.featurestore.fields().names():
                    added.append((field, i))
            self.store.featurestore.startEditing()
            self.store.featurestore.dataProvider().deleteAttributes(deleted)
            self.store.featurestore.updateFields()
            fields = QgsFields()
            positions = []
            for field, i in added:
                fields.append(field)
                positions.append(i)
            self.store.featurestore.addFields(fields, positions)
            self.store.featurestore.commitChanges()

    #======================================================#

    class _methodCaller(MethodCaller):
        @QUtilsExceptions.ErrorHandling
        def __call__(self, *args, **kwargs):
            self.instance: FeatureProcessing
            datarename = False
            rename = False
            if isinstance(self.method.__self__, QgsVectorDataProvider):
                if self.method.__name__ == "renameAttributes":
                    if 0 in args[0].keys(): QUtilsExceptions.CriticalError("Cannot rename '_fid_' field", self.instance.feedback)
                    elif self.instance._bulkbuffer != None: datarename = True
            elif self.method.__name__ == "renameAttribute":
                if 0 == args[0]: QUtilsExceptions.CriticalError("Cannot rename '_fid_' field", self.instance.feedback)
                elif self.instance._bulkbuffer != None: rename = True
            elif self.method.__name__  == "deleteAttributes" or self.method.__name__ == "deleteAttribute":
                if 0 == args[0] or 0 in args[0]: QUtilsExceptions.CriticalError("Cannot delete '_fid_' field", self.instance.feedback)

            before: list = self.instance.featurestore.fields().names()
            beforemaxid = 0
            if self.instance:
                beforemaxid = max(self.instance.featurestore.allFeatureIds())
            _return = self.method(*args, **kwargs)
            if self.instance:
                if beforemaxid < max(self.instance.featurestore.allFeatureIds()):
                    mNextFeatureId[self.instance.featurestore.id()] = max(self.instance.featurestore.allFeatureIds())
            if datarename:
                self.instance._bulkbuffer.store.featurestore.dataProvider().renameAttributes(*args, **kwargs)
                return _return
            elif rename:
                self.instance._bulkbuffer.store.featurestore.renameAttribute(*args, **kwargs)
                return _return
            if isinstance(_return, QgsVectorDataProvider):
                return self.datawrapper(_return, FeatureProcessing._methodCaller, self.instance)
            if self.instance.featurestore.fields().names() != before and self.instance._bulkbuffer != None:
                self.instance._bulkbuffer.updateFields()
            return _return

    def __getattr__(self, name):
        if hasattr(self.cursor, name):
            return getattr(self.cursor, name)
        else:
            _return = getattr(VectorProcessing(self.featurestore.id(), self.context, self.feedback), name)
            if callable(_return):
                return self._methodCaller(_return, self)
            return _return
class FeatureProcessing_Buffer(FeatureProcessing):
    pass

if TYPE_CHECKING:
    class FeatureProcessing(Iterator[QgsFeature], FeatureProcessing_Buffer, QgsFeatureIterator, VectorProcessing):
        pass

mNextFeatureId = {}

#  ⩘-\▪◜
#grasshopper :3

#========================================================================================================#
#--------------------------------------------Raster Processing-------------------------------------------#
#===============================================>      <=================================================#

class RasterProcessing(BaseLayerProcesser):
    
    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>     Debug Methods     <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def peak(self, bins: int, y_truncpercent: int = 100, minValue: float | None = None, maxValue: float | None = None, band: int = 1, showTable: bool = False, tabname: str = None):
        minValue: float = self.dataProvider().bandStatistics(band, QgsRasterBandStats.All).minimumValue if minValue is None else minValue
        maxValue: float = self.dataProvider().bandStatistics(band, QgsRasterBandStats.All).maximumValue if maxValue is None else maxValue
        binSizes = (maxValue - minValue) / bins
        rasterClone = self.Clone(False)
        rasterClone.dataProvider().setNoDataValue(band, -999) if math.isnan(rasterClone.dataProvider().sourceNoDataValue(band)) else None
        NoData = rasterClone.dataProvider().sourceNoDataValue(band)
        self.feedback.setProgress(1)
        rastercalc = QgsProcessingUtils().mapLayerFromString(
            processing.run(
                "native:rastercalc", {      #gdal was being mean  ~◺˰◿~
                    'LAYERS':[str(rasterClone)],
                    'EXPRESSION':f' if (  ( "{rasterClone.name()}@{band}" < {minValue} )  OR  ( "{rasterClone.name()}@{band}" > {maxValue} ) , {NoData}, "{rasterClone.name()}@{band}" ) ',
                    'EXTENT':None,
                    'CELL_SIZE':None,
                    'CRS':None,
                    'CREATION_OPTIONS':None,
                    'OUTPUT':'TEMPORARY_OUTPUT'
                },
                is_child_algorithm=True,
                context=self.context,
                feedback=QgsProcessingFeedback()    #silent feedback >.o
            )['OUTPUT'],
            self.context
        )
        histDict = {}
        histogram = rastercalc.dataProvider().histogram(1, bins, minValue, maxValue, rastercalc.extent(), 0, includeOutOfRange=False).histogramVector
        self.context.temporaryLayerStore().removeMapLayer(rastercalc.id())
        for i_bin in range(bins):
            value = histogram[i_bin]
            bin_min = minValue + i_bin * binSizes
            bin_max = minValue + (i_bin + 1) * binSizes
            histDict[(bin_min, bin_max)] = value
            self.feedback.setProgress((100 / bins) * (i_bin + 1))
            if self.feedback.isCanceled():
                raise QgsProcessingException("Cancelled")
        self.histDict = {} #for IDE
        setattr(self, f"histDict@{band}", histDict)

        maxsum = max(histDict.values()) * (y_truncpercent / 100)
        linestring = renderGraph(histDict, 29, y_truncpercent, 0, minValue, maxValue, self.feedback)

        #sinful ~⪖◞⪕~
        binnolist = [1]
        for binno in range(2, bins + 1):
            number = binno + len(str(binnolist[len(binnolist) - 1]))
            number += 1 if binnolist[len(binnolist) - 1] == 98 else 0   #the sequence is always the same, 98 is the last 2 digit number.
            if number > bins:
                break
            binnolist.append(number) if number - len(str(binnolist[len(binnolist) - 1])) > binnolist[len(binnolist) - 1] and number != 101 else None 
        binstring = "·".join([f"{number}" for number in binnolist])                                                         #101 for the same reason as 98
        linestring = f"\nBin Numbers\n{'·' * 6}{binstring}\n" + linestring

        self.histogram = ""
        setattr(self, f"histogram@{band}", linestring)
        if showTable:
            columns = bins // (22 + len(str(bins))) if bins // (22 + len(str(bins))) > 4 else 4
            linestring += f"\n \n{'=♡' * ((bins + len(str(maxsum)) + 1) // 2)}="
            linestring += self.HistogramTable(columns, band, True)

        feedback: Feedback = self.feedback
        if isinstance(tabname, str) and hasattr(feedback, "widget"):
            if feedback.widget.withtabs:
                feedback = Feedback()
                widget = FeedbackWidget(feedback)
                widget._setWrap()
                widget.barpalette.setColor(QPalette.ColorRole.Base, Color("#5F095F"))
                widget.barpalette.setColor(QPalette.ColorRole.Text, Color("#ECECEC"))
                widget.bar.setPalette(widget.barpalette)
                widget.bar.setValue(0)
                widget.bar.setFormat(f"{self.name()}@{band} Histogram")
                setattr(self, f"tabfeedback@{band}", feedback)
                self.feedback.widget.addTab(widget, tabname)
            else:
                feedback.pushWarning("FeedbackWidget initialised without tabs")

        feedback.pushInfo(f"{'=♡' * 35}=")
        feedback.pushCommandInfo(linestring)
        feedback.pushInfo(f"\n{'=♡' * 35}=")

        return self
# ¯ <
# ∟ ?

    def HistogramTable(self, columns: int = 4, band: int = 1, returnstr: bool = False):
        if f"histDict@{band}" not in self.__dict__.keys():
            self.feedback.pushWarning("HistogramTable Method requires histogram materialisation of specified band. Run peak() first.")
            return self
        feedback = self.feedback
        if hasattr(self, f"tabfeedback@{band}"):
            feedback = getattr(self, f"tabfeedback@{band}")
        dictlist = [(key, value) for key, value in getattr(self, f"histDict@{band}").items()]
        linestring = "\n \n"
        rows = len(dictlist) / columns
        for row in range(int(rows)):
            linestring += "".join([
                 f"({(row * columns) + i + 1}){'·' * (len(str(len(dictlist))) - len(str((row * columns) + i + 1)))}"
                 f"{'·' * (5 - len(PrettyNumber(dictlist[(row * columns) + i][0][0], 3)))}{PrettyNumber(dictlist[(row * columns) + i][0][0], 3)} - "
                 f"{'·' * (5 - len(PrettyNumber(dictlist[(row * columns) + i][0][1], 3)))}{PrettyNumber(dictlist[(row * columns) + i][0][1], 3)}: "
                 f"{'·' * (5 - len(PrettyNumber(dictlist[(row * columns) + i][1], 3)))}{PrettyNumber(dictlist[(row * columns) + i][1], 3)}│"
                 for i in range(columns)
                 ])
            linestring += f"\n"
        remainder = len(dictlist) - (int(rows) * columns)
        linestring += "".join([
            f"({i + (int(rows) * columns) + 1}){'·' * (len(str(len(dictlist))) - len(str(i + (int(rows) * columns) + 1)))}"
            f"{'·' * (5 - len(PrettyNumber(dictlist[i + (int(rows) * columns)][0][0], 3)))}{PrettyNumber(dictlist[i + (int(rows) * columns)][0][0], 3)} - "
            f"{'·' * (5 - len(PrettyNumber(dictlist[i + (int(rows) * columns)][0][1], 3)))}{PrettyNumber(dictlist[i + (int(rows) * columns)][0][1], 3)}: "
            f"{'·' * (5 - len(PrettyNumber(dictlist[i + (int(rows) * columns)][1], 3)))}{PrettyNumber(dictlist[i + (int(rows) * columns)][1], 3)}│"
            for i in range(remainder)
            ])
        linestring += "".join([f"{'·' * (22 + len(str(len(dictlist))))}│" for i in range(columns - remainder)]) if remainder > 0 else ""

        if returnstr:
            return linestring
        else:
            feedback.pushCommandInfo(linestring)
            return self

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>     Layer Methods     <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#

    def topographicCrossSection(self, transect: Iterable[QgsPointXY], resolution: float, band: int = 1, graphheight: int = 29, returndict = False, tabname: str = None) -> dict[tuple[float, float], float] | None:
        feedback: Feedback = self.feedback
        newtab = False
        if isinstance(tabname, str) and hasattr(feedback, "widget"):
            if feedback.widget.withtabs:
                feedback = Feedback()
                widget = FeedbackWidget(feedback)
                widget._setWrap()
                widget.barpalette.setColor(QPalette.ColorRole.Base, Color("#5F095F"))
                widget.barpalette.setColor(QPalette.ColorRole.Text, Color("#ECECEC"))
                widget.bar.setPalette(widget.barpalette)
                widget.bar.setValue(0)
                widget.bar.setFormat(f"{tabname} Cross-Section")
                newtab = True
            else:
                feedback.pushWarning("FeedbackWidget initialised without tabs")

        line = QgsGeometry.fromPolylineXY(transect)
        steps = line.length() / resolution
        graphdict = {}
        _min = self.dataProvider().bandStatistics(band, QgsRasterBandStats.All).minimumValue
        for step in range(int(steps)):
            stepmin = resolution * step
            stepmid = line.interpolate(stepmin + (resolution / 2)).asPoint()
            stepmax = resolution * (step + 1)
            pixel = self.dataProvider().identify(stepmid, Qgis.RasterIdentifyFormat.Value)
            elevation = pixel.results()[band]
            elevation = _min if elevation is None else elevation
            graphdict[(stepmin, stepmax)] = elevation
            _max = stepmax
            self.feedback.setProgress((100 / int(steps)) * (step + 1))
        if returndict:
            if not steps.is_integer():
                remainder = resolution * (steps - int(steps))
                remainder_pixel = self.dataProvider().identify(line.interpolate(line.length()).asPoint(), Qgis.RasterIdentifyFormat.Value)
                remainder_elevation = remainder_pixel.results()[band]
                remainder_elevation = _min if remainder_elevation is None else remainder_elevation
                graphdict[(_max, _max + remainder)] = remainder_elevation
            return graphdict
        else:
            linestring = "····m\n"
            linestring += renderGraph(graphdict, graphheight, minValue=0, maxValue=_max, feedback=self.feedback)
            linestring += "\n····m"
            feedback.pushCommandInfo(linestring)
            if newtab:
                self.feedback.widget.addTab(widget, tabname)

    def xyToColRow(self, x: float, y: float):
        tlx = self.dataProvider().extent().xMinimum()
        tly = self.dataProvider().extent().yMaximum()
        return (
            int((x - tlx) // self.rasterUnitsPerPixelX()),
            int((tly - y) // self.rasterUnitsPerPixelY())
        )

    def colRowToXY(self, col: int, row: int):
        tlx = self.dataProvider().extent().xMinimum() + (self.rasterUnitsPerPixelX() / 2)
        tly = self.dataProvider().extent().yMaximum() - (self.rasterUnitsPerPixelY() / 2)
        return(
            (tlx + (col * self.rasterUnitsPerPixelX())),
            (tly - (row * self.rasterUnitsPerPixelY()))
        )

    #5BCEFA #F5A9B8 #FFFFFF #F5A9B8 #5BCEFA        ~>.o~

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Native Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def ClipRasterByMaskLayer(self, mask:str, source_crs:QgsCoordinateReferenceSystem = None, target_crs:QgsCoordinateReferenceSystem = None, target_extent:str = None, nodata:float = None, alpha_band:bool = False, crop_to_cutline:bool = True, keep_resolution:bool = False, set_resolution:bool = False, x_resolution:float = None, y_resolution:float = None, multithreading:bool = False, creation_options:str = None, data_type:int = 0, extra='', output = "TEMPORARY_OUTPUT", printfeedback=True):
        """
        GDAL Clip raster by mask layer process \n
        :param mask: Pointer string of the mask layer (vector or raster).
        :param source_CRS: CRS of the input raster. Uses raster CRS if None.
        :param target_CRS: CRS of the output raster. Uses raster CRS if None.
        :param nodata: NoData value assigned to pixels outside the mask.
        :param alpha_band: Adds an alpha band to represent transparency.
        :param crop_to_cutline: Crops output to mask geometry extent.
        :param keep_resolution: Preserves input raster resolution.
        :param set_resolution: Forces output resolution using X/Y values.
        :param x_resolution: Output pixel width (required if Set_Resolution=True).
        :param y_resolution: Output pixel height (required if Set_Resolution=True).
        :param multithreading: Enables GDAL multi-threaded processing.
        :param creation_Options: GDAL creation options string.
        :param data_type: Output raster data type (GDAL numeric code).
        :param extra: Additional GDAL command-line arguments.
        :param output: Output file path string | Default Temporary Memory Output.
        :return: RasterProcessing(FlexibleRasterLayer) object.
        """
        return self.run(
            "gdal:cliprasterbymasklayer", {
                'INPUT': "__self__",
                'MASK': mask,
                'SOURCE_CRS':source_crs,
                'TARGET_CRS':target_crs,
                'TARGET_EXTENT':target_extent,
                'NODATA':nodata,
                'ALPHA_BAND':alpha_band,
                'CROP_TO_CUTLINE':crop_to_cutline,
                'KEEP_RESOLUTION':keep_resolution,
                'SET_RESOLUTION':set_resolution,
                'X_RESOLUTION':x_resolution,
                'Y_RESOLUTION':y_resolution,
                'MULTITHREADING':multithreading,
                'CREATION_OPTIONS':creation_options,
                'DATA_TYPE':data_type,
                'EXTRA':extra,
                'OUTPUT':output
            },
            printfeedback=printfeedback
        )
    def ClipRasterByExtent(self, clipping_extent:str, override_crs:bool = False, nodata:float = 0, creation_options:str = None, data_type:int = 0, extra='', output="TEMPORARY_OUTPUT", printfeedback=True):
        """
        GDAL Clip raster by extent process \n
        :param clipping_extent: Extent string "xmin,xmax,ymin,ymax" defining the output raster bounds.
        :param override_crs: Treats extent as being within the rasters CRS.
        :param nodata: NoData value assigned to pixels outside the extent.
        :param creation_options: GDAL creation options string.
        :param data_type: Output raster data type (GDAL numeric code).
        :param extra: Additional GDAL command-line arguments.
        :param output: Output file path string | Default Temporary Memory Output.
        :return: RasterProcessing(FlexibleRasterLayer) object.
        """
        return self.run(
            "gdal:cliprasterbyextent", {
                'INPUT':"__self__",
                'PROJWIN':clipping_extent,
                'OVERCRS':override_crs,
                'NODATA':nodata,
                'CREATION_OPTIONS':creation_options,
                'DATA_TYPE':data_type,
                'EXTRA':extra,
                'OUTPUT':output
            },
            printfeedback=printfeedback
        )
    def RasterCalc(self, layers: list, expression: str, extent: str | QgsRectangle = None, cell_size: float = None, crs: str | QgsCoordinateReferenceSystem = None, creation_options: str = None, output = 'TEMPORARY_OUTPUT', printfeedback=True):
        """
        Native Raster calculator process
        """
        return self.run(
            "native:rastercalc", {
                'LAYERS':layers,
                'EXPRESSION':expression,
                'EXTENT':extent,
                'CELL_SIZE':cell_size,
                'CRS':crs,
                'CREATION_OPTIONS':creation_options,
                'OUTPUT':output
            },
            printfeedback=printfeedback
        )
    def FillNoData(self, fill_value: float, band: int = 1, creation_options: str = None, output = 'TEMPORARY_OUTPUT', printfeedback=True):
        """
        Native Fill NoData cells process
        """
        return self.run(
            "native:fillnodata", {
                'INPUT':"__self__",
                'BAND':band,
                'FILL_VALUE':fill_value,
                'CREATION_OPTIONS':creation_options,
                'OUTPUT':output
            },
            printfeedback=printfeedback
        )
    def Merge(self, input: str | list[str], nodata_input: float, nodata_output: float, pct: bool = False, separate: bool = False, creation_options: str = None, extra: str = '', data_type: int = 5, output = 'TEMPORARY_OUTPUT', printfeedback=True):
        """
        GDAL Merge process
        """
        input_list = ["__self__"]
        input_list.extend(input) if isinstance(input, list) else input_list.append(input)
        return self.run(
            "gdal:merge", {
                'INPUT':input_list,
                'PCT':pct,
                'SEPARATE':separate,
                'NODATA_INPUT':nodata_input,
                'NODATA_OUTPUT':nodata_output,
                'CREATION_OPTIONS':creation_options,
                'EXTRA':extra,
                'DATA_TYPE':data_type,
                'OUTPUT':output
            },
            printfeedback=printfeedback
        )

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Custom Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def GradientMask(self, maskvalue: float, band: int = 1, slopeangle: float = 0.5, printfeedback=True):
        self.feedback.setProgress(0) if printfeedback else None
        extent: QgsRectangle = self.extent()
        crs: QgsCoordinateReferenceSystem = self.crs()
        rastersize = extent.width() if extent.width() > extent.height() else extent.height()

        RasterClone = self.Clone(False).FillNoData(-999, band, printfeedback=False)
        self.feedback.setProgress(12) if printfeedback else None
        RasterMask = RasterClone.RasterCalc(["__self__"], f' if ( "{RasterClone.name()}@{band}" > {maskvalue}, "{RasterClone.name()}@1", -999 ) ', extent, crs=crs, printfeedback=False)
        self.feedback.setProgress(24) if printfeedback else None

        bin_RasterMask = RasterMask.RasterCalc(["__self__"], f' if ( "{RasterMask.name()}@1" = -999, -999, 1 ) ', extent, printfeedback=False)
        bin_RasterMask.dataProvider().setNoDataValue(1, -999)
        self.feedback.setProgress(36) if printfeedback else None

        RasterBuffer = bin_RasterMask.Vectorise(1, printfeedback=False) \
            .Dissolve("VALUE", printfeedback=False) \
            .RingBuffer(rastersize + (rastersize / 2), 1, printfeedback=False) \
            .Rasterise("CLASS", width=self.rasterUnitsPerPixelX(), height=self.rasterUnitsPerPixelY(), nodata=-999, printfeedback=False)
        self.feedback.setProgress(52) if printfeedback else None

        Gradient = RasterBuffer.run(
            "native:fillsinkswangliu", {
                'INPUT':"__self__",
                'BAND':1,
                'MIN_SLOPE':slopeangle,
                'CREATION_OPTIONS':None,
                'OUTPUT_FILLED_DEM':'TEMPORARY_OUTPUT'
                },
            "OUTPUT_FILLED_DEM",
            printfeedback=False
        )
        self.feedback.setProgress(64) if printfeedback else None
        GradientMask = Gradient.RasterCalc(["__self__", RasterClone], f' if ( "{RasterClone.name()}@{band}" > {maskvalue}, -999, "{Gradient.name()}@1" ) ', extent, crs=crs, printfeedback=False)
        self.feedback.setProgress(76) if printfeedback else None
        Gradient_dif = maskvalue - GradientMask.dataProvider().bandStatistics(1, QgsRasterBandStats.All).maximumValue
        GradientMask_corected = GradientMask.RasterCalc(["__self__"], f' {Gradient_dif} + "{GradientMask.name()}@1" ', extent, crs=crs, printfeedback=False)
        self.feedback.setProgress(88) if printfeedback else None

        output_raster = GradientMask_corected.Merge(RasterMask, -999, -999, printfeedback=False)
        output_raster.setCrs(crs)
        self.feedback.setProgress(100) if printfeedback else None

        output_raster.setName("GradientMask")
        self.feedback.pushInfo(f"Results: {output_raster.id()}") if printfeedback else None
        return output_raster

    #-------------------------------------------------------#
    #>>>>>>>>>>>>    Layer Type Conversion    <<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def Vectorise(self, raster_band: int = 1, field_name: str = 'VALUE', output="TEMPORARY_OUTPUT", printfeedback=True) -> VectorProcessing:
        """
        Native Raster pixels to polygons Process \n
        :param raster_band: Raster band index to convert.
        :param field_name: Attribute field name storing pixel values.
        :param output: Output file path string | Default Temporary Memory Output.
        :return: VectorProcessing(FlexibleVectorLayer) object.
        """
        return self.setRETURN_CLS(VectorProcessing, 1).run(
                "native:pixelstopolygons", {
                    'INPUT_RASTER': "__self__",
                    'RASTER_BAND': raster_band,
                    'FIELD_NAME': field_name,
                    'OUTPUT': output
                },
                printfeedback=printfeedback
            )

    #======================================================#

class RasterProcessing_Buffer(RasterProcessing):
    pass

if TYPE_CHECKING:
    class RasterProcessing(RasterProcessing_Buffer, QgsMapLayer, QgsRasterLayer):
        def dataProvider(self) -> QgsRasterDataProvider:
            pass


#========================================================================================================#


# >(,)(,)(,)(,)(,)(◜⋅)          i dont know what this is, but he's kinda cute, no?
#  ^^ ^^ ^^ ^^ ^^

try: installPointerString(PointerString)
except Exception as exc:
    QgsMessageLog.logMessage(f"PointerString failed to hook, call str(obj) or obj.id() when pointer string is needed. {exc}", "QUtils", Qgis.Warning)


#                    ↓↓ what pyQGIS does to a girl ↓↓
#                                                                                                       +++++                                                                               
#                                        ++++++                                                     ++++++++++                                                                              
#                                        +++++++++++++                                            +++++πππ+ππ++                                                                             
#                                                ++++++++                                       +++πππππ+++ππ++                                                                             
#                                                   ++++++                                     ++ππππππ+++πππ++                                                                             
#                                                    ++π+++++                               ++++πππππππ+++ππππ++                                                                            
#                              ++++++                  +++ππ++++                         +++++ππππππππ++++ππππ++                         ++                                                 
#                            ++++π++++++                +++πππ++                       ++++πππππππππππ++ππππππ++                       ++++                                                 
#                            ++++ππππ+++++              ++++ππ++++                    +++ππππππππππππ+++ππππππ++                       ++++                                                 
#                            ++πππππππππ+++++             ++ππππ++                  ++++πππππππππππππ+++ππππππ++                      ++π++                                                 
#                            ++ππππππππππππ+++            +++πππ++                 ++++ππππππππππππππ++πππππππ++                    ++++π++                                                 
#                           +++πππππππππππππππ+++         +++πππ+++             +++++++ππππππππππππππ++πππππππ++++++++             +++πππ++                ++                               
#                           +++ππππππππππππππππ++++        ++π+++++            +++++++ππππππππππππππ+++ππππππππππππ++              ++ππππ++              ++π++                              
#                           +++ππππππππππππππππ+++++       +++++++           +++++++++ππππππππππππππ+++πππππππππππ+++            ++ππππππ++             ++ππ++                              
#                           ++πππππππππππππππππππ++++++    +++++++          +++++++++πππππππππππππππ+++ππππππππππ++             +++ππππππ++           ++++π+++                              
#                           ++πππππππππππππππππππ+++++++++ ++++++++++++++++++++++++++ππππππππππππππ++πππππππππ++++++++++++++  ++++πππππππ++        +++++πππ+++                              
#                           +++ππππππππππππππππππ++++++++++++++++++++++++++++++++++++πππππππππππππ+++ππππππππππππππππππ+++++ ++πππππππππ+++       +++πππππ++++                              
#                           +++πππππππππππππππππππ+++++++++++++++++++++++++++++++++++πππππππππππππ+++ππππππππππππππππππ++  ++ππππππππππ++       ++++ππππππ+++                               
#                            ++πππππππππππππππππππ++++++++++++++++++++++++++++++++++++ππππππππππππ++ππππππ+++++++++π++++  ++πππππππππππ++    ++++πππππππππ+++                               
#                            ++ππππππππππππππππππ++++πππππ+++++++++++++ππππππππ+++++++ππππππππππππ++π+++++ππππ++++++++++++πππππππππππππ+++  +++πππππππππ+++++                               
#          ++++     ++++++++++++πππππππππππππππππ++πππππππ++++++ππππππππππππππππππππππ+++πππππππππ+++++ππ+++++ππππππππ+++++++++ππππππ++++++++πππππππππππ+++++                               
#          +++++       ++πππππ+++ππππππππππππππ++ππππππ++++πππππππππππππππππππππππππππππ+++ππππππ+++ππ+++ππππππππ++++πππππ++++++πππππππππππππππππππππππ++++++                               
#          +++++++       ++πππ+++πππππππππππππ++πππππ++++ππππππππππππππππππππππππππππππππππ+πππ++++ππ++πππππππ+++ππππππππππππ+++++πππππππππππππππππππ++++++                                 
#            ++++++      ++ππππ++πππππππππππππ++ππππ+++πππππππππππππππππππππππππππππππππππππ++π++ππππ++πππππ++ππππππππππππππ++++++πππππππππππππππππππ++++++                                 
#            ++++++++++++ ++πππ+++ππππππππππππ+++π+++πππππππππππππππππππππππππππππππππππππππππ++++++++ππππ+++πππππππππππππππ+++++++πππππππππππππππππ+++++++                                 
#            +++++++++++++++ππππ+++ππππππ+++++πππππ+πππππππππππππππππππππππππππππππππππππππππ+++++++++πππ++πππππππππππππππππ+++++++πππππππππππππππ+++++++++                                 
#            ++++++++++++++πππππππ++ππππ++ππππππππππππππππππππππππππππππππππππππππ+++π+++πππππ+++++++++π++ππππππππππππ+++πππ++++++π++πππππππππππππ++++++++                                  
#            ++++++++++++ππππππππππ++π+++ππππππππππππππππππππππππππππππππππππ+++++πππ+++π++ππππ++++++++++++ππππππ++++++ππππππ+++++π++ππππππππππππ+++++++++                       ++         
#             ++++++++++πππππππππππ+++++πππππππππππππππππππππππππππππππππππππ++πππ+++π++π++πππππ++++++++++++++++++++++++++++πππππππ++ππππππππππ+++++++++                         ++         
#             ++++++++++++++ππππ++++++++ππππππππππ++πππππππππππππππππππππππππππ++πππππππ+ππ++πππππ+++++++++++++++++++++++++++ππππππ++ππππππππ+++++++++++++++++++++++          +++++         
#              +++++++++++++π++++π++++++ππππππππππππ+++πππππππππππππππππππ+++πππππ+ππ+πππ++π++πππ++++++++++++++++++++++++++++++ππππππππππ+++++++++++++++++++++++++++    ++   +++π++         
#               +++++++++++ππ++πππ++ππ++ππππππππππππ++++πππππππππππππππππ+πππ++++π+πππ++ππππ++π++++++++++++++++++ππ++++++++++++πππ+++++++++++++++++++++++++++++++++     ++++ ++ππ++         
#                ++++++++++++++πππ+++++++πππππππππππ+++++ππππππππππππππππ+++ππππ+++πππ++ππππ++++++++++++++++++++πππ++++++++++++++++++++++++++++++++++++++++++++++       ++π++ππππππ+++++++++
#+++++++++++++++++++++++++++++ππππ+++πππ+ππππππππππ+++π+++ππππππππππππππππππ+++πππ+++πππππππ++++++++++++++++++ππππππ+++++++++++++++++++++++++++++++++++++++++++++       ++πππππππππππππππ++ 
# ++++++++++++++++++++++++++ππππ++πππ+++ππππππππππ+++πππ+++++ππππππππ+πππππππππ+++ππππππππππππ++++++++++++++πππππππππππππππππ+++++++++++++++++++++++++++++++++++        ++ππππππππππππ+++   
#   ++++++++++++++++++++++++ππππ++π+++ππ+πππππππππ+++ππππππ+++++ππππ++πππππππ++++++ππππππππππππ+++++++πππ++ππππππππππππππππππ+++++++++++++++++++++++++++++++++         ++ππππππππππ+++++    
#   ++++++++++++++++++++++πππππ++π+++πππ++ππππππππ++ππππππππππ+++++π++πππ++++++++++ππππππππππππ++ππ+++πππ++++++++++++ππππππ+++++++++++++++++++++++++++++++++++         ++ππππππππππ++       
#    ++++++++++++++++++++++ππππ+++ππππ++ππππππ+πππ++πππππππππππππ++++++++++++++++++ππππππππππππππ+++++++++++++++++++++π++++++++++++++++++++++++++++++++++++++        ++++πππππππππππ++++    
#      ++++++++++++++++++++ππππ++ππ+++++πππππππ++π++ππππππππ+ππππππ++ππππ++++++++++++ππππππππππππππππππππππ++++++++++++++++++++++++++++++++++++++++++++++++++       +++ππππππππππ++++       
#       +++++++++++++++++++ππππ++ππππ++++++ππ++++++++++ππππ+++ππ+++πππππππ++++++++++++πππππππππππππππππππππππππππππ++++++++++++++++++++++++++++++++++++++++       ++πππππππππ+++++          
#            +++++++++++++++πππ++ππππ+++++++++++++++π++++ππππ+++++πππππππ++++πππ+++ππ++++++ππππππππππππππππππππππππ+++++++++++++++++++++++++++++++++++++++       +++πππππππππ++             
#               ++++++++++++πππ++πππππ++++++++++++++πππππππππππππππ+++π+++πππππππππππ+++++++++ππππππππππππππππππππππ++++++++++++++++++++++++++++++++++++         ++ππππππππ++++             
#              +++++++++++++++ππ++ππππ++++++++++++++++πππππππππππππ++++++ππππππππππ+++++++++++ππππππππππππππππππππππ+++++++++++++++++++++++++++++++++++        ++πππππππππ+++               
#          ++++++++++++++++++++π+++πππ++++++++++++++++++ππππππππππππ++++ππππππππππ+++++++++π+++ππππππππππππππππππππ+++++++++++++++++++++++++++++++++          +++ππππππππ+++                
#            +++++++++++++++++++++++π+++++++++++++++πππ+++ππππππππππ++πππππππππππ++ππ++++++πππ+ππππππππππππππππππππ++++++++++++++++++++++++++++             ++ππππππππππ++                  
#             +++++++++++++++++++πππππππ++++++++++++πππππππ++πππππππππππππππππππ+++πππ++++ππππ+++ππππππππππππππππ++++++++++++++++++++++++++++++++++++++    ++ππππππππππ++                   
#                +++++++++++++ππππππππππ++++++++++++ππππππ+++πππππππππππππππππππ++ππππ++++πππππ++πππππππππππππ+++++++++++++++++++++++++++++++++++++++    ++++πππππππππ+++                   
#                   ++++++ππππππππππππ+++++++++++++++πππππ+ππππππππππππ+++++πππ+++ππππ+++ππππππ+++++++++++++++++++++++++++++++++++++++++++++++++++      +++πππππππππ+++                     
#                     ++πππππππππππ++++π++++++++π++++++πππππππππππ++πππππ+++ππππ++ππππ+++ππππππππ+++++++++++++++++++++++++++++++++++++++++++++        ++πππππππππππ+++                      
#                     ++ππππππππππ+++πππ+++++π++π+++++++++ππππ+++++πππ+++ππππππ+++ππππ+++ππππππππππ++++++++++++++++++++++++++++++++++                ++ππππππππππ++                         
#                      ++πππππππππ+++ππππ++++ππ++++++++++++++ππππ+++++πππππππ+++++ππππ++ππππππππππ++++++++++++++ππ+++++++++++++++++++              ++++ππππππππππ++                         
#                        ++πππππππ++πππππ++ππππππ+++++++++++++++ππππππππππππ++++++ππππ++ππππππππππ++++++++++++++πππ++++++++++++++++               +++ππππππππππ++                           
#                      +++++++++++++ππππ++ππππ++++++ππππ++++++++++++++++++++++++++++ππ+++πππππππππ++++++++++++++ππππ++++++++++++++              +++ππππππππππ+++                            
#                     +++++++++++++πππ++πππ+++++ππ+++ππππππ++++++++++++++++++++++++++π++++πππππππππ++++++++++++++++ππ+++++++++++++             ++ππππππππππ+++                              
#                     ++++++++++++πππ+++++++++ππππ++++πππππππ++++++++++++++++++++++++π++++++ππππππππ++++++++++++++++ππ++++++++++             ++πππππππππππ+++                               
#                   ++++++++++++++πππ+++++++++ππππ++++ππππππππ++++++++++++++++++++++++++πππ+++πππππππ+++++++++++++++++πππ++++++             ++πππππππππππ++                                 
#                   +++++++++++++++++++++++++πππππ++++ππππππππππ+++++++++++++++++++ππ++++πππ+++++πππππ+++++++++++++  ++++++++          +++++ππππππππππππ++                                  
#                   +++++++++++++++++++++++++πππ++++ππππππππππππππππ+++πππππ++π++++++++++ππππππ++++++++++++++++++++                   +++ππππππππππππ+++                                    
#                         +++++++++++++    ++++++ ++++πππππππππππππ+++ππππ+++ππ+++ππ++++πππππππππππππ+++++++++++++                 +++ππππππππππππ+++                                       
#                                                   +++++πππππππ++++++πππ++ππ++ππππππ+++ππππππππππππππππ++++++++++               ++ππππππππππππππ+                                          
#                                                       ++++++++++++++πππ+πππππππππππ++πππππππππππππππππ++++++++++            ++++πππππππππππππ++                                           
#                                                                  ++ππππ++ππππππππ+++ππππππππππππππππππ++++++++          +++++ππππππππππππ++++                                             
#                                                                  ++πππππππ+++πππ+++πππππππππππππππππππ++++++++     +++++πππππππππππππππ++                                                 
#                                                                  +++πππππππ++++++ππππππππππππππππππππ++++++++++++++++πππππππππππππππ+++                                                   
#                                                                   ++ππππππππππ++ππππππππππππππππππππ+++++++++++πππππππππππππππππππ++                                                      
#                                                      +++++++++++++++++++ππππππππππππππππππππππππ+++++++++++++++++πππππππππππππ+++++                                                       
#                                             +++++++++πππ++++++ππππππ++++++++++++++++++++++++++++++π++++++++πππππππ+++++πππ++++++                                                          
#                                    ++++++++++ππππππππ++++ππππππππ+++ππππππ++++ππππππππ++++++πππππππππ++++ππππππππππππππ+++++++++                                                          
#                                 ++++ππππππππππππππ+++ππππππππππ+++πππππππππππ+++πππ+++ππππππ+++++ππ+++++ππππππππππππππππ+++++++++                                                         
#                                 ++πππππππππππ+++++ππππππππππππ+πππππππππππππππππ+++πππππππππππππ++++++++ππππππππππππππππππ+++ππππ++++++                                                   
#                               +++ππππππππππ++πππππππππππππππππππππππππππππππππππ++πππππππππππππππππ+++++πππππππππππππππππππππππππππππππ+++++++++++                                        
#                              ++ππππ+++πππππππππππππππππ+πππππππππππππππππππππππ+ππππππππππππππππππ++πππ+ππππππππππππππππππππππππ+++πππππππππππππ++++++++                                 
#                               ++++++ππππππππππππππππππ++ππππππππππππππππππππππ++πππππππππππππππππππ++πππ+πππππππππππππππππππππππππππ+++ππππππππππππππππ+++++                              
#                              ++++ππππππππππππππππππππ+ππππππππππππππππππππππππ++πππππππππππππππππππ++ππππππππππππππππππππππππππππππππππ+++ππππππππππππππππ++++                            
#                        ++++++πππππππππππππππππππππππ+ππππππππππππππππππππππππ+πππππππππππππππππππππ++ππππ++πππππππππππππππππππππππππππππππ+++ππππππππππππ+++                              
#                   +++++ππππππππππππππππππππππππππ+ππππππππππππππππππππππππππ+ππππππππππππππππππππππππππππ++πππππππππππππππππππππππππππππππππππππ+πππππππ+++                               
#                +++++πππππππππππππππππππππππππ++πππππππππππππππππππππππππππ+πππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππ+++++                               
#             +++++πππππππππππππππππππππππππππ+++πππππππππππππππππππππππππππ+ππππππππππππππππππππππππππ+πππππ+πππππππππππππππππππππππππππ++++++ππππππππ+++π+++++                            
#            +++ππππππππππππππππππππππππππππ+++πππππππππππππππππππππππππππ++πππππππππππππππππππππππππππ+πππππ+πππππππππππππππππππππππ++++ππππππ+++++π+++ππππππ+++                           
#               +++πππππππππππππππππππππππ+ππππππππππππππππππππππππππππππππππππππππππππππππππππππππππππ+ππππππππππππππππππππππππ++++++πππππππππππ+++π+++πππππππππ+++++                      
#                ++π+++ππππππππππππππππ+ππππππππ+++++ππππππππππππππππππππππππππππππππππππππππππππππππππ+πππππππππππππππππππππ+++++++++πππππππππππ+πππ+++πππππππππππππ++                     
#                +++πππ++ππππππππππππ+πππ+++++ππππππ++++++ππππππππππππππππππππππππππππππππππππππππππππππππππππ++ππππππππππ++++++++++++++πππππππ+++π++++ππππππππππππππππ++                   
#                  ++ππππ+ππππππππππ+π++++ππππππππππ+++++++++ππππππππππππππππ++++++++++πππππππππππππππππ++ππππ++πππππππππ++++++++++++++++ππππππ++++++πππππππππππππππππ+++                   
#                  +++ππππ++ππππππππ++++ππππππππππ++++++++++++++ππππππππππππ+πππ+++++++++++++πππππππππππ++πππππππππππππ+++++++++π++++++++++ππ++++++++++πππππππ+++++++++                     
#                   +++++++++++ππππππ+++πππππππππ++++++++++++++++++πππππππ++ππππ++++++++++++++++++++++++ππππππππππππππ+++++++++πππππππ++++++++++++++++++π++++++++++                         
#                   ++ππππππ+++πππππππππ+++ππππ++++++++++++++++++πππππππππππ+ππ+++++++++++++++++++ππππππ++ππππππππππ++++++++++++ππππππππππππ+++++++++++++++                                 
#                  +++++πππππ++ππππππππππ++ππππ+++++++++++++++++ππππππππππππ+ππ+++++++++++++++++++ππππππ++ππππππππππππ++++++++++ππππππππππππππππππ++++++++                                  
#                     +++++ππ++ππππππππππππ+ππ++++++++++++++++++πππππππππππππ+++++++++++++++++++++πππππ+++πππππππππππππ+++++++++ππππππππππππππππππππππ++++                                  
#                        ++++++++++++πππππ++++++++++++++++++++++πππππππππππππ++++++++++++++++++++++++++ππππππππππππππππ++++++++++πππππππππππππππππππππππ++                                  
#                           +++++++++++++++++++++++++++++++++++++++ππππππ++++++++++++++++++++++++++++++πππππππππππππππ++++++++++++ππππππππππππππππππππππ++                                  
#                               ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ππππππππππππππππππππππ++                                  



#                Chihiro <3 </3                                                  ....:::::::::....                                                            
#                                                                            ..:=+***#***#********+-:...                                                    
#                                                    ...:-++*#******++-.....+*****#****#***#***********+=..                                                 
#                                               ..:-+#######**###**#****=+*##*******#**********************+-..                                             
#                                             .-+#########**###**#**#*+***************************************+-.                                           
#                                          .:+############**##**###***#*####*#***#***************************+***=.                                         
#                                        .-#######################**#*##**######*##***#****************************=.                                       
#                                       .#############*###*#**#**#**#***************************+***+-==++***********=.                                     
#                                     .=%%%#############*########*#***###**#*#*#************************=====+********+-.                                   
#                                    :##%#%###########**###****##****#***********************************+=-=====+*++**+=:.                                 
#                                  .-%%#%%############***#######**#***###**###**##**##**********************+-======+==++=-.                                
#                                 .+%%%%%%############+###**##**###**#**##***#********************************=-============:                               
#                                .*%%%%%%%%%%##*#####=######**##**##+**##**###*###*##*****#*******************#+=-+==========:.                             
#                               .*#%%%%%%%%%%#+%#####+#############*=#***##***#*****************#***##*#########*+-===========:.                            
#                              .*####%%%%%%%*#%%%%%#*###############*+####*###**##***#**#####################+++++==-==========:.                           
#                             .-#######%%%%*%%#%%%#%*%#%%%###########=############################*##########*=======:-========-..                          
#                            .-###########*##%%%%%%%=%%%%%%%%#%%%##%##+#%##########################*+#######**========--========-.                          
#                           .-############+####%%%%%=%%%%%%%%%%%%%%%%%=#%%%%##%%%%%##################++#******+========--========:.                         
#                           -############+##########=%%%%%%%%%%%%%%%%%#=%%%%%#%%%%#%%################**-=******==========-========.                         
#                         .-############****##*#####=#######%%%#%%%##%%+*%####+#################********+-=+***+=========-:=======:.                        
#                        .+#############=*##*##**###=###################+#####**#############*************====**==-=======-:=======..                       
#                      .-###############=#**#**#*#**+#***##*#############-#####+#######********************+-==+===-=======--======-.                       
#                     :*######*#########=####*#*+*##++******#**##***####*=-*##**+****************************=======-=======.=======-.                      
#                   :*######*+##%#######=#####*#*+*#=-*##****##**********==-+****=+******+**+*****************+-=====-======-.=======-.                     
#                .-*#######++###########-*######*=##==+***##*************+=-=+****+=*********=*****************+-=====-======--=======-.                    
#          ...-*****+=-:...*############+=*###*##=+*==-+*##***#*#+#**#****==--=*****-=********+=******+****+***++-====--======:-=======-.                   
#                       .-#############*#-=*#####+=#+=-=+*##*+**#*=*******+=-+-==****=-=+*******+-+**********+***+--===-======-:========-.                  
#                     .:*##########*#####*-=+**##+=+*==:-=+##*+****-*******=-**-===+***-===+******+-==+********+***=:===-======-.-========..                
#                   ..+############+######=-=+####+=*+=---==+**=#***-***#***==**=-====+**-=====+****+=-===+**+***+**+--=--======:...-===-==-.               
#                 .-*#########+###*+######*--==+*#+==+==-+:===+*=+##*-+#**##+=+***:=======+=-=======++++--====++***++*+=--=======..  ..:---==-.             
#              ..+###########**##*+#***##*+==-=+========-=#+:=====-+**==+*****-**##*--===------::::-=======-:-=====+++***+-======-.       ........          
#         ..:=############*+=####+*##****====:========--::+#--=====-+*+-=*****-#*%%#*::==========--==-:-======-:-==========--====-.                        
#      ..:+*##########*+++++=####*+##**##+====-+--=---======###=:=====-=+=-=+**+=##%%%%%+--===========--=---=========----=====----=-..                      
# ...=#########*+=--=+++=-#=+####*+###*##+=====#*-=.:=====--.+###*:.====-===-==+++##%%%%%%%#-.-============--:===============-------:....                   
#      .........::::-+*###++####*=+#***#*====-*+#%###+-::::--:-=*%###=--===-==-====##%%%%%%+=-++-::-==---====-===------------::::---==-.                    
#               ..=######++###**+==*##*#+====-*##%*-*##+=--::::.:-*%%%%#*=--==----=-*#%%%%==-:..........::::::--:-----------==-=========:.                  
#           ::=*#######*+*#####+===##*+*+====-*-=-%#-............:+=+%%%%%%##*-:---:-=#%%-:.....:--:::....:-=+*=:=========--===--========-..                
# ....---=+#######**+++-#####*+====*##+#+=====+*++...=*==++++++=-:.-#%%%%%%%%%%###*+=--+%=.=-=+++++++-**=:.:+++-:+========:===--=--========-:.              
#    ..:::-=++======---#####*+=+==-*#***+====-+=-..=#@+++++*++++++-+-%%%%%%%%%%%%%%%%%%%*-%=++++++++++-%%*=..++=:+========:-====-.:---=======--..           
#                   :+#####*++==+=++##*=+===+=##:.+%@@=++++++-++++=@#%%%%%%%%%%%%%%%%%%%+@%=++++-++++++*%%%-.:*=-*+======-:=--===-.  ......:.......         
#                 .=######+====-+##=#**=+====-#=.:%@@@+*+++++-++*++%@%%%%%%%%%%%%%%%%%%%%@#=++++:=+++++=%%%*.-*=-++======--==--===-.                        
#               .-######+===-.:###*=*#*+=+===-##-:#@@@+*++++++++*+=@@%%%%%%%%%%%%%%%%%%%%@@+++++++++++++%%%+:**=-*+-=====-.====--===:                       
#             .-#####*+==-..  :*****=***=====-=#%*-%@@#+*++*+++++++@@%%%%%%%%%%%%%%%%%%%%@@+++++++++++=%%%*:=+*:-++======: ..=++=---=-.                     
#          ..=#####*=-:..     .=##**-##*+=====.#*%%=#@@%++++++++++@%%%%%%%%%%%%%%%%%%%%%%%%@#=+++++++-%@%=+%%#+::++-====-.    ..:-+++---..                  
#       .:=###+=-...          .=**##=-#**=====.*#%%*%%@@@#====-+%@%%%%%%%%%%%%%%%%%%%%%%%%%%@@*-==-+%%%#%%%%%#-:-++-====-.          ........                
#  ....:::....                -*##*====###====-:#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%+.-:=+-====-:                                  
#                            .=#*#+====+**+===--=#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%+#%%%%%%%%%%%%%%%%%%%%%%%%%%%#:===-++===---.                                 
#                           .=*##+==+=:==##+====-+%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%---==-++-==--=:                                 
#                         .:+##*=====..==:+#+==-=:*%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%=:==-=-=*===-==-.                                
#                       .-*#*+=====:..:*==--#*-=-=:#%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%=..:==---=+-=--==-.                               
#                 ...-==+=======-..  .++====-+*==-=-+%%%%%%%%%%%%%%%%%%%##%%%%%%%%%%%##%%%%%%%%%%%%%%%%%%---. .===--++--====-.                              
#                  ....:::::...     .-#=======-++=-=--%%%%%%%%%%%%%%%%-=+@@@@@@@@@@@@@*-=%%%%%%%%%%%%%%%:-==..  .-+=-+=--===--.                             
#                                   :**===========+-==-%%%%%%%%%%%%%%+-=====-------=====:%%%%%%%%%%%%%--====-.    .:++=--=====-.                            
#                                  :**+======-======-:===%%%%%%%%%%%%*-===========-=-----%%%%%%%%%%%=:=======-.      .-=:=--====:.                          
#                                 -#*+===========--+=====-=%%%%%%%%%%%===-=+++++++++==-=%%%%%%%%%%+:-==========:.       ..-=+=--=-.                         
#                               .+**+==========-:.+*========-%%%%%%%%%%+=++++++++++++++%%%%%%%%%+-===-++=========:.          ...:..:..                      
#                             .:***+=========-.. =**========-=:#%%%%%%%%%=+++++++++++#%%%%%%%%--======--+++========:.                                       
#                           .:+#*+========-..   -**+=======-====--*%%%%%%%%%=---==*%%%%%%%%+:-========--=--=+*++======:..                                   
#                         .-+#++======-:..     .+**=======-========--*%%%%%%%%%%%%%%%%%%+--=====-=======--===-------====--...                               
#                      ..++==--::...          .+#*=======--========-....=%%%%%%%%%%%%=.-====-====-=+======-:=====-.                                         
#                     .......                :***=======:-========.  .:#**+=-=+**=--++=.=====-=====--+++=====---===-:.                                      
#                                           -**+======..====-===:. ...:#%#*****+++++++=..-====-:-=====--++++=====-::-=-:.                                   
#                                         .=+==-===:. .===-===...:+##*:%%%%%#****++++++-#**=--==..-=====-..-=+++++++===-:::...                              
#                                       .-===-=-:.. .-====-.. ..#####*-%%%%%%%##***++++-#-+#*+:==-..:-===-..  ........::.:::.....                           
#                                     .-=--::..   .:::..      .%@@##--=%%%%%%%%%%***+++-:*#****:-==:...-===:.                                               
#                                    .                     ..+@@@@@@%#++====+**+==---+*+==*####*+:..:.. .:-=-.                                              
#                                                        .-%@@@@@@@@##%%##+=+#*#+++=##**+==#%@@###*=:..    ..:-..                                           
#                                                   ...-+@@@@@@@@@@%#@@@@#+#####++#-:----++#@@@@%#****+:.      ....                                         
#                                            ...:-=#%@@@@@@@@@@@@@%#@@@@@-####*#+=##=++==+#%#*=#@@%#*****==-:...                                            
#                                      ..:-=*%@@@@@@@@@@@@@@@@@@@%#@@@@@+=##=#*-##-#%%%%%%%#+--*+@%#*#********++=-...                                       
#                             ...::=+#%@@@@@@@@@@@@@@@@@@@@@@@@@%#%@@@@#-=#@==*#=%%%%%#%%%%%%%#==%%########**##******+=-...                                 
#                          .-#%@@%##%@@@@@@@@@@@@@@@@@@@@@@@@@@%#%@@@@%-#+*===:=%%#-=**+--=**#*++=%@@@@@@%@@%%%%%#******+==--:..                            
#                          .-=-@@@@@###@@@@@@@@@@@@@@@@@@@@@@@%#%@@#+-..:=%%%%%%%-#%%%%%%%%%=***-+=@@@@@@@@@@@@%%%%%#*+==+*+**+++-.                         
#                       .-=====-:%@@@@%##%@@@@@@@@@@@@@@@@@@#+--======-:+%%+##*#%+++==-==##**-***=++@@@@@@@@@@@@@%%%#+*##***++=--=.                         
#                      .-===-=====-#@@@@%##%@@@@@@@@@@@@@#-=====---=-+=*%%%%%%%%%%****=*+-***+-**+++--#@@@@@@%@@%%***%%%%%#*=:::::::..                      
#                     .-==-==--=====:*@@@@@###@@@@@@@@@@+===--+@@@@-#=*%%%%%%%#*+-:=**=+*:+***++***=---=@@@%@@%#**#%%%%%%%=::::::::::.                      
#                    .======--=-======-=@@@@@###%@@@@@@@-=-=#@@@@%-#=*%%%%%%%%#=-+***+---:+*****+**+:--:%@@%#**#%%%%%%%*::-:::::::::::..                    
#                   .-==========:========:%@@@@%###%@@@%--=-*#+-::--*%%%%%%%%%+-=**--+*+-*%*****++*=---:=****%@%%%%%%=:--::::-:::::::::.                    
#                  .-=====----==---=-=====-:#@@@@@%#####*--===-----=%%%%%%%%%#=+*++=*+-#%%%#****+*+---=%@@@%%%%%%%#-:--::::-:::::::::-::.                   
#                 .:======-===--==---===-===-:+@@@@@@@@@@@@#*-----=%%%%%%%%%%*-*****-+%%%%%%******+=@@@@@%@@%%%%=:---::::--.:::::::::---:.                  
#                .:========---==--=-:-=-=======--#@@@@@@@@@--=:=-:%%%%%%%%%%#*=***==#%%%%%%%#*****:#@%%%@@%%%+.----:::----:::--:::::-::::.                  
#                .-=======--==----=-------=======-:-+##++=-==:=@*=%%%%%%%%%#*++**-+%%%%%%%#*****+-:-==*#*+-::----::::---:::---::::::::::::.                 
#               .-========-==========-======-=====--==---=====--@%:#%%%%%%%#*+**=*%%%%%%%*****+-.--:----------::::-----:::----::::::::::::..                
#              .:====--===---=--=-=------=---==-==-----:---=---=:+@#:#%%%%#*****-%%%%%%****+==------::::::::::::------::-----::::::::::::::.                
#              .-=========-==========-=-=-===------==----=====--=-:+#+-#%#*****+:#%%%#**+-=+----------::::::::--------:------::::::::::::::..               
#              .-====================-------=-===-==-------=--:-----.=*+:+*****+.-*#*+-=*+-------------:::::---------:------::::::::::::::::.               
#             .:=========--===--==--=-:------------:------+=::--------.-*+-:=-.::-:-=*+=--------+=-=::--:----------:-:------::::::::::::::::.               
#             .-===-=============-===-:------==---:---------------------::**+-:..=**=----------:=--=-:---:--------:::------:::::::::::::::::..              
#            .-=========-======-=-===------==-=--=------=------------------:-+:.-=::------------:==--.-----:------::--------::::::::::::::::..              
#           .:=--==-===--==---==--==-------=-:------------------------------::::.---------------::::::-------:---:::---------::::::::::::::::.              
#           .-===-===--==---=---==----::---:-=--==---=------------------:--:::---------------------------------:-::::----------::::::::::::::..             
#           .:=-===--==-====-===--===-:.-:-=---=------------------::---------::---------------------------------::::.-----------::::::::::::::.             
#           .--==--=---==---=---=-----...-----=---=--------=----------------::::----------------------------------::.:-----------:::::::::::::.             
#           .-=====--==--=-=--==-----:..:---------------=-------:---::-:--:.:--:::---------------------------------:.::---------::::::::::::::.             
#           .-===-===--==----=---=---.-----------=-------------:-::--:--:.:-:::-:-:::------------------------------:.:::--------::::::::::::::.             
#          .-==-===-========---=--------=---------------------::-:-::-:.:::::::::=-.::::----------------------------..:::-------::::::::::::::.             
#          .-====-===-------==--=----=---=---=-------------------::-:.:--::--:::-=-::::::----------------------------.::::------::::::::::::::.             
#         .-=======-=======---=----=---=---=----=--------------:--:.:--::--::--::==::::::::---------------------------:::::------:::::::::::::..            
#        .:=---==--=----=----:-===---==-------=---=--------------::-----------:-:=+::::::::----------------------------::::-----::::::::::::::..            
#        :=========-------::--=----------------------------:--:::---::-:::::::::-+*-----::::-----------------------------:::::-::::::::::::::::.            
#       .-===-===-===---.--===--==--==----=-------------:----.:-:::-::::::::::---+*--------.:-----------------------------:::::::::::::::::::::.            
#      ..==========-:---====-===--===--==--=---=-----------::--:-------:---::----+*--------:.:-----------------------------::::::::::::::::::::.            
#      .--===-=--:.-----=--------------------------------:.-:----::--::::::------+*---------:.:------------------------------:::::::::----::::::.           
#      .-=====:--:=-============-==---==---=----------:-::-----:---::--::--------+*---------:::.:-------------------------------::---------:::::.           
#      .-===-:-:--===---=--=---=-----=---=-----------::------:-::::--::----------#+----------::::.:--------------------------------::::::::::::::.          
#     .-===-----==--===-=-=---=--===---=-----------::-::--:---:::--::------------#=-----------:::::.::---------------------------------::::::::::..         
#    .-==--==-===-===-===--===--=---==----------:::-----:---::---::--------------#---------:::-:::::.::::-------------------------------:.::::::::.         
#   .-=========-===-===--===--=---------------::::------------------------------+#----------::::::::::.:::::-----------------------------::.::::::.         
#   .-===-==--==--==---==-------------------:-.:----::--:-----------------------#+-----------::::::::::..:::::::--------------------------::::::::.         
#    :-================-=-------------------:.:-----------:--------------------=#--------------::::::::::.:::::::::::-----------------------::::::..        
#   .:-=--==---=---=----------------------:.. .-----:--------------------------*+---------------::::::::::.::::::::::::::::::::::::::::::::::::::::..       
#   .-------===--==----------------------..   .:-------------------:----------=#------------------::::::::::.:::::::::::::::::::::::::::::::::::::::.       
#   .---------==-----------------------:.     .-------------------------------**--------------------:::::::::.::::::::::::::::::::::::::::::::::::::.       
#   .:-------------------------------:.       .------------------------------=#=:----------------------:::::::::::::::::::::::::::::::::::::::::::..        
#    .:----------------------------:..       .:------------------------------*+==------------------------::::::..::::::::::::::::::::::::::::::::::.        
#     .:--------------------------:.        .:------=-----------------------=#-=*--------------------------:::::..:::::::::::::::::::::::::::::::::..       
#       .-----------------------:.         .:-------------------------------**=-#=---------------------------::::...:::::::::::::::::::::::::::::::..       
#        .:-------------------:.          .--:------------------------------#-*=+*----------------::-::::-::-:::::. .::::::::::::::::::::::::::::::.        
#          .:-------------:...           .--------------------:------------*+=*+-#-------------:--------------:::::. ..:::::::::::::::::::::::::::.         
#            .::-----:...               .--------------------:-------------#-+**=**-------------:--------------:::::.  .::::::::::::::::::::::::..          
#                ...                   .-------:::::::::::::::------------#+++=++-#=-------------:::::::::::::::::::..  ..::::::::::::::::::::..            
#                                     .--=--------------------------------#:+=##*#*#-------------------------::::::::..    ...::::::::::::::..              
#                                    .--=--=-----------------------------#=++#%%%%-#+-----------------------------:::::.       ...::::::::..                
#                                   .-=-===---=-------------------------=*-*=#%%%%++#=----------------------------::::::.          ......                   
#                                  .------------------------------------#=**=%%%%%=-**----------------------------:::::::.                                  
#                                 .-=----------------------------------+*=**=%%%%%=+-#=---------------------------::::::::.                                 
#                                .----=-=-----------------------------=#-+**=%%%%%=+=+#:---------------------:------:::::::.                                
#                               .--===---=----=-----------------------#+=***=%%%%%++#-#*:---------------------------::::::::.                               
#                              ..##+------------=--------------------*#-***#=%%%%%++%*=#+------------------------::::::::.:-=..                             
#                               ..-+#####+=-------------------------=#=+****#%%%%%++%%++#=--------------------::::--======--..                              
#                                   .....:-==++*########**###########+=*****-*+=+*=+*##-*######***##*###*+====----::.....                                   
#                                            ..--::::::::::...::.:::::::::::::::.::.::::....:::.:::::::::::::::..                                           
#                                            .-=====---------:===::--================-=====-=+=-:::::::::::--:::.                                           
#                                            .===========---:+++++--==============--===--=-+++++-::::::::-::::-:..                                          
#                                           .-====-=======---+++++-:-==------=----==---=---=+++=-::::::::::::::::.                                          
#                                           .===============--==--:--========-----------::::---::::::::::::::::::.                                          
#                                          .:==-:::---========------:--:::-::--::::::::::::::::::::::::::::...:::..                                         
#                                        .:==--===--=======-=-----::::::--:-:::::::::::::----------=---=-:::::::-::..                                       
#                                      .:==-=====-========-============--===-------=---=----=-------=-----:::::::::::..                                     
#                                    .:========-=========:========-====-======-===--=-----=--==-------------:::::::::::..                                   
#                                  .:==-===============--=============--===--===--==---==--=----=---:---=----::::::::::::..                                 
#                                .-==-======-=========--=========-===---=--==---==--==---=-----------:--------::::::::::::::.                               
#                              .-=========--=========--==============--=-=====----==---=--==---------::--------::::::::::::::..                             
#                            .-==-======--==========--===============-============--=---=-----=--=----:----------::::::::::::::..                           
#                          .-==-=======:-==========-=================-==-=-=======--=---=---=---==-----:----------:::::::::::::-::.                         
#                        .-==-=======--===========-=================:======--==-==--=--:----------------:-----------::::::::::::::::.                       
#                      .:==-========-===========--==================-=============-==-=-=======-==--==--::-----------::::::::::::::::..                     
#                    .:-=--=======--===========--==============-===--===-===-=======--=---===-==---=---=-::-==-==-----:::::::::::::::::..                   
#                  .:-==-========--===========-:==================-:-==-========-======--==------=---=----:-------==---::::::::::::-:::::..                 
#                .::==-=========:============--===================-:==============-====-:====-==----------::------------::::::::::::::::::...               
#              ..:-==-========--===========---===================-:-================-===---====-====----=-:::=-====-=-==-:::::::::::::::::::...             
#             .:-==-=========--===========----========-===-=====----===-===--==--===--==:-==--=------------::-------=-----::::::::::::::::::::..            
#           ..-===-=========--===========----===================---==========--===--===-----===-===--==--==:::-=--===-====---:::::::::::::::::::..          
#         ..-==============--===========----==========-===--===-:----==--==-==---===----:-==----------------:::-=-----=-----:::::::::::::::::::::...        
#        .:===============:============----===================---:-==-=================-----=-------=-------::::-=--=--------::::::::::::::::::::::..       
#      ..-==============-:===========-----============-=======-:--=--==-====-===-===--=-::----=-------------::::-=-------=---=-:::::::::::::::::::::...     
#     .-==============---===========-----====================------======-===--===-===------=----=-----------::::------------=--::::::::::::::::::::::..    
#    .-==============---===========------=============-===--=--::-==-=====---===-===--=-:--=-----------------::::---=------------::::::::::::::::::::::..   
#  .:==============----===========------============-=======----:--=---=-------=----===-::---=------==--=-----::::---------=-----::::::::::::::::.::::::... 
# .:==============----===========------====================----:-======-========-=----=-::-=-----------==--=--:::::---------------::::::::::::::::::::::::..