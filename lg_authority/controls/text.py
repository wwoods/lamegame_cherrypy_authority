from ..control import Control

#from the python wiki: http://wiki.python.org/moin/EscapingHtml
def escape_html_text(text):
    return ''.join(escape_html_text.table.get(c,c) for c in text)
escape_html_text.table = {
    '&': '&amp;'
    ,'"': '&quot;'
    ,"'": '&apos;'
    ,'>': '&gt;'
    ,'<': '&lt;'
    }

@Control.Kwarg('text', '', 'The text to display (will be escaped)')
class TextControl(Control):
    """A plaintext control.  Pass text to the constructor or set the 
    text attribute.
    """

    template = """<span>{text}</span>"""

    def prerender(self, kwargs):
        kwargs['text'] = escape_html_text(kwargs['text'])

