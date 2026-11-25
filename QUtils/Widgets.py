"""
Custom Qt Widgets to be used in QGIS. \n
Includes FeedbackWidget which mimics the QGIS processing log but with more features.
The widget is created when working in the QGIS python console when createContextAndFeedback(showWidget=True) (which is also the defualt),
from the Console module.
"""

from qgis.core import (
    QgsProcessingFeedback,
    QgsApplication,
    QgsProject
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
from qgis.PyQt import sip
from qgis.PyQt.QtSvg import QSvgRenderer
from html import escape
from typing import Any, Literal, Callable
from bisect import bisect_left
import re, sys

from .Internal.ErrorHandling import QUtilsExceptions
from .Storage import *

__author__ = "Roxanne Minerals"
__version__ = 1.1


class FeedbackWidget:
    pass

#========================================================================================================#
#------------------------------------------------Widgets-------------------------------------------------#
#===============================================>      <=================================================#

class Feedback(QgsProcessingFeedback):
    def __init__(self, *args, **kwargs):
        pass

class PushButton(QPushButton):
    mouseOver = pyqtSignal(bool)
    def __init__(self, size: QSize, *args, tooltip = "", **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedSize(size)
        self.setToolTip(tooltip)
    def enterEvent(self, a0):
        self.mouseOver.emit(True)
        return super().enterEvent(a0)
    def leaveEvent(self, a0):
        self.mouseOver.emit(False)
        return super().leaveEvent(a0)
    
class ToolButton(QToolButton):
    def __init__(self, size: QSize, *args, tooltip = "", icon: QIcon = None, autoraise = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedSize(size)
        self.setToolTip(tooltip)
        self.setAutoRaise(autoraise)
        if icon is not None:
            self.setIcon(icon)

class Highlighter(QSyntaxHighlighter):
    startCount = pyqtSignal()
    finishCount = pyqtSignal()
    runhighlight = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.text = ""
        self.colour = QTextCharFormat()
        self.colour.setBackground(Color("#3C86A8"))
        self.expr = QRegularExpression()
        self.docclone = self.document().clone()
        self.positions = []
        self.lengths = []
        self.gen = 0
        self.runhighlight.connect(self.rehighlight)
        self.timer = None

    def highlight(self, text: str, flags: QRegularExpression.PatternOptions = QRegularExpression.PatternOption.CaseInsensitiveOption, whole = False):
        self.startCount.emit()
        self.gen += 1
        self.text = text
        if self.document().toPlainText() != self.docclone.toPlainText():
            self.docclone = self.document().clone()
        document = self.docclone
        esc = QRegularExpression.escape(self.text)
        if whole:
            esc = r"(?<![\p{L}\p{N}])" + esc + r"(?![\p{L}\p{N}])"
        self.expr = QRegularExpression(esc, flags)
        if not text:
            self.positions = []
            self.lengths = []
            self.runhighlight.emit()
            return 0
        esctext = re.escape(text)
        if whole:
            esctext = r"(?<![^\W_])" + esctext + r"(?![^\W_])"
        flag = re.IGNORECASE if flags & QRegularExpression.PatternOption.CaseInsensitiveOption else 0
        count = len(re.findall(esctext, document.toPlainText(), flag))
        gen = self.gen
        doctext = document.toPlainText()
        expr = QRegularExpression(self.expr)
        QThreadPool.globalInstance().start(lambda: self._cursorcount(doctext, expr, gen))
        return count

    def _cursorcount(self, doc, expr: QRegularExpression, gen):
        positions = []
        lengths = []
        try:
            expriter = expr.globalMatch(doc)
            while expriter.hasNext():
                _match = expriter.next()
                positions.append(_match.capturedStart())
                lengths.append(_match.capturedLength())
        except: positions, lengths = [], []
        finally:                #I hate how try except blocks looks... but needs must..  ~⪖ ˰⪕~
            if gen == self.gen:
                self.positions = positions
                self.lengths = lengths
                self.runhighlight.emit()

    def highlightBlock(self, text):
        if self.timer is None:
            self.timer = Timer(self)
        self.timer.addTime(10)
        start = self.currentBlock().position()
        end = start + len(text)
        i = bisect_left(self.positions, start)
        while i < len(self.positions) and self.positions[i] < end:
            self.timer.addTime(10)
            self.setFormat(self.positions[i] - start, self.lengths[i], self.colour)
            i += 1
        self.timer.singleShot(10, self.finishCount.emit)

def globalPos(a0: QInputEvent) -> QPoint:
    if hasattr(a0, "globalPosition"):
        return a0.globalPosition().toPoint()
    return a0.globalPos()

class DragableWidget(QWidget):
    movedPosition = pyqtSignal(QPoint)
    mousereleased = pyqtSignal()
    crossedSnapArea = pyqtSignal()

    def __init__(self, *args, snappoint: Callable[[], QPoint] | QPoint = None, snaparea: int = 10, showpreview = True, dragable = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.snappoint = snappoint
        self.snaparea = snaparea
        self.showpreview = showpreview
        self.dragable = dragable
        self.dragpos = None
        self.snappos = None
        self.movedPosition.connect(self._snap)
        self.mousereleased.connect(self._mouserelease)
        self.crossedSnapArea.connect(lambda: (setattr(self, "dopreview", True), setattr(self, "stop_oprange", True)))
        self.insnap = True
        self.preview = None
        self.previewopacity = 0
        self.dopreview = True
        self.stop_oprange = False
        self.previewvisible = False

    def mousePressEvent(self, a0: QMouseEvent):
        if a0.button() == Qt.MouseButton.LeftButton and self.dragable:
            self.dragpos = globalPos(a0) - self.frameGeometry().topLeft()
            self.previewvisible = True
            if self.preview is not None:
                self._preview()
                self.preview.show()
                self.raise_()
        return super().mousePressEvent(a0)
    def mouseMoveEvent(self, a0):
        if self.dragpos is not None and a0.buttons() & Qt.MouseButton.LeftButton and self.dragable:
            self.move(globalPos(a0) - self.dragpos)
            self.movedPosition.emit(self.mapToGlobal(QPoint(0, 0)))
        return super().mouseMoveEvent(a0)
    def mouseReleaseEvent(self, a0):
        self.dragpos = None
        self.mousereleased.emit()
        return super().mouseReleaseEvent(a0)

    def _snap(self, point: QPoint):
        if self.snappoint is None:
            return None
        self.snappos = None
        snappoint = self.snappoint() if callable(self.snappoint) else self.snappoint
        tl = QPoint(snappoint.x() - self.snaparea - self.width(), snappoint.y() - self.snaparea - self.height())
        lr = QPoint(snappoint.x() + self.snaparea + self.width(), snappoint.y() + self.snaparea + self.height())
        if point.x() > tl.x() and point.y() > tl.y() and point.x() < lr.x() and point.y() < lr.y():
            if not self.insnap:
                self.crossedSnapArea.emit()
            self.insnap = True
            self.snappos = snappoint
            self.previewvisible = True
            self._preview()
            return None
        if self.insnap:
            self.crossedSnapArea.emit()
        self.insnap = False
        self.previewvisible = False
        self._preview()

    def _preview(self):
        if self.snappoint is None or not self.showpreview:
            return None
        snappoint = self.snappoint() if callable(self.snappoint) else self.snappoint
        if self.preview is None:
            roundness = self.roundness if hasattr(self, "roundness") else (0, 0)
            self.preview = paintedSimpleInfoWidget(parent=self.parent(), colour="#6b6b6b", roundness=roundness, flags=Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.preview.setFixedSize(self.size())
        self.preview.move(snappoint)
        QTimer.singleShot(0, lambda: self._previewShow(self.previewvisible))
        self.raise_()

    def _previewShow(self, visible):
        if not self.dopreview:
            return None
        self.dopreview = False
        self.stop_oprange = False
        maxop = 35
        slowness = 3000
        _range = range(self.previewopacity * slowness, maxop * slowness + 1) if visible else range(-self.previewopacity * slowness, 1)
        if visible:
            self.preview.setVisible(self.previewvisible)
        for op in _range:
            if self.stop_oprange:
                break
            opacity = abs(op) // slowness
            self.preview.setWindowOpacity(opacity / 100)
            self.previewopacity = opacity
            QApplication.processEvents()
        self.stop_oprange = False
        if not visible:
            self.preview.setVisible(self.previewvisible)

    def _mouserelease(self):
        if self.snappos is not None:
            self.move(self.snappos)
            self.snappos = None
        if self.insnap and self.preview is not None:
            self.preview.hide()

    def closeEvent(self, a0):
        if self.preview is not None:
            self.preview.close()
        return super().closeEvent(a0)

class SimpleInfoWidget(DragableWidget):
    activeChange = pyqtSignal(bool)
    mouseOver = pyqtSignal(bool)
    clickedOn = pyqtSignal()
    scrollWheel = pyqtSignal(int)

    def __init__(self, parent = None, flags = Qt.WindowType(0), dragable = False, **kwargs):
        super().__init__(parent, flags, dragable=dragable, **kwargs)
        if parent:
            self.resize(parent.size() * 0.6)
        else: self.resize(iface.mainWindow().size() * 0.6)
        self.hovered = False

    def changeEvent(self, a0):
        if a0.type() == QEvent.Type.ActivationChange:
            self.activeChange.emit(self.isActiveWindow())
        return super().changeEvent(a0)
    def enterEvent(self, a0):
        self.hovered = True
        self.mouseOver.emit(True)
        return super().enterEvent(a0)
    def leaveEvent(self, a0):
        self.hovered = False
        self.mouseOver.emit(False)
        return super().leaveEvent(a0)
    def mousePressEvent(self, a0):
        self.clickedOn.emit()
        return super().mousePressEvent(a0)
    def wheelEvent(self, a0):
        if a0.angleDelta().y() > 0:
            self.scrollWheel.emit(-1)
        elif a0.angleDelta().y() < 0:
            self.scrollWheel.emit(1)
        return super().wheelEvent(a0)

class paintedSimpleInfoWidget(SimpleInfoWidget):
    def __init__(self, *args, colour: str = None, roundness: tuple[int, int] = (0, 0), **kwargs):
        super().__init__(*args, **kwargs)
        self.roundness = roundness
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        colour = self.palette().color(QPalette.ColorRole.Window).name() if colour is None else colour
        self.setObjectName("PSIW")
        self.setStyleSheet(f"#PSIW {{ background-color: {colour};}}")

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().color(QPalette.ColorRole.Window))
        painter.drawRoundedRect(self.rect(), self.roundness[0], self.roundness[1])
        painter.end()

class SimpleLineEdit(QLineEdit):
    activeChange = pyqtSignal(bool)
    clickedOn = pyqtSignal()
    scrollWheel = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def changeEvent(self, a0):
        if a0.type() == QEvent.Type.ActivationChange:
            self.activeChange.emit(self.isActiveWindow())
        return super().changeEvent(a0)
    def mousePressEvent(self, a0):
        if a0.button() == Qt.MouseButton.LeftButton:
            self.clickedOn.emit()
        return super().mousePressEvent(a0)
    def wheelEvent(self, a0):
        if a0.angleDelta().y() > 0:
            self.scrollWheel.emit(True)
        elif a0.angleDelta().y() < 0:
            self.scrollWheel.emit(False)
        return super().wheelEvent(a0)

class SimpleTextEdit(QTextEdit):
    scrollWheel = pyqtSignal(bool)
    scrollEvent = pyqtSignal(QWheelEvent)
    resizeWidget = pyqtSignal()
    closeWidget = pyqtSignal(QCloseEvent)
    anyEvent = pyqtSignal()
    clicked = pyqtSignal()
    appendedText = pyqtSignal(str)

    def __init__(self, *args, passive = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.passive = passive

    def wheelEvent(self, e):
        if self.underMouse():
            self.scrollEvent.emit(e)
            if e.angleDelta().y() > 0:
                self.scrollWheel.emit(True)
            elif e.angleDelta().y() < 0:
                self.scrollWheel.emit(False)
        if self.passive:
            e.accept()
            return
        super().wheelEvent(e)
    def resizeEvent(self, a0):
        self.resizeWidget.emit()
        return super().resizeEvent(a0)
    def closeEvent(self, a0):
        self.closeWidget.emit(a0)
        return super().closeEvent(a0)
    def event(self, e):
        self.anyEvent.emit()
        return super().event(e)
    def mousePressEvent(self, e):
        self.clicked.emit()
        return super().mousePressEvent(e)

    def append(self, text):
        super().append(text)
        self.appendedText.emit(text)

class appendedSimpleTextEdit(SimpleTextEdit):
    def __init__(self, parentlog: SimpleTextEdit, appendkey: Callable[[], Any] | Any, *args, appendsize = 50, appendkeystore: SupportsAppend[str | int | float] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parentlog = parentlog
        self.appendkey = appendkey
        self.appendsize = appendsize
        self.appendstore = appendkeystore
        self.parentlog.appendedText.connect(self._appendblock)
    
    def _appendblock(self, html: str):
        autoscroll = True if self.verticalScrollBar().value() == self.verticalScrollBar().maximum() else False
        doc = self.document()
        cursor = QTextCursor(doc)
        tableformat = QTextTableFormat()
        tableformat.setBorder(0)
        tableformat.setCellSpacing(0)
        tableformat.setCellPadding(0)
        tableformat.setMargin(0)
        tableformat.setPadding(0)
        tableformat.setColumnWidthConstraints([QTextLength(QTextLength.Type.FixedLength, self.appendsize), QTextLength(QTextLength.Type.VariableLength, 0)])
        for block in splitHtml(html):
            key = str(self.appendkey() if callable(self.appendkey) else self.appendkey)
            cursor.movePosition(QTextCursor.MoveOperation.End)
            table = cursor.insertTable(1, 2, tableformat)
            textalign = QTextBlockFormat()
            textalign.setAlignment(Qt.AlignmentFlag.AlignRight)
            textalign.setNonBreakableLines(True)
            cursor.mergeBlockFormat(textalign)
            cursor.insertText(f"{key} | ")
            cursor.setPosition(table.rowEnd(cursor).position() + 1)
            cursor.insertHtml(block)
            cursor.setPosition(table.rowEnd(cursor).position() + 1)
            if self.appendstore is not None:
                for cast in (int, float):
                    try: appendkey = cast(key); break
                    except ValueError: continue
                else: appendkey = key
                self.appendstore.append(appendkey)
        if autoscroll:
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def append(self, text):
        self._appendblock(text)

#this isnt implemented yet... im working on it! >~<
class LineFinderWidget(paintedSimpleInfoWidget):
    def __init__(self, text: QTextEdit, rangelookup: RangeLookup, *args, colour=None, roundness = (0, 0), **kwargs):
        super().__init__(*args, colour=colour, roundness=roundness, **kwargs)
        self.textdoc = text
        self.rangelookup = rangelookup
        self.resize(QSize(1, int(iface.mainWindow().height() * 0.024)))
        box = QHBoxLayout(self)
        boxsize = QSize(int(iface.mainWindow().width() * 0.04), int(self.height()))
        self.startbox = SimpleLineEdit()
        self.startbox.setFixedSize(boxsize)
        self.endbox = SimpleLineEdit()
        self.endbox.setFixedSize(boxsize)
        dash = QLabel("-")
        dash.setContentsMargins(0, 0, 0, 6)
        font = QFont()
        font.setStyleHint(QFont.StyleHint.Decorative)
        font.setPixelSize(25)
        dash.setFont(font)
        dash.setFixedSize(int(iface.mainWindow().width() * 0.00588), int(self.height()))
        box.addWidget(self.startbox)
        box.addWidget(dash)
        box.addWidget(self.endbox)
        self.startbox.textChanged.connect(lambda text: self._autoDash(text, 1))
        self.endbox.textChanged.connect(lambda text: self._autoDash(text, 2))

    def _autoDash(self, text: str, box: Literal[1, 2]):
        if text.endswith("-") and box == 1 and not self.endbox.text():
                if len(text) > 1: self.startbox.setText(text.removesuffix("-"))
                self.endbox.setFocus()
        if text.endswith("-") and box == 2 and not self.startbox.text():
            self.startbox.setText(text.removesuffix("-"))
            self.endbox.setText("")
            if len(text) == 1: self.startbox.setText("-")

    def _find(self):
        pass



class Timer(QTimer):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.running = False
        self.slot = lambda: None
        self.timeout.connect(self._run)
    
    def singleShot(self, msec, slot):
        if not self.running:
            self.running = True
            self.slot = slot
            self.start(msec)

    def addTime(self, msec):
        if self.running:
            self.start(msec)

    def _run(self):
        self.stop()
        self.slot()
        self.running = False


class FeedbackWidget(QWidget):
    """A mimic of the processing dialog's log, progress bar and cancel button, for use in the python console"""
    def __init__(self, feedback: Feedback, parent = None, withtabs = False, tabname = "log"):
        self.elapsed = QElapsedTimer()
        self.elapsed.start()
        parent = iface.mainWindow() if parent is None else parent
        super().__init__(parent, Qt.WindowType.Window)
        self.setMinimumSize(int(1920 * 0.48), int(1080 * 0.48))
        self.resize(iface.mainWindow().size() * 0.6)
        self.setWindowTitle("Processing log")
        self.feedback = feedback
        if self.feedback.widget is None:
            self.feedback.widget = self
        self.sysexcepthook = sys.excepthook
        sys.excepthook = self.feedback.exception
        buttonsize = QSize(int(self.size().width() * 0.07), int(self.size().height() * 0.04))
        squaresize = QSize(buttonsize.height(), buttonsize.height())
        self.log = SimpleTextEdit(readOnly=True)
        self.currentlog = self.log
        self.getCurrentLog = lambda: self.currentlog
        self.elapsedappendstore = RangeLookup()
        self.elapsedappend = appendedSimpleTextEdit(self.log, lambda: round(self.elapsed.elapsed() / 1000, 2), appendkeystore=self.elapsedappendstore, readOnly=True)
        self.elapsedappendbutton = PushButton(squaresize, icon=QgsApplication.getThemeIcon("/propertyicons/temporal.svg"), tooltip="Elapsed Time (secs)")
        self.linenumberappend = appendedSimpleTextEdit(self.log, self._linenumber, readOnly=True)
        self.linenumberappendbutton = PushButton(squaresize, icon=lineNumberIcon(), tooltip="Line Numbers")
        self.linefinder = LineFinderWidget(self.log, self.elapsedappendstore, self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint, dragable=True, roundness=(10, 10))
        logpalette = QPalette()
        logpalette.setColor(QPalette.ColorRole.Highlight, Color("#0945ec"))
        self.contextmenu = self.log.createStandardContextMenu()
        for log in (self.log, self.elapsedappend, self.linenumberappend):
            log.setPalette(logpalette)
            log.customContextMenuRequested.connect(lambda pos: self.contextmenu.exec(self.currentlog.mapToGlobal(pos)))
            log.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            log.loghistory = ""
            log.linenumber_save = 0
        self.toendbuffer = SimpleInfoWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.toendbuffer.setWindowOpacity(0.01)
        self.toendbuffer.hide()
        self.tostartbuffer = SimpleInfoWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.tostartbuffer.setWindowOpacity(0.01)
        self.tostartendwidget = SimpleInfoWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.tostartendwidget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.tostartbuffer.hide()
        self.bar = QProgressBar()
        self.barpalette = QPalette()
        self.barpalette.setColor(QPalette.ColorRole.Highlight, Color("#965EC4"))
        self.bar.setPalette(self.barpalette)
        self.bar.setRange(0, 100)
        self.cancelButton = PushButton(buttonsize, "Cancel")
        self.wrapbutton = PushButton(buttonsize, "Unwrap")
        self.copytext = PushButton(squaresize, icon=QgsApplication.getThemeIcon("/mActionEditCopy.svg"), tooltip="Copy Log")
        self.clearlog = PushButton(squaresize, icon=QgsApplication.getThemeIcon("/console/iconClearConsole.svg"), tooltip="Clear Log")
        self.savelog = PushButton(squaresize, icon=QgsApplication.getThemeIcon("/mActionFileSave.svg"), tooltip="Save Log")
        self.keybinds = PushButton(squaresize, icon=QgsApplication.getThemeIcon("/mActionKeyboardShortcuts.svg"), tooltip="Key Binds")
        self.toend = ToolButton(squaresize, icon=rotateIcon(arrowIcon(), 180))
        self.tostart = ToolButton(squaresize, icon=arrowIcon())
        tostartendbackground = "#BE" + self.palette().color(QPalette.ColorRole.Window).name().removeprefix("#")
        tostartendhover = self.palette().color(QPalette.ColorRole.Button).name()
        tostartendpressed = self.palette().color(QPalette.ColorRole.Base).name()
        self.toend.setStyleSheet(f"QToolButton {{background-color: {tostartendbackground};border: none; border-radius: 3px;}} QToolButton:hover {{background-color: {tostartendhover};}} QToolButton:pressed {{background-color: {tostartendpressed};}}")
        self.tostart.setStyleSheet(f"QToolButton {{background-color: {tostartendbackground};border: none; border-radius: 3px;}} QToolButton:hover {{background-color: {tostartendhover};}} QToolButton:pressed {{background-color: {tostartendpressed};}}")
        self.toend.hide()
        self.tostart.hide()
        self.loading = QLabel("searching...")
        self.loading.setFixedWidth(70)
        self.loading.hide()
        self.iswrap = True
        self._widget = self
        bottom = QHBoxLayout()
        self._bottom = QHBoxLayout()
        bottom.addWidget(self.elapsedappendbutton)
        bottom.addWidget(self.linenumberappendbutton)
        bottom.addWidget(self.bar, 1)
        bottom.addWidget(self.cancelButton)
        self._bottom.addWidget(self.savelog)
        self._bottom.addWidget(self.copytext)
        self._bottom.addWidget(self.clearlog)
        self._bottom.addStretch(1)
        self._bottom.addWidget(self.loading)
        self._bottom.addWidget(self.keybinds)
        self._bottom.addWidget(self.wrapbutton)
        self.tabwidget = QWidget()
        page = QVBoxLayout(self.tabwidget) if withtabs else QVBoxLayout(self)
        self.logpage = QHBoxLayout()
        self.logpage.addWidget(self.log)
        self.logpage.addWidget(self.elapsedappend)
        self.logpage.addWidget(self.linenumberappend)
        self.elapsedappend.hide()
        self.linenumberappend.hide()
        page.addLayout(self.logpage)
        page.addLayout(bottom)
        page.addLayout(self._bottom)
        if withtabs:
            self.tabs = QTabWidget()
            self.tabs.addTab(self.tabwidget, tabname)
            layout = QVBoxLayout(self)
            layout.addWidget(self.tabs)
            self.tabs.currentChanged.connect(self._updatetabs)
            self.tabright = QShortcut(QKeySequence(Qt.Key.Key_Right), self, lambda: self._movetabs(True))
            self.tableft = QShortcut(QKeySequence(Qt.Key.Key_Left), self, lambda: self._movetabs(False))
        self.search = QShortcut(QKeySequence.StandardKey.Find, self, self._findwidget)
        self.keybindsshortcut = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Slash), self, self._keybindsquerytoggle)
        self.savelogshortcut = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_S), self, self._saveLog)
        self.elapsedappendshortcut = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_E), self, lambda: self._appendTextToggle(self.elapsedappend))
        self.linenumberappendshortcut = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_L), self, lambda: self._appendTextToggle(self.linenumberappend))
        for action in self.contextmenu.actions(): action.setEnabled(True)
        CMpalette = self.contextmenu.palette()
        findcolour = CMpalette.color(QPalette.ColorRole.WindowText).name()
        try: self.CMfindaction = self.contextmenu.addAction(findIcon(findcolour), "Find...", self._findwidget, QKeySequence.StandardKey.Find)
        except: self.CMfindaction = self.contextmenu.addAction(findIcon(findcolour), "Find...", QKeySequence.StandardKey.Find, self._findwidget)
        self.highlight = Highlighter(self.log)
        self.highlight.startCount.connect(lambda: (self.loading.setVisible(True), self.HLcountbox.setText("Searching...") if hasattr(self, "HLcountbox") and not sip.isdeleted(self.HLcountbox) else None))
        self.highlight.finishCount.connect(lambda: self.loading.setVisible(False))
        self.HLoptions = {"sensitivity": (QTextDocument.FindFlag(0), QRegularExpression.PatternOption.CaseInsensitiveOption, False), "wholewords":(QTextDocument.FindFlag(0), False)}
        self.tostartendpage = QVBoxLayout(self.tostartendwidget)
        self.tostartpage = QHBoxLayout()
        self.toendpage = QHBoxLayout()
        self.tostartpage.addWidget(self.tostart, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        self.toendpage.addWidget(self.toend, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        self.tostartendpage.addLayout(self.tostartpage)
        self.tostartendpage.addLayout(self.toendpage)
        self.tostartendwidget.show()
        QTimer.singleShot(0, self._updatetostartendbuffers)
        self.currenttab = self
        self.withtabs = withtabs
        self.tabname = tabname
        self.findline_save = ""
        self.findopen = False
        self.findwidgetpos = None
        self.findwidget_insnap = True
        self.tabi = 0
        self.linen = 0
        self.showtostartend = False
        self.allowtostartend = None
        self.stoptostartend = False
        self.forceclose = False
        self.do_logappend = True
        feedback.messageLogged.connect(self.appendMessage)
        feedback.progressChanged.connect(self._setProgress)
        feedback.finished.connect(lambda complete: self._setProgress(100, True, not complete))
        self.elapsedappendbutton.clicked.connect(lambda: QTimer.singleShot(0, lambda: self._appendTextToggle(self.elapsedappend)))
        self.linenumberappendbutton.clicked.connect(lambda: QTimer.singleShot(0, lambda: self._appendTextToggle(self.linenumberappend)))
        self.cancelButton.clicked.connect(self.feedback.cancel)
        self.wrapbutton.clicked.connect(self._setWrap)
        self.copytext.clicked.connect(lambda: QApplication.clipboard().setText(self.currentlog.toPlainText()))
        self.clearlog.clicked.connect(self._clearlog)
        self.savelog.clicked.connect(self._saveLog)
        self.keybinds.pressed.connect(self._keybindsquerytoggle)
        self.tostart.clicked.connect(lambda: self._tostartend(-1))
        self.toend.clicked.connect(lambda: self._tostartend(1))
        self.toendbuffer.mouseOver.connect(lambda show: self._showtostartend(self.toend, show) if self._widget.currentlog.verticalScrollBar().value() < self._widget.currentlog.verticalScrollBar().maximum() else None)
        self.tostartbuffer.mouseOver.connect(lambda show: self._showtostartend(self.tostart, show) if self._widget.currentlog.verticalScrollBar().value() > self._widget.currentlog.verticalScrollBar().minimum() else None)
        self.toendbuffer.clickedOn.connect(self.tostartendwidget.raise_)
        self.tostartbuffer.clickedOn.connect(self.tostartendwidget.raise_)
        self.tostartendwidget.mouseOver.connect(lambda show: setattr(self, "showtostartend", show))
        self.tostartbuffer.scrollWheel.connect(lambda direction: self._widget.currentlog.verticalScrollBar().setValue(self._widget.currentlog.verticalScrollBar().value() + (QApplication.wheelScrollLines() * self._widget.currentlog.verticalScrollBar().singleStep() * direction)))
        self.toendbuffer.scrollWheel.connect(lambda direction: self._widget.currentlog.verticalScrollBar().setValue(self._widget.currentlog.verticalScrollBar().value() + (QApplication.wheelScrollLines() * self._widget.currentlog.verticalScrollBar().singleStep() * direction)))
        self.tostartendwidget.activeChange.connect(lambda active: setattr(self, "stoptostartend", True) if not active and self._widget.currentlog.verticalScrollBar().isActiveWindow() else None)
        for log in (self.log, self.elapsedappend, self.linenumberappend):
            log.verticalScrollBar().rangeChanged.connect(lambda h, l: QTimer.singleShot(0, self._showtostartendbuffers))
            log.verticalScrollBar().valueChanged.connect(lambda x: self._updatetostartend())
        for signal in (self.log.scrollEvent, self.elapsedappend.scrollEvent, self.linenumberappend.scrollEvent, self._widget.toendbuffer.scrollWheel, self._widget.tostartbuffer.scrollWheel):
            signal.connect(lambda *x: setattr(self, "stoptostartend", True))

    @QUtilsExceptions.ErrorHandling
    def addTab(self, tab: QWidget, name: str = None):
        if not self.withtabs:
            QUtilsExceptions.CriticalError("Cannot add tabs to FeedbackWidget with tabs uninitialised", self.feedback)
        if hasattr(tab, "tabname"):
            name = tab.tabname if name is None else name
        if name is None:
            QUtilsExceptions.CriticalError("Tab name has not been set", self.feedback)
        if hasattr(tab, "search"):
            if isinstance(tab.search, QShortcut):
                for shortcut in (tab.search, tab.keybindsshortcut, tab.savelogshortcut, tab.elapsedappendshortcut, tab.linenumberappendshortcut):
                    shortcut.setEnabled(False)
                tab.contextmenu.removeAction(tab.CMfindaction)
                tab.contextmenu.addAction(self.CMfindaction)
                tab._closetostartendbuffers()
                tab._settostartendbuffers(self)
                for log in (tab.log, tab.elapsedappend, tab.linenumberappend):
                    log.scrollEvent.connect(lambda *x: setattr(self, "stoptostartend", True))
                tab.elapsedappendbutton.clicked.connect(lambda: QTimer.singleShot(0, self._updateAppend))
                tab.linenumberappendbutton.clicked.connect(lambda: QTimer.singleShot(0, self._updateAppend))
                tab.linefinder.close()
                sys.excepthook = self.feedback.exception
        self.tabs.addTab(tab, name)
        QgsApplication.processEvents()

    #>>>QtSignal Slot functions<<<
    def appendMessage(self, text: str, style: str):
        html = escape(text).replace("\n", "<br>")
        formated = style.format(html)
        self.log.append(formated)
        QgsApplication.processEvents()

    def _setProgress(self, value, complete = False, raised = False):
        from .Processing import PrettyNumber
        if self.feedback.isCanceled():
            self.barpalette.setColor(QPalette.ColorRole.HighlightedText, Color("#1d1d1d"))
            self.bar.setFormat(f"Canceled - {PrettyNumber(self.elapsed.elapsed() / 1000)} Seconds")
            self.bar.setPalette(self.barpalette)
            self.bar.setValue(100)
            return None
        self.bar.setValue(int(value))
        self.bar.setFormat(f"%p% - {PrettyNumber(self.elapsed.elapsed() / 1000)} Seconds")
        self.barpalette.setColor(QPalette.ColorRole.HighlightedText, Color("#dfdfdf"))
        if self.bar.value() > 50:
            self.barpalette.setColor(QPalette.ColorRole.HighlightedText, Color("#1d1d1d"))
        if complete:
            sys.excepthook = self.sysexcepthook
            if raised: self.bar.setFormat(f"Exception Raised - {PrettyNumber(self.elapsed.elapsed() / 1000)} Seconds")
            else: self.bar.setFormat(f"Complete in {PrettyNumber(self.elapsed.elapsed() / 1000)} Seconds")
        self.bar.setPalette(self.barpalette)
        QgsApplication.processEvents()
    def _appendTextToggle(self, appendobj: appendedSimpleTextEdit):
        currentVscrollbar = self.currentlog.verticalScrollBar()
        currentHscrollbar = self.currentlog.horizontalScrollBar()
        if appendobj is not self.currentlog:
            self.currentlog.hide()
            appendobj.show()
            appendobj.verticalScrollBar().setValue(currentVscrollbar.value())
            appendobj.horizontalScrollBar().setValue(currentHscrollbar.value())
            if currentVscrollbar.value() == currentVscrollbar.maximum():
                appendobj.verticalScrollBar().setValue(appendobj.verticalScrollBar().maximum())
            self.currentlog = appendobj
        else:
            appendobj.hide()
            self.log.show()
            self.log.verticalScrollBar().setValue(currentVscrollbar.value())
            self.log.horizontalScrollBar().setValue(currentHscrollbar.value())
            if currentVscrollbar.value() == currentVscrollbar.maximum():
                self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())
            self.currentlog = self.log
        self._updateAppend()
    def _updateAppend(self):
        self.highlight.setDocument(self.currentlog.document())
        if getattr(self, "findwidget", None) is not None:
            if self.findline.text():
                counttext = self.HLcountbox.text()
                self.highlight.startCount.emit()
                QTimer.singleShot(0, self._updatehiglight)
                self.HLcountbox.setText("")
                if "/" in counttext:
                    self.HLcountbox.setText(counttext)
                QTimer.singleShot(0, self._changecursorpos)
        QTimer.singleShot(0, self._updatetostartendbuffers)
    def _linenumber(self):
        self.linen += 1
        return self.linen
    

    def _setWrap(self):
        self.iswrap = not self.iswrap
        for log in (self.log, self.elapsedappend, self.linenumberappend):
            log.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap) if not self.iswrap else log.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.wrapbutton.setText("Wrap") if not self.iswrap else self.wrapbutton.setText("Unwrap")
    def _clearlog(self):
        for log in (self.log, self.elapsedappend, self.linenumberappend):
            if QApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier and log.loghistory:
                log.setHtml(log.loghistory + log.toHtml())
                self._updatehiglight()
                log.loghistory = ""
                log.linenumber_save = 0
            elif not log.document().isEmpty():
                log.loghistory = log.toHtml()
                log.linenumber_save = self.linen
                log.clear()
                self._widget.highlight.positions = []
                self._widget.highlight.lengths = []
                self._widget.highlight.startCount.emit()
                self._widget.highlight.rehighlight()
                self._updatecursorcount()
            QgsApplication.processEvents()
    def _saveLog(self):
        path = QFileDialog.getSaveFileName(self, directory=QgsProject.instance().homePath(), filter="Text files (*.txt)")
        if not path[0]:
            return None
        with open(path[0], "w", encoding="utf-8") as f:
            f.write(self._widget.currentlog.toPlainText())
    def _updatetabs(self):
        tab: FeedbackWidget = self.tabs.widget(self.tabi)
        tab = self if self.tabi == self.tabs.indexOf(self.tabwidget) else tab
        self.currenttab = self if self.tabs.currentIndex() == self.tabs.indexOf(self.tabwidget) else self.tabs.currentWidget()
        if hasattr(tab, "_closefind"):
            self._closefind(True)
        self.tabi = self.tabs.currentIndex()
        self._widget = getattr(self.tabs.currentWidget(), "_widget", self)
        if hasattr(self, "findline"):
            if self._widget.findline_save and self._widget.findopen:
                self._findwidget(self.findwidgetpos, False)
        QTimer.singleShot(1, self._updatetostartendbuffers)
    def _movetabs(self, right):
        if self.isActiveWindow():
            if right:
                if self.tabs.count() - 1 == self.tabs.currentIndex():
                    self.tabs.setCurrentIndex(0)
                    return None
                self.tabs.setCurrentIndex(self.tabs.currentIndex() + 1)
                return None
            if 0 == self.tabs.currentIndex():
                self.tabs.setCurrentIndex(self.tabs.count() - 1)
                return None
            self.tabs.setCurrentIndex(self.tabs.currentIndex() - 1)
    def _keybindsquery(self):
        self.keyswidget = SimpleInfoWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint)
        self.keyswidget.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.keyswidget.activeChange.connect(lambda _bool: self._keybindsquerytoggle() if not _bool else None)
        table = "".join(f"<tr><td><code>{escape(keys)}</code></td><td>{escape(desc)}</td></tr>" for keys, desc in self.keybindstable.items())
        label = QLabel(f"<table cellspacing='6'>{table}</table>", self.keyswidget)
        box = QVBoxLayout(self.keyswidget)
        box.addWidget(label)
        self.keyswidget.setMaximumSize(label.size())
        self.keyswidget.show()
        self.keyswidget.activateWindow()
        self.keyswidget.move(self.mapToGlobal(QPoint(self.width() - self.keyswidget.width() - 20, self.height() - self.keyswidget.height() - 80)))
        self.keyswidget.setWindowOpacity(0.85)
    def _keybindsquerytoggle(self):
        if getattr(self, "keyswidget", None) is not None:
            self.keyswidget.close()
            QTimer.singleShot(50, lambda: setattr(self, "keyswidget", None))
        else:
            self._keybindsquery()
    def _closetostartendbuffers(self):
        for startend in (self.toendbuffer, self.tostartbuffer, self.tostartendwidget):
            if sip.isdeleted(startend): continue
            startend.close()
            startend.deleteLater()
    def _settostartendbuffers(self, instance: FeedbackWidget):
        self.toendbuffer = instance.toendbuffer
        self.tostartbuffer = instance.tostartbuffer
        self.tostartendwidget = instance.tostartendwidget
        self.tostart = instance.tostart
        self.toend = instance.toend
    def _updatetostartendbuffers(self):
        if sip.isdeleted(self.toendbuffer) or sip.isdeleted(self.tostartbuffer): return None
        if not isinstance(self.currenttab, FeedbackWidget):
            self.toendbuffer.hide()
            self.tostartbuffer.hide()
            return None
        self._movetostartendbuffers()
        self._showtostartendbuffers()
    def _showtostartendbuffers(self):
        if sip.isdeleted(self.toendbuffer) or sip.isdeleted(self.tostartbuffer): return None
        self.toendbuffer.setVisible(self._widget.currentlog.verticalScrollBar().isVisible())
        self.tostartbuffer.setVisible(self._widget.currentlog.verticalScrollBar().isVisible())
        self._movetostartendbuffers()
        self._widget.tostartendwidget.raise_()
    def _movetostartendbuffers(self):
        bufferwidth = int(self._widget.currentlog.height() * 0.2)
        bufferheight = int(self._widget.currentlog.height() * 0.2)
        if bufferwidth > self._widget.tostart.width() * 2.5:
            self._widget.toendbuffer.resize(bufferwidth, bufferheight)
            self._widget.tostartbuffer.resize(bufferwidth, bufferheight)
        self._widget.tostartendwidget.resize(self._widget.toendbuffer.width(), self._widget.currentlog.height() - 10)
        self._widget.toendbuffer.move(self._widget.currentlog.mapToGlobal(QPoint(self._widget.currentlog.width() - self._widget.toendbuffer.width() - 15, self._widget.currentlog.height() - self._widget.toendbuffer.height() - 15)))
        self._widget.tostartbuffer.move(self._widget.currentlog.mapToGlobal(QPoint(self._widget.currentlog.width() - self._widget.tostartbuffer.width() - 15, self._widget.currentlog.pos().y() - 10)))
        self._widget.tostartendwidget.move(self._widget.currentlog.mapToGlobal(QPoint(self._widget.currentlog.width() - self._widget.tostartendwidget.width() - 10, self._widget.currentlog.height() - self._widget.tostartendwidget.height() - 10)))
    def _updatetostartend(self):
        if sip.isdeleted(self.toend) or sip.isdeleted(self.tostart): return None
        scrollbar = self._widget.currentlog.verticalScrollBar()
        if (self.toendbuffer.hovered or self.toend.underMouse()) and scrollbar.value() == scrollbar.maximum():
            self.toend.hide()
            self.activateWindow()
        elif (self.tostartbuffer.hovered or self.tostart.underMouse()) and scrollbar.value() == scrollbar.minimum():
            self.tostart.hide()
            self.activateWindow()
        elif self.toendbuffer.hovered and scrollbar.value() != scrollbar.maximum():
            self.toend.show()
        elif self.tostartbuffer.hovered and scrollbar.value() != scrollbar.minimum():
            self.tostart.show()
    def _showtostartend(self, tostartend: PushButton, show, forcehide = False):
        widget = self._widget.tostartendwidget
        if not widget.windowHandle().isExposed():
            widget.hide()
            widget.show()
        widget.raise_()
        if not show and not forcehide:
            QTimer.singleShot(0, lambda: tostartend.setVisible(self.showtostartend) if self.showtostartend else tostartend.setVisible(show))
        else:
            tostartend.setVisible(show)
    def _tostartend(self, direction: Literal[1, -1]):
        if direction == self.allowtostartend:
            return None
        self.allowtostartend = direction
        scrollbar = self._widget.currentlog.verticalScrollBar()
        distancetoend = scrollbar.value() - scrollbar.minimum() if direction == -1 else scrollbar.maximum() - scrollbar.value()
        mid = (distancetoend // 2) + scrollbar.minimum() if direction == -1 else scrollbar.maximum() - (distancetoend // 2)
        for pos in range(distancetoend):
            if self.stoptostartend:
                break
            first, second = (scrollbar.value(), mid) if direction == 1 else (mid, scrollbar.value())
            if first > second:
                pos = maxpos - (pos - maxpos)
            else: maxpos = pos
            speed = min(pos, distancetoend - 1 - pos) * 0.03
            speed = max(1, speed)
            scrollbar.setValue(int(scrollbar.value() + speed * direction))
            QApplication.processEvents()
            if scrollbar.value() == scrollbar.minimum() or scrollbar.value() == scrollbar.maximum():
                break
        self._updatetostartend()
        self.activateWindow()
        QTimer.singleShot(0, lambda: setattr(self, "stoptostartend", False))
        self.allowtostartend = None

    keybindstable = {
        "Ctrl+F": "Find / switch focus",
        "Ctrl+G": "Go To",
        "Up/Down Arrows": "Previous/Next match",
        "Left/Right Arrows": "switch tabs (if any)",
        "Ctrl+M": "Toggle Match Case",
        "Ctrl+W": "Toggle Whole Words",
        "Ctrl+Q": "Query find options",
        "Esc": "Clear the search text or close find",
        "Ctrl+H": "Hide find box",
        "Ctrl+E": "Show/Hide Elapsed time",
        "Ctrl+L": "Show/Hide Line numbers",
        "Ctrl+Clear Button": "Restore the cleared log",
        "Ctrl+S": "Save As",
        "Ctrl+?": "Key Bindes"
    }

    #>>> find Widget <<<
    def _findwidget(self, pos: QPoint = None, active = True):
        if not isinstance(self.currenttab, FeedbackWidget):
            return None
        if getattr(self, "findwidget", None) is not None:
            if self.findwidget.isActiveWindow():
                self.activateWindow()
            else:
                self.findwidget.activateWindow()
                self.findline.setFocus()
                cursor = self._widget.currentlog.textCursor()
                if cursor.selectedText():
                    self.findline.setText(max(cursor.selectedText().split("\u2029"), key=len))
            return None
        self.findwidget = paintedSimpleInfoWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint, snappoint = lambda: QPoint(self.x() + self.width() - self.findwidget.width(), self.y() + 35), roundness = (10, 10), dragable=True)
        self.findwidget.resize(QSize(int(iface.mainWindow().width() * 0.084), int(iface.mainWindow().height() * 0.024)))
        self.findwidget.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.findwidget.insnap = self.findwidget_insnap
        box = QHBoxLayout(self.findwidget)
        self.findline = QLineEdit()
        self.findline.setFixedSize(QSize(int(self.findwidget.size().width() * 0.8), self.findwidget.size().height()))
        self.findline.setPlaceholderText("Find...")
        tab = self
        if self.withtabs:
            tab = self.tabs.currentWidget() if self.tabi != self.tabs.indexOf(self.tabwidget) else self
        tab.findopen = True
        buttonsize = QSize(self.findline.height(), self.findline.height())
        finddownbutton = ToolButton(buttonsize)
        finddownbutton.setArrowType(Qt.ArrowType.DownArrow)
        findupbutton = ToolButton(buttonsize)
        findupbutton.setArrowType(Qt.ArrowType.UpArrow)
        closebutton = ToolButton(buttonsize, icon=closeIcon())
        closebutton.setIconSize(buttonsize)
        self.HLcountbox = SimpleLineEdit(readOnly=True)
        self.HLcountbox.setFixedWidth(70)
        self.HLcountbox.setFrame(False)
        self.HLcountbox.setStyleSheet("QLineEdit { background:transparent; border:none }")
        self.HLcountbox.setText("No Results")
        self.findoptions = ToolButton(buttonsize, tooltip="More Options", icon=optionsIcon())
        self.findoptionsmenu = QMenu(self.findoptions)
        self.findactions = (self.findoptionsmenu.addAction("Match Case", lambda: self._highlightoptions("sensitivity")), self.findoptionsmenu.addAction("Whole Words", lambda: self._highlightoptions("wholewords")))
        if self._widget.HLoptions["sensitivity"][2]: self.findactions[0].setIcon(tickIcon())
        if self._widget.HLoptions["wholewords"][1]: self.findactions[1].setIcon(tickIcon())
        self.findoptions.setMenu(self.findoptionsmenu)
        self.findoptions.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        box.addWidget(self.findline)
        box.addWidget(self.HLcountbox)
        box.addWidget(finddownbutton)
        box.addWidget(findupbutton)
        box.addWidget(self.findoptions)
        box.addWidget(closebutton)
        self.timer = Timer()
        self.findline.textChanged.connect(lambda: self.timer.addTime(500))
        self.findline.textChanged.connect(lambda: self.timer.singleShot(500, self._updatehiglight))
        finddownbutton.pressed.connect(lambda: self._find(False))
        findupbutton.pressed.connect(lambda: self._find(True))
        closebutton.pressed.connect(self._closefind)
        if tab.findline_save:
            self.findline.setText(tab.findline_save)
        cursor = self._widget.currentlog.textCursor()
        if cursor.selectedText() and active:
            self.findline.setText(max(cursor.selectedText().split("\u2029"), key=len))
        self.findline.editingFinished.connect(self._findenter)
        self.findclose = QShortcut(QKeySequence.StandardKey.Cancel, self, self._esc)
        self.uparrow = QShortcut(QKeySequence(Qt.Key.Key_Up), self, lambda: self._find(True))
        self.downarrow = QShortcut(QKeySequence(Qt.Key.Key_Down), self, lambda: self._find(False))
        self.findhide = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_H), self, lambda: self._closefind(True))
        self.HLoptionssens = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_M), self, lambda: self._highlightoptionstooltip("sensitivity"))
        self.HLoptionswhole = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_W), self, lambda: self._highlightoptionstooltip("wholewords"))
        self.HLoptionquery = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Q), self, lambda: self._highlightoptionstooltip(""))
        self.HLcountboxgoto = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_G), self, lambda: self._editHLcountbox(True))
        for log in (self._widget.log, self._widget.elapsedappend, self._widget.linenumberappend):
            log.selectionChanged.connect(self._updatecursorcount)
        self._widget.highlight.finishCount.connect(self._updatecursorcount)
        self.HLcountbox.editingFinished.connect(self._changecursorpos)
        self.HLcountbox.textChanged.connect(lambda: self.HLcountbox.setToolTip(self.HLcountbox.text()))
        self.HLcountbox.clickedOn.connect(self._editHLcountbox)
        self.HLcountbox.scrollWheel.connect(self._find)
        self.findwidget.movedPosition.connect(lambda pos: setattr(self, "findwidgetpos", pos))
        self.findwidget.show()
        if pos is None and self.findwidgetpos is None or self.findwidget_insnap:
            self.findwidgetpos = QPoint(self.x() + self.width() - self.findwidget.width(), self.y() + 35)
        self.findwidget.move(self.findwidgetpos)
        self.activateWindow()
        if active:
            self.findwidget.activateWindow()
            self.findline.setFocus()
        self._updatecursorcount()
        if self.HLcountbox.text() != "No Results" and not self.findline.text():
            self._updatehiglight()

    #>>Find Widgets QtSignal Slot functions<<
    def _find(self, up):
        if getattr(self, "findwidget", None) is None:
            return None
        text = self.findline.text()
        if not text: return
        active = True
        flags = QTextDocument.FindFlag.FindBackward if up else QTextDocument.FindFlag(0)
        extraflags = self._widget.HLoptions["sensitivity"][0] | self._widget.HLoptions["wholewords"][0]
        pos = self._widget.currentlog.textCursor().position()
        if not self._widget.currentlog.find(text, flags | extraflags):
            cursor = self._widget.currentlog.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End if up else QTextCursor.MoveOperation.Start)
            self._widget.currentlog.setTextCursor(cursor)
            found = "bottom" if up else "top"
            if not self._widget.currentlog.find(text, flags | extraflags):
                cursor.setPosition(pos)
                self._widget.currentlog.setTextCursor(cursor)
                QTimer.singleShot(100, lambda: QToolTip.showText(QPoint(self.findwidget.x() + 10, self.findwidget.y() + 20), f'Cannot find "{self.findline.text()}"', self.findwidget, QRect(), 5000) if getattr(self, "findwidget", None) is not None else None)
                active = False
            if active:
                QTimer.singleShot(100, lambda: QToolTip.showText(QPoint(self.findwidget.x() + 10, self.findwidget.y() + 20), f'Found next from the {found}', self.findwidget, QRect(), 5000) if getattr(self, "findwidget", None) is not None else None)
        if active:
            self.activateWindow()
    def _findenter(self):
        if self._widget.currentlog.textCursor().selectionStart() not in self._widget.highlight.positions:
            self._find(False)
    def _closefind(self, maintaintext=False):
        if getattr(self, "findwidget", None) is not None:
            tab = self
            if self.withtabs:
                tab = self.tabs.widget(self.tabi) if self.tabi != self.tabs.indexOf(self.tabwidget) else self
            tab.findline_save = self.findline.text()
            if not maintaintext:
                tab.findopen = False
                self._widget.highlight.highlight("")
            for findkey in (self.findclose, self.uparrow, self.downarrow, self.findhide, self.HLoptionssens, self.HLoptionswhole, self.HLoptionquery, self.HLcountboxgoto):
                findkey.setEnabled(False)
                findkey.deleteLater()
            for connection in (self._widget.log.selectionChanged, self._widget.elapsedappend.selectionChanged, self._widget.linenumberappend.selectionChanged, self._widget.highlight.finishCount):
                try: connection.disconnect(self._updatecursorcount)
                except: "No disconnect to make... ~o.o~"
            self.findwidget_insnap = self.findwidget.insnap
            self.findwidget.close()
            self.findwidget.deleteLater()
            self.findwidget = None
    def _esc(self):
        if getattr(self, "findwidget", None) is not None:
            tab = self
            if self.withtabs:
                tab = self.tabs.currentWidget() if self.tabi != self.tabs.indexOf(self.tabwidget) else self
            if self.findline.text():
                self.findline.setText("")
                tab.findline_save = ""
                self.findwidget.activateWindow()
                self.findline.setFocus()
            else:
                self._closefind()
    def _updatehiglight(self):
        if getattr(self, "findwidget", None) is not None:
            count = self._widget.highlight.highlight(self.findline.text(), self._widget.HLoptions["sensitivity"][1], self._widget.HLoptions["wholewords"][1])
            if count > 0:
                self.HLcountbox.setPalette(QPalette())
                self.HLcountbox.setReadOnly(False)
            else:
                if self.findline.text():
                    palette = QPalette()
                    palette.setColor(QPalette.ColorRole.Text, Color("#b61e1e"))
                    self.HLcountbox.setPalette(palette)
                else:
                    self.HLcountbox.setPalette(QPalette())
                self.HLcountbox.setText("No Results")
                self.HLcountbox.setReadOnly(True)
    def _updatecursorcount(self):
        if getattr(self, "findwidget", None) is not None:
            positions = self._widget.highlight.positions
            if not len(positions):
                self.HLcountbox.setText("No Results")
                return self.HLcountbox.text()
            cursor = self._widget.currentlog.textCursor()
            if cursor.isNull():
                self.HLcountbox.setText(str(len(positions)))
                return self.HLcountbox.text()
            try: cursorpos = positions.index(cursor.selectionStart())
            except:
                self.HLcountbox.setText(str(len(positions)))
                return self.HLcountbox.text()
            self.HLcountbox.setText(f"{cursorpos + 1} / {len(positions)}")
            self.HLcountbox.setReadOnly(False)
            return self.HLcountbox.text()
    def _highlightoptions(self, option: str):
        if option == "sensitivity":
            if self._widget.HLoptions["sensitivity"][2]:
                self._widget.HLoptions["sensitivity"] = (QTextDocument.FindFlag(0), QRegularExpression.PatternOption.CaseInsensitiveOption, False)
                self.findactions[0].setIcon(QIcon())
            else:
                self._widget.HLoptions["sensitivity"] = (QTextDocument.FindFlag.FindCaseSensitively, QRegularExpression.PatternOption(0), True)
                self.findactions[0].setIcon(tickIcon())
        elif option == "wholewords":
            if self._widget.HLoptions["wholewords"][1]:
                self._widget.HLoptions["wholewords"] = (QTextDocument.FindFlag(0), False)
                self.findactions[1].setIcon(QIcon())
            else:
                self._widget.HLoptions["wholewords"] = (QTextDocument.FindFlag.FindWholeWords, True)
                self.findactions[1].setIcon(tickIcon())
        self.timer.addTime(250)
        self.timer.singleShot(250, self._updatehiglight)
    def _highlightoptionstooltip(self, option: str):
        if option:
            self._highlightoptions(option)
        sens = "Set" if self._widget.HLoptions["sensitivity"][2] else "unset"
        whole = "Set" if self._widget.HLoptions["wholewords"][1] else "Unset"
        QTimer.singleShot(100, lambda: QToolTip.showText(QPoint(self.findwidget.x() + self.findwidget.width() - 120, self.findwidget.y() + 20), f"Match Case {sens}\nWhole Words {whole}", self.findwidget, QRect(), 5000))
    def _changecursorpos(self):
        positions = self._widget.highlight.positions
        if not positions:
            return None
        text = self.HLcountbox.text()
        pos = text
        if "/" in text:
            pos = text.split("/")[0]
        self._updatecursorcount()
        try: pos = abs(int(pos))
        except:
            self.activateWindow()
            return None
        if pos > len(positions): pos = len(positions)
        elif pos == 0: pos = 1
        cursor = self._widget.currentlog.textCursor()
        cursor.setPosition(positions[pos - 1])
        cursor.setPosition(positions[pos - 1] + len(self.findline.text()), QTextCursor.MoveMode.KeepAnchor)
        self._widget.currentlog.setTextCursor(cursor)
        self._widget.currentlog.ensureCursorVisible()
        self.activateWindow()
    def _editHLcountbox(self, keybind = False):
        if getattr(self, "findwidget", None) is not None:
            if self.HLcountbox.text() != "No Results":
                self.HLcountbox.setPlaceholderText(self._updatecursorcount())
                self.HLcountbox.clear()
                if keybind:
                    self.findwidget.activateWindow()
                    self.HLcountbox.setFocus()

    #>>>Find Widget Event Syncronisation<<<
    def hide(self):
        if getattr(self, "findwidget", None) is not None:
            self.findwidget.hide()
        return super().hide()
    def show(self):
        if getattr(self, "findwidget", None) is not None:
            self.findwidget.show()
        return super().show()
    def setVisible(self, visible):
        if getattr(self, "findwidget", None) is not None:
            self.findwidget.setVisible(visible)
        return super().setVisible(visible)

    def closeEvent(self, a0):
        if not self.feedback.isfinished and not self.forceclose:
            self._createAYSwidget()
            a0.ignore()
            return None
        self.stoptostartend = True
        self.linefinder.close()
        self._closefind()
        self._closetostartendbuffers()
        return super().closeEvent(a0)
    def moveEvent(self, a0):
        self._movetostartendbuffers()
        if getattr(self, "findwidget", None) is not None:
            if self.findwidget.insnap:
                self.findwidget.move(self.x() + self.width() - self.findwidget.width(), self.y() + 35)
                self.findwidgetpos = self.findwidget.pos()
        return super().moveEvent(a0)
    def resizeEvent(self, a0):
        self._movetostartendbuffers()
        if getattr(self, "findwidget", None) is not None:
            if self.findwidget.insnap:
                self.findwidget.move(self.x() + self.width() - self.findwidget.width(), self.y() + 35)
                self.findwidgetpos = self.findwidget.pos()
        return super().resizeEvent(a0)

    #>>>Are You Sure widget<<<
    def _createAYSwidget(self):
        colour = "#EE" + self.palette().color(QPalette.ColorRole.Window).name().removeprefix("#")
        widget = paintedSimpleInfoWidget(self, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint, colour=colour, roundness=(10, 10))
        widget.setMaximumSize(int(iface.mainWindow().width() * 0.2), int(iface.mainWindow().height() * 0.2))
        widget.move(self.mapToGlobal(QPoint(int(self.width() / 2 - widget.width() / 2), int(self.height() / 2 - widget.height() / 2))))
        box = QVBoxLayout(widget)
        labelbox = QVBoxLayout()
        label = QLabel("Are you sure?")
        process = QLabel("The Process is still running...")
        hearts = QLabel("=♡" * widget.width())
        hearts.setFixedSize(widget.width(), int(widget.height() * 0.04))
        font = QFont()
        font.setPixelSize(25)
        label.setFont(font)
        font.setPixelSize(20)
        process.setFont(font)
        labelbox.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
        labelbox.addWidget(process, alignment=Qt.AlignmentFlag.AlignCenter)
        buttonbox = QHBoxLayout()
        buttonsize = QSize(int(widget.width() * 0.24), int(widget.height() * 0.12))
        yesbutton = PushButton(QSize(int(buttonsize.width() / 2), buttonsize.height()), "Yes")
        andcancelbutton = PushButton(QSize(int(buttonsize.width() * 1.2), buttonsize.height()), "Close and Cancel")
        nobutton = PushButton(buttonsize, "No")
        buttonbox.addWidget(yesbutton)
        buttonbox.addWidget(andcancelbutton)
        buttonbox.addStretch(1)
        buttonbox.addWidget(nobutton)
        box.addWidget(hearts)
        box.addLayout(labelbox)
        box.addLayout(buttonbox)
        def close(self, widget):
            if not sip.isdeleted(self):
                self.forceclose = True
                self.close()
                self.deleteLater()
            if not sip.isdeleted(widget):
                widget.close()
                widget.deleteLater()
        yesbutton.pressed.connect(lambda: QTimer.singleShot(750, lambda: close(self, widget)))
        nobutton.pressed.connect(lambda: (widget.close(), widget.deleteLater()))
        andcancelbutton.pressed.connect(lambda: (self.feedback.cancel(), QTimer.singleShot(750, lambda: close(self, widget))))
        widget.activeChange.connect(lambda active: (widget.close(), widget.deleteLater()) if not active else None)
        widget.show()
        widget.activateWindow()

