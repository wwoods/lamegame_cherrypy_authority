"""LameGame Productions' CherryPy Authentication and Authorization Framework
"""

import cherrypy
from .tools import AuthTool
from .common import groups, check_groups, check_groups_all, deny_access
from .authroot import AuthRoot

tool = cherrypy.tools.lg_authority = AuthTool()

del AuthTool

