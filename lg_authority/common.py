
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
                'auth': { 'password': ( 'sha256', ['bff74028f285748241375d1c9c7f9b6e85fd3900edf8e601a78f7f84d848b42e', 'admin'] ) }
                ,'groups': [ 'admin' ]
                }
            }
        }
    #Configuration options for the user/group store
    ,
    'groups': [ 'any' ]
    #Static groups allowed to access the resource.
    #'any' means everyone, even unauthenticated users
    #'auth' means all authenticated users
    #'user-' + username means specifically username
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

