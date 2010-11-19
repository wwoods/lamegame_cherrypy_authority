from ..common import *

from ..control import Control
from .page import PageControl
from .literal import LiteralControl
from .center import CenterControl
from .cssreset import CssResetControl

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
  }
  p {
    margin-bottom: 0.5em;
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
            CssResetControl().appendto(p)
            self.DefaultStyle().appendto(p)
            center = CenterControl('800px').appendto(p)
            for c in children:
                center.append(c)

