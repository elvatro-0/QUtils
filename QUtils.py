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
    QgsCoordinateReferenceSystem
)
from qgis import processing
from typing import TYPE_CHECKING
import sys

#========================================================================================================#
#----------------------------------------------Functions-------------------------------------------------#
#===============================================>      <=================================================#

def ListSlicer(List: list, feedback: QgsProcessingFeedback, Slice: tuple[list[int], tuple[int, int] | list[tuple[int, int]], list[int]] = None):
    """
    
    """
    _featurenumber = []
    if Slice == None:
        for ix, f in enumerate(List):
            _featurenumber.append(ix)
        _except = []
    elif isinstance(Slice, tuple) and len(Slice) == 3:
        _include, _range, _except = Slice
        
        #=====Include=====#
        if _include == None:
            pass
        elif isinstance(_include, list) and len(_include) > 0 and max(_include) <= len(List) - 1:
            _featurenumber.extend(_include)
        elif len(_include) < 0 or max(_include) >= len(List):
            feedback.reportError("slice error: first object contains int lower then 0 or higher then the max feature id.", True)
            sys.exit()
        else:
            feedback.reportError("slice error: First object must be list.", True)
            sys.exit()
        
        #=====Range======#
        if _range == None:
            pass
        elif (isinstance(_range, tuple) and len(_range) == 2) or isinstance(_range, list):
            _range = [_range] if isinstance(_range, tuple) else _range
            if not isinstance(_range[0], tuple) or len(_range[0]) != 2:
                feedback.reportError("slice error: second object must be a tuple containing a range of two values or a list of said tuple.", True)
                sys.exit()
            for start, stop in _range:
                if stop > len(List) - 1:
                    feedback.reportError("slice error: second object end int is higher then the max feature id.", True)
                    sys.exit()
                if start > stop:
                    feedback.reportError("slice error: second object must be a tuple containing a range of two values or a list of said tuple. The first value must be less then the second value.", True)
                    sys.exit()
                start = 0 if start == None else start
                stop = len(List) - 1 if stop == None else stop
                _featurenumber.extend([r for r in range(start, stop + 1)])
        else:
            feedback.reportError("slice error: second object must be tuple containing a range of two values. None as first or second value evaluates as either highest or lowest value.", True)
            sys.exit()

        #=====Except=====#
        if _except == None:
            _except = []
        elif isinstance(_except, list) and len(_except) > 0 and max(_except) <= len(List) - 1:
            pass
        else:
            feedback.reportError("slice error: third object must be None or list of ints", True)
            sys.exit()
        
    else:
        for ix, _ in enumerate(List):
            _featurenumber.append(ix)
        feedback.pushWarning("slice error: object must be tuple containing three list/tuple objects (Include, Range, Exclude). Defaulting to entire QgsFeature list.")

    check_featurenumber = []
    for featuren in _featurenumber:
        if featuren not in check_featurenumber and featuren not in _except:
            check_featurenumber.append(featuren)
    
    _returnList = []
    for n in sorted(check_featurenumber):
        _returnList.append(List[n])
    return _returnList


#========================================================================================================#
#------------------------------------------Proxy Base Wrappers-------------------------------------------#
#===============================================>      <=================================================#

class FlexibleMapLayer:
    def __init__(self, Input_Pointer: str, context: QgsProcessingContext):
        if not isinstance(Input_Pointer, str):
            raise TypeError("FlexibleMapLayer Received Live Qgs Object - Requires Pointer String")
        self._pointer = Input_Pointer
        self._context = context

    def __str__(self):
        return str(self._pointer)

    def __repr__(self):
        return f"FlexibleVectorLayer({self._pointer!r})"
        
    def __getattr__(self, name):
        return getattr(QgsProcessingUtils.mapLayerFromString(self._pointer, self._context), name)

