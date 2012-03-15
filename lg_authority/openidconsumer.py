"""Root for open-id client (consumer)

Initially modeled after the django one:
http://github.com/openid/python-openid/blob/master/examples/djopenid/consumer/views.py
"""
import cherrypy

try:
    import openid
except ImportError:
    class OpenIdConsumerRoot(object):
        """The OpenIdConsumerRoot when python-openid is not installed OR lg_slates is not installed."""

        supported = False
        
        def __init__(self, *args, **kwargs):
            pass

        @cherrypy.expose
        def default(*args, **kwargs):
            return """<div class="lg_auth_form">OpenID is not supported on this server</div>"""

else:
    from .common import *

    from openid.consumer import consumer
    from openid.consumer.discover import DiscoveryFailure
    from openid.extensions import ax, pape, sreg
    from openid.yadis.constants import YADIS_HEADER_NAME, YADIS_CONTENT_TYPE
    from openid.server.trustroot import RP_RETURN_TO_URL_TYPE
    from .openidstore import OpenIdStore

    PAPE_POLICIES = [
        pape.AUTH_PHISHING_RESISTANT
        ,pape.AUTH_MULTI_FACTOR
        ,pape.AUTH_MULTI_FACTOR_PHYSICAL
        ]

    #Map AX urls to sreg attributes
    AX_MAPPING = {
        'http://axschema.org/contact/email': 'email'
        ,'http://schema.openid.net/namePerson': 'nickname'
        }

    class OpenIdConsumerRoot(object):
        """A cherrypy object that logs into open id.  Is presumed to be
        mounted at {AuthRoot}/login_openid/
        """

        supported = True

        static_path = '../static'
        store = OpenIdStore('openid_c')

        def __init__(self, auth_root):
            self.auth_root = auth_root

        def get_consumer(self):
            return consumer.Consumer(cherrypy.session, self.store)

        def redirect_err(self, error, redirect):
            raise cherrypy.HTTPRedirect(
                url_add_parms('../login', { 'error': error, 'redirect': redirect })
                )

        def get_points(self, redirect=None, admin=False):
            """For any root-level openid consumer request, returns
            the urls for trust_root and return_to endpoints.
            """
            return_dict = {}
            if redirect:
                return_dict['redirect'] = redirect
            if admin:
                return_dict['admin'] = 'true'
            return (
                cherrypy.url('./') #MUST be static.  If changed, some providers
                                   #also change the identity URL.
                , url_add_parms(cherrypy.url('./finish'), return_dict)
                )

        @cherrypy.expose
        def index(self, url=None, redirect=None, admin=False):
            """Begin the openID request"""

            if url is None:
                #Meta request; the YADIS header is all that matters.
                cherrypy.response.headers[YADIS_HEADER_NAME] = cherrypy.url('xrds')
                return 'Hi!'

            openid_url = url
            redirect = redirect or ' ' #Blank doesn't get retransmitted
            c = self.get_consumer()
            error = None

            try:
                auth_request = c.begin(openid_url)
            except DiscoveryFailure as e:
                error = 'OpenID Discovery Failure: {0}'.format(e)
                self.redirect_err(error, redirect)

            #These two are so widely unsupported and uncompliant,
            #that they're hardly worth supporting.
            #Here's where we ask for things like email
            sreg_request = sreg.SRegRequest(required=['email','nickname'])
            auth_request.addExtension(sreg_request)

            #Look at attribute exchange (ax) more
            ax_request = ax.FetchRequest()
            for key in AX_MAPPING.keys():
                ax_request.add(ax.AttrInfo(key, required=True))
            auth_request.addExtension(ax_request)

            #PAPE policies
            requested_policies = PAPE_POLICIES
            pape_request = pape.Request(requested_policies)
            auth_request.addExtension(pape_request)

            #Trust root / return path
            trust_root, return_to = self.get_points(redirect, admin)

            if auth_request.shouldSendRedirect():
                raise cherrypy.HTTPRedirect(
                    auth_request.redirectURL(trust_root, return_to)
                    )
            else:
                form_id = 'openid_message'
                form_html = auth_request.formMarkup(
                    trust_root
                    , return_to
                    , False
                    , { 'id': form_id }
                    )
                return self.request_form(form_html)

        @cherrypy.expose
        #This WOULD be POST filtered, but apparently OpenID2 can send
        #arguments as either POST or GET
        def finish(self, **kwargs):
            """End the openID request"""
            redirect = kwargs['redirect'] #Required
            if redirect == ' ': #Fix our hack earlier
                redirect = ''
            result = {}

            c = self.get_consumer()

            trust_root, return_to = self.get_points(redirect)
            if log.enabled:
                log("openidconsumer - Got finish kwargs: " + repr(kwargs))
            response = c.complete(kwargs, return_to)

            #Check the sreg response
            if response.status == consumer.SUCCESS:
                sreg_response = sreg.SRegResponse.fromSuccessResponse(response)
                ax_response = ax.FetchResponse.fromSuccessResponse(response)
                pape_response = pape.Response.fromSuccessResponse(response)
                if not pape_response.auth_policies:
                    pape_response = None

                # Set up any user data we got in the request (we prioritize
                # sreg)
                user_params = {}
                if ax_response:
                    for key,value in AX_MAPPING.items():
                        user_params[value] = ax_response.getSingle(key, None)
                if sreg_response:
                    for k,v in sreg_response.items():
                        user_params[k] = v

                if not user_params.get('nickname') and user_params.get('email'):
                    user_params['nickname'] = user_params.get('email') \
                        .split('@')[0]

                extra_args = {}
                if 'admin' in kwargs:
                    extra_args['admin'] = True
                return self.auth_root.login_openid_response(
                    response.getDisplayIdentifier()
                    ,redirect=redirect
                    ,user_params=user_params
                    ,**extra_args
                    )
                return """<p>OpenID: OK</p><p>url: {0}</p><p>sreg: {1}</p><p>ax: {2}</p><p>pape: {3}</p><p>user_params: {4}</p>""".format(
                    response.getDisplayIdentifier(), repr(sreg_response), repr(ax_response), repr(pape_response), repr(user_params)
                    )

            elif response.status == consumer.CANCEL:
                self.redirect_err('OpenID authentication cancelled', redirect)
            elif response.status == consumer.FAILURE:
                self.redirect_err('OpenID authentication failed: {0}'.format(response.message), redirect)

        @cherrypy.expose
        def xrds(self):
            trust_root, return_to = self.get_points()
            cherrypy.response.headers['Content-Type'] = YADIS_CONTENT_TYPE
            return """<?xml version="1.0" encoding="UTF-8"?>
<xrds:XRDS xmlns:xrds="xri://$xrds" xmlns="xri://$xrd*($v*2.0)">
  <XRD>
    <Service priority="0">
      <Type>{type_uri}</Type>
      <URI>{return_to}</URI>
    </Service>
  </XRD>
</xrds:XRDS>""".format(type_uri=RP_RETURN_TO_URL_TYPE, return_to=return_to)

        def request_form(self, html):
            """Returns the request form when openId requests a form instead
            of a redirect.
            """
            return """<div class="lg_auth_form" id="lg_auth_form_autosubmit">
  <script type="text/javascript">
  function submit_form() {{ 
    document.getElementById('openid_message').submit(); 
    document.getElementById('lg_auth_form_autosubmit').innerHTML = 'Please Wait... Submitting request';
  }}
  window.onload = submit_form;
  </script>
  <p>Your OpenID provider has requested that you transmit your information in a POST request.  If you have javascript disabled, please click the following button:</p>
{0}
</div>
""".format(html)

