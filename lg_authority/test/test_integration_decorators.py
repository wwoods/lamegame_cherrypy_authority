import cherrypy
from lg_authority.testutil import LgWebCase
import lg_authority
import re

class TestDecorators(LgWebCase):
    """Test the functionality of our decorators"""

    @staticmethod
    def setup_server():
        @lg_authority.groups('auth')
        class Root(object):
            auth = lg_authority.AuthRoot()

            @lg_authority.deny_no_redirect
            class Deny401(object):
                @cherrypy.expose
                def index(self):
                    return "index"

                @cherrypy.expose
                @lg_authority.groups('blah')
                def invalid(self):
                    return "fail"
            deny401 = Deny401()
        cherrypy.config.update({
            'tools.lg_authority.on': True
            ,'tools.lg_authority.site_debug': True
            ,'tools.lg_authority.site_storage': 'ram'
        })

        root = Root()
        cherrypy.tree.mount(root, '/')


    def setUp(self):
        LgWebCase.setUp(self)
    

    def test_deny_no_redirect_anon(self):
        self.getPage("/deny401/")
        self.assertStatus("401 Unauthorized")

        self._loginAdmin()
        self.getPage("/deny401/")
        self.assertStatus('200 OK')
        self.assertBody('index')


    def test_deny_no_redirect_auth(self):
        self._loginAdmin()
        self.getPage("/deny401/invalid")
        self.assertStatus('401 Unauthorized')


    def _loginAdmin(self):
        """Logs in as the admin user"""
        self.getPage("/auth/login_password/", method="POST"
            , body = { 'username': 'admin', 'password': 'admin' }
        )
        

