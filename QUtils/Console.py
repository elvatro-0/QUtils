"""
Allows processing to work in the QGIS python console.\n
Call createContextAndFeedback()
"""

from qgis.core import QgsProcessingContext, QgsProcessingUtils
from qgis.gui import QgisInterface
from dataclasses import dataclass
from typing import TYPE_CHECKING
import traceback

from .Widgets import *

__author__ = "Roxanne Minerals"

#========================================================================================================#
#--------------------------------------------Python Console----------------------------------------------#
#===============================================>      <=================================================#

class Feedback(QgsProcessingFeedback):
    messageLogged = pyqtSignal(str, str)
    finished = pyqtSignal(bool)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget: FeedbackWidget = None
        self.isfinished = False

    def _log(self, text, style, printtoconsole = False):
        if printtoconsole:
            print(text, file=sys.stderr)
        self.messageLogged.emit(text, style)

    def pushInfo(self, info):
        super().pushInfo(info)
        style = "{}"
        self._log(info, style)

    def pushWarning(self, warning):
        super().pushWarning(warning)
        style = '<span style="color:#b8860b">{}</span>'
        self._log(warning, style, True)

    def pushCommandInfo(self, info):
        super().pushCommandInfo(info)
        style = f'<span style="font-family:\'{QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()}\'; white-space:pre">{{}}</span>'
        self._log(info, style)

    def pushDebugInfo(self, info):
        super().pushDebugInfo(info)
        style = '<span style="color:#777">{}</span>'
        self._log(info, style)

    def pushConsoleInfo(self, info):
        super().pushConsoleInfo(info)
        style = f'<span style="font-family:\'{QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont).family()}\'; color:#777; white-space:pre">{{}}</span>'
        self._log(info, style, True)

    def reportError(self, error, fatalError=False):
        super().reportError(error, fatalError)
        style = '<span style="color:red">{}</span>'
        self._log(error, style, True)

    def complete(self):
        self.isfinished = True
        self.finished.emit(True)
    def exception(self, exc_type, exc_value, exc_traceback):
        self.isfinished = True
        self.finished.emit(False)
        if not self.isCanceled():
            self.reportError(f"{exc_type.__name__}: {exc_value}\n{'=' * 35}=\n{''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))}", True)
        else: print("Canceled")

def loadLayers(context: QgsProcessingContext):
    for layer, detials in context.layersToLoadOnCompletion().items():
        detials.project.addMapLayer(QgsProcessingUtils.mapLayerFromString(layer, context))

def createContextAndFeedback(showWidget = True, withtabs = False):
    context = QgsProcessingContext()
    context.setProject(QgsProject.instance())
    feedback = Feedback()
    context.setFeedback(feedback)
    feedback.finished.connect(lambda: loadLayers(context))
    if showWidget:
        FeedbackWidget(feedback, withtabs=withtabs)
        feedback.widget.show()
    return context, feedback

if TYPE_CHECKING:
    @dataclass
    class iface(QgisInterface):
        pass