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

class TextControl(Control):
    """A plaintext control.  Pass text to the constructor or set the 
    text attribute.
    """

    text = ''
    text__doc = "The text to display (will be escaped)"

    template = """<span>{text}</span>"""

    def __init__(self, text=''):
        self.text = text
        Control.__init__(self)

    def prerender(self):
        self.kwargs['text'] = escape_html_text(self.text)

