
from pprint import pprint
import re
from urllib import unquote

import cherrypy
from lg_authority.testutil import LgWebCase
import lg_authority
from lg_authority.common import url_add_parms

class TestOpenId(LgWebCase):
    """Test the OpenID functionality"""

    @staticmethod
    def setup_server():
        @lg_authority.groups('auth')
        @cherrypy.config(**{
            'tools.lg_authority.on': True
            ,'tools.lg_authority.site_debug': True
            ,'tools.lg_authority.site_storage': 'ram'
            ,'tools.lg_authority.session_cookie': 'session'
        })
        class Root(object):
            def __init__(self):
                # This must be in init() or the two instances will share
                # an AuthRoot!
                self.auth = lg_authority.AuthRoot()

            @cherrypy.expose
            def index(self):
                return cherrypy.request.config[
                    'tools.lg_authority.session_cookie'
                ]

            @cherrypy.expose
            @lg_authority.groups('any')
            def blah(self):
                cherrypy.session['hi'] = 'there'
                return 'ok'

        root1 = Root()
        root2 = Root()

        cherrypy.tree.mount(root1, '/root1/', config={ '/': {
            'tools.lg_authority.session_cookie': 'session1'
        }})
        cherrypy.tree.mount(root2, '/root2/', config={ '/': {
            'tools.lg_authority.session_cookie': 'session2'
        }})


    def setUp(self):
        LgWebCase.setUp(self)


    def login(self, rootPath):
        # Login as admin on the given root
        self.getPage(rootPath + "/auth/login_password/", method='POST'
            , body = { 'username': 'admin', 'password': 'admin' }
        )


    def test_root1(self):
        # Pre-test to make sure that root1 works
        self.login('/root1')
        self.getPage('/root1/')
        self.assertStatus(200)
        self.assertBody('session1')


    def test_root2(self):
        # Pre-test to make sure that root2 works
        self.login('/root2')
        self.getPage('/root2/')
        self.assertStatus(200)
        self.assertBody('session2')


    def test_root1_and_2(self):
        # Ensure that root1 and root2 are on different sessions
        self.login('/root1')
        self.getPage('/root2/')
        self.assertStatus(303)


    def _test_openid(self, loginBefore):
        # Test a basic openID request from root2 to root1...
        # loginBefore is used since this is really two tests.  The code paths
        # are different depending on if we're already logged into root1 or
        # not (the open ID server)

        if loginBefore:
            self.login('/root1')
            print("Logged in first")

        urlTarget = cherrypy.url('/root1/auth/openid/')
        print("URL for OpenID: " + urlTarget)

        clientHopInitial = url_add_parms(
            '/root2/auth/login_openid/'
            , {
                'url': urlTarget
                , 'redirect': cherrypy.url('/root2/')
            }
        )
        print("Going to client hop " + clientHopInitial)

        self.getPage(clientHopInitial)
        self.assertStatus(200) # OK

        # Parse
        body = self.body
        self.assertTrue('lg_auth_form_autosubmit' in body)
        formUrl = re.search(r'<form[^>]+action="([^"]+)"', body)
        formUrl = formUrl.group(1)
        formParams = re.findall(
            r'<input[^>]+name="([^"]+)"[^>]+value="([^"]+)"'
            , body
        )
        # The formParams are sent to us in HTML encoding... obviously... since
        # we just parsed a form body... so unencode them before using them.
        parms = dict([ (a,b) for (a,b) in formParams ])
        for k,v in parms.items():
            # I love stack overflow:
            # http://stackoverflow.com/questions/275174/how-do-i-perform-html-decoding-encoding-using-python-django
            parms[k] = (
                v
                .replace('&#39;', "'")
                .replace('&quot;', '"')
                .replace('&gt;', '>')
                .replace('&lt;', '<')
                .replace('&amp;', '&')
            )
        print("Form parameters:")
        pprint(parms)

        self.getPage(formUrl, method='POST', body=parms)
        if not loginBefore:
            # We're not logged in yet, so go through that business
            self.assertStatus(303) # See other
            self.assertTrue('Please+log+in' in self.body)
            self.assertTrue('OpenID' in self.body)

            # Parse the resumeUrl out of our login redirect
            resumeUrl = re.search(r'redirect=([^&]+)', self.body).group(1)
            resumeUrl = unquote(resumeUrl)
            print("Result of form was " + resumeUrl)

            self.login('/root1')
            print("Logged in, hopping to resume at " + resumeUrl)

            self.getPage(resumeUrl)
            self.assertStatus(303)
            trustUrl = dict(self.headers)['Location']
        else:
            self.assertStatus(303) # See other
            trustUrl = dict(self.headers)['Location']
            print("Should already be logged in... straight to trust")

        print("Got trust url, hopping to " + trustUrl)
        self.getPage(trustUrl)
        self.assertStatus(302) # Found
        print("Got headers: ")
        pprint(self.headers)

        finishUrl = dict(self.headers)['Location']
        print("Got finish url " + finishUrl)
        self.assertTrue('login_openid/finish' in finishUrl)

        self.getPage(finishUrl)
        self.assertStatus(303)
        # If we get an unknown openID, we're good to go!
        self.assertTrue('error=Unknown+OpenID' in self.body)


    def test_openid_loggedInBefore(self):
        self._test_openid(True)


    def test_openid_logInDuringAuth(self):
        self._test_openid(False)


