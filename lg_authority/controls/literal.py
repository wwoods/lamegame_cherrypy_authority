from ..control import Control

@Control.Kwarg('html', '', 'The HTML to render')
class LiteralControl(Control):
    """A verbatim HTML control."""

    template = "{html}"

    def __init__(self, html=''):
        self.html = html
        Control.__init__(self)

