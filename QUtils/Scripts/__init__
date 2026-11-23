"""Processing Algorithm Scripts"""

import sys, importlib

__author__ = "Roxanne Minerals"
__version__ = 1.1

def reload():
  for module in ("ProcessingAlgorithms", "ScriptHelper"):
    name = f"{__name__}.{module}"
    if name in sys.modules:
      importlib.reload(sys.modules[name])
      globals().update({key: val for key, val in vars(sys.modules[name]).items() if not key.startswith("_")})