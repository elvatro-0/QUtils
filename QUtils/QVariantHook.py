"""
A way to let your own classes cross into Qt as a real QVariant, used primerily for QString conversion.\n
Instances of those str classes can sit directly in a processing parameter dict (or anything
else PyQt turns into a QVariant) and Qt receives a QVariant built from your classes designated converter callable.\n
PyQt converts a Python object to a QString with an exact type == str check and
wraps everything else as an opaque PyQt_PyObject. Meaning str subclasses don't get converted to a QString
(which is silly if you ask me). However! PyQt also exports a C hook that runs BEFORE that
check (pyqt5_/pyqt6_register_to_qvariant_convertor). This module registers a ctypes callback on that!\n
Works for PyQt5 (QGIS 3.x) and PyQt6 (QGIS 4.x). It only touches objects whose class you registered.
"""

import qgis.core as core
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt import QtCore, sip
from typing import Any, Callable
from dataclasses import dataclass, field, fields, MISSING
import sys, ctypes
from ctypes import CFUNCTYPE, POINTER, c_bool, c_char_p, c_int, c_void_p, py_object
import threading

from .Storage import *

__author__ = "Roxanne Minerals"

#========================================================================================================#
#----------------------------------------------FLEXIBILITY!----------------------------------------------#
#=========================================>Now this.. is EPIC!<==========================================#

#if PyQt would let str subclasses become a QString none of this would be neccissary... ~⪖ ‸⪕~

IMPORT_SYMBOL_OFFSET = {12: 296, 13: 288}
_QT5_QVARIANT_SIZE = 16
_QVARIANT_SIZE_RANGE = (16, 64)
_STATE_ATTR = "_qvariant_hook_state"
_MAX_DEPTH = 8   #how deep converters may nest (a converter returning a list of hooked objects and so on)
_MISSING = object()
_NO_HOOK = (object, str, bytes, int, float, bool, list, tuple, dict, set, type(None))   #PyQt already converts these itself

@dataclass
class _State:
    converters: dict = field(default_factory=dict)
    cache: dict = field(default_factory=dict)
    warned: set = field(default_factory=set)
    local: object = field(default_factory=threading.local)
    callback: object = None
    dispatch: object = None
    size: int = 0
    error: Exception = None

def _getState():
    state = getattr(sys, _STATE_ATTR, None)
    if state is None:
        state = _State()
        setattr(sys, _STATE_ATTR, state)
    for f in fields(_State):
        if not hasattr(state, f.name):
            setattr(state, f.name, f.default_factory() if f.default_factory is not MISSING else f.default)
    return state

def _qvariantSize(pyqt: int):
    if pyqt == 5:
        return _QT5_QVARIANT_SIZE
    try:
        size = QtCore.QMetaType(QtCore.QMetaType.Type.QVariant.value).sizeOf()
    except Exception:
        size = None
    low, high = _QVARIANT_SIZE_RANGE
    if not isinstance(size, int) or not low <= size <= high or size % 8:
        raise RuntimeError(f"unexpected sizeof(QVariant) = {size!r}")
    return size

def _findRegisterFunction(pyqt: int):
    """Look up PyQt's exported register_to_qvariant_convertor through SIP's C API."""
    abi = sip.SIP_ABI_VERSION
    offset = IMPORT_SYMBOL_OFFSET.get(abi >> 16)
    if offset is None:
        raise RuntimeError(f"unsupported SIP ABI {abi >> 16}.{(abi >> 8) & 255}")

    capsule_import = ctypes.pythonapi.PyCapsule_Import
    capsule_import.restype = c_void_p
    capsule_import.argtypes = [c_char_p, c_int]
    api = capsule_import(f"PyQt{pyqt}.sip._C_API".encode(), 0)
    if not api:
        raise RuntimeError("SIP C API capsule not found")

    import_symbol = CFUNCTYPE(c_void_p, c_char_p)(c_void_p.from_address(api + offset).value)
    address = import_symbol(f"pyqt{pyqt}_register_to_qvariant_convertor".encode())
    if not address:
        raise RuntimeError("PyQt did not export the QVariant convertor hook")
    return CFUNCTYPE(None, c_void_p)(address)

