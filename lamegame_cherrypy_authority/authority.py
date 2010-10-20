
import time
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode
import json

import cherrypy
import couchdb

import templates

# TODO - Separate users database from authorizations database; draw up
# how linking SC and this site would work.  SC permissions . . . how?


class _AuthDb:
  """
  Initializes the authorization database with the given couchdb database.
  If the database does not exist on the server, it will be initialized
  with the administrator account "admin".
  
  address is a couchdb server address:  "http://127.0.0.1:5984"
  
  db is the database name: "lamegame_auth"
  """
  
  def __init__(self, address, db):
    self._auth_server = couchdb.Server(address)
    self._auth_db_name = db
    self._auth_db = None
    
    try:
      self._auth_db = self._auth_server[self._auth_db_name]
    except couchdb.http.ResourceNotFound:
      try:
        self._auth_db = self._auth_server.create(self._auth_db_name)
        self._auth_db_init()
      except:
        del self._auth_server[self._auth_db_name]
        raise
    
  def get_user(self, username):
    """
    Returns the user document desired.  Raises exception if
    username is not a valid user.
    """
    return self._auth_db['user-' + username]

  def get_user_groups(self, username):
    """Returns a set of groups that the user belongs to

    Format is { 'id': id, 'name': name[, 'isUserPrimary': True ] }
    """
    result = [ 
      { 'id': 'user-' + username, 'name': 'User - ' + username }
    ]
    groups = [ 'group-' + g for g in self.get_user(username)['groups'] ]
    for grp in self.view('_all_docs', keys=groups, include_docs=True).rows:
      result.append({
        'id': grp.id[6:]
        ,'name': grp.doc.get('Name', grp.id[6:])
      })
    return result

  def get_user_primary(self, username):
    """Returns a group identifier for the user's own, personal group."""
    return 'user-' + username

  def get_resource(self, resource):
    """
    Returns the resource document desired.  Raises exception
    if resource is not a valid resource.
    """
    return self._auth_db['res-' + resource]

  def get_resource_groups(self, resource):
    """Returns a set of group names that the resource belongs to"""
    results = self.get_resource(resource)['groups']
    return set(results)
    
  def save(self, doc):
    """Saves a document back to the database"""
    self._auth_db.save(doc)
    
  def view(self, *args, **kwargs):
    return self._auth_db.view(*args, **kwargs)
          
  def _auth_db_init(self):
    """
    Initializes the authentication / authorization database with a single
    admin user, a group of admins, and a resource named "admin" which grants
    access to everything in the AuthorityRoot.
    
    Also creates a group 'authenticated' that requires logged-in users and
    'anonymous' that allows anonymous access
    """
    self._auth_db['_design/authdb'] = {
      'language': 'javascript'
      ,'views': {
        'groupresources': {
          'map': """
function(doc) {
  if (doc.type === 'resource') {
    for (var i = 0, j = doc.groups.length; i < j; i++) {
      emit(doc.groups[i], null);
    }
  }
}
          """
        }
      }
    }
    self._auth_db['user-admin'] = {
      'type': 'user'
      ,'groups': [ 'administrators' ]
      ,'auth': {
        'password': {
          'sha256': _pword_sha256('admin')
        }
      }
    }
    self._auth_db['group-administrators'] = {
      'type': 'group'
      ,'name': 'Administrators'
    }
    self._auth_db['group-anonymous'] = {
      'type': 'group'
      ,'name': 'Anonymous Users'
    }
    self._auth_db['group-authenticated'] = {
      'type': 'group'
      ,'name': 'Authenticated Users'
    }
    self._auth_db['res-admin'] = {
      'type': 'resource'
      ,'name': 'Administrative Permissions'
      ,'description': 'Ability to edit all permissions'
      ,'groups': [ 'administrators' ]
    }
        
_db = _AuthDb('http://127.0.0.1:5984', 'lamegame_auth')

def _access_deny():
  user = cherrypy.session.get('username')
  if not user:
    #Not logged in; that's probably why
    login_url = '/auth/login'
    if cherrypy.request.method == 'GET':
      old_url = cherrypy.request.path_info
      old_query = cherrypy.request.query_string
      if old_query:
        old_url += '?' + old_query
      login_url += '?' + urlencode([ ('redirect', old_url) ])
    raise cherrypy.HTTPRedirect(login_url)
  else:
    #Logged in..
    raise cherrypy.HTTPRedirect('/auth/deny')

def get_user_groups():
  """Returns a list of group ids for the current user"""
  groups = [ 'anonymous' ]
  user = cherrypy.session.get('username')
  if user is not None:
    groups.append('authenticated')
    for grp in cherrypy.session.get('usergroups', []):
      groups.append(grp['id'])
  return groups

def require_access(*resources):
  """Looks at a list of resources and returns True if any of them
  may be accessed from the currently logged in user's account.
  """
  
  def decorate(f):
    def decorated(*args, **kwargs):
      result = False

      groups = set(get_user_groups())
      for resource in resources:
        if _check_access(groups, resource):
          result = True
          break
      
      if not result:
        _access_deny()

      return f(*args, **kwargs)
      
    return decorated
  return decorate

def require_group(*groups):
  """If the user is any any of the specified groups (or if anonymous is in
  the groups list), then allows access.  authenticated is a group depicting
  any authenticated user.
  """
  
  gs = set(groups)
  def decorate(f):
    def decorated(*args, **kwargs):
      result = False
      ugs = set(get_user_groups())

      if len(gs.intersection(ugs)) > 0:
        result = True

      if not result:
        _access_deny()

      return f(*args, **kwargs)

    return decorated
  return decorate
  
def _check_access(groups, resource):
  """Looks at a single resource and returns True if the 
  any of the specified groups can access that resource
  """
  if not isinstance(groups, set):
    groups = set(groups)

  res = _db.get_resource(resource)
  if len(set(res.get('groups', [])).intersection(groups)) > 0:
    return True
  return False

class Root:
  """
  Authorization and authentication server / web interface.
  
  Self-protects against non-administrator access to 
  non-authentication functions.
  
  Default user / password is admin / admin
  """
  
  default_redirect = '..'
        
  @cherrypy.expose
  def login(self, **args):
    if cherrypy.request.method == "POST":
      userdata = self.check_login(**args)
      if userdata is not None:
        cherrypy.session['username'] = userdata['username']
        cherrypy.session['usergroups'] = userdata['usergroups']
    
    if cherrypy.session.get('username') is not None:
      if 'redirect' in args:
        raise cherrypy.HTTPRedirect(args['redirect'])
      raise cherrypy.HTTPRedirect(self.default_redirect)
    
    # Show login page
    return templates.render('auth-login.html')
    
  @cherrypy.expose
  def deny(self):
    return templates.render('auth-deny.html')
    
  @cherrypy.expose
  @require_group('authenticated')
  def change_password(self, **kwargs):
    templateargs = {}
    
    if cherrypy.request.method == 'POST':
      user = cherrypy.session['username']
      oldpass = kwargs['oldpassword']
      newpass1 = kwargs['newpassword1']
      newpass2 = kwargs['newpassword2']
      
      if newpass1 == newpass2:
        if self.check_login(username=user,password=oldpass):
          userstruct = _db.get_user(user)
          userstruct['auth']['password'] = {
            'sha256': _pword_sha256(newpass2)
          }
          _db.save(userstruct)
          templateargs['updated'] = True
        else:
          templateargs['error'] = "Old password did not match"
      else:
        templateargs['error'] = "New passwords did not match"
        
    return templates.render('auth-changepass.html', **templateargs)
  
  @cherrypy.expose
  def logout(self):
    cherrypy.lib.sessions.expire()
    raise cherrypy.HTTPRedirect(self.default_redirect)
        
  @cherrypy.expose
  def login_service(self, **args):
    cherrypy.response.headers['Content-Type'] = "text/plain"
    return json.dumps(self.check_login(**args))
  
  def check_login(self, **args):
    #Anti brute-force measure
    time.sleep(0.7)
    
    #credentials extracted from authentication
    auth_info = None
    
    try:
      if 'username' in args and 'password' in args:
        user = _db.get_user(args['username'])
        user_pass = user['auth']['password']
        if 'sha256' in user_pass:
          sha256_hex = _pword_sha256(args['password'], user_pass['sha256'][1])
          if sha256_hex == user_pass['sha256']:
            groups = _db.get_user_groups(args['username'])
            primary = _db.get_user_primary(args['username'])
            auth_info = {
              'username': args['username']
              ,'userprimary': primary
              ,'usergroups': groups
            }
    except:
      #Means authentication failed, really.  Just return no username.
      pass
        
    return auth_info
    
