from .base import *
from .cssreset import CssResetControl

#from the python wiki: http://wiki.python.org/moin/EscapingHtml
def _escape_html_text(text):
    return ''.join(_escape_html_text.table.get(c,c) for c in text)
_escape_html_text.table = {
    '&': '&amp;'
    ,'"': '&quot;'
    ,"'": '&apos;'
    ,'>': '&gt;'
    ,'<': '&lt;'
    }

@Control.Kwarg("title", "Page", "The page title")
class PageControl(Control):
    """A webpage in lg_authority land"""

    template = """
<!DOCTYPE html>
<html>
  <head>
    {meta}
    {head}
    <title>{title}</title>
    <style type="text/css">{style}</style>
    <script type="text/javascript">{script}</script>
  </head>
  <body>
    {children}
  </body>
</html>
    """

    def prerender(self, kwargs):
        kwargs['meta'] = ''.join(self.getheaders('meta'))
        kwargs['head'] = ''.join(self.getheaders('head'))
        kwargs['style'] = ''.join(self.getheaders('style'))
        kwargs['script'] = '(function() { ' \
            + ' })();(function() { '.join(self.getheaders('script')) \
            + ' })();'

@Control.Kwarg('id', '', 'The HTML id of this div')
@Control.Kwarg('cls', '', 'The space separated list of classes for this div')
class DivControl(Control):
    template = '<div{id}{cls}>{children}</div>'

    def prerender(self, kwargs):
        if kwargs['id']:
            kwargs['id'] = ' id="' + kwargs['id'] + '"'
        if kwargs['cls']:
            kwargs['cls'] = ' class="' + kwargs['cls'] + '"'

@Control.Kwarg('text', '', 'The text to display (will be escaped)')
class TextControl(Control):

    def __init__(self, text='', **kwargs):
        """A plaintext control.  Pass text to the constructor or set the 
        text attribute.
        """
        Control.__init__(self, text=text, **kwargs)

    template = """<span>{text}</span>"""

    def prerender(self, kwargs):
        kwargs['text'] = _escape_html_text(kwargs['text'])

@Control.Kwarg('width', '1024px', 'The width of the centered content.  Must be valid CSS')
class CenterControl(Control):
    """A centered div with a specific width"""

    template = """
<div style="width:{width};margin-left:auto;margin-right:auto;">
    {children}
</div>
    """

class NoIndexControl(Control):
    """Adds meta name="robots" content="noindex" to a page."""
    template = '{{{ meta <meta name="robots" content="noindex" /> }}}'

def GenericControl(template, **kwargs):
    """Creates a generic control with the specified template.  Useful
    for spot code that you want to use formatting for.
    """
    result = GenericControl.__types__.get(template, None)
    if result is None:
        result = type(
            'GenericControlDynamicType'
            , (Control,)
            , {
                'template': template
                }
            )
        GenericControl.__types__[template] = result
    return result(**kwargs)
GenericControl.__types__ = {}

