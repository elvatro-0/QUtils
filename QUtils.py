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
    QgsProcessingException
)
from qgis import processing
from typing import TYPE_CHECKING, Union
import functools, inspect, traceback

#========================================================================================================#
#---------------------------------------------Error Handler----------------------------------------------#
#===============================================>      <=================================================#

#I want error messages to look pretty
class QUtilsExceptions(QgsProcessingException):
    def __init__(self, message: str = None):
        super().__init__(message)
        self.message = "" if message == None else message
    @staticmethod
    def CriticalError(message: str = None):
        raise QUtilsExceptions(message)

    def ErrorHandling(func):
        @functools.wraps(func)
        def stack_tracer(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except QUtilsExceptions as _except:
                feedback = None
                for fb in inspect.signature(func).bind(*args, **kwargs).arguments.values():
                    if isinstance(fb, QgsProcessingFeedback):
                        feedback = fb
                        break

                feedback.reportError(
                "\n QUtils Critical Error\n"
                f"{'='*50}\n"
                f"{func.__name__ if func.__name__ != '__init__' else func.__class__} Error\n"
                f"Traceback:\n{''.join(traceback.format_list(traceback.extract_stack()[:-1]))}"
                ) if feedback != None else None
                raise QgsProcessingException(f"{_except.message}\n")
        return stack_tracer


#========================================================================================================#
#----------------------------------------------Functions-------------------------------------------------#
#===============================================>      <=================================================#

#and if your using some random, niche backend provider that doesn't support rewinding of FeatureIterators, then materialise it into a python list.
#That performance loss is on you for being weird.
@QUtilsExceptions.ErrorHandling
def ListSlicer(input_list: list | QgsFeatureIterator, input_slice: tuple[Union[list[int], None], Union[tuple[int, int], list[tuple[int, int]], None], Union[list[int], list[tuple[int, int]], None]], feedback: QgsProcessingFeedback, context: QgsProcessingContext = None) -> list | QgsFeatureIterator:
    """
    Applies a three component slicing rule to a list of objects or QgsFeatureIterator, returning a filtered List or QgsFeatureIterator. \n
    *because the native slice is a bit rubbish* \n
    :param input_list: List of objects to slice (supports QgsFeatureIterator).
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
    :return: Filtered list of objects or QgsFeatureIterator
    """

    if input_slice == None:
        return input_list
    if isinstance(input_list, list):
        _count = len(input_list)
    if isinstance(input_list, QgsFeatureIterator):
        if context != None:
            first = next(input_list)
            input_list.rewind()
            geomlist = ["MultiPoint", "MultilineString", "MultiPolygon"] if first.geometry().isMultipart() else ["Point", "LineString", "Polygon"]
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
        
        #=====Include=====#
        if _include == None:
            pass
        elif isinstance(_include, list):
            if _count - 1 < max(_include):
                QUtilsExceptions.CriticalError(f"Slice Error: first object contains int higher then the objects bounds. Max int: {max(_include)} Object upper bound int: {_count - 1}")
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
                    ind_range = (0, -max(ind_range)) if max(ind_range) < 0 else (max(ind_range), None)
                    #max here is just a neat way to extract the value if you add a comma after the int. E.g. (5,) == (5) -> (5, None); (-5,) == (-5) -> (0, 5)
                start, stop = ind_range
                start = 0 if start == None else start
                stop = _count - 1 if stop == None or stop > _count - 1 else stop
                if start > stop:
                    QUtilsExceptions.CriticalError("Slice Error: second object must be a tuple containing a range of two values or a list of tuple ranges. The first value must be less then the second value.")
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
                        ind_except = (0, -max(ind_except)) if max(ind_except) < 0 else (max(ind_except), None)
                    estart, estop = ind_except
                    estart = 0 if estart == None else estart
                    estop = _count - 1 if estop == None or estop > _count - 1 else estop
                    r_except.extend([r for r in range(estart, estop + 1)])
                elif isinstance(ind_except, int):
                    r_except.append(ind_except)
                else:
                    QUtilsExceptions.CriticalError("Slice Error: third object must be None or list of ints or tuple ranges")
            if max(r_except) > _count - 1:
                QUtilsExceptions.CriticalError("Slice Error: third object max value int is higher then the objects bounds.")
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


    if isinstance(input_list, QgsFeatureIterator):
        filterList = sorted(check_featurenumber_1based)
        return c_layer.getFeatures(QgsFeatureRequest().setFilterFids(filterList).setOrderBy(QgsFeatureRequest().OrderBy([QgsFeatureRequest().OrderByClause("$id", True)])))

#========================================================================================================#
#------------------------------------------Proxy Base Wrappers-------------------------------------------#
#===============================================>      <=================================================#

class FlexibleMapLayer:
    def __init__(self, input_pointer: str, context: QgsProcessingContext):
        if not isinstance(input_pointer, str):
            raise TypeError("FlexibleMapLayer Received Live Qgs Object - Requires Pointer String")
        self._pointer = input_pointer
        self._context = context

    def __str__(self):
        return str(self._pointer)

    def __repr__(self):
        return f"FlexibleVectorLayer({self._pointer!r})"
        
    def __getattr__(self, name):
        return getattr(QgsProcessingUtils.mapLayerFromString(self._pointer, self._context), name)

class BaseLayerProcesser(FlexibleMapLayer):
    def __init__(self, input_pointer: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        super().__init__(input_pointer, context)
        self._feedback = feedback

    def is_pointerStr(self, Input) -> bool:
        if not isinstance(Input, str):
            return False
        _string = QgsProcessingUtils.mapLayerFromString(Input, self._context)
        return isinstance(_string, QgsMapLayer)
    
    def ProcessingOutput(self, ProcessDict: dict, Output: int = 0) -> str:
        _return = []
        for _value in ProcessDict.values():
            if self.is_pointerStr(_value):
                _return.append(_value)
        return _return[Output]

    def addLayerToLoadOnCompletion(self, Output_name: str):
        self._context.addLayerToLoadOnCompletion(str(self._pointer), QgsProcessingContext.LayerDetails(Output_name, self._context.project()))


#========================================================================================================#
#--------------------------------------Direction AND MAGNITUDE!------------------------------------------#
#==========================================> OH YEAH!!! <================================================#

#And before you want to write to me, and say I shouldnt inherit twice, read the note
class VectorProcessing(BaseLayerProcesser):
    """NOTE: This class inherits from BaseLayerProcesser *only* to preserve type identity 
    so that QGIS and external scripts treat it as a FlexibleMapLayer object. \n
    All actual layer behaviour is delegated to an internal BaseLayerProcessing instance stored 
    in self._vector. This dual structure allows the returned VectorProcessing object to behave 
    as BOTH a pointer string (via __str__) and a live QgsMapLayer (via __getattr__), which is 
    required for seamless use in processing.run() while maintaining VectorProcessing methods for chaining."""
    def __init__(self, input_vector: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        self._context = context
        self._feedback = feedback
        self._vector = BaseLayerProcesser(input_vector, self._context, self._feedback)
    
    def run(self, algorname:str | QgsProcessingAlgorithm, parameters: dict[str, object], Output: int = 0):
        _output = self._vector.ProcessingOutput(
            processing.run(
                algorname,
                parameters,
                is_child_algorithm=True,
                context=self._context,
                feedback=self._feedback
            ),
            Output=Output
        )

        return VectorProcessing(_output, self._context, self._feedback)
    
    #def head(self, rows: int = 5):
    #    QgsVectorLayer.fields().names
        
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
                'INPUT': str(self._vector),
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
                'INPUT':str(self._vector),
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
                'INPUT':str(self._vector),
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
                'INPUT': str(self._vector),
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
        return FeatureProcessing(self._vector.getFeatures(), self._context, self._feedback)

    #======================================================#

    def __getattr__(self, name):
        return getattr(self._vector, name)
class VectorProcessing_Buffer(VectorProcessing):
    pass

if TYPE_CHECKING:
    class VectorProcessing(VectorProcessing_Buffer, QgsMapLayer, QgsVectorLayer):
        pass


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

    def FeaturesToLayer(self, input_slice: tuple[list[int], tuple[int, int] | list[tuple[int, int]], list[int] | list[tuple[int, int]]] = None):
        geomlist = ["MultiPoint", "MultiLine", "MultiPolygon"] if self._feature.geometry().isMultipart() else ["Point", "Line", "Polygon"]
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


#========================================================================================================#
#--------------------------------------------Raster Processing-------------------------------------------#
#===============================================>      <=================================================#

class RasterProcessing(BaseLayerProcesser):
    def __init__(self, input_raster: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        self._context = context
        self._feedback = feedback
        self._raster = BaseLayerProcesser(input_raster, self._context, self._feedback)
    
    def run(self, algorname:str | QgsProcessingAlgorithm, parameters: dict[str, object], Output: int = 0):
        _output = self._raster.ProcessingOutput(
            processing.run(
                algorname,
                parameters,
                is_child_algorithm=True,
                context=self._context,
                feedback=self._feedback
            ),
            Output=Output
        )

        return RasterProcessing(_output, self._context, self._feedback)

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
                'INPUT': str(self._raster),
                'MASK': str(mask),
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
                'INPUT':str(self._raster),
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


    def __getattr__(self, name):
        return getattr(self._raster, name)
class RasterProcessing_Buffer(RasterProcessing):
    pass

if TYPE_CHECKING:
    class RasterProcessing(RasterProcessing_Buffer, QgsMapLayer, QgsRasterLayer):
        pass


#========================================================================================================#


# >(,)(,)(,)(,)(,)(◜⋅)
#  ^^ ^^ ^^ ^^ ^^


#========================================================================================================#
#------------------------------------------Functionally Useless------------------------------------------#
#=========================================> (just use GeoJson) <=========================================#

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
