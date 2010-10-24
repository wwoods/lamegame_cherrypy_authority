
import datetime
import cherrypy

def log(message):
    if log.enabled:
        cherrypy.log(message, 'LG_AUTHORITY')
log.enabled = False

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
    'site_storage': 'ram'
    #The storage backend for the auth framework.  Essentially, we use 
    #a namespaced key-value store with expiration times on the namespaces.
    ,
    'site_storage_conf': {
        }
    #Configuration options for the specified site storage.
    ,
    'site_storage_sections': {
        'user': { 'index_lists':  [ 'auth_openid', 'groups' ] }
        }
    #Configuration items for various sections of slates.
    #Most sections do not need any options, but if you want anything
    #indexed, then this is where you specify it.
    ,
    'site_storage_clean_freq': 60
    #Minutes between cleaning up expired site storage.
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
    'site_registration': 'open'
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
    'site_registration_timeout': 7
    #The number of days between which a registration request is placed and 
    #expires.  For open or None, this is irrelevant.  For email, it refers to
    #the time window that the user has to receive the activation email and
    #activate their account.  For admin, this value IS NOT USED.
    ,
    'site_debug': True
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
    'user_home_page': '/'
    #The page to redirect to (if relative, then from AuthRoot/OneLevel/)
    #on successful authentication when a redirect action was not requested.
    #May be a function that returns a URL, given a user record.
    ,
    'logout_page': None
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
    """Unconditionally denies access to the current request."""
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

    if not allow:
        deny_access()

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

    if not allow:
        deny_access()

