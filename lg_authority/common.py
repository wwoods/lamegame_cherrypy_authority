
class _ConfigDict(dict):
    """Holds all configuration items.  Its own class so that
    it may hold flags as well.
    """

config = _ConfigDict()
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
    ,
    'authtype_conf': {
        'users': [
            #The example admin user - the password is 'admin', and
            #was processed through lg_authority.passwords.sha256('admin').
            #These hashes may also be generated through 
            #AuthRoot()/helper/sha256
            { 'name': 'admin', 'auth': { 'password': { 'sha256': ['bff74028f285748241375d1c9c7f9b6e85fd3900edf8e601a78f7f84d848b42e', 'admin'] } } 
                ,'groups': [ 'admin' ]
                }
            ]
        }
    ,
    'groups': [ 'any' ]
    #Static groups allowed to access the resource.
    #'any' means everyone, even unauthenticated users
    #'auth' means all authenticated users
    #'user-' + username means specifically username
    ,
    'deny_page_anon': None
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

