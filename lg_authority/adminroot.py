"""Administration functions for lg_authority"""

import json
import datetime

from .common import *
from .controls import *

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
        ulist = config.Slate.find_between('user', 'user-', 'user.', maxusers)
        unames = [ u.id[5:] for u in ulist ]
        users = [ 
            '<li><a href="edit_user?user={0}">{0}</a></li>'.format(u) for u in unames 
            ]
        maxiusers = 100
        ulist = config.Slate.find_between('user', 'userhold-', 'userhold.', maxiusers)
        unames = [ u.id[9:] for u in ulist ]
        iusers = [
            '<li><a href="edit_user?user={0}">{0}</a></li>'.format(u) for u in unames
            ]

        ulist = config.Slate.find_between('user', 'userold-', 'userold.', maxiusers)
        unames = [ u.id[8:] for u in ulist ]
        inusers = [
            '<li><a href="edit_user?user={0}">{0}</a></li>'.format(u) for u in unames
            ]

        p = LgPageControl()
        p.append('<h1>Users</h1>')
        form = GenericControl('<form method="GET" action="edit_user">{children}</form>').appendto(p)
        form.append('Find/Create User: <input type="text" name="user" />')
        form.append('<input type="submit" value="Add/Edit" />')

        @Control.Kwarg('users')
        @Control.Kwarg('usertype')
        class UserTypeControl(Control):
            template = '<h2>Top {users} {usertype} Users</h2><ul>{children}</ul>'

        g = UserTypeControl(users=maxiusers, usertype='Pending').appendto(form)
        g.extend(iusers)

        g = UserTypeControl(users=maxusers, usertype='Active').appendto(form)
        g.extend(users)

        g = UserTypeControl(users=maxiusers, usertype='Inactive').appendto(form)
        g.extend(inusers)

        return p.gethtml()


        return self.make_page("""
<h1>Users</h1>
<form method="GET" action="edit_user">
  Find/Create User: <input type="text" name="user" />
  <input type="submit" value="Add/Edit" />
  <h2>Top {leniusers} Pending Users</h2>
  <ul>{iusers}</ul>
  <h2>Top {lenusers} Active Users</h2>
  <ul>{users}</ul>
  <h2>Top {leninusers} Inactive Users</h2>
  <ul>{inusers}</ul>
</form>
        """.format(users=''.join(users),lenusers=maxusers
                ,iusers=''.join(iusers),leniusers=maxiusers
                ,inusers=''.join(inusers),leninusers=maxiusers
                )
            )

    @cherrypy.expose
    def edit_user(self, user):
        holder = False
        inactive = False
        urec = config.auth.user_get_record(user)
        body = []
        if urec.is_expired():
            holder = True
            urec = config.auth.user_get_holder(user)
        if urec.is_expired():
            holder = False
            inactive = True
            urec = config.auth.user_get_inactive(user)

        if not urec.is_expired():
            if not holder and not inactive:
                body.append('<p>Active User</p>')
                body.append('<p>')
                body.append('<form method="POST" action="edit_user_deactivate?user={0}"><input type="submit" value="Deactivate User"/></form>'.format(user))
                body.append('</p>')

            if holder:
                body.append('<p>Pending User</p>')
                if config['site_registration'] == 'admin':
                    body.append('<p>')
                    body.append('<form method="POST" action="edit_user_confirm?user={0}"><input type="submit" value="Activate User"/></form>'.format(user))
                    body.append('<form method="POST" action="edit_user_reject?user={0}"><input type="submit" value="Deny User"/></form>'.format(user))
                    body.append('</p>')

            if inactive:
                body.append('<p>Inactive User</p>')
                body.append('<p>')
                body.append('<form method="POST" action="edit_user_activate?user={0}"><input type="submit" value="Activate User"/></form>'.format(user))
                body.append('<form method="POST" action="edit_user_delete?user={0}"><input type="submit" value="Delete User (Frees username for later usage)"/></form>'.format(user))
                body.append('</p>')

            stats = sorted(urec.items())
            body.append('<table><thead><tr><td>Name</td><td>Value</td></tr></thead><tbody>')
            for k,v in stats:
                body.append('<tr><td>{k}</td>'.format(k=k))

                body.append('<td>{v}</td></tr>'.format(v=json.dumps(v,default=admin_to_json)))
            body.append('</tbody></table>')
                
        else:
            body.append('<h2>User does not exist</h2>')

        return self.make_page("""
<h1>User '{user}'</h1>
{body}
""".format(user=user, body=''.join(body))
            )

    @cherrypy.expose
    def edit_user_confirm(self, user):
        if config['site_registration'] != 'admin':
            return "This site does not use admin registration."
        hold = config.auth.user_get_holder(user)
        if hold is not None:
            config.auth.user_promote_holder(hold)
            raise cherrypy.HTTPRedirect(cherrypy.url('edit_user?user={0}'.format(user)))
        return "User does not exist"

    @cherrypy.expose
    def edit_user_reject(self, user):
        if config['site_registration'] != 'admin':
            return "This site does not use admin registration."
        hold = config.auth.user_get_holder(user)
        if hold is not None:
            hold.expire()
            raise cherrypy.HTTPRedirect(cherrypy.url('./'))
        return "User does not exist"

    @cherrypy.expose
    def edit_user_activate(self, user):
        inact = config.auth.user_get_inactive(user)
        if inact is not None:
            config.auth.user_activate(user)
            raise cherrypy.HTTPRedirect(cherrypy.url('edit_user?user={0}'.format(user)))
        return "User does not exist"

    @cherrypy.expose
    def edit_user_deactivate(self, user):
        act = config.auth.user_get_record(user)
        if act is not None:
            config.auth.user_deactivate(user)
            raise cherrypy.HTTPRedirect(cherrypy.url('edit_user?user={0}'.format(user)))
        return "User does not exist"

    @cherrypy.expose
    def edit_user_delete(self, user):
        inact = config.auth.user_get_inactive(user)
        if inact is not None:
            inact.expire()
            raise cherrypy.HTTPRedirect(cherrypy.url('./'))
        return "User does not exist"

    @cherrypy.expose
    def groups(self):
        return self.make_page("""
<h1>Groups</h1>
        """)

