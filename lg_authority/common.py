
import re

import datetime
import cherrypy

#Python 2to3 helpers
try:
    basestring
except NameError:
    basestring = str

def log(message):
    if log.enabled:
        cherrypy.log(message, 'LG_AUTHORITY')
log.enabled = False

def get_site_name():
    """Returns the site domain for the current cherrypy request."""
    name_match = get_site_name.namere.match(cherrypy.request.base)
    log('Base: ' + cherrypy.request.base)
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

class AuthError(Exception):
    pass

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
    'site_key': 'abc123o2qh3otin;oiH#*@(TY(#*Th:T*:(@#HTntb982#HN(:@#*TBH:@#(*THioihI#HOIH%oihio3@H%IOH#@%I)(!*@Y%+(+!@H%~`un23gkh'
    #Site encryption key for passwords.  Should be more than 60 chars.
    ,
    'site_password_renewal': 365
    #Days until users receive warnings that their passwords are old when they
    #log in.  Use None for no warning.  Only users with passwords (not openid
    #users) will be prompted.
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
        'index_lists':  [ 'auth_openid', 'groups', 'emails' ]
        }
    #Configuration items for various sections of slates.
    #Just replace "_user" with "_{section name}" to set up config.
    #Most sections do not need any options, but if you want anything
    #indexed, or admin-editable, then this is where you specify it.
    ,
    'site_storage_sections_session': {
        'cache': [ 'auth', 'authtime', 'authtime_admin' ]
        }
    #Session vars to be cached at first read.
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
    'site_user_list': {
        'admin': {
            'auth_password': { 'date': datetime.datetime.utcnow(), 'pass': [ 'sha256', ['bff74028f285748241375d1c9c7f9b6e85fd3900edf8e601a78f7f84d848b42e', 'admin'] ] }
            ,'auth_openid': []
            ,'groups': [ 'admin' ]
            }
        }
    #User records to create if they do not already exist
    ,
    'site_group_list': {
        'admin': { 'name': 'Administrators' }
        }
    #Group records to create if they do not already exist.  
    #any, auth, and user- groups are automatic.
    ,
    'site_registration': 'email'
    #The required USER-SIDE registration mechanism.  All registration mechanisms use
    #recaptcha if it is installed.
    #Accepted values are:
    #open - Anyone passing recaptcha may make a valid account, no confirmation
    #    is necessary.
    #email - Email based registration (optionally w/ recaptcha).  
    #    See site_email_ settings.
    #admin - A user will define their account (optionally with recaptcha), but 
    #    an admin must sign off on it.
    #None - Users will be redirected to the login page if their openID
    #    fails, and the New Account link will be replaced with text asking
    #    users who feel they should have permission to contact the 
    #    administrator.
    ,
    'site_registration_conf': {
        'subject': email_reg_default_subject
        ,'body': email_reg_default_body
        ,'from': 'Site Registration <test@example.com>'
        }
    #Config items for the specific 
    ,
    'site_registration_timeout': 2
    #The number of days between which a registration request is placed and 
    #expires.  For open or None, this is irrelevant.  For email, it refers to
    #the time window that the user has to receive the activation email and
    #activate their account.  For admin, this value IS NOT USED.
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
    'session_cookie': 'session_id'
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
    #deny_page_anon may be pointed to a login page.
    ,
    'deny_page_auth': None
    #Page that unauthorized users are sent to when trying to access a
    #resource they cannot retrieve AND are already authenticated.
    #Use None for a standard "Access Denied" page.
    })

#Alternative to None, used mostly for slates
missing = object()

#Some requests should be POST only
def method_filter(methods=['GET','HEAD']):
    """From http://tools.cherrypy.org/wiki/HTTPMethodFiltering"""
    method = cherrypy.request.method.upper()
    if method not in methods:
        cherrypy.response.headers['Allow'] = ', '.join(methods)
        raise cherrypy.HTTPError(405)

method_filter = cherrypy.tools.http_method_filter = cherrypy.Tool('on_start_resource', method_filter)

#Commonly resolve urlencode
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode

from .common_templates import *

def url_add_parms(base, qs):
    if type(qs) != dict:
        raise TypeError('qs must be dict')
    if len(qs) == 0:
        return base
    qs = urlencode(qs)
    if '?' in base:
        return base + '&' + qs
    return base + '?' + qs

# Basic rejection function calls
def deny_access():
    """Denies access to the current request.  Raises an HTTPRedirect or
    HTTPError depending on the user's login state.
    """
    denial_key = 'deny_page_anon'
    if cherrypy.serving.user is not None:
        denial_key = 'deny_page_auth'

    denial = cherrypy.tools.lg_authority._merged_args()[denial_key]
    if denial is not None:
        raise cherrypy.HTTPRedirect(
            url_add_parms(denial, { 'redirect': cherrypy.url(relative='server', qs=cherrypy.request.query_string) })
            )
    else:                
        raise cherrypy.HTTPError(401, 'Access Denied')

def get_user_groups():
    """Returns a list of ids for the user's groups.  Includes
    special groups 'any', and if logged in, 'auth' and 'user-'
    """
    user = cherrypy.serving.user
    result = [ 'any' ]
    if user is not None:
        result = [ 'any', 'auth', 'user-' + user.name ] + user.groups
    return result

def get_user_groups_named():
    """Returns a dictionary of id: name groupings for the user"""
    result = {}
    for grp in get_user_groups():
        result[grp] = config.auth.get_group_name(grp)
    return result

def groups(*groups):
    """Decorator function that winds up calling cherrypy.config(**{ 'tools.lg_authority.groups': groups })"""
    if len(groups) == 1 and type(groups[0]) == list:
        groups = groups[0]

    return cherrypy.config(**{ 'tools.lg_authority.groups': groups })

def check_groups(*groups):
    """Compare the user's groups to *groups.  If the user is in ANY
    of the supplied groups, access is granted.  Otherwise, an
    appropriate cherrypy.HTTPRedirect or cherrypy.HTTPError is raised.
    """
    if len(groups) == 1 and type(groups[0]) == list:
        groups = groups[0]

    allow = False
    usergroups = get_user_groups()
    for group in groups:
        if group in usergroups:
            allow = True
            break

    return allow

def check_groups_all(*groups):
    """Compare the user's groups to *groups.  If the user is in ALL
    of the supplied groups, access is granted.  Otherwise, an
    appropriate cherrypy.HTTPRedirect or cherrypy.HTTPError is raised.

    Passing an empty array will always allow access.
    """
    if len(groups) == 1 and type(groups[0]) == list:
        groups = groups[0]

    allow = True
    usergroups = get_user_groups()
    for group in groups:
        if group not in usergroups:
            allow = False
            break

    return allow

def require_groups(*groups):
    """Helper function that checks if the user is a member of any of the
    groups specified, and if not, denies access (raises a CherryPy
    redirect or error.
    """
    if not check_groups(*groups):
        deny_access()

def require_groups_all(*groups):
    """Helper function that checks if the user is a member of all
    groups specified, and if not, denies access (raises a CherryPy
    redirect or error.
    """
    if not check_groups_all(*groups):
        deny_access()