#========================================================================================================#
#------------------------------------------------Icons---------------------------------------------------#
#===============================================>      <=================================================#
def rotateIcon(icon: QIcon, rotation: float, size: int = 16):
    pixmap = icon.pixmap(size, size)
    rotated = pixmap.transformed(QTransform().rotate(rotation), Qt.TransformationMode.SmoothTransformation)
    return QIcon(rotated)

def svgIcon(byteArray: QByteArray | bytes | bytearray, size = 16):
    renderer = QSvgRenderer(QByteArray(byteArray))
    if not renderer.isValid():
        return QIcon()
    pixelratio = QGuiApplication.primaryScreen().devicePixelRatio()
    px = max(1, int(size * pixelratio))
    image = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, px, px))
    painter.end()
    pixelmap = QPixmap.fromImage(image)
    pixelmap.setDevicePixelRatio(pixelratio)
    return QIcon(pixelmap)

def tickIcon(colour = "#cfcfcf"):
    return svgIcon(
    f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
    <path d="M3.2 8.8 6.7 12.2 12.8 4.5" fill="none" stroke="{colour}"
    stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""".encode("utf-8")
    )
def optionsIcon(colour = "#838282"):
    return svgIcon(
    f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
    <g fill="none" stroke="{colour}" stroke-width="1.0583">
    <path d="M15.15 5.29H16M0 5.29H10.51M6.66 10H16M0 10H2.02"/>
    <ellipse cx="12.83" cy="5.29" rx="2.32" ry="2.43"/>
    <ellipse cx="4.34" cy="10" rx="2.32" ry="2.43"/>
    </g>
    </svg>""".encode("utf-8")
    )
