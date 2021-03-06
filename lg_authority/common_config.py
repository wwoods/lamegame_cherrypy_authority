"""A few functions needed for the defaults, followed by a large dict
of all of the available configuration options for lg_authority.
"""

import re
import datetime
import cherrypy

def get_site_name():
    """Returns the site domain for the current cherrypy request."""
    name_match = get_site_name.namere.match(cherrypy.request.base)
    return name_match.group(1)
get_site_name.namere = re.compile('^[^:]+://([^/:]*)')

def email_reg_default_subject(username):
    return """{site} - Registration""".format(site=get_site_name())

def email_reg_default_body(username):
    return """You have requested registration as {user} at {site}.""".format(
        user=username
        ,site=get_site_name()
        )

#config.Slate is set by slates

class ConfigDict(dict):
    """Holds all configuration items.  Its own class so that
    it may hold flags as well.
    """

config = ConfigDict()
#Set defaults, show params.  These are overwritten first 
#by any config in the tools.lg_authority or lg_authority aliased section, then
#by CherryPy config.
#Any key prefixed with site_ is meant to be site-wide, and will be written
#to this dict on the first request (NO MATTER WHERE THE REQUEST IS TO).
config.update({
    'site_auth_root': '/auth/'
    #The absolute path to the site's auth root, with ending slash.
    ,
    'site_admin_login_window': 120
    #Seconds after reauthentication that the administrative window closes.
    #Used for things like changing the user's password or adding a new 
    #e-mail address.
    ,
    'site_storage': 'ram'
    #The storage backend for the auth framework.  Essentially, we use 
    #a namespaced key-value store with expiration times on the namespaces for
    #our general framework storage.
    ,
    'site_storage_conf': {
        }
    #Configuration options for the specified site storage.
    ,
    'site_storage_sections_user': {
        'index_lists':  [ 'auth_openid', 'auth_token', 'groups', 'emails' ]
        }
    #Configuration items for various sections of slates.
    #Just replace "_user" with "_{section name}" to set up config.
    #Most sections do not need any options, but if you want anything
    #indexed, or admin-editable, then this is where you specify it.
    ,
    'site_storage_clean_freq': 60
    #Minutes between cleaning up expired site storage.
    ,
    'site_email': {
        'smtpserver': '127.0.0.1'
        ,'smtpport': 25
        ,'smtpssl': False
        ,'smtpuser': None
        ,'smtppass': None
        ,'default': 'Site <test@example.com>'
        }
    #Not *strictly* required (set to None for no email), but enables
    #functionality like e-mail registration and forgot password resets via
    #email.
    ,
    'site_template': None#default_template
    #The template used to render the authroot forms.  If this is a function,
    #it will be called with the internal HTML for that particular form as
    #an argument.  If this is a two-member array, then the form content
    #is placed firmly in the middle.
    ,
    'site_user_list': {
        'admin': {
            'auth_password': { 'date': datetime.datetime.utcnow(), 'pass': [ 'sha256', ['bff74028f285748241375d1c9c7f9b6e85fd3900edf8e601a78f7f84d848b42e', 'admin'] ] }
            ,'auth_openid': []
            ,'groups': [ 'admin' ]
            }
        }
    #User records to create if they do not already exist.  Is a username to 
    #data pairing; the user's ID will be generated.
    ,
    'site_group_list': {
        'admin': { 'name': 'Administrators' }
        }
    #Group records to create if they do not already exist.  
    #any, auth, and user- groups are automatic.
    ,
    'site_key': 'abc123o2qh3otin;oiH#*@(TY(#*Th:T*:(@#HTntb982#HN(:@#*TBH:@#(*THioihI#HOIH%oihio3@H%IOH#@%I)(!*@Y%+(+!@H%~`un23gkh'
    #Site encryption key for passwords.  Should be more than 60 chars.
    ,
    'site_password_renewal': 365
    #Days until users receive warnings that their passwords are old when they
    #log in.  Use None for no warning.  Only users with passwords (not openid
    #users) will be prompted.
    ,
    'site_registration': None
    #The required USER-SIDE registration mechanism.  All registration mechanisms use
    #recaptcha if it is installed.
    #Accepted values are:
    #open - Anyone passing recaptcha may make a valid account, no confirmation
    #    is necessary.
    #email - Email based registration (optionally w/ recaptcha).  
    #    See site_email_ settings.
    #admin - A user will define their account (optionally with recaptcha), but 
    #    an admin must sign off on it.
    #external - No special registration - use an external (currently only 
    #   openID) source for logins.  Trust that username for logins.
    #   Options:
    #       open_id: OpenID endpoint URL to use
    #       email: { e-mail registration settings } - If set (not None), require
    #           an e-mail address to register.  If the openID endpoint does
    #           not provide an e-mail, the user will be prompted.
    #       logout: Additional URL to use for logouts
    #None - Users will be redirected to the login page if their openID
    #    fails, and the New Account link will be replaced with text asking
    #    users who feel they should have permission to contact the 
    #    administrator.
    ,
    'site_registration_conf': {
        'subject': email_reg_default_subject
        ,'body': email_reg_default_body
        #,'from': 'Site Registration <test@example.com>' Optional; if not
        #specified, will use the site_email's 'default' parameter
        }
    #Config items for the specific 
    ,
    'site_registration_recaptcha': {
        'public': None
        ,'private': None
        }
    #Your public and private keys for recaptcha, or None to disable recaptcha
    ,
    'site_debug': False
    #Print debug messages for lg_authority?  True/False
    ,
    'override_sessions': True
    #Use Slates instead of sessions.  This defaults to True, but you might
    #want to set it to false if you typically set properties in 
    #cherrypy.session WITHOUT setting them directly (e.g. 
    #a = MyClass();
    #cherrypy.session['var'] = a
    #a.data = 6 #THIS WILL NOT BE SAVED WITH SITE_OVERRIDE_SESSIONS AS TRUE
    #
    #If you use an app that does this, feel free to set its specific 
    #configuration to override_sessions: False
    ,
    'session_timeout': 60
    #Minutes until a session expires; applicable only if override_sessions is
    #True.
    ,
    'session_cookie': 'session'
    #The cookie value used to read the session id.  Applicable only if 
    #override_sessions is True.
    ,
    'user_slate_section': 'userslate'
    #The prefix for named slates for each user (only applicable when using
    #lamegame_cherrypy_slates).  Can be overridden at different paths to 
    #"isolate" user storage.  Don't use any of the existing ones.
    ,
    'groups': [ 'any' ]
    #Static groups allowed to access the resource.  If the FIRST ELEMENT
    #of the array is 'all:', then the user must be in EVERY group specified
    #to gain access.  Otherwise, if the user matches a single group, they
    #will be allowed access.  This convention is ugly, but prevents errors
    #when a site might wish to use both AND and OR group configurations
    #in the same environment.
    #
    #Special groups:
    #'any' means everyone, even unauthenticated users
    #'auth' means all authenticated users
    #'user-' + username means specifically (and only) username
    ,
    'user_home_page': '..'
    #The page to redirect to (if relative, then from AuthRoot/OneLevel/)
    #on successful authentication when a redirect action was not requested.
    #May be a function that returns a URL; that function may use cherrypy.user
    #to determine the user's identity.
    ,
    'logout_page': '..'
    #Page to redirect to on logout.  Use None to show a standard auth
    #page confirming the logout.
    ,
    'deny_page_anon': '/auth/login'
    #Page that unauthorized users are sent to when trying to access a
    #resource they cannot retrieve AND are not authenticated.  
    #Use None for a standard "Access Denied" page.
    #
    #If the path starts with '/auth/', then site_auth_root will be substituted.
    #
    #deny_page_anon may be pointed to a login page.
    ,
    'deny_page_auth': None
    #Page that unauthorized users are sent to when trying to access a
    #resource they cannot retrieve AND are already authenticated.
    #Use None for a standard "Access Denied" page.
    })

