import cherrypy
from lg_authority.testutil import LgWebCase
import lg_authority

class TestAdmin(LgWebCase):
    """Test the admin functionality"""

    @staticmethod
    def setup_server():
        @lg_authority.groups('auth')
        class Root(object):
            auth = lg_authority.AuthRoot()

            @cherrypy.expose
            def index(self):
                return "ok"

        cherrypy.config.update({
            'tools.lg_authority.on': True
            ,'tools.lg_authority.site_debug': True
            ,'tools.lg_authority.site_storage': 'ram'
        })

        root = Root()
        cherrypy.tree.mount(root, '/')


    def setUp(self):
        LgWebCase.setUp(self)
        self.getPage("/auth/login_password/", method='POST'
            , body = { 'username': 'admin', 'password': 'admin' }
        )


    def test_index(self):
        self.getPage("/auth/admin/")
        self.assertTrue('Active Users' in self.body, "Page fail: " + self.body)