def closeIcon(colour = "#838282"):
    return svgIcon(
    f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16">
    <path d="M2.46 13.54 13.54 2.46M13.54 13.54 2.46 2.46" fill="none" stroke="{colour}" stroke-width="1.0583" stroke-linecap="round"/>
    </svg>""".encode("utf-8")
    )
def findIcon(colour = "#ffffff"):
    return svgIcon(
    f"""<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="{colour}" stroke-width="1.06" stroke-linecap="round"
    xmlns="http://www.w3.org/2000/svg"> <circle cx="10.5" cy="5.5" r="4.3"/> <path d="m7.5 8.5-6.2 6.2"/>
    </svg>""".encode("utf-8")
    )
def arrowIcon(colour = "#848484"):
    return svgIcon(
    f"""<svg width="16mm" height="16mm" version="1.1" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
    <g fill="none" stroke="{colour}" stroke-linecap="round" stroke-linejoin="round">
    <path d="m7.8939 0.75046v14.616" stroke-width="1.5009"/>
    <path d="m0.76098 7.5215 7.1329-6.771 7.3557 6.7875" stroke-width="1.5009"/></g>
    </svg>""".encode("utf-8")
    )
def lineNumberIcon(colour="#b8b8b8"):
    return svgIcon(
    f"""<svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">
    <g fill="none" stroke="{colour}" stroke-linecap="round">
    <path d="M4.46 2.6h10.52" stroke-width="1.85"/>
    <path d="M4.63 6.04h6.92" stroke-width="1.75"/>
    <path d="M4.46 10.39h10.52" stroke-width="1.85"/>
    <path d="M4.63 13.95h6.92" stroke-width="1.8"/> </g>
    <g fill="{colour}" font-family="Bahnschrift">
    <text x="0.05" y="7.17" font-size="8.2">1</text>
    <text x="-0.35" y="14.79" font-size="8.2">2</text></g>
    </svg>""".encode("utf-8")
    )