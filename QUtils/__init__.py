"""QUtils"""
"""            lllll                              Aqua <3
         llll lllllll        ll‡                     
         lllllllllllll‡l     l‡ll‡l                  
         lllllllll¯`````l‡ll ll¯`*‡                  
         l‡ll`"lll¯````````"l*`````ll                
         ll````````````````````````l‡               
       ‡l"```````````````````¯ll‡"`ll               
 ‡ll   l‡"```````````````````¯‡l l‡l‡               
 l‡l‡l ‡l"```````````````"l3gü`` ll                 
ll```¯l¯``````````````lll‡gggggü‡l                  
ll``````````````¯l6ggggggggggggl`*‡ll‡l````         
 ‡l*````````````lggggg‡llll3gggl``````¯ggg3````     
 l‡*`````*l``gggÇllllllll‡gggÇl¯`````gggggggl``     
   l‡ll‡l‡ l‡l3ggggg3llll‡gggü```‡ügggggggggl``     
       l‡l ll```lggggggggÞ`````ügggggggggggggg"`    
           ‡l`````````ÞggGl*`‡gggggggggggggggg¯`    
     ll‡lll`````````*llllllllllÇgggggü3`````````    
       l‡"````````3g6ülllll3gggl`‡ü``````           
         l‡ll```lgggggggggggggggg*`                 
           l‡`¯ggg3`6gggggggggggg6ü``               
         ````ggggg3`6gggggggggggggg"`````           
     ````‡ügggggÞü*`6ggggggggggggggggü3``````       
     ``üggggggggü`*üÞggggggggggggggüü`"lll¯``       
       ``Çgggggg6`3gggggggggggggggg"`lllll¯``       
       ````GggGül`3gggggggggggggg6ü``lll¯``         
         ````gÞ`lggggggggggggggl```  ``````         
             `````*üÞggggGü‡``````                  
                  ````````````                      
                    ````gggÇ``                      
                      ``lll*``                      
                    ``*llll*``                      
                    ````````                            """
#=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=

__author__ = "Roxanne Minerals"

import importlib, sys

def reload():
  for module in ("Storage", "ErrorHandling", "QVariantHook", "Legacy", "Widgets", "Console", "Processing", "ProcessingAlgorithms", "Experimental"):
    name = f"{__name__}.{module}"
    if name in sys.modules:
      importlib.reload(sys.modules[name])
      globals().update({key: val for key, val in vars(sys.modules[name]).items() if not key.startswith("_")})

from .Processing import *
from .ProcessingAlgorithms import *

#=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=♡=
#Repository:
#https://github.com/elvatro-0/QUtils

# QUtils - a fluent processing framework for QGIS map layers
# Copyright (C) 2026  Roxanne Minerals
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.