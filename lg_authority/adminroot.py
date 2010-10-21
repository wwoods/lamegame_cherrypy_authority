"""Administration functions for lg_authority"""

from .common import *

@groups('admin')
class AdminRoot(object):
    @cherrypy.expose
    def index(self):
        return ":O You're an admin!"

