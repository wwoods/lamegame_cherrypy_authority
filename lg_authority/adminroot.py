"""Administration functions for lg_authority"""

from .common import *

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
        return self.make_page("""
<h1>Users</h1>
<form method="GET" action="edit_user">
  Find/Create User: <input type="text" name="username" />
  <input type="submit" value="Add/Edit" />
</form>
        """)

    @cherrypy.expose
    def edit_user(self, username):
        return self.make_page("""
<h1>User '{user}'</h1>
""".format(user=username)
            )
    
    @cherrypy.expose
    def groups(self):
        return self.make_page("""
<h1>Groups</h1>
        """)

