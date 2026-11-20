"""Long before time had a name"""

from qgis.core import (
    QgsFeatureIterator,
    QgsVectorLayer,
    QgsMapLayer,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsFeature,
    QgsFeatureRequest,
    QgsProcessingFeatureSource,
    QgsGeometry
)
from typing import Union

from .ErrorHandling import QUtilsExceptions

__author__ = "Roxanne Minerals"
__version__ = 1.0

#and if your using some random, niche backend provider that doesn't support rewinding of FeatureIterators, then materialise it into a python list.
#That performance loss is on you for being weird.
@QUtilsExceptions.ErrorHandling
def ListSlicer(input_list: list | QgsFeatureIterator | QgsVectorLayer | QgsMapLayer, input_slice: tuple[Union[list[int], None], Union[tuple[int, int], list[tuple[int, int]], None], Union[list[int], list[tuple[int, int]], None]], feedback: QgsProcessingFeedback, context: QgsProcessingContext = None) -> list | QgsFeatureIterator | QgsVectorLayer:
    """
    Applies a three component slicing rule to a list of objects, a QgsFeatureIterator, or a QgsVectorLayer, returning a filtered List, QgsFeatureIterator, or QgsVectorLayer. \n
    *because the native slice is a bit rubbish* \n
    NOTE: if your input is QgsFeatures (QgsFeatureIterator or QgsVectorLayer), the fid is the positional int.\n
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
                    - list[(start, stop)] -> range of indicies to exclulde (can be multiple ranges)
                    - Exclude range logic is consistant with Range param logic
                    - Note: Exclude ints override include (Include and Range) ints
    :return: Filtered list of objects, QgsFeatureIterator, or QgsVectorLayer
    """
    from .Processing import (
        FlexibleMapLayer,
        BaseLayerProcesser,
        VectorProcessing,
        CloneLayer,
        NewVectorLayer
    )

    if input_slice == None:
        return input_list
    elif isinstance(input_list, list):
        _count = len(input_list)
    elif isinstance(input_list, (QgsVectorLayer, QgsMapLayer, BaseLayerProcesser, FlexibleMapLayer, VectorProcessing)):
        if context != None:
            _count = input_list.featureCount()
            c_layer = CloneLayer(input_list, context, feedback)
        else:
            QUtilsExceptions.CriticalError("Slice Error: Context required for QgsVectorLayer as input")
    elif isinstance(input_list, QgsFeatureIterator):
        if context != None:
            first: QgsFeature = next(input_list)
            input_list.rewind()
            c_layer = NewVectorLayer(first.geometry().wkbType(), context, "_ListSlicer_MEM_LAYER_", "index=yes")
            c_layer.startEditing()
            c_layer.setCrs(context.project().crs())
            c_layer.dataProvider().addAttributes(first.fields())
            c_layer.dataProvider().addFeatures(input_list)
            c_layer.commitChanges()
            _count = c_layer.featureCount()
        else:
            QUtilsExceptions.CriticalError("Slice Error: Context required for QgsFeatureIterator as input")

    
    _includeList = []
    r_except = []
    if isinstance(input_slice, tuple) and len(input_slice) == 3:
        _include, _range, _except = input_slice
        if _include is None and _range is None:
            _includeList.extend(range(_count))
        
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
        elif len(_range) == 0:
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
                _includeList.extend(range(start, stop + 1))                
        else:
            QUtilsExceptions.CriticalError("Slice Error: second object must be tuple containing a range of two values or a list of tuple ranges. None as first or second value evaluates as either highest or lowest value.")

        #=====Except=====#
        if _except == None:
            pass
        elif len(_except) == 0:
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
                    r_except.extend(range(estart, estop + 1))
                elif isinstance(ind_except, int):
                    r_except.append(ind_except)
                else:
                    QUtilsExceptions.CriticalError("Slice Error: third object must be None, or list of ints or of tuple ranges")
            if max(r_except) > _count - 1:
                QUtilsExceptions.CriticalError(f"Slice Error: third object max value int is higher then the objects bounds. Max int: {max(r_except)}, Object upper bound int: {_count - 1}")
        else:
            QUtilsExceptions.CriticalError("Slice Error: third object must be None or list of ints or tuple ranges")
        
    else:
        _includeList.extend([r for r in range(0, _count)])
        feedback.pushWarning("Slice Error: object must be tuple containing three list/tuple objects (Include, Range, Exclude). Defaulting to entire list.")

    check_featurenumber = []
    for featuren in _includeList:
        if featuren not in check_featurenumber and featuren not in r_except:
            check_featurenumber.append(featuren)
    filterList = sorted(check_featurenumber)

    if isinstance(input_list, list):
        return [input_list[n] for n in filterList]

    if isinstance(input_list, (QgsVectorLayer, QgsMapLayer, BaseLayerProcesser, FlexibleMapLayer, VectorProcessing)):
        c_layer.startEditing()
        c_layer.selectByIds(filterList)
        c_layer.invertSelection()
        c_layer.deleteSelectedFeatures(QgsVectorLayer().DeleteContext(True, context.project()))
        c_layer.commitChanges()
        return c_layer
    
    if isinstance(input_list, QgsFeatureIterator):
        return c_layer.getFeatures(QgsFeatureRequest().setFilterFids(filterList).setOrderBy(QgsFeatureRequest().OrderBy([QgsFeatureRequest().OrderByClause("$id", True)])))


#========================================================================================================#
#------------------------------------------Functionally Useless------------------------------------------#
#=========================================> (just use GeoJson) <=========================================#
#and kinda not very good at all....
class _Vector_Decoding:
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