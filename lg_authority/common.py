
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

class AuthError(Exception):
    pass

class TokenExistedError(Exception):
    """The user already had a recent token.  That token is contained in the
    token attribute of this exception.
    """
    def __init__(self, oldToken, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)
        self.token = oldToken

from .common_config import *

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

#Utility function to get the domain for a URL
_get_domain_url = re.compile('^[a-z]+://([^/:]+)')
def get_domain(url):
    return _get_domain_url.search(url).group(1)

from .common_templates import *

def url_add_parms(base, qs={}, **kwargs):
    if type(qs) != dict:
        raise TypeError('qs must be dict')
    kwargs.update(qs)
    if len(kwargs) == 0:
        return base
    qs = urlencode(kwargs)
    if '?' in base:
        return base + '&' + qs
    return base + '?' + qs

def get_auth_path(path):
    """If path starts with /auth/, substitutes in site_auth_root"""
    if path.startswith('/auth/'):
        return config['site_auth_root'] + path[6:]
    return path

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
            url_add_parms(denial, { 'redirect': cherrypy.url(qs=cherrypy.request.query_string) })
            )
    else:
        raise cherrypy.HTTPError(401, 'Unauthorized')

def get_user_groups(userId = None):
    """Returns a list of ids for the user's groups.  Includes
    special groups 'any', and if logged in, 'auth' and 'user-'

    userId - str -- If non-none, get groups for this user instead of the
            user logged in (cherrypy.user is used if None)
    """
    userGroups = None
    if userId is None:
        user = cherrypy.serving.user
        if user is not None:
            userGroups = user.groups
    else:
        user = config.auth.get_user_from_id(userId)
        if user is None:
            raise ValueError("Invalid user ID")
        userGroups = user['groups']

    result = [ 'any' ]
    if userGroups is not None:
        result = [ 'any', 'auth', 'user-' + user.id ] + userGroups
    return result

def get_user_groups_named():
    """Returns a dictionary of id: name groupings for the user"""
    result = {}
    for grp in get_user_groups():
        result[grp] = config.auth.get_group_name(grp)
    return result

def get_user_id(nameOrEmail):
    """Returns a user ID acquired from the given user name or e-mail.
    """
    user = config.auth.get_user_from_email(nameOrEmail)
    if user is not None:
        return user.id
    user = config.auth.get_user_from_name(nameOrEmail)
    if user is not None:
        return user.id
    return None

def groups(*groups):
    """Decorator function that winds up calling cherrypy.config(**{ 'tools.lg_authority.groups': groups })"""
    if len(groups) == 1 and type(groups[0]) == list:
        groups = groups[0]

    return cherrypy.config(**{ 'tools.lg_authority.groups': groups })

def deny_no_redirect(cls_or_func):
    """Decorator function that ensures that any denied response will not
    be redirected, but will instead raise a 401 Unauthorized.  Useful for
    AJAX calls.
    """
    return cherrypy.config(**{ 
        'tools.lg_authority.deny_page_anon': None
        ,'tools.lg_authority.deny_page_auth': None
        })(cls_or_func)

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

