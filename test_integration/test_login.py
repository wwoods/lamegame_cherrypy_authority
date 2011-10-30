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
                return "Hello!"

        cherrypy.config.update({
            'tools.lg_authority.on': True
            ,'tools.lg_authority.site_debug': True
            ,'tools.lg_authority.site_storage': 'pymongo'
            ,'tools.lg_authority.site_storage_conf': {
                'db': 'lg_auth_testroot'
                }
            })

        root = Root()
        cherrypy.tree.mount(root, '/')

    def test_passwordLogin(self):
        self.getPage("/auth/login_password", method='POST'
            , body = { 'username': 'admin', 'password': 'admin' }
            )

        self.assertBody("This resource can be found at <a href='http://127.0.0.1:8080/'>http://127.0.0.1:8080/</a>.")

