from ..control import Control

class LiteralControl(Control):
    """A verbatim HTML control."""

    template = "{html}"

    html = ""
    html__doc = "The HTML to render"

    def __init__(self, html=''):
        self.html = html
        Control.__init__(self)

    def prerender(self):
        self.kwargs['html'] = self.html

