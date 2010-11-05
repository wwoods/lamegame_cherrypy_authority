"""Root for open-id server

Initially modeled after the django one:
http://github.com/openid/python-openid/blob/master/examples/djobpenid/server/views.py
"""
import cherrypy

try:
    import openid
except ImportError:
    class OpenIdServerRoot(object):
        """The OpenIdServerRoot when python-openid is not installed"""

        supported = False

        def __init__(self, *args, **kwargs):
            pass

        @cherrypy.expose
        def default(*args, **kwargs):
            return """<div class="lg_auth_form">OpenID is not supported on this server</div>"""

else:
    from .common import *

    from openid.server.server import Server, ProtocolError, CheckIDRequest, EncodingError
    from openid.server.trustroot import verifyReturnTo
    from openid.yadis.discover import DiscoveryFailure
    from openid.consumer.discover import OPENID_IDP_2_0_TYPE
    from openid.extensions import sreg, pape
    from openid.fetchers import HTTPFetchingError
    from .openidstore import OpenIdStore

    class OpenIdServerRoot(object):
        """A cherrypy object that exposes the user to the provided service.
        Is presumed to be mounted at {AuthRoot}/openid
        """

        supported = True

        static_path = '../static'
        store = OpenIdStore('openid-s')

        def __init__(self, auth_root):
            self.auth_root = auth_root

        def get_server(self):
            return Server(self.store, self.get_endpoint())

        def set_request(self, openid_request):
            """Store the openid request in session state"""
            cherrypy.session['openid_request'] = openid_request

        def get_request(self):
            """Retrieve stored openid request from session state"""
            return cherrypy.session['openid_request']

        def get_endpoint(self):
            """Get the endpoint URL from one of the other openid server
            URLs.
            """
            #TODO - Look at if this SHOULD enforce scheme="https".
            return cherrypy.url('endpoint')

        def get_user_url(self):
            """Retrieve the absolute URL identifying this user"""
            if not cherrypy.user:
                return None
            return cherrypy.url('user/' + cherrypy.user.name)

        @cherrypy.expose
        def index(self):
            templ = get_template('openid_server_index.html')
            return templ.format(xrds=cherrypy.url('xrds'))

        @cherrypy.expose
        def xrds(self):
            templ = get_template('openid_xrds.xml')
            return templ.format(type=OPENID_IDP_2_0_TYPE, endpoint=self.get_endpoint())

        class UserRoot(object):
            """Interestingly, even though all users need their own URL,
            I think we can treat them all the same.
            """

            @cherrypy.expose
            def default(self, username):
                templ = get_template('openid_server_idpage.html')
                return templ.format(server=cherrypy.url('../endpoint'))

        user = UserRoot()

        @cherrypy.expose
        def trust(self):
            templ = get_template('openid_server_trust.html')
            return templ.format(trust_handler=cherrypy.url('trust_result'))

        @cherrypy.expose
        def endpoint(self, **kwargs):
            s = self.get_server()

            try:
                openid_request = s.decodeRequest(kwargs)
            except ProtocolError as why:
                templ = get_template('openid_server_endpoint.html')
                return templ.format(error=str(why))

            if openid_request is None:
                templ = get_template('openid_server_endpoint.html')
                return templ.format(error='No request')

            log('OpenID Server - Request mode {0}'.format(openid_request.mode))
            if openid_request.mode in ["checkid_immediate", "checkid_setup"]:
                return self.handleCheckIDRequest(openid_request)
            else:
                openid_response = s.handleRequest(openid_request)
                return self.displayResponse(openid_response)

        @cherrypy.expose
        def resume(self):
            return self.handleCheckIDRequest(self.get_request())

        def handleCheckIDRequest(self, openid_request):
            if not cherrypy.user:
                self.set_request(openid_request)
                raise cherrypy.HTTPRedirect(
                    url_add_parms(
                        '../login'
                        , { 'redirect': cherrypy.url('resume'), 'error': 'Please log in to use your OpenID' }
                        )
                    )

            if not openid_request.idSelect():
                id_url = self.get_user_url()

                #Confirm that this server can vouch for that ID
                if id_url != openid_request.identity:
                    error = ProtocolError(
                        openid_request.message
                        ,"This server cannot verify the URL {0}".format(openid_request.identity)
                        )
                    return self.displayResponse(error)

            if openid_request.immediate:
                #TODO - This is where we would do something for users that 
                #are already logged in
                openid_response = openid_request.answer(False)
                return self.displayResponse(openid_response)
            else:
                self.set_request(openid_request)
                return self.showDecidePage(openid_request)

        def showDecidePage(self, openid_request):
            """Let the user decide if they want to trust the consumer."""
            trust_root = openid_request.trust_root
            return_to = openid_request.return_to

            try:
                trust_root_valid = verifyReturnTo(trust_root, return_to)
            except DiscoveryFailure as err:
                trust_root_valid = "DISCOVERY_FAILED"
            except HTTPFetchingError as err:
                trust_root_valid = "Unreachable"

            if trust_root_valid != True:
                return '<div class="lg_auth_form">The trust root / return is not valid.  Denying authentication.  Reason: {0}</div>'.format(trust_root_valid)

            pape_request = pape.Request.fromOpenIDRequest(openid_request)

            templ = get_template('openid_server_trust.html')
            return templ.format(
                trust_root=trust_root
                ,trust_handler=cherrypy.url('trust_result')
                ,trust_root_valid=trust_root_valid
                ,pape_request=pape_request
                )

        @cherrypy.expose
        def trust_result(self, **kwargs):
            openid_request = self.get_request()

            response_id = self.get_user_url()

            allowed = 'allow' in kwargs

            openid_response = openid_request.answer(
                allowed
                , identity=response_id
                )

            if allowed:
                sreg_data = {} #TODO - link sreg data to user data (except
                               #be sure to remove auth_ stuff)

                sreg_req = sreg.SRegRequest.fromOpenIDRequest(openid_request)
                sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
                openid_response.addExtension(sreg_resp)

                pape_response = pape.Response()
                pape_response.setAuthLevel(pape.LEVELS_NIST, 0)
                openid_response.addExtension(pape_response)

            return self.displayResponse(openid_response)

        def displayResponse(self, openid_response):
            s = self.get_server()

            try:
                webr = s.encodeResponse(openid_response)
            except EncodingError as why:
                text = why.response.encodeToKVForm()
                templ = get_template('openid_server_endpoint.html')
                return templ.format(
                    error=text
                    )

            body = webr.body
            cherrypy.response.status = webr.code
            for header,value in webr.headers.items():
                cherrypy.response.headers[header] = value
            return body

