"""
Custom, pretty error handling.\n
Mainly for internal use.
"""

from qgis.core import QgsProcessingFeedback, QgsProcessingException
import functools, inspect, traceback

__author__ = "Roxanne Minerals"

#========================================================================================================#
#---------------------------------------------Error Handler----------------------------------------------#
#===============================================>      <=================================================#

#I want error messages to look pretty
class QUtilsExceptions(QgsProcessingException):
    def __init__(self, message: str = None, feedback: QgsProcessingFeedback | None = None):
        super().__init__(message)
        self.message = "" if message == None else message
        self.feedback = feedback
    @staticmethod
    def CriticalError(message: str = None, feedback: QgsProcessingFeedback = None):
        raise QUtilsExceptions(message, feedback)

    def ErrorHandling(func):
        @functools.wraps(func)
        def stack_tracer(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except QUtilsExceptions as _except:
                if _except.feedback is None:
                    feedback = None
                    for fb in inspect.signature(func).bind(*args, **kwargs).arguments.values():
                        if isinstance(fb, QgsProcessingFeedback):
                            feedback = fb
                            break
                else:
                    feedback = _except.feedback

                feedback.reportError(
                "\n QUtils Critical Error\n"
                f"{'=♡'*35}=\n"
                f"{func.__name__} Error\n"
                f"Traceback:\n{''.join(traceback.format_list(traceback.extract_stack()[:-1]))}"
                ) if feedback != None else None
                raise QgsProcessingException(f"{_except.message}\n{'=♡'*35}=\n")
        return stack_tracer