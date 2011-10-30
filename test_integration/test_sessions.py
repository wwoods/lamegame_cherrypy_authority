import cherrypy
from lg_authority.testutil import LgWebCase
import lg_authority

class TestUserSlate(LgWebCase):
    """Tests that user slates work properly."""

    @staticmethod
    def setup_server():
        @lg_authority.groups('auth')
        class Root(object):
            @cherrypy.expose
            def index(self):
                return "Logged in body"

            @cherrypy.expose
            @lg_authority.groups('any')
            def fakeLogin(self):
                cherrypy.session.login_as('admin', [ 'admin' ])
                return "Logged in as admin"

            @cherrypy.expose
            @lg_authority.groups('grue')
            def gruesOnly(self):
                return "Grues are cool!  Yeah!"

            @cherrypy.expose
            def userIdAndName(self):
                return cherrypy.user.id + ',' + cherrypy.user.name

            @cherrypy.expose
            @lg_authority.groups('any')
            def sessionSet(self, **kwargs):
                print('Updating with ' + repr(kwargs))
                cherrypy.session.update(kwargs)
                return "ok"

            @lg_authority.groups('any')
            class SessionGet(object):
                @cherrypy.expose
                def default(self, var):
                    return cherrypy.session.get(var, '(unset)')
            sessionGet = SessionGet()

        cherrypy.config.update({
            'tools.lg_authority.on': True
            ,'tools.lg_authority.site_debug': True
            ,'tools.lg_authority.site_storage': 'ram'
            })

        root = Root()
        cherrypy.tree.mount(root, '/')

    def test_authAccess(self):
        # Ensure we get a redirect notice since we're not logged in
        self.getPage("/")
        self.assertStatus('303 See Other')

        # Log in as admin (also tests 'any' group)
        self.getPage("/fakeLogin")

        # Now test that we can get to root
        self.getPage("/")
        self.assertStatus('200 OK')
        self.assertHeader('Content-Type', 'text/html;charset=utf-8')
        self.assertBody('Logged in body')

        # Test that we can't get to a group we don't have membership for
        self.getPage("/gruesOnly")
        self.assertStatus('401 Unauthorized')

    def test_sessionMigrateToUser(self):
        # Set a session var
        self.getPage("/sessionSet", body={ "a": "myValue" })
        self.getPage("/sessionGet/a")
        self.assertBody("myValue")

        # Log in as admin
        self.getPage("/fakeLogin")

        # Make sure the session var still exists
        self.getPage("/sessionGet/a")
        self.assertBody("myValue")

    def test_userInformation(self):
        # Should get rejected...
        self.getPage("/")
        self.assertStatus('303 See Other')

        # Log in as admin
        self.getPage("/fakeLogin")

        # Ensure we have our name
        self.getPage("/userIdAndName")
        self.assertBody("admin,admin")

