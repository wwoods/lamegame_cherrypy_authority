import cherrypy
from lg_authority.testutil import LgWebCase
import lg_authority
import re

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


    def test_user_create(self):
        un = 'myUser'
        self.getPage("/auth/admin/edit_user?userName=" + un)
        self.assertTrue('User does not exist' in self.body, "Did not say that "
            + "user does not exist"
        )
        self.assertTrue('edit_user_create?userName=' + un in self.body, "Did not "
            + "offer create user link"
        )

        self.getPage("/auth/admin/edit_user_create?userName=" + un)
        self.assertStatus("303 See Other")
        expectedBody = """This resource can be found at <a href='http://127.0.0.1:54583/auth/admin/edit_user?userId=ramStore_X'>http://127.0.0.1:54583/auth/admin/edit_user?userId=ramStore_X</a>."""
        actualBody = re.sub('ramStore_\d+', 'ramStore_X', self.body)
        self.assertEqual(expectedBody, actualBody)


    def test_index(self):
        self.getPage("/auth/admin/")
        self.assertTrue('Active Users' in self.body, "Page fail: " + self.body)

