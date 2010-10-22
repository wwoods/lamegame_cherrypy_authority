
import datetime
import cherrypy

class ConfigDict(dict):
    """Holds all configuration items.  Its own class so that
    it may hold flags as well.
    """

config = ConfigDict()
#Set defaults, show params.  These are overwritten first 
#by any config in the tools.lg_authority or lg_authority section, then
#CherryPy config.
config.update({
    'site_key': 'abc123o2qh3otin;oiH#*@(TY(#*Th:T*:(@#HTntb982#HN(:@#*TBH:@#(*THioihI#HOIH%oihio3@H%IOH#@%I)(!*@Y%+(+!@H%~`un23gkh'
    #Site encryption key for passwords.  Should be more than 60 chars.
    ,
    'user_slate_prefix': 'user-'
    #The prefix for named slates for each user (only applicable when using
    #lamegame_cherrypy_slates
    ,
    'authtype': 'userlist'
    #type of system that users and groups are fetched from
    ,
    'authtype_conf': {
        'users': {
            #The example admin user - the password is 'admin', and
            #was processed through lg_authority.passwords.sha256('admin').
            #These hashes may also be generated through 
            #AuthRoot()/helper/sha256
            'admin': {
                'auth': { 
                    'password': { 'date': datetime.datetime.utcnow(), 'pass': ( 'sha256', ['bff74028f285748241375d1c9c7f9b6e85fd3900edf8e601a78f7f84d848b42e', 'admin'] ) } 
                    ,'openid': [ ]
                    }
                ,'groups': [ 'admin' ]
                }
            }
        ,'groups': {
            #Groups other than 'any', 'auth', and 'user-'+username
            #Keys the group identifier to its name
            'admin': { 'name': 'Administrators' }
            }
        }
    #Configuration options for the user/group store.  The default is 
    #a configuration for userlist (RAM / predefined) storage.
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

