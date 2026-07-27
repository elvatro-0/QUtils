"""QUtils"""
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

import qgis.core
from qgis.core import(
    QgsProcessingParameterFeatureSource,
    QgsProcessingFeatureSource,
    QgsFeature,
    QgsGeometry,
    QgsVectorLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingUtils,
    QgsProcessingAlgorithm,
    QgsMapLayer,
    QgsFields,
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsFeatureIterator,
    QgsFeatureRequest,
    QgsProcessingException,
    QgsRasterBandStats,
    QgsRasterDataProvider,
    QgsRasterBlockFeedback,
    QgsVectorDataProvider
)
from qgis.analysis import(
    QgsRasterCalculatorEntry,
    QgsRasterCalculator
)
from qgis import processing
from typing import TYPE_CHECKING, Union
import functools, inspect, traceback, math


#========================================================================================================#
#---------------------------------------------Error Handler----------------------------------------------#
#===============================================>      <=================================================#

#I want error messages to look pretty
class QUtilsExceptions(QgsProcessingException):
    def __init__(self, message: str = None, feedback: QgsProcessingFeedback | None = None):
        super().__init__(message)
        self.message = "" if message == None else message
        self._feedback = feedback
    @staticmethod
    def CriticalError(message: str = None, feedback: QgsProcessingFeedback = None):
        raise QUtilsExceptions(message, feedback)

    def ErrorHandling(func):
        @functools.wraps(func)
        def stack_tracer(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except QUtilsExceptions as _except:
                if _except._feedback is None:
                    feedback = None
                    for fb in inspect.signature(func).bind(*args, **kwargs).arguments.values():
                        if isinstance(fb, QgsProcessingFeedback):
                            feedback = fb
                            break
                else:
                    feedback = _except._feedback

                feedback.reportError(
                "\n QUtils Critical Error\n"
                f"{'=♡'*35}=\n"
                f"{func.__name__} Error\n"
                f"Traceback:\n{''.join(traceback.format_list(traceback.extract_stack()[:-1]))}"
                ) if feedback != None else None
                raise QgsProcessingException(f"{_except.message}\n{'=♡'*35}=\n")
        return stack_tracer


#========================================================================================================#
#----------------------------------------------Functions-------------------------------------------------#
#===============================================>      <=================================================#

#and if your using some random, niche backend provider that doesn't support rewinding of FeatureIterators, then materialise it into a python list.
#That performance loss is on you for being weird.
@QUtilsExceptions.ErrorHandling
def ListSlicer(input_list: list | QgsFeatureIterator | QgsVectorLayer | QgsMapLayer, input_slice: tuple[Union[list[int], None], Union[tuple[int, int], list[tuple[int, int]], None], Union[list[int], list[tuple[int, int]], None]], feedback: QgsProcessingFeedback, context: QgsProcessingContext = None) -> list | QgsFeatureIterator | QgsVectorLayer:
    """
    Applies a three component slicing rule to a list of objects, a QgsFeatureIterator, or a QgsVectorLayer, returning a filtered List, QgsFeatureIterator, or QgsVectorLayer. \n
    *because the native slice is a bit rubbish* \n
    NOTE: if your input is QgsFeatures (QgsFeatureIterator or QgsVectorLayer), the fid is the positional int, but for an accurate output you must subtract 1 on
    the desired fids ints in the input_slice as fids are 1-based, and the slicing logic is 0-based. The output will return the correct 1-based feature ids after slicing logic.\n
    :param input_list: List of objects to slice (supports QgsFeatureIterator, and QgsVectorLayer). QgsVectorLayer as input slices the layers features.
    :param feedback: QgsProcessingFeedback object for error and warning reporting.
    :param input_slice: Tuple defining slicing behaviour: \n
                (Include, Range, Exclude)
                Include:
                    - None -> no explicit inclusions
                    - list[int] -> explicit feature indicies to include \n
                Range:
                    - None -> no ranges
                    - (start, stop) -> range of indices to be included
                    - list[(start, stop)] -> multiple ranges
                    - single positive int within a range defaults as the start, stop defaults as None
                    - single negative int defauls as stop, start defaults as 0
                    - start as None defaults as 0, stop as None defaults as object count - 1 (because 0-based)
                Exclude:
                    - None -> no explicit exclusions
                    - list[int] -> explicit indicies to exclude
                    - list[(start, stop)] -> range if indicies to exclulde (can be multiple ranges)
                    - Exclude range logic is consistant with Range param logic
                    - Note: Exclude ints override include (Include and Range) ints
    :return: Filtered list of objects, QgsFeatureIterator, or QgsVectorLayer
    """

    if input_slice == None:
        return input_list
    elif isinstance(input_list, list):
        _count = len(input_list)
    elif isinstance(input_list, (QgsVectorLayer, QgsMapLayer, BaseLayerProcesser, FlexibleMapLayer, VectorProcessing)):
        if context != None:
            _count = input_list.featureCount()                       #if gaps in fid lists weren't possible, this would be much simpler... ~⪖ ‸⪕~
            geomlist = ["MultiPoint", "MultiLineString", "MultiPolygon"] if next(input_list.getFeatures()).geometry().isMultipart() else ["Point", "LineString", "Polygon"]
            c_layer = context.temporaryLayerStore().addMapLayer(QgsVectorLayer(geomlist[input_list.geometryType()], "_ListSlicer_MEM_LAYER_", "memory"))
            c_layer.startEditing()
            c_layer.setCrs(input_list.crs())
            c_layer.dataProvider().addAttributes(input_list.fields())
            c_layer.dataProvider().addFeatures(input_list.getFeatures())
            c_layer.commitChanges()
        else:
            QUtilsExceptions.CriticalError("Slice Error: Context required for QgsVectorLayer as input")
    elif isinstance(input_list, QgsFeatureIterator):
        if context != None:
            first = next(input_list)
            input_list.rewind()
            geomlist = ["MultiPoint", "MultiLineString", "MultiPolygon"] if first.geometry().isMultipart() else ["Point", "LineString", "Polygon"]
            c_layer = context.temporaryLayerStore().addMapLayer(QgsVectorLayer(geomlist[first.geometry().type()], "_ListSlicer_MEM_LAYER_", "memory"))
            c_layer.startEditing()
            c_layer.setCrs(context.project().crs())
            c_layer.dataProvider().addAttributes(first.fields())
            c_layer.dataProvider().addFeatures(input_list)
            c_layer.commitChanges()
            _count = c_layer.featureCount()
        else:
            QUtilsExceptions.CriticalError("Slice Error: Context required for QgsFeatureIterator as input")

    
    _includeList = []
    if isinstance(input_slice, tuple) and len(input_slice) == 3:
        _include, _range, _except = input_slice
        if _include is None and _range is None:
            _includeList.extend([n for n, i in enumerate(input_list)])
        
        #=====Include=====#
        if _include == None:
            pass
        elif isinstance(_include, list):
            if _count - 1 < max(_include):
                QUtilsExceptions.CriticalError(f"Slice Error: first object contains int higher then the objects bounds. Max int: {max(_include)}, Object upper bound int: {_count - 1}")
            _includeList.extend(_include)
        else:
            QUtilsExceptions.CriticalError("Slice Error: First object must be list.")
        
        #=====Range======#
        if _range == None:
            pass
        elif (isinstance(_range, tuple) and len(_range) <= 2) or isinstance(_range, list):
            _range = [_range] if isinstance(_range, tuple) else _range
            for ind_range in _range:
                if not isinstance(ind_range, tuple) or len(ind_range) > 2:
                    QUtilsExceptions.CriticalError("Slice Error: second object must be a tuple containing a range of two values or a list of tuple ranges.")
                if len(ind_range) == 1:
                    ind_range = (0, -ind_range[0]) if ind_range[0] < 0 else (ind_range[0], None)
                    #A neat way to extract the value if you add a comma after the int. E.g. (5,) == (5) -> (5, None); (-5,) == (-5) -> (0, 5)
                start, stop = ind_range
                start = 0 if start == None else start
                start = _count - 1 if start > _count - 1 else start
                stop = _count - 1 if stop == None or stop > _count - 1 else stop
                if start > stop:
                    QUtilsExceptions.CriticalError(f"Slice Error: second object must be a tuple containing a range of two values or a list of tuple ranges. The first value must be less then the second value. start: {start}, stop: {stop}")
                _includeList.extend([r for r in range(start, stop + 1)])                
        else:
            QUtilsExceptions.CriticalError("Slice Error: second object must be tuple containing a range of two values or a list of tuple ranges. None as first or second value evaluates as either highest or lowest value.")

        #=====Except=====#
        r_except = []
        if _except == None:
            pass
        elif isinstance(_except, list) and len(_except) > 0:
            for ind_except in _except:
                if isinstance(ind_except, tuple):
                    if len(ind_except) == 1:
                        ind_except = (0, -ind_except[0]) if ind_except[0] < 0 else (ind_except[0], None)
                    estart, estop = ind_except
                    estart = 0 if estart == None else estart
                    estart = _count - 1 if estart > _count - 1 else estart
                    estop = _count - 1 if estop == None or estop > _count - 1 else estop
                    r_except.extend([r for r in range(estart, estop + 1)])
                elif isinstance(ind_except, int):
                    r_except.append(ind_except)
                else:
                    QUtilsExceptions.CriticalError("Slice Error: third object must be None or list of ints or tuple ranges")
            if max(r_except) > _count - 1:
                QUtilsExceptions.CriticalError(f"Slice Error: third object max value int is higher then the objects bounds. Max int: {max(r_except)}, Object upper bound int: {_count - 1}")
        else:
            QUtilsExceptions.CriticalError("Slice Error: third object must be None or list of ints or tuple ranges")
        
    else:
        _includeList.extend([r for r in range(0, _count)])
        feedback.pushWarning("Slice Error: object must be tuple containing three list/tuple objects (Include, Range, Exclude). Defaulting to entire list.")

    check_featurenumber = []
    check_featurenumber_1based = []
    for featuren in _includeList:
        if featuren not in check_featurenumber and featuren not in r_except:
            check_featurenumber.append(featuren)
            check_featurenumber_1based.append(featuren + 1)
    filterList = sorted(check_featurenumber)

    if isinstance(input_list, list):
        return [input_list[n] for n in filterList]

    if isinstance(input_list, (QgsVectorLayer, QgsMapLayer, BaseLayerProcesser, FlexibleMapLayer, VectorProcessing)):
        filterList = sorted(check_featurenumber_1based)
        c_layer.startEditing()
        c_layer.selectByIds(filterList)
        c_layer.invertSelection()
        c_layer.deleteSelectedFeatures(QgsVectorLayer().DeleteContext(True, context.project()))
        c_layer.commitChanges()
        return c_layer
    
    if isinstance(input_list, QgsFeatureIterator):
        filterList = sorted(check_featurenumber_1based)
        return c_layer.getFeatures(QgsFeatureRequest().setFilterFids(filterList).setOrderBy(QgsFeatureRequest().OrderBy([QgsFeatureRequest().OrderByClause("$id", True)])))

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
    return f"{number:.{ndigits - 1}e}" if abs(number) >= 10 ** 15 else f"{trunc_numb}{letter[0]}"

#========================================================================================================#
#------------------------------------------Proxy Base Wrappers-------------------------------------------#
#===============================================>      <=================================================#

class FlexibleMapLayer:     #this is my baby ♡
    def __init__(self, input_pointer: str, context: QgsProcessingContext):
        if not isinstance(input_pointer, str):
            raise TypeError(f"FlexibleMapLayer Received {repr(input_pointer)} - Requires Pointer String")
        self._pointer = input_pointer
        self._context = context

    def __str__(self):
        return str(self._pointer)

    def __repr__(self):
        return f"FlexibleMapLayer({self._pointer!r})"
        
    def __getattr__(self, name):
        return getattr(QgsProcessingUtils.mapLayerFromString(self._pointer, self._context), name)

class BaseLayerProcesser(FlexibleMapLayer):
    def __init__(self, input_pointer: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        super().__init__(input_pointer, context)
        self._feedback = feedback

    def is_pointerStr(self, input) -> bool:
        if not isinstance(input, (str, FlexibleMapLayer)):
            return False
        _string = QgsProcessingUtils.mapLayerFromString(str(input), self._context)
        return isinstance(_string, QgsMapLayer)

    #output can be specified by the position of the layer pointer str in the processing output dict, or by the spcefic keys name.
    @QUtilsExceptions.ErrorHandling
    def ProcessingOutput(self, processdict: dict, output: str | int = 0) -> str | None:
        if isinstance(output, str):
            if output not in processdict.keys():
                QUtilsExceptions.CriticalError(f"output {output} does not exist", self._feedback)
            elif not self.is_pointerStr(processdict[output]):
                self._feedback.pushWarning(f"output {output} is not pointer string.")
                self._feedback.pushInfo(f"{output}: {processdict[output]}")
                return None
            else:
                return processdict[output]
        if isinstance(output, int):
            _return = []
            for _value in processdict.values():
                if self.is_pointerStr(_value):
                    _return.append(_value)
            return _return[output]

    def ProcessingInput(self, parameters: dict[str, object]):
        for key, val in parameters.items():
            if self.is_pointerStr(val):
                parameters[key] = str(val)
        return parameters

    def forceMapLayer(self):
        return QgsProcessingUtils.mapLayerFromString(str(self._pointer), self._context)
    
    #roses are red, I like mantle wedge depletion-
    def addLayerToLoadOnCompletion(self, output_name: str):
        self._context.addLayerToLoadOnCompletion(str(self._pointer), QgsProcessingContext.LayerDetails(output_name, self._context.project()))


#========================================================================================================#
#--------------------------------------Direction AND MAGNITUDE!------------------------------------------#
#==========================================> OH YEAH!!! <================================================#

#And before you want to write to me, and say I shouldnt inherit twice, read the note
class VectorProcessing(BaseLayerProcesser):
    """NOTE: This class inherits/abstracts from BaseLayerProcesser *only* to preserve type identity
    and correct external behaviour so that QGIS and external scripts treat it as a FlexibleMapLayer object. \n
    All actual layer behaviour is delegated to an internal BaseLayerProcessing instance stored 
    in self._vector. This "*dual*" structure allows the returned VectorProcessing object to behave 
    as BOTH a pointer string (via __str__) and a live QgsMapLayer (via __getattr__), which is 
    required for seamless use in processing.run() while maintaining VectorProcessing methods for chaining."""
    def __init__(self, input_vector: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        self._context = context
        self._feedback = feedback
        self._vector = BaseLayerProcesser(input_vector, self._context, self._feedback)
    
    def run(self, algorname:str | QgsProcessingAlgorithm, parameters: dict[str, object], output: str | int = 0):
        _output = self._vector.ProcessingOutput(
            processing.run(
                algorname,
                self.ProcessingInput(parameters),
                is_child_algorithm=True,
                context=self._context,
                feedback=self._feedback
            ),
            output=output
        )

        if not _output:
            return self
        else:
            return VectorProcessing(_output, self._context, self._feedback)

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>     Debug Methods     <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def peak(self, rows: int = 5, start: int = 1, min_colwidth: int = 6):
        stop = start + rows - 1 if self._vector.featureCount() >= start + rows - 1 else self._vector.featureCount()
        self._feedback.pushInfo(f"\n{'=♡' * 35}=\n Attribute table for {str(self._vector)}\n rows {start}-{stop}")
        min_colwidth += 1 if min_colwidth & 1 == 1 else 0
        name_string = ""
        for name in self._vector.fields().names():
            name_Length = min_colwidth if len(str(name)) < min_colwidth else len(str(name))
            name_string += f"{'·' * ((name_Length - len(str(name))) // 2)}{name}{('·' * ((name_Length - len(str(name))) // 2)) + ('·' if len(str(name)) & 1 == 1 else '')}|"        #big padding >.<
        self._feedback.pushCommandInfo(name_string)
        for row, feature in enumerate(self._vector.getFeatures()):
            if row < start - 1: continue
            if row > stop - 1: break
            row_string = ""
            for name in self._vector.fields().names():
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
            self._feedback.pushCommandInfo(row_string)
        self._feedback.pushInfo(f"{'=♡' * 35}=\n")                                 #Chonky </3

        return self
# ⋅ >.<
# · 
# · <<
# ∙ 

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>  Modification Methods  <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def layer_Slicer(self, input_slice: tuple[Union[list[int], None], Union[tuple[int, int], list[tuple[int, int]], None], Union[list[int], list[tuple[int, int]], None]]):
        self._feedback.pushInfo(f"Result: layerFeatures_Slicer: {str(self._vector)}")
        return VectorProcessing(ListSlicer(self._vector, input_slice, self._feedback, self._context).id(), self._context, self._feedback)

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Native Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def fixGeometries(self, method: int = 1, output="TEMPORARY_OUTPUT"):
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
                'INPUT': self._vector,
                'METHOD': method,
                'OUTPUT': output
            }
        )
    def Dissolve(self, field: QgsFields = [], separate_disjoint: bool = False, output="TEMPORARY_OUTPUT"):
        """
        Native Dissolve Process \n
        :param field: QgsFields list of attributes | Blank list will dissolve all atrtibute fields
        :param separateDisJoint: If True, features and parts that do not overlap or touch will be exported as separate features
        :param output: Output file path string | Default Temporary Memory Output
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        return self.run(
            "native:dissolve", {
                'INPUT':self._vector,
                'FIELD': field,
                'SEPARATE_DISJOINT': separate_disjoint,
                'OUTPUT': output
            }
        )
    def Smooth(self, iterations:int = 1, offset: float = 0.5, max_angle: float = 180, output="TEMPORARY_OUTPUT"):
        """
        Native Smooth geometry process
        """
        return self.run(
            "native:smoothgeometry", {
                'INPUT':self._vector,
                'ITERATIONS':iterations,
                'OFFSET':offset,
                'MAX_ANGLE':max_angle,
                'OUTPUT':output
            }
        )

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Custom Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def RingBuffer(self, diameter: float, rings: int, invert: bool = False, overlap: int = 0, segments: int = 16, output="TEMPORARY_OUTPUT"):
        """
        Creates a multi-ring buffer with overlap logic based on a generated Class field \n
        NOTE: Does not preserve attributes. Creates new CLASS Field. \n
        :param input: TypeVectorPoint | TypeVectorLine
        :param diameter: Total Diameter (map units)
        :param rings: Number of donut rings
        :param invert: True = Increasing class value inwards (inner ring as highest value) \n
                       False = increases class value outwards (Outer ring as highest value)
        :param overlap: Overlap Resolution: \n
                        0 = Lower value overrides
                        1 = Higher value overrides
        :param segments: Number of line segments to approximate a quarter circle when creating rounded offsets
        :param output: Output file path string | Default Temporary Memory Output
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        return self.run(
            "script:Ring_Buffer", {
                'INPUT': self._vector,
                'DIAMETER': diameter,
                'RINGS': rings,
                'INVERT': invert,
                'OVERLAP': overlap,
                'SEGMENTS': segments,
                'OUTPUT': output
            }
        )
    #-------------------------------------------------------#
    #>>>>>>>>>>>>    Layer Type Conversion    <<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def Rasterise(self, field:str, burn:float = 0, use_Z:bool = False, units:int = 1, width:float = 30, height:float = 30, extent:str = None, nodata:float = 0, creation_options:str = None, data_type:int = 5, init:float = None, invert:bool = False, extra:str = '', output = "TEMPORARY_OUTPUT"):
        """
        GDAL rasterize Process \n
        :param field: Attribute field used to assign pixel values.
        :param burn: Constant value to burn into all pixels.
        :param use_Z: Uses Z-values from geometry as pixel values, if True.
        :param units: Pixel size units: \n
                  0 = Georeferenced units per pixel
                  1 = Pixels per map unit
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
        _output = self._vector.ProcessingOutput(
            processing.run(
                "gdal:rasterize", {
                    'INPUT': str(self._vector),
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
                is_child_algorithm=True,
                context=self._context,
                feedback=self._feedback
            )
        )

        return RasterProcessing(_output, self._context, self._feedback)

    #-------------------------------------------------------#
    #>>>>>>>>>>>  Vector to Feature Conversion  <<<<<<<<<<<<#
    #-------------------------------------------------------#
    def VectorToFeature(self):
        self._feedback.pushInfo(f"Result: VectorToFeature: {str(self._vector)}_QgsFeatureIterator")
        return FeatureProcessing(self._vector.getFeatures(), self._context, self._feedback)

    #======================================================#

    def __getattr__(self, name):
        return getattr(self._vector, name)
class VectorProcessing_Buffer(VectorProcessing):
    pass

if TYPE_CHECKING:
    class VectorProcessing(VectorProcessing_Buffer, QgsMapLayer, QgsVectorLayer):
        pass

#I studied geology not english language, of course theres spelling mistakes ~>.<~

#========================================================================================================#
#-------------------------------------------Feature Processing-------------------------------------------#
#===============================================>      <=================================================#

class FeatureProcessing:
    """NOTE: When calling QgsFeature methods on a FeatureProcessing object, the method is executed *only* on the first QgsFeature in the feature list/iterator. \n
    This is useful for broader geometry introspection, but for geometry operations or transformations, iterate through the featurelist attribute."""
    @QUtilsExceptions.ErrorHandling
    def __init__(self, input_features: list[QgsFeature] | QgsFeatureIterator, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        if (isinstance(input_features, list) and isinstance(input_features[0], QgsFeature)) or isinstance(input_features, QgsFeatureIterator):
            self._context = context
            self._feedback = feedback
            self.featurelist = input_features
            if isinstance(input_features, list):
                self._feature = self.featurelist[0]
            if isinstance(input_features, QgsFeatureIterator):
                self._feature = next(self.featurelist)
                self.featurelist.rewind()
        else:
            QUtilsExceptions.CriticalError("Input_Features contain invalid objects or is empty - Requres list of QgsFeature objects or QgsFeatureIterator as input")

    #-------------------------------------------------------#
    #>>>>>>>>>  Feature List to Vector Conversion  <<<<<<<<<#
    #-------------------------------------------------------#

    def FeaturesToLayer(self, input_slice: tuple[Union[list[int], None], Union[tuple[int, int], list[tuple[int, int]], None], Union[list[int], list[tuple[int, int]], None]] = None):
        geomlist = ["MultiPoint", "MultiLineString", "MultiPolygon"] if self._feature.geometry().isMultipart() else ["Point", "LineString", "Polygon"]
        _layer = self._context.temporaryLayerStore().addMapLayer(QgsVectorLayer(geomlist[self._feature.geometry().type()], "_FeatureToLayer_MEM_LAYER_", "memory"))
        _layer.startEditing()
        _layer.setCrs(self._context.project().crs())
        _layer.dataProvider().addAttributes(self._feature.fields())
        _layer.dataProvider().addFeatures(ListSlicer(self.featurelist, input_slice, self._feedback, self._context))
        _layer.commitChanges()

        self._feedback.pushInfo(f"Result: FeaturesToLayer: {_layer.id()}")
        return VectorProcessing(_layer.id(), self._context, self._feedback)

    #======================================================#

    def __getattr__(self, name):
        return getattr(self._feature, name)
class FeatureProcessing_Buffer(FeatureProcessing):
    pass

if TYPE_CHECKING:
    class FeatureProcessing(FeatureProcessing_Buffer, QgsFeature):
        pass

#  ⩘-\▪◜
#grasshopper :3

#========================================================================================================#
#--------------------------------------------Raster Processing-------------------------------------------#
#===============================================>      <=================================================#

class RasterProcessing(BaseLayerProcesser):
    def __init__(self, input_raster: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        self._context = context
        self._feedback = feedback
        self._raster = BaseLayerProcesser(input_raster, self._context, self._feedback)
    
    def run(self, algorname:str | QgsProcessingAlgorithm, parameters: dict[str, object], output: str | int = 0):
        _output = self._raster.ProcessingOutput(
            processing.run(
                algorname,
                self.ProcessingInput(parameters),
                is_child_algorithm=True,
                context=self._context,
                feedback=self._feedback
            ),
            output=output
        )
        
        if not _output:
            return self
        else:
            return RasterProcessing(_output, self._context, self._feedback)

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>     Debug Methods     <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def peak(self, bins: int, y_truncpercent: int = 100, minValue: float | None = None, maxValue: float | None = None, band: int = 1, showTable: bool = False):
        minValue: float = self._raster.dataProvider().bandStatistics(band, QgsRasterBandStats.All).minimumValue if minValue is None else minValue
        maxValue: float = self._raster.dataProvider().bandStatistics(band, QgsRasterBandStats.All).maximumValue if maxValue is None else maxValue
        binSizes = (maxValue - minValue) / bins
        self._raster.dataProvider().setNoDataValue(band, -9999) if math.isnan(self._raster.dataProvider().sourceNoDataValue(band)) else None
        NoData = self._raster.dataProvider().sourceNoDataValue(band)
        self._feedback.setProgress(1)
        rastercalc = QgsProcessingUtils().mapLayerFromString(
            processing.run(
                "native:rastercalc", {      #gdal was being mean  ~◺˰◿~
                    'LAYERS':[str(self._raster)],
                    'EXPRESSION':f' if (  ( "{self._raster.name()}@{band}" < {minValue} )  OR  ( "{self._raster.name()}@{band}" > {maxValue} ) , {NoData}, "{self._raster.name()}@{band}" ) ',
                    'EXTENT':None,
                    'CELL_SIZE':None,
                    'CRS':None,
                    'CREATION_OPTIONS':None,
                    'OUTPUT':'TEMPORARY_OUTPUT'
                },
                is_child_algorithm=True,
                context=self._context,
                feedback=QgsProcessingFeedback()    #silent feedback >.o
            )['OUTPUT'],
            self._context
        )
        histDict = {}
        histogram = rastercalc.dataProvider().histogram(band, bins, minValue, maxValue, rastercalc.extent(), 0, includeOutOfRange=False).histogramVector
        for i_bin in range(bins):
            value = histogram[i_bin]
            bin_min = minValue + i_bin * binSizes
            bin_max = minValue + (i_bin + 1) * binSizes
            histDict[(bin_min, bin_max)] = value
            self._feedback.setProgress((100 / bins) * (i_bin + 1))
            if self._feedback.isCanceled():
                raise QgsProcessingException("Cancelled")
        setattr(self, f"histDict@{band}", histDict)
        
        y_bins = 29   #number of lines
        maxsum = int(max(histDict.values()) * (y_truncpercent / 100))
        y_bins = maxsum if maxsum < y_bins else y_bins
        y_bins += 1 if y_bins == 0 else 0
        y_Sizes = maxsum / y_bins
        next_min = maxsum - y_Sizes
        linestring = ""
        linestring += f"{int(maxsum + y_Sizes)}│" + "".join(["#" if value >= (maxsum + y_Sizes) else "·" for value in histDict.values()]) + f"\n"
        linestring += f"{maxsum}│" + "".join(["#" if value >= maxsum else "·" for value in histDict.values()]) + f"\n"
        for y_i in range(y_bins):
            y_min = next_min if next_min > 0 else 0
            next_min = y_min - y_Sizes
            linestring += f"{'·' * (len(str(maxsum)) - len(str(int(y_min))))}{int(y_min)}│"
            linestring += "".join(["#" if value > y_min else "·" for value in histDict.values()]) + f"\n"
        
        #All this.. just for the x-axis ~>.<~
        x_pad = bins + 1 + (len(PrettyNumber(minValue, 3)) % 2) - len(PrettyNumber(minValue, 3) + PrettyNumber(maxValue)) + (len(PrettyNumber(maxValue, 3)) // 2)
        x_list = [minValue, maxValue]
        for x_i in range(x_pad):
            hold_list = []
            for v_i in range(len(x_list) - 1):
                pad_remain = (x_pad - (5 * len(ListSlicer(x_list, (None, None, [0, len(x_list) - 1]), self._feedback)))) // (len(x_list) - 1)
                if pad_remain < 13: # 8(4 spaces between labels) + 5(max width of labels)
                    _break = True
                    break
                _break = False
                hold_list.append((x_list[v_i] + x_list[v_i + 1]) / 2)
            x_list.extend(hold_list)
            x_list.sort()
            if _break:
                break
        mid_list = ListSlicer(x_list, (None, None, [0, len(x_list) - 1]), self._feedback)
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
        linestring += f"{'·' * (len(str(maxsum)) - (len(PrettyNumber(minValue, 3)) % 2))}{PrettyNumber(minValue, 3)}{mid_labels}{'·' * pad_subtraction}{PrettyNumber(maxValue, 3)}"

        #sinful ~⪖◞⪕~
        binnolist = [1]
        for binno in range(2, bins + 1):
            number = binno + len(str(binnolist[len(binnolist) - 1]))
            number += 1 if binnolist[len(binnolist) - 1] == 98 else 0   #the sequence is always the same, 98 is the last 2 digit number.
            if number > bins:
                break
            binnolist.append(number) if number - len(str(binnolist[len(binnolist) - 1])) > binnolist[len(binnolist) - 1] and number != 101 else None 
        binstring = "·".join([f"{number}" for number in binnolist])                                                         #101 for the same reason as 98
        linestring = f"\nBin Numbers\n{'·' * (len(str(maxsum)) + 1)}{binstring}\n" + linestring

        setattr(self, f"histogram@{band}", linestring)
        if showTable:
            columns = bins // (22 + len(str(bins))) if bins // (22 + len(str(bins))) > 4 else 4
            linestring += f"\n \n{'=♡' * ((bins + len(str(maxsum)) + 1) // 2)}="
            linestring += self.HistogramTable(columns, band, True)

        self._feedback.pushInfo(f"{'=♡' * 35}=")
        self._feedback.pushCommandInfo(linestring)
        self._feedback.pushInfo(f"\n{'=♡' * 35}=")
        return self
# ¯ <
# ∟ ?

    def HistogramTable(self, columns: int = 4, band: int = 1, returnstr: bool = False):
        if f"histDict@{band}" not in self.__dict__.keys():
            self._feedback.pushWarning("HistogramTable Method requires histogram dictionary materialisation of specified band. Run peak() first.")
            return self
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
            self._feedback.pushCommandInfo(linestring)
            return self

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Native Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def ClipRasterByMaskLayer(self, mask:str, source_crs:QgsCoordinateReferenceSystem = None, target_crs:QgsCoordinateReferenceSystem = None, target_extent:str = None, nodata:float = None, alpha_band:bool = False, crop_to_cutline:bool = True, keep_resolution:bool = False, set_resolution:bool = False, x_resolution:float = None, y_resolution:float = None, multithreading:bool = False, creation_options:str = None, data_type:int = 0, extra='', output = "TEMPORARY_OUTPUT"):
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
                'INPUT': self._raster,
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
            }
        )
    def ClipRasterByExtent(self, clipping_extent:str, override_crs:bool = False, nodata:float = 0, creation_options:str = None, data_type:int = 0, extra='', output="TEMPORARY_OUTPUT"):
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
                'INPUT':self._raster,
                'PROJWIN':clipping_extent,
                'OVERCRS':override_crs,
                'NODATA':nodata,
                'CREATION_OPTIONS':creation_options,
                'DATA_TYPE':data_type,
                'EXTRA':extra,
                'OUTPUT':output
            }
        )

    #-------------------------------------------------------#
    #>>>>>>>>>>>>    Layer Type Conversion    <<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def Vectorise(self, raster_band: int = 1, field_name: str = 'VALUE', output="TEMPORARY_OUTPUT"):
        """
        Native Raster pixels to polygons Process \n
        :param raster_band: Raster band index to convert.
        :param field_name: Attribute field name storing pixel values.
        :param output: Output file path string | Default Temporary Memory Output.
        :return: VectorProcessing(FlexibleVectorLayer) object.
        """
        _output = self._raster.ProcessingOutput(
            processing.run(
                "native:pixelstopolygons", {
                    'INPUT_RASTER': str(self._raster),
                    'RASTER_BAND': raster_band,
                    'FIELD_NAME': field_name,
                    'OUTPUT': output
                },
                is_child_algorithm=True,
                context=self._context,
                feedback=self._feedback
            )
        )

        return VectorProcessing(_output, self._context, self._feedback)

    #======================================================#

    def __getattr__(self, name):
        return getattr(self._raster, name)
class RasterProcessing_Buffer(RasterProcessing):
    pass

if TYPE_CHECKING:
    class RasterProcessing(RasterProcessing_Buffer, QgsMapLayer, QgsRasterLayer):
        pass


#========================================================================================================#


# >(,)(,)(,)(,)(,)(◜⋅)          i dont know what this is, but he's kinda cute, no?
#  ^^ ^^ ^^ ^^ ^^


#========================================================================================================#
#------------------------------------------Functionally Useless------------------------------------------#
#=========================================> (just use GeoJson) <=========================================#
#and kinda not very good at all....
class Vector_Decoding:
    def __init__(self, Vector_layer: QgsProcessingFeatureSource):
        self.Vector_layer = Vector_layer

    def QfeatureAttrToDict(self, attribute_field_list: list, fid_Field: str = None):
        """Decodes Qgsfeature Attribute table into a Python Dictionary
        Return dict: \n
        {'Feature 1': {'Attribute Column 1 Name': Features Value, 'Attribute Column 2 Name': Feature value, -> }, 'Feature 2': {-> }, ->}"""

        _dict = {}
        for i, f in enumerate(self.Vector_layer.getFeatures()):
            if fid_Field is None:
                feature_number = i
            else:
                feature_number = f[fid_Field]
            feature = f"{'Feature' if fid_Field is None else fid_Field} {feature_number}"
            _dict[feature] = {}
            for flist in attribute_field_list:
                _dict[feature][flist] = f[flist]
                
        return _dict


    def GeometryFeaturesToDict(self):
        """just use GeoJson"""

        dict_ = {}
        geomTypeList = ["Point", "Line", "Polygon"]
        dict_["GeometryType"] = geomTypeList[self.Vector_layer.geometryType()]
        for i, feature in enumerate(self.Vector_layer.getFeatures()):
            geom = feature.geometry()
            geomType = geom.type()
            geomdict = {}

     #    --Point Geometry--
            if geomType == 0:
                if geom.isMultipart():
                    point = geom.asMultiPoint()
                    isMulti = True
                else:
                    point = [geom.asPoint()]
                    isMulti = False
                geomdict["NumberofPoints"] = len(point)
                geomdict["isMultiPoint"] = isMulti
                for pt_i, pt in enumerate(point):
                    PointNumber = f"Point{pt_i}"
                    geomdict[PointNumber] = pt

     #   --Line Geometry--
            elif geomType == 1:
                if geom.isMultipart():
                    line = geom.asMultiPolyline()
                    isMulti = True
                else:
                    line = [geom.asPolyline()]
                    isMulti = False
                geomdict["NumberofLines"] = len(line)
                geomdict["isMultiPolyLine"] = isMulti
                for ln_i, ln in enumerate(line):
                    IndivLineAsGeom = QgsGeometry.fromPolylineXY(ln)
                    LineNumber = f"Line{ln_i}"
                    geomdict[LineNumber] = {
                        "Length": IndivLineAsGeom.length(),
                        "NumberofVertices": len(ln),
                        "Vertices": ln
                    }

     #   --Polygon Geometry--
            elif geomType == 2:
                if geom.isMultipart():
                    polygons = geom.asMultiPolygon()
                    isMulti = True
                else:
                    polygons = [geom.asPolygon()]
                    isMulti = False
                geomdict["NumberofPolygons"] = len(polygons)
                for P_in, P_i in enumerate(polygons):
                    IndivPolyAsGeom = QgsGeometry.fromPolygonXY(P_i)
                    IndivPolyAsGeomMinHoles = QgsGeometry.fromPolygonXY([P_i[0]])
                    NoH = len(P_i) - 1
                    Polygon_key = f"Polygon{P_in}"
                    geomdict[Polygon_key] = {
                        "NumberofHoles": NoH,
                        "Area": IndivPolyAsGeom.area()
                        }
                    if NoH > 0:
                        geomdict[Polygon_key]["AreaMinusHoles"] = IndivPolyAsGeomMinHoles.area()
                    geomdict[Polygon_key]["Perimeter"] = IndivPolyAsGeom.length()
                    if NoH > 0:
                        geomdict[Polygon_key]["PerimeterMinusHoles"] = IndivPolyAsGeomMinHoles.length()
                    geomdict[Polygon_key]["NumberofPerimeterVertices"] = len(P_i[0]) - 1
                    geomdict[Polygon_key]["PerimeterXY"] = P_i[0]
         #       --Hole Isolation--
                    if NoH > 0:
                        geomdict[Polygon_key]["InteriorHoles"] = {}
                        for r_in, r_i in enumerate(P_i[1:]):
                            IndivHoleAsGeom = QgsGeometry.fromPolygonXY([r_i])
                            HoleIndex_Key = f"Hole{r_in + 1}"
                            HoleIndex_List = r_i
                            geomdict[Polygon_key]["InteriorHoles"][HoleIndex_Key] = {
                                "HoleArea": IndivHoleAsGeom.area(),
                                "HolePerimeter": IndivHoleAsGeom.length(),
                                "NumberofHoleVertices": len(r_i) - 1,
                                "HoleXY": HoleIndex_List
                                }
            else:
                continue
 
            FeatureNumber = f"Feature{i}"
            dict_[FeatureNumber] = geomdict

        return dict_
    

    def __getattr__(self, name):
        return getattr(self.Vector_layer, name)



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