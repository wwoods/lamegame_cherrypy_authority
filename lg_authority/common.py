
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
            url_add_parms(denial, { 'redirect': cherrypy.url(qs=cherrypy.request.query_string) })
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
        result = [ 'any', 'auth', 'user-' + user.id ] + user.groups
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

