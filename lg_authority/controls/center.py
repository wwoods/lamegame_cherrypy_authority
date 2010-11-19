from ..control import Control

@Control.Kwarg('width', '1024px', 'The width of the centered content.  Must be valid CSS')
class CenterControl(Control):
    """A centered div with a specific width"""

    template = """
<div style="width:{width};margin-left:auto;margin-right:auto;">
    {children}
</div>
    """

