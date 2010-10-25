"""LameGame Productions' cherrypy slates tool.

Usage: Put tools.lg_slates.on = True in the [global] section in your config file to enable this tool.

tools.lg_slates.storage_type may be specified to change the storage medium (defaults to 'ram' for RamStorage)
"""

__all__ = [ 'Slate', 'init_session' ]
__author__ = 'Walt Woods'

import cherrypy
from ..common import *
from .slates import Slate
from .session import init_session

#Seed global config with Slate variable
config.Slate = Slate

