"""Manages loading templates for lg_authority; all templates are basic
python .format() calls.
"""

import os

_templates = {}
def get_template(name):
    result = _templates.get(name, None)
    if result is not None:
        return result

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    fname = os.path.join(path, name)
    with open(fname, 'r') as f:
        data = f.read()
    result = data.decode()
    _templates[name] = result
    return result

