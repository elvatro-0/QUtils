"""
Every import QUtils uses to make my life easier.
"""

import qgis.core as core
from qgis.core import(
    Qgis,
    QgsProcessingParameterFeatureSource,
    QgsProcessingFeatureSource,
    QgsProcessingParameterNumber,
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
    QgsRasterDataProvider,
    QgsVectorDataProvider,
    QgsDataProvider,
    QgsWkbTypes,
    QgsRectangle,
    QgsSpatialIndex,
    QgsFeatureStore,
    QgsPointXY,
    QgsPoint,
    QgsProject,
    QgsApplication
)
from qgis.analysis import(
    QgsRasterCalculatorEntry,
    QgsRasterCalculator
)
from qgis.PyQt.QtWidgets import(
    QHBoxLayout,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QApplication,
    QTabWidget,
    QFileDialog,
    QLineEdit,
    QShortcut,
    QToolButton,
    QToolTip,
    QMenu,
    QLabel,
    QStyle
)
from qgis.PyQt.QtCore import(
    QVariant,
    pyqtSignal,
    Qt,
    QSize,
    QElapsedTimer,
    QPoint,
    QTimer,
    QEvent,
    QRegularExpression,
    QByteArray,
    QRectF,
    QRect,
    QThreadPool,
    QObject,
)
from qgis.PyQt.QtGui import(
    QColor,
    QFontDatabase,
    QPalette,
    QTextDocument,
    QTextCursor,
    QKeySequence,
    QIcon,
    QSyntaxHighlighter,
    QTextCharFormat,
    QGuiApplication,
    QPixmap,
    QPainter,
    QImage,
    QWheelEvent,
    QTransform,
    QCloseEvent,
    QFont,
    QMouseEvent,
    QTextBlockFormat,
    QTextOption,
    QFontMetrics,
    QTextFrame,
    QTextFrameFormat,
    QTextTableFormat,
    QTextLength,
    QTextTable,
    QInputEvent
)
from qgis.utils import iface
from qgis.gui import QgisInterface
from qgis.PyQt import QtCore, sip
from qgis.PyQt.QtSvg import QSvgRenderer
from qgis import processing
from html import escape
from typing import TYPE_CHECKING, Union, overload, Iterator, Iterable, Any, Literal, Callable, Protocol, TypeVar
from pathlib import Path
from dataclasses import dataclass, field, fields, MISSING
from bisect import bisect_left, bisect_right
import functools, inspect, traceback, math, re, sys, ctypes
from ctypes import CFUNCTYPE, POINTER, c_bool, c_char_p, c_int, c_void_p, py_object
import threading