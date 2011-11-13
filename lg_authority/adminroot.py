"""Administration functions for lg_authority"""

import json
import datetime

from .common import *
from .controls import *
from .slates import Slate

def admin_to_json(obj):
    if isinstance(obj, datetime.datetime):
        return 'DATE:' + obj.isoformat() + 'Z'
    raise TypeError("Cannot encode " + str(type(obj)) + " to JSON")

@groups('admin')
class AdminRoot(object):
    def make_page(self, body):
        return """<div class="lg_auth_form">{menu}{body}</div>""".format(menu=self.get_menu(), body=body)

    def get_menu(self):
        return """<ul class="lg_auth_menu">
<li><a href="./">Users</a></li>
<li><a href="groups">Groups</a></li>
</ul>"""

    @cherrypy.expose
    def index(self):
        maxusers = 100
        ulist = config.Slate.find_between('user', '', 'zzzzzz', maxusers)
        udata = [ (u.id, u.get('name', '(noname)')) for u in ulist if not u.get('inactive') ]
        users = [
            '<li><a href="edit_user?userId={0}">{1}</a></li>'.format(id, name) for id,name in udata
            ]
        maxiusers = 100
        unames = [ (u.id, u.get('name', '(noname)')) for u in ulist if u.get('inactive') ]
        iusers = [
            '<li><a href="edit_user?userId={0}">{1}</a></li>'.format(id, name) for id,name in unames
            ]

        maxpusers = 100
        plist = Slate.find_between('username', '', 'zzzzzz', maxpusers)
        pdata = [ u.id for u in plist if u.get('holder') ]
        pusers = [
            '<li><a href="edit_user?username={0}">{0}</a></li>'.format(u) for u in pdata
            ]

        p = LgPageControl()
        p.append('<h1>Users</h1>')
        form = GenericControl('<form method="GET" action="edit_user">{children}</form>').appendto(p)
        form.append('Find/Create User: <input type="text" name="userName" />')
        form.append('<input type="submit" value="Add/Edit" />')

        @Control.Kwarg('users')
        @Control.Kwarg('usertype')
        class UserTypeControl(Control):
            template = '<h2>Top {users} {usertype} Users</h2><ul>{children}</ul>'

        g = UserTypeControl(users=maxpusers, usertype='Pending').appendto(form)
        g.extend(pusers)

        g = UserTypeControl(users=maxusers, usertype='Active').appendto(form)
        g.extend(users)

        g = UserTypeControl(users=maxiusers, usertype='Inactive').appendto(form)
        g.extend(iusers)

        return p.gethtml()


        return self.make_page("""
<h1>Users</h1>
<form method="GET" action="edit_user">
  Find/Create User: <input type="text" name="username" />
  <input type="submit" value="Add/Edit" />
  <h2>Top {lenpusers} Pending Users</h2>
  <ul>{pusers}</ul>
  <h2>Top {lenusers} Active Users</h2>
  <ul>{users}</ul>
  <h2>Top {leniusers} Inactive Users</h2>
  <ul>{iusers}</ul>
</form>
        """.format(users=''.join(users),lenusers=maxusers
                ,iusers=''.join(iusers),leniusers=maxiusers
                ,pusers=''.join(pusers),lenpusers=maxpusers
                )
            )

    @cherrypy.expose
    def edit_user(self, userName=None, userId=None):
        holder = False
        inactive = False

        if userId is not None:
            user = config.auth.get_user_from_id(userId)
            userName = user.get('name', '(No Name Found)')
        elif userName is not None:
            user = config.auth.get_user_from_name(userName)
            if user is not None:
                userId = user.id
            else:
                holder = True
                user = config.auth.get_user_holder(userName)
        else:
            return "INVALID REQUEST - need userName or userId"

        if user is not None and user.get('inactive', False):
            inactive = True

        body = []

        if user is not None:
            if not holder and not inactive:
                body.append('<p>Active User</p>')
                body.append('<p>')
                body.append('<form method="POST" action="edit_user_deactivate?userId={0}"><input type="submit" value="Deactivate User"/></form>'.format(userId))
                body.append('</p>')

            if holder:
                body.append('<p>Pending User</p>')
                if config['site_registration'] == 'admin':
                    body.append('<p>')
                    body.append('<form method="POST" action="edit_user_confirm?username={0}"><input type="submit" value="Activate User"/></form>'.format(username))
                    body.append('<form method="POST" action="edit_user_reject?username={0}"><input type="submit" value="Deny User"/></form>'.format(username))
                    body.append('</p>')

            if inactive:
                body.append('<p>Inactive User</p>')
                body.append('<p>')
                body.append('<form method="POST" action="edit_user_activate?userId={0}"><input type="submit" value="Activate User"/></form>'.format(userId))
                body.append('<form method="POST" action="edit_user_delete?userId={0}"><input type="submit" value="Delete User (Frees username for later usage)"/></form>'.format(userId))
                body.append('</p>')

            stats = sorted(user.items())
            body.append('<table><thead><tr><td>Name</td><td>Value</td></tr></thead><tbody>')
            for k,v in stats:
                body.append('<tr><td>{k}</td>'.format(k=k))

                body.append('<td>{v}</td></tr>'.format(v=json.dumps(v,default=admin_to_json)))
            body.append('</tbody></table>')
                
        else:
            body.append('<h2>User does not exist</h2>')
            body.append('<form method="POST" action="edit_user_create?userName={0}"><input type="submit" value="Create User"/></form>'.format(userName))

        return self.make_page("""
<h1>User '{user}'</h1>
{body}
""".format(user=userName, body=''.join(body))
            )

    @cherrypy.expose
    def edit_user_confirm(self, username):
        if config['site_registration'] != 'admin':
            return "This site does not use admin registration."
        hold = config.auth.get_user_holder(username)
        if hold is not None:
            userId = config.auth.user_promote_holder(hold)
            raise cherrypy.HTTPRedirect(cherrypy.url('edit_user?username={0}'.format(username)))
        return "User does not exist"

    @cherrypy.expose
    def edit_user_reject(self, username):
        if config['site_registration'] != 'admin':
            return "This site does not use admin registration."
        hold = config.auth.get_user_holder(username)
        if hold is not None:
            hold.expire()
            raise cherrypy.HTTPRedirect(cherrypy.url('./'))
        return "User does not exist"

    @cherrypy.expose
    def edit_user_activate(self, userId):
        config.auth.user_activate(userId)
        raise cherrypy.HTTPRedirect(cherrypy.url('edit_user?userId={0}'.format(userId)))

    @cherrypy.expose
    def edit_user_deactivate(self, userId):
        config.auth.user_deactivate(userId)
        raise cherrypy.HTTPRedirect(cherrypy.url('edit_user?userId={0}'.format(userId)))

    @cherrypy.expose
    def edit_user_delete(self, userId):
        config.auth.user_delete(userId)
        raise cherrypy.HTTPRedirect(cherrypy.url('./'))

    @cherrypy.expose
    def edit_user_create(self, userName):
        userId = config.auth.user_create(userName, {})
        raise cherrypy.HTTPRedirect(cherrypy.url('edit_user?userId={0}'.format(userId)))

    @cherrypy.expose
    def groups(self):
        return self.make_page("""
<h1>Groups</h1>
        """)

