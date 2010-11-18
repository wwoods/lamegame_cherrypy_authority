from ..control import Control

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

    title = "Page"
    title__doc = "The page title"

    def prerender(self):
        self.kwargs['meta'] = ''.join(self.getheaders('meta'))
        self.kwargs['head'] = ''.join(self.getheaders('head'))
        self.kwargs['style'] = ''.join(self.getheaders('style'))
        self.kwargs['script'] = '(function() { ' \
            + ' })();(function() { '.join(self.getheaders('script')) \
            + ' })();'

        self.kwargs['title'] = self.title

