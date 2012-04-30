
import cherrypy
import lg_authority
from lg_authority.common import url_add_parms
from lg_authority.testutil import LgWebCase

class TestExternal(LgWebCase):
    """Test signing up for an external service."""

    @classmethod
    def setup_server(cls):
        @lg_authority.groups('auth')
        @cherrypy.config(**{
            'tools.lg_authority.on': True
            ,'tools.lg_authority.site_debug': True
            ,'tools.lg_authority.site_storage': 'ram'
            ,'tools.lg_authority.session_cookie': 'session'
        })
        class Root(object):
            def __init__(self):
                self.auth = lg_authority.AuthRoot()
            @cherrypy.expose
            def index(self):
                return cherrypy.user.name

        cls.root1 = Root()
        cls.root2 = Root()

        cherrypy.tree.mount(cls.root1, '/root1/', config={ '/': {
            'tools.lg_authority.session_cookie': 'session1'
            , 'tools.lg_authority.site_registration': 'open'
        }})
        cherrypy.tree.mount(cls.root2, '/root2/', config={ '/': {
            'tools.lg_authority.session_cookie': 'session2'
            , 'tools.lg_authority.site_registration': 'external'
            , 'tools.lg_authority.site_registration_conf': {
                'open_id': cherrypy.url('/root1/auth/openid/')
                , 'logout': cherrypy.url('/root1/auth/logout')
            }
        }})

    def setUp(self):
        LgWebCase.setUp(self)

    def registerWithOpen(self, username):
        # Reset lg_authority with root1's site config
        cherrypy.tools.lg_authority.reset()
        self.getPage("/root1/auth/login_password/", method='POST'
            , body = { 'username': 'admin', 'password': 'admin' }
        )
        print("Admin login result: " + self.body)
        self.getPage("/root1/auth/admin/edit_user_create?userName=" 
                + username
        )
        self.getPage("/root1/auth/logout")
        self.getPage("/root1/auth/login_password/", method='POST'
            , body = { 'username': username, 'password': 'password' }
        )
        print("User login result: " + self.body)

    def loginExternal(self, uname):
        # Reset lg_authority with root2's site config
        cherrypy.tools.lg_authority.reset()
        self.getPage("/root2/auth/login")
        print("Login result: " + self.body)
        self.assertStatus(303) # See other
        nextUrl = dict(self.headers)['Location']
        self.assertTrue('root2/auth/login_openid' in nextUrl)

        # Fake out a successful openID login
        loginOpenId = self.root2.auth.login_openid
        @cherrypy.expose
        def fakeFinish(**kwargs):
            return loginOpenId.auth_root.login_openid_response(
                url=cherrypy.url('/' + uname)
                ,redirect=cherrypy.url('/')
                ,user_params={ 'nickname': uname, 'email': uname }
            )
        oldFinish = loginOpenId.finish
        loginOpenId.finish = fakeFinish
        try:
            self.getPage('/root2/auth/login_openid/finish')
        finally:
            loginOpenId.finish = oldFinish

        self.assertStatus(303) # See other
        nextUrl = dict(self.headers)['Location']
        self.assertTrue('new_account' in nextUrl)

        # Make the account
        self.getPage(nextUrl)
        print("GOT BODY : " + self.body)

    def test_external(self):
        """Try using just any old username as external source"""
        uname = 'hiImAUser'
        self.loginExternal(uname)

        # Make sure the login _really_ worked
        self.getPage("/root2/")
        self.assertBody(uname)

    def test_externalWithEmail(self):
        """Try using an e-mail address as an external username."""
        uname = 'hi@motown.com'
        self.loginExternal(uname)

        # Make sure the login _really_ worked
        self.getPage("/root2/")
        self.assertBody(uname)

