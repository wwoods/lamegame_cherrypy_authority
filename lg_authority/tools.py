import cherrypy

from .common import *

from . import slates
from .slates import storage
from .authinterface import AuthInterface
from . import registration

class AuthTool(cherrypy.Tool):
    """Authentication tool for CherryPy.  Called with various parameters
    to enforce different restrictions on a resource.  

    If the user is found to be logged in, cherrypy.user.slate will be set to
    the user's slate if lamegame_cherrypy_slates is also installed.  Otherwise,
    cherrypy.user.slate will be set to cherrypy.session['slate'].
    """

    aliases = []

    def __init__(self):
        """Setup the tool configuration"""
        self._name = 'lg_authority'

    def reset(self):
        """Reset the initialized variable, so that the next request reloads
        lg_authority's configuration.  Useful for testing.
        """
        del self.initialized

    def register_as(self, name):
        """Adds an alias for this tool; may be called multiple times.
        e.g. cherrypy.tools.lg_authority.register_as('auth') allows things 
        like auth.groups instead of tools.lg_authority.groups in your 
        config files.
        """
        self.aliases.append(name)

    def _merged_args(self):
        """Since we have aliases and a base config dict, we merge our
        own arguments.
        """
        #Merge conf out of the default configuration, aliased configurations,
        #and tools configuration.
        base_dict = config.copy()
        for name in self.aliases:
            namestart = name + '.'
            lenstart = len(namestart)
            for k,v in cherrypy.request.config.items():
                if k.startswith(namestart):
                    base_dict[k[lenstart:]] = v
        return cherrypy.Tool._merged_args(self, base_dict)

    def _setup(self):
        """Hook into cherrypy.request.  Called automatically if turned on."""

        hooks = cherrypy.serving.request.hooks

        conf = self._merged_args()
        #Store request config for non-tools as well
        cherrypy.serving.lg_authority = conf

        #Initialization stuff
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self._setup_initialize(conf)

        p = conf.pop('priority', 60) #Priority should be higher than session
                                     #priority, since we read the session.
        if conf['override_sessions']:
            hooks.attach('before_request_body', slates.init_session, priority=p-10, **conf)
        hooks.attach('before_request_body', self.check_auth, priority=p, **conf)

    def _setup_initialize(self, conf):
        #Set the site specific settings in config (Most params don't update the 
        #base config dict)
        for k,v in conf.items():
            if k.startswith('site_'):
                config[k] = v

        log.enabled = conf['site_debug']

        #Set up cherrypy.session?  We do this even if we're not overriding
        #sessions, since it plays nice with the builtin sessions module.
        if not hasattr(cherrypy, 'session'):
            cherrypy.session = cherrypy._ThreadLocalProxy('session')

        #Set up cherrypy.user
        if not hasattr(cherrypy, 'user'):
            cherrypy.user = cherrypy._ThreadLocalProxy('user')

        #Setup slate storage medium
        self.storage_type = conf['site_storage']
        self.storage_class = storage.get_storage_class(self.storage_type)

        config.storage_class = self.storage_class
        log('Found: ' + str(config.storage_class))
        config.storage_class.setup(conf['site_storage_conf'])

        #Setup monitor thread...
        if getattr(config, 'storage_cleanup_thread', None) is not None:
            config.storage_cleanup_thread.stop()
            config.storage_cleanup_thread.unsubscribe()
            config.storage_cleanup_thread = None
        clean_freq = conf['site_storage_clean_freq']
        if clean_freq:
            def cleanup():
                config.storage_class.clean_up()
            config.storage_cleanup_thread = cherrypy.process.plugins.Monitor(
                cherrypy.engine, cleanup, clean_freq * 60
                ,name = 'Slate Storage Cleanup'
                )
            config.storage_cleanup_thread.subscribe()
            config.storage_cleanup_thread.start()

        #Set up the authentication system interface
        config.auth = AuthInterface()

        #Add config groups/users
        for name,data in config['site_group_list'].items():
            try:
                config.auth.group_create(name, data)
            except AuthError:
                pass
        for name,data in config['site_user_list'].items():
            try:
                config.auth.user_create(name, data)
            except AuthError:
                pass
                
        #Set up registration mechanism
        reg_method = config['site_registration']
        #TODO registration method stuff...

    def check_auth(self, **kwargs):
        """Check for authenticated state, and setup user slate if applicable.

        Then validate permissions by group.
        """
        #Make the user into an object for conveniences
        user = cherrypy.session.get('auth', None)
        user = user and ConfigDict(user)
        cherrypy.serving.user = user
        if user is not None:
            user.name = user['name'] #Convenience
            user.groups = user['groups'] #Convenience
            user.slate = slates.Slate(
                kwargs['user_slate_section'], user['name']
                )

        #Now validate static permissions, if any
        access_groups = kwargs['groups']
        if access_groups is not None:
            if len(access_groups) > 0 and access_groups[0] == 'all:':
                access_groups = access_groups[1:]
                check_groups_all(*access_groups)
            else:
                check_groups(*access_groups)

