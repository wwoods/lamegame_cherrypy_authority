"""LameGame Productions' CherryPy Authentication and Authorization Framework
"""

import cherrypy
from .tools import AuthTool
from .common import groups, check_groups, check_groups_all, require_groups, require_groups_all, deny_access, get_user_groups, get_user_groups_named, AuthError
from .authroot import AuthRoot

tool = cherrypy.tools.lg_authority = AuthTool()
from .slates.slates import Slate

del AuthTool

