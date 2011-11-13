import cherrypy
from lg_authority.testutil import LgWebCase
import lg_authority

class TestLogin(LgWebCase):
    """Test every different login type."""

    @staticmethod
    def setup_server():
        @lg_authority.groups('auth')
        class Root(object):
            auth = lg_authority.AuthRoot()

            @cherrypy.expose
            def index(self):
                return "{0} / {1}".format(cherrypy.user.id, cherrypy.user.name)

        cherrypy.config.update({
            'tools.lg_authority.on': True
            ,'tools.lg_authority.site_debug': True
            ,'tools.lg_authority.site_storage': 'pymongo'
            ,'tools.lg_authority.site_storage_conf': {
                'db': 'lg_auth_testroot'
                }
            ,'tools.lg_authority.session_cookie': 'not_standard' #not std for 
                                                                 #regression
          })

        root = Root()
        cherrypy.tree.mount(root, '/')
        
    def test_nonexistLogin(self):
        self.getPage("/auth/login_password", method='POST'
            , body = { 'username': 'blah', 'password': 'hi' }
        )
        self.assertTrue('Invalid+Credentials' in self.body, "Did not show Invalid Credentials")
        self.assertStatus('303 See Other')

    def test_passwordLogin(self):
        self.getPage("/auth/login_password", method='POST'
            , body = { 'username': 'admin', 'password': 'admin' }
        )

        self.assertBody("This resource can be found at <a href='http://127.0.0.1:54583/'>http://127.0.0.1:54583/</a>.")

        self.getPage("/")
        # We're expecting an ID first, not our username.
        self.assertStatus('200 OK')
        self.assertNotEqual("admin / admin", self.body)
        self.assertTrue(' / admin' in self.body, "User name not displayed")

