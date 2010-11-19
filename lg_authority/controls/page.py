from ..control import Control

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

