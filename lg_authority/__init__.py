from .common import *
from .tools import *

from . import passwords

from .authroot import AuthRoot

tool = cherrypy.tools.lg_authority = AuthTool()