class BaseLayerProcesser(FlexibleMapLayer):
    def __init__(self, Input_Pointer: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        super().__init__(Input_Pointer, context)
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
    """NOTE: This class inherits from BaseLayerWrapper *only* to preserve type identity 
    so that QGIS and external scripts treat it as a FlexibleMapLayer object. \n
    All actual layer behaviour is delegated to an internal BaseLayerWrapper instance stored 
    in self._vector. This dual structure allows the returned VectorProcessing object to behave 
    as BOTH a pointer string (via __str__) and a live QgsMapLayer (via __getattr__), which is 
    required for seamless use in processing.run() while maintaining VectorProcessing methods for chaining."""
    def __init__(self, Input_Vector: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback):
        self._context = context
        self._feedback = feedback
        self._vector = BaseLayerProcesser(Input_Vector, self._context, self._feedback)
    
    def run(self, algOrName:str | QgsProcessingAlgorithm, parameters: dict[str, object], Output: int = 0):
        _output = self._vector.ProcessingOutput(
            processing.run(
                algOrName,
                parameters,
                is_child_algorithm=True,
                context=self._context,
                feedback=self._feedback
            ),
            Output=Output
        )

        return VectorProcessing(_output, self._context, self._feedback)
        
    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Native Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def fixGeometries(self, Method: int = 1, Output="TEMPORARY_OUTPUT"):
        """
        Native Fix geometries Process \n
        :param Method: Repair method: \n
                       0 = Linework
                       1 = Structure
        :param Output: Output file path string | Default Temporary Memory Output
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        return self.run(
            "native:fixgeometries", {
                'INPUT': str(self._vector),
                'METHOD': Method,
                'OUTPUT': Output
            }
        )
    def Dissolve(self, Field: QgsFields = [], SeparateDisjoint: bool = False, Output="TEMPORARY_OUTPUT"):
        """
        Native Dissolve Process \n
        :param Field: QgsFields list of attributes | Blank list will dissolve all atrtibute fields
        :param SeparateDisJoint: If True, features and parts that do not overlap or touch will be exported as separate features
        :param Output: Output file path string | Default Temporary Memory Output
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        return self.run(
            "native:dissolve", {
                'INPUT':str(self._vector),
                'FIELD': Field,
                'SEPARATE_DISJOINT': SeparateDisjoint,
                'OUTPUT': Output
            }
        )
    def Smooth(self, Iterations:int = 1, Offset: float = 0.5, Max_Angle: float = 180, Output="TEMPORARY_OUTPUT"):
        """
        Native Smooth geometry process
        """
        return self.run(
            "native:smoothgeometry", {
                'INPUT':str(self._vector),
                'ITERATIONS':Iterations,
                'OFFSET':Offset,
                'MAX_ANGLE':Max_Angle,
                'OUTPUT':Output
            }
        )

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>    Custom Processes    <<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def RingBuffer(self, Radius: float, Rings: int, Invert: bool = False, Overlap: int = 0, Segments: int = 16, Output="TEMPORARY_OUTPUT"):
        """
        Creates a multi-ring buffer with overlap logic based on a generated Class field \n
        :param Input: TypeVectorPoint | TypeVectorLine
        :param Radius: Total Radius (map units)
        :param Rings: Number of donut rings
        :param Invert: True = Increasing class value inwards (inner ring as highest value) \n
                       False = increases class value outwards (Outer ring as highest value)
        :param Overlap: Overlap Resolution: \n
                        0 = Lower value overrides
                        1 = Higher value overrides
        :param Segments: Number of line segments to approximate a quarter circle when creating rounded offsets
        :param Output: Output file path string | Default Temporary Memory Output
        :return: VectorProcessing(FlexibleVectorLayer) Object
        """
        return self.run(
            "script:Ring_Buffer", {
                'INPUT': str(self._vector),
                'RADIUS': Radius,
                'RINGS': Rings,
                'INVERT': Invert,
                'OVERLAP': Overlap,
                'SEGMENTS': Segments,
                'OUTPUT': Output
            }
        )
    #-------------------------------------------------------#
    #>>>>>>>>>>>>    Layer Type Conversion    <<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def Rasterise(self, Field:str, Burn:float = 0, Use_Z:bool = False, Units:int = 1, Width:float = 30, Height:float = 30, Extent:str = None, NoData:float = 0, Creation_Options:str = None, Data_Type:int = 5, Init:float = None, Invert:bool = False, Extra:str = '', Output = "TEMPORARY_OUTPUT"):
        """
        GDAL rasterize Process
        """
        _output = self._vector.ProcessingOutput(
            processing.run(
                "gdal:rasterize", {
                    'INPUT': str(self._vector),
                    'FIELD':Field,
                    'BURN':Burn,
                    'USE_Z':Use_Z,
                    'UNITS':Units,
                    'WIDTH':Width,
                    'HEIGHT':Height,
                    'EXTENT':Extent,
                    'NODATA':NoData,
                    'CREATION_OPTIONS':Creation_Options,
                    'DATA_TYPE':Data_Type,
                    'INIT':Init,
                    'INVERT':Invert,
                    'EXTRA':Extra,
                    'OUTPUT':Output
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
        featurelist = []
        for f in self._vector.getFeatures():
            featurelist.append(f)
        
        return FeatureProcessing(featurelist, self._vector.crs(), self._context, self._feedback)

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
    """NOTE: When calling QgsFeature methods on a FeatureProcessing object, the method is executed only on the first QgsFeature in the feature list. \n
    This is useful for broader geometry introspection, but for geometry operations or transformations, iterate through the featurelist attribute."""
    def __init__(self, Input_Features: list[QgsFeature], CRS: QgsCoordinateReferenceSystem, context: QgsProcessingContext, feedback: QgsProcessingFeedback, LayerID: str = None):
        if not isinstance(Input_Features[0], QgsFeature):
            raise TypeError("Input_Features contain invalid objects or is empty - Requres list of QgsFeature objects")
        self._id = LayerID
        self._crs = CRS
        self._context = context
        self._feedback = feedback
        self.featurelist = Input_Features
        self._feature = self.featurelist[0]
        self._fields = self._feature.fields()
        self._wkb = self._feature.geometry().wkbType()

    #-------------------------------------------------------#
    #>>>>>>>>>  Feature List to Vector Conversion  <<<<<<<<<#
    #-------------------------------------------------------#

    def FeaturesToLayer(self, Slice: tuple[list[int], tuple[int, int] | list[tuple[int, int]], list[int]] = None):
        sink, _id = QgsProcessingUtils.createFeatureSink(self._id, self._context, self._fields, self._wkb, self._crs)
        sink.addFeatures(ListSlicer(self.featurelist, self._feedback, Slice))

        return VectorProcessing(_id, self._context, self._feedback)

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
    def __init__(self, Input_Raster: str, context: QgsProcessingContext, feedback: QgsProcessingFeedback, Name: str = None):
        self._context = context
        self._feedback = feedback
        self._raster = BaseLayerProcesser(Input_Raster, self._context, self._feedback)
    
    def run(self, algOrName:str | QgsProcessingAlgorithm, parameters: dict[str, object], Output: int = 0):
        _output = self._raster.ProcessingOutput(
            processing.run(
                algOrName,
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
    def ClipRasterByMaskLayer(self, Mask:str, Source_CRS:QgsCoordinateReferenceSystem = None, Target_CRS:QgsCoordinateReferenceSystem = None, Target_Extent:str = None, NoData:float = None, Alpha_Band:bool = False, Crop_To_Cutline:bool = True, Keep_Resolution:bool = False, Set_Resolution:bool = False, X_Resolution:float = None, Y_Resolution:float = None, Multithreading:bool = False, Creation_Options:str = None, Data_Type:int = 0, Extra='', Output = "TEMPORARY_OUTPUT"):
        """
        GDAL Clip raster by mask layer process
        """
        return self.run(
            "gdal:cliprasterbymasklayer", {
                'INPUT': str(self._raster),
                'MASK': str(Mask),
                'SOURCE_CRS':Source_CRS,
                'TARGET_CRS':Target_CRS,
                'TARGET_EXTENT':Target_Extent,
                'NODATA':NoData,
                'ALPHA_BAND':Alpha_Band,
                'CROP_TO_CUTLINE':Crop_To_Cutline,
                'KEEP_RESOLUTION':Keep_Resolution,
                'SET_RESOLUTION':Set_Resolution,
                'X_RESOLUTION':X_Resolution,
                'Y_RESOLUTION':Y_Resolution,
                'MULTITHREADING':Multithreading,
                'CREATION_OPTIONS':Creation_Options,
                'DATA_TYPE':Data_Type,
                'EXTRA':Extra,
                'OUTPUT':Output
            }
        )
    def ClipRasterByExtent(self, Clipping_Extent:str, OverrideCRS:bool = False, NoData:float = 0, Creation_Options:str = None, Data_Type:int = 0, Extra='', Output="TEMPORARY_OUTPUT"):
        """
        GDAL Clip raster by extent process
        """
        return self.run(
            "gdal:cliprasterbyextent", {
                'INPUT':str(self._raster),
                'PROJWIN':Clipping_Extent,
                'OVERCRS':OverrideCRS,
                'NODATA':NoData,
                'CREATION_OPTIONS':Creation_Options,
                'DATA_TYPE':Data_Type,
                'EXTRA':Extra,
                'OUTPUT':Output
            }
        )

    #-------------------------------------------------------#
    #>>>>>>>>>>>>    Layer Type Conversion    <<<<<<<<<<<<<<#
    #-------------------------------------------------------#
    def Vectorise(self, Raster_Band: int = 1, Field_Name: str = 'VALUE', Output="TEMPORARY_OUTPUT"):
        """
        Native Raster pixels to polygons Process
        """
        _output = self._raster.ProcessingOutput(
            processing.run(
                "native:pixelstopolygons", {
                    'INPUT_RASTER': str(self._raster),
                    'RASTER_BAND': Raster_Band,
                    'FIELD_NAME': Field_Name,
                    'OUTPUT': Output
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
#
# >(,)(,)(,)(,)(,)(◜⋅)
#  ^^ ^^ ^^ ^^ ^^
#========================================================================================================#
#------------------------------------------Functionally Useless------------------------------------------#
#========================================================================================================#

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
        """Decodes Feature Geometry Attributes into a Python Dictionary"""

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
