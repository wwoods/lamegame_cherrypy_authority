from ..control import Control

def GenericControl(template, **kwargs):
    """Creates a generic control with the specified template.  Useful
    for spot code that you want to use formatting for.
    """
    result = GenericControl.__types__.get(template, None)
    if result is None:
        def getter(self, key):
            return self.kwargs[key]
        def setter(self, key, value):
            if hasattr(self, key):
                self.__dict__[key] = value
            else:
                self.kwargs[key] = value
        result = type(
            'GenericControl: ' + template
            , (Control,)
            , {
                '__getattr__': getter
                ,'__setattr__': setter
                ,'template': template
                }
            )
        GenericControl.__types__[template] = result
    return result(**kwargs)

GenericControl.__types__ = {}

