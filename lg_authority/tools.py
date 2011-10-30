import cherrypy

from .common import *

from . import slates
from .slates import storage, Slate
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

        MUST be called BEFORE any config is set to take effect.

        e.g. cherrypy.tools.lg_authority.register_as('auth') allows things 
        like auth.groups instead of tools.lg_authority.groups in your 
        config files.
        """
        raise NotImplementedError()
        self.aliases.append(name)
        def gen_aliaser(k, v):
            cherrypy.config['tools.lg_authority.' + k] = v
        def req_handler():
            post_conf = getattr(cherrypy.serving, 'lg_authority_aliased', None)
            if post_conf is not None:
                log('Applying: {0}'.format(post_conf))
                cherrypy.request.namespaces(post_conf)
                log('New config: {0}'.format(cherrypy.request.config))
        def req_aliaser(k, v):
            import traceback
            traceback.print_stack()
            log('Aliasing {0}, {1}'.format(k,v))
            temp = getattr(cherrypy.serving, 'lg_authority_aliased', None)
            if temp is None:
                temp = {}
                cherrypy.serving.lg_authority_aliased = temp
                cherrypy.request.hooks.attach('on_start_resource', req_handler)
                log('Hook attached for aliases')
            temp['tools.lg_authority.' + k] = v
        cherrypy.config.namespaces[name] = gen_aliaser
        cherrypy.Application.namespaces[name] = req_aliaser
        cherrypy.Application.request_class.namespaces[name] = req_aliaser

    def _merged_args(self, auth_args=None):
        """Since we have aliases and a base config dict, we merge our
        own arguments.

        auth_args may be specified for debugging from a prompt.
        """
        #Merge conf out of the default configuration, aliased configurations,
        #and tools configuration.
        base_dict = config.copy()
        if auth_args is None:
            base_dict = cherrypy.Tool._merged_args(self, base_dict)
        else:
            base_dict.update(auth_args)

        return base_dict

    def _setup(self):
        """Hook into cherrypy.request.  Called automatically if turned on."""

        hooks = cherrypy.serving.request.hooks

        conf = self._merged_args()
        #Store request config for non-tools as well
        cherrypy.serving.lg_authority = conf

        #Initialization stuff
        if not getattr(self, 'initialized', False):
            self.initialized = True
            try:
                self._setup_initialize(conf)
            except:
                self.initialized = False
                raise

        p = conf.pop('priority', 60) #Priority should be higher than session
                                     #priority, since we read the session.
        if conf['override_sessions']:
            hooks.attach('before_request_body', slates.init_session, priority=p-10, **conf)
            hooks.attach('before_finalize', slates.send_session_cookie, priority=p, **conf)
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
            #Start with a bang!
            cleanup()

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
        if reg_method is not None:
            reg_conf = config['site_registration_conf']
            config.registrar = registration.get_registrar(reg_method)(reg_conf)
        else:
            config.registrar = None

    def check_auth(self, **kwargs):
        """Check for authenticated state, and setup user slate if applicable.

        Then validate permissions by group.
        """
        #Make the user into an object for conveniences
        user = cherrypy.session.get('auth', None)
        config.auth.serve_user_from_dict(user)

        if cherrypy.user:
            #Move the session over to the user session
            cherrypy.serving.session = Slate('session_user', cherrypy.user.id)

        #Now validate static permissions, if any
        access_groups = kwargs['groups']
        if access_groups is not None:
            if len(access_groups) > 0 and access_groups[0] == 'all:':
                access_groups = access_groups[1:]
                require_groups_all(*access_groups)
            else:
                require_groups(*access_groups)

