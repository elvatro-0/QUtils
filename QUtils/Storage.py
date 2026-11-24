"""Basically a Utils module with a better name"""

from qgis.core import QgsProcessingFeedback, QgsFeatureRequest
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QTextDocument, QTextCursor
from typing import Any, Protocol, TypeVar, Iterable
from bisect import bisect_left, bisect_right

__author__ = "Roxanne Minerals"
__version__ = 1.1

#========================================================================================================#
#------------------------------------------------Storage-------------------------------------------------#
#===============================================>      <=================================================#


    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>       Constants     <<<<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#

NO_REQUEST = QgsFeatureRequest().setOrderBy(QgsFeatureRequest().OrderBy([QgsFeatureRequest().OrderByClause("$id", True)]))

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>>    Conveniences   <<<<<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#

class FieldType:
    string = QVariant.String
    int = QVariant.Int
    int64 = QVariant.LongLong
    double = QVariant.Double
    date = QVariant.Date
    time = QVariant.Time
    datetime = QVariant.DateTime
    bool = QVariant.Bool
    bytearray = QVariant.ByteArray
    json = QVariant.Map
    array = QVariant.List
    unset = QVariant.Invalid

def Color(hex: str):
    return QColor(hex)

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>>  Typing Protocols <<<<<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#

_generic = TypeVar("_generic", contravariant=True)
class SupportsAppend(Protocol[_generic]):
    def append(self, value): ... 
class SupportsStr(Protocol[_generic]):
    def __str__(self) -> str: ...

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>>>>    Functions   <<<<<<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#

def htmlToPlain(text):
    string = QTextDocument()
    string.setHtml(text)
    return string.toPlainText()

def htmlToFont(html: str):
    doc = QTextDocument()
    doc.setHtml(html)
    block = doc.begin()
    _iter = block.begin()
    if _iter.atEnd():
        return doc.defaultFont()
    return _iter.fragment().charFormat().font()

def splitHtml(html: str) -> list[str]:
    doc = QTextDocument()
    doc.setHtml(html)
    cuts = [-1] + [i for i in range(doc.characterCount()) if doc.characterAt(i) == "\u2028"]
    cuts.append(doc.characterCount() - 1)
    parts = []
    cursor = QTextCursor(doc)
    for a, b in zip(cuts, cuts[1:]):
        cursor.setPosition(a + 1)
        cursor.setPosition(b, QTextCursor.MoveMode.KeepAnchor)
        parts.append(cursor.selection().toHtml())
    return parts

    #-------------------------------------------------------#
    #>>>>>>>>>>>>>>>>>   Custom Classes  <<<<<<<<<<<<<<<<<<<#
    #-------------------------------------------------------#

class Carrier:
    """key={"output": 1} -> args[1] == carrier["output"]"""
    def __init__(self, *args, key: dict[str | Any, int] = None):
        self.store = args
        self.key = {} if key is None else dict(key)
        def _newkey(key):
            i_key = int(key.rstrip("_")) if isinstance(key, str) else key
            if key not in self.key.keys():
                self.key[key] = i_key
            else: _newkey(f"{key}_")
        for i, _arg in enumerate(self.store):
            if i not in self.key.values():
                _newkey(i)

    def __getitem__(self, key: Any | int) -> Any:
        return self.store[self.key[key]]

    def __setitem__(self, key: str | Any, value: int):
        self.key[key] = value
    def __iter__(self): return iter(self.store)
    def __len__(self): return len(self.store)
    def __contains__(self, item): return item in self.store

class MethodCaller:
    def __init__(self, method, instance = None):
        self.method = method
        self.instance = instance
    @property
    def __class__(self):
        return self.method.__self__.__class__

    def __call__(self, *args, **kwargs):
        raise NotImplementedError(f"{type(self).__name__} must implement __call__")

    class datawrapper:
        def __init__(self, dataprovider, cls, instance = None):
            self.dataprovider = dataprovider
            self.cls = cls
            self.instance = instance
        @property
        def __class__(self):
            return self.dataprovider.__class__

        def __getattr__(self, name):
            _return = getattr(self.dataprovider, name)
            if callable(_return):
                return self.cls(_return, self.instance)
            return _return
    def __getattr__(self, name):
        return getattr(self.method, name)

class RangeLookup(list):
    """Mutable sequence of ints or floats which remains sorted"""
    def __init__(self, iterable: Iterable = None):
        iterable = [] if not iterable else iterable
        super().__init__(iterable)
        self.sort()

    def range(self, start: float | int = None, end: float | int = None):
        return (0 if start is None else bisect_left(self, start),
        len(self) if end is None else bisect_right(self, end))
    def round(self, value: float | int):
        index = bisect_left(self, value)
        if index == 0: return 0
        if index == len(self): return len(self) - 1
        return index if self[index] - value < value - self[index - 1] else index - 1

    def append(self, object):
        super().append(object)
        self.sort()
    def extend(self, iterable):
        super().extend(iterable)
        self.sort()
    def insert(self, index, object):
        super().insert(index, object)
        self.sort()
    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.sort()
    def __iadd__(self, value):
        _return = super().__iadd__(value)
        self.sort()
        return _return
    def __imul__(self, value):
        _return = super().__imul__(value)
        self.sort()
        return _return
    
class SilentFeedback(QgsProcessingFeedback):
    def __init__(self, parent: QgsProcessingFeedback):
        super().__init__(False)
        parent.canceled.connect(self.cancel)

