import cherrypy

from .common import *

# Check for slate support
try:
    from lamegame_cherrypy_slates import Slate as _Slate
    _slates = True
except ImportError:
    _slates = False

class AuthTool(cherrypy.Tool):
    """Authentication tool for CherryPy.  Called with various parameters
    to enforce different restrictions on a resource.  

    If lamegame_cherrypy_slates are installed, will automatically replace
    cherrypy.session with a slate keyed by the user's name.

    If the user is found to be logged in, cherrypy.user.slate will be set to
    the user's slate.
    """

    aliases = []

    def __init__(self):
        """Setup the tool configuration"""
        self._name = 'lg_authority'

    def register_as(self, name):
        """Adds an alias for this tool; may be called multiple times.
        e.g. cherrypy.tools.lg_authority.register_as('auth') allows things 
        like auth.groups instead of tools.lg_authority.groups in your 
        config files.
        """
        self.aliases.append(name)

    def _setup(self):
        """Hook into cherrypy.request.  Called automatically if turned on."""

        hooks = cherrypy.serving.request.hooks

        #Merge conf out of the default configuration, aliased configurations,
        #and tools configuration.
        base_dict = config.copy()
        for name in self.aliases:
            namestart = name + '.'
            lenstart = len(namestart)
            for k,v in cherrypy.request.config.items():
                if k.startswith(namestart):
                    base_dict[k[lenstart:]] = v
        conf = self._merged_args(base_dict)

        p = conf.pop('priority', 60) #Priority should be higher than session
                                     #priority, since we read the session.
        hooks.attach('before_request_body', self.check_auth, priority=p, **conf)

        if self.hasattr('initialized'):
            return
        self.initialized = True

        #Set the site specific key (Most params don't update the 
        #base config dict)
        config['site_key'] = conf.get('site_key', config['site_key'])

        if not hasattr(cherrypy, 'user'):
            cherrypy.user = cherrypy._ThreadLocalProxy('user')

    def check_auth(self, **kwargs):
        """Check for authenticated state, and setup user slate if applicable.

        Then validate permissions by group.
        """
        user = cherrypy.serving.user = cherrypy.session.get('auth', None)
        if user is not None and _slates:
            user.slate = _Slate(
                kwargs['user_slate_prefix'] + user['name']
                )
        else:
            #TODO - Determine if the alternative of storing "slate" 
            #content in session is a good idea.
            user.slate = None

        #Now check static permissions.
        groups = kwargs['groups']
        allow = False
        if 'any' in groups:
            allow = True
        elif user is not None:
            if 'auth' in groups:
                allow = True
            else:
                usergroups = user['groups']
                for group in groups:
                    if group in usergroups:
                        allow = True
                        break

        if not allow:
            denial_key = 'deny_page_anon'
            if user is not None:
                denial_key = 'deny_page_auth'

            denial = kwargs[denial_key]
            if denial is not None:
                #TODO - put current request URL in a param
                raise cherrypy.HTTPRedirect(denial)
            else:
                raise cherrypy.HTTPError(200, 'Access Denied')

