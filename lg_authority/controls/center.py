from ..control import Control

class CenterControl(Control):
    """A centered div; width must be set"""

    template = """
<div style="width:{width};margin-left:auto;margin-right:auto;">
    {children}
</div>
    """

    def __init__(self, width):
        self.width = width
        Control.__init__(self)

    def prerender(self):
        self.kwargs['width'] = self.width

