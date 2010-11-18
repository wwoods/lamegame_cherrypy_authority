from ..common import *

from ..control import Control
from .page import PageControl
from .literal import LiteralControl

class LgPageControl(Control):
    """An lg_authority page.  This class overrides template rendering such
    that it will also check cherrypy.serving.lg_authority for 
    various arguments and render its children accordingly.
    """

    template = "{children}"

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
            p = PageControl().appendto(self)
            for c in children:
                p.append(c)

