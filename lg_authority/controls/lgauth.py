import cherrypy

from ..common import *
from .common import *

class LgPageControl(Control):
    """An lg_authority page.  This class overrides template rendering such
    that it will also check cherrypy.serving.lg_authority for 
    various arguments and render its children accordingly.
    """

    template = "{children}"

    class DefaultStyle(Control):
        template = """
{{{ style
  body {
    background-color: #d0d0ff;
    font-size: 12pt;
    line-height: 150%;
  }
  td {
    padding-right: 1em;
  }
  .lg-auth-form {
    background-color: #ffffff;
    -moz-border-radius: 0.5em;
    padding: 1em;
    margin-top: 1em;
    margin-bottom: 1em;
  }
}}}
        """

    def build(self):
        self.prepend(LgMenuControl())

        if config['site_template'] is not None:
            templ = config['site_template']
            if isinstance(templ, list) and len(templ) == 2:
                self._children.insert(0, templ[0])
                self._children.append(templ[1])
            else:
                raise ValueError('lg_authority site_template config is not a function or two-element list')
        else:
            #Use PageControl
            children = self._children[:]
            self._children = []
            p = PageControl(title=get_site_name()).appendto(self)
            NoIndexControl().appendto(p) #Don't index auth pages...
            CssResetControl().appendto(p)
            self.DefaultStyle().appendto(p)
            center = CenterControl(width='800px').appendto(p)
            form = DivControl(cls="lg-auth-form").appendto(center)
            form.extend(children)

class LgMenuControl(Control):
    """The lg_authority menu"""

    template = """
{{{ style
  .lg-auth-menu {
    margin-bottom: 0.5em;
  }
  .lg-auth-menu a {
    color: #000000;
    text-decoration: underline;
    display: inline-block;
    margin-right: 1em;
    padding: 0.25em;
  }
  .lg-auth-menu a:hover {
    background-color: #efffef;
  }
}}}
<div class="lg-auth-menu">
  {children}
</div>
    """

    def __init__(self, **kwargs):
        Control.__init__(self, **kwargs)

    def build(self):
        if not cherrypy.user:
            self.template = ''
            return
        class Link(Control):
            template = '<a href="{path}">{name}</a>'
            def prerender(self, kwargs):
                kwargs['path'] = get_auth_path(kwargs['path'])
        self.append(Link(path='/auth/', name='Dashboard'))
        self.append(Link(path='/auth/change_password', name='Change Password'))
        self.append(Link(path='/auth/logout', name='Logout'))
        if 'admin' in cherrypy.user.groups:
            admin = GenericControl(
                '<div style="'
                + 'background-color:#eff;display:inline-block;'
                + 'padding-left:1em;'
                + '">'
                + 'Admin: {children}'
                + '</div>'
            ).appendto(self)
            admin.append(Link(path='/auth/admin/', name='Users'))
            admin.append(Link(path='/auth/admin/groups', name='Groups'))

@Control.Kwarg('error', '', 'The error text to display')
class LgErrorControl(Control):
    template = """
{{{ style
  .lg-auth-error {
    color: #ff0000;
  }
}}}
<div class="lg-auth-error">{error}</div>
    """