def _warnOnce(state: _State, tp: type, exc: BaseException):
    if not isinstance(exc, Exception) or tp in state.warned:
        return
    state.warned.add(tp)
    try: core.QgsMessageLog.logMessage(f"QVariant converter for {tp.__name__} failed ({exc!r}); passing it to Qt unconverted.", "QUtils", core.Qgis.Warning)
    except Exception: pass

def _makeDispatch(state: _State, size: int):

    def resolve(tp):
        fn = state.cache.get(tp, _MISSING)
        if fn is _MISSING:
            fn = state.cache[tp] = next((state.converters[c] for c in tp.__mro__ if c in state.converters), None)
        return fn

    def dispatch(obj, out_ptr, ok):
        tp = type(obj)
        fn = resolve(tp)
        if fn is None:
            return False
        depth = getattr(state.local, "depth", 0)
        if depth >= _MAX_DEPTH:
            return False
        state.local.depth = depth + 1
        try:
            result = fn(obj)
            if type(result) is tp:
                return False
            src = QVariant(result)   #PyQt does the real conversion, so anything it can put in a QVariant works!
            src_ptr = sip.unwrapinstance(src)
            ctypes.memmove(out_ptr, src_ptr, size)
            ctypes.memset(src_ptr, 0, size)
            ok[0] = True
            return True
        except BaseException as exc:
            _warnOnce(state, tp, exc)
            return False
        finally: state.local.depth = depth

    return dispatch

def _makeCallback(state: _State):
    @CFUNCTYPE(c_bool, py_object, c_void_p, POINTER(c_bool))
    def convertor(obj, out_ptr, ok):
        try:
            dispatch = state.dispatch
            return dispatch(obj, out_ptr, ok) if dispatch is not None else False
        except BaseException:
            return False
    return convertor

#seg-faults are scary ~>.<~
def _selfTest(state: _State):
    probes = [(type("_ProbeStr", (str,), {}), str, "probe"), (type("_ProbeInt", (), {}), lambda obj: 7, 7)]
    try:
        for cls, fn, _ in probes: state.converters[cls] = fn
        state.cache.clear()
        passed = all(QVariant(cls("probe") if issubclass(cls, str) else cls()).value() == want for cls, _, want in probes)
    finally:
        for cls, _, _ in probes: state.converters.pop(cls, None)
        state.cache.clear()
    if not passed:
        raise RuntimeError("self-test failed: QVariant layout is incorrect for this version.")

def _register(state: _State):
    pyqt = int(QtCore.PYQT_VERSION_STR.split(".")[0])
    state.size = _qvariantSize(pyqt)
    convertor = _makeCallback(state)
    _findRegisterFunction(pyqt)(ctypes.cast(convertor, c_void_p))
    state.callback = convertor
    state.dispatch = _makeDispatch(state, state.size)
    _selfTest(state)

def installQVariantType(cls: type = None, converter: Callable[[Any], Any] = str):
    """Make instances of cls reach Qt as QVariant(converter(obj)).\n
    converter is called with the instance and may return anything PyQt can put in a QVariant:
    a str (QString), QColor, QPointF, a dict (QVariantMap), a list (QVariantList)... Defaults to str(obj).
    Subclasses inherit it unless they are registered themselves. Use as installQVariantType(cls, fn),
    @installQVariantType, or @installQVariantType(converter=fn). Safe to call repeatedly and across reloads.
    """
    if cls is None:
        return lambda target: installQVariantType(target, converter)
    if not isinstance(cls, type) or cls in _NO_HOOK or issubclass(cls, sip.simplewrapper):
        raise TypeError(f"{cls!r} cannot be hooked, PyQt already converts it itself.")
    if not callable(converter):
        raise TypeError(f"converter must be callable, got {converter!r}")

    state = _getState()
    if state.callback is None and state.error is None:
        try:_register(state)
        except Exception as exc:
            state.error = exc
    if state.error is not None:
        raise RuntimeError(f"hook could not activate: {state.error}") from state.error

    state.dispatch = _makeDispatch(state, state.size)
    state.converters[cls] = converter
    state.cache.clear()
    return cls

def installPointerString(*classes: SupportsStr):
    """Register classes whose instances should reach Qt as a QString (via str(obj))."""
    for cls in classes:
        installQVariantType(cls)
    return classes[0] if len(classes) == 1 else classes

def is_StateActive():
    state = getattr(sys, _STATE_ATTR, None)
    return bool(state and state.callback is not None and state.error is None)
