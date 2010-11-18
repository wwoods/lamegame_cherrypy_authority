"""A flexible, basic, templated control class for generating HTML on the fly.
The reason this exists is that I don't want any dependencies for this module.
"""

import re
import inspect

class Control(object):
    """An object representing a control (tag set) on a webpage.  It is 
    generally assumed that there is one primary Control per page.
    """

    _parent = None
    _parent__doc = "The parent of this Control; can be None"

    _children = []
    _children__doc = "Ordered list of child Controls"

    child_wrapper = None
    child_wrapper__doc = """An optional formatting for children.  The {child} marker will be substituted with the child's content.  Or, this can be a three element array, where the first element is a "header", the second occurs only between two children, and the third occurs at the end."""

    template = ""
    template__doc = """The text that will be format()'d with kwargs and emitted.
    Note that {children} will be replaced with any child controls.

    Is assumed to be a file name unless it starts with '\n', '<', or '{'.

    Additional once-per-class header sections may be defined like:

    {{{ style
      .my-class {
        background-color: red;
      }
    }}}

    The space between the {{{ and the keyword is mandatory.  These sections
    are NOT formatted with format().

    Implemented header sections: style (css section), script (automatically
    enclosed), meta, and head (anything below meta but before anything else)

    TODO - Custom appended parts of those sections... maybe...

    TODO - Inheritance.  The static blocks would auto add, but we'd need
    a method for dealing with dynamic content.
    """

    _headers = {}
    _headers__doc = "Any include-once header sections from the template."

    _template_static_loader = re.compile(r"\{\{\{ (\w+)(.*?)\}\}\}", re.DOTALL & re.M)

    _template_loaded = False
    _template_loaded__doc = "Flag as to whether or not the template for this class has been loaded."

    kwargs = {}
    kwargs__doc = "The keyword arguments that will be passed to template.  A kwarg may be a Control; it will be handled properly."

    def __init__(self):
        """Initializes this Control's children and kwargs"""
        self._children = []
        self.kwargs = {}

    @classmethod
    def _check_template(cls):
        """Initializes self with the given template (Must either start
        with "\n" or be a file name).
        """
        if cls._template_loaded:
            return
        cls._template_loaded = True

        template = cls.template
        if not template.startswith('\n') \
            and not template.startswith('{') \
            and not template.startswith('<') \
            :
            fname = template
            if not os.path.isabs(fname):
                fname = os.path.join(os.path.abspath(__file__), fname)
            file = open(fname, 'r')
            try:
                text = file.read()
                template = text.decode()
                cherrypy.engine.autoreload.files.add(fname)
            finally:
                file.close()

        #Process template
        cls._headers = {}
        for m in re.finditer(cls._template_static_loader, template):
            cls._headers[m.group(1)] = m.group(2)
            template = template.replace(m.group(0), '')

        #Set our template
        cls.template = template

    def append(self, child):
        """Appends a child to self, then returns self."""
        self._children.append(child)
        child._parent = self
        return self

    def appendto(self, parent):
        """Appends self to a parent, then returns self."""
        parent.append(self)
        return self

    def remove(self):
        """Removes self from parent, or does nothing.  Returns self."""
        if self._parent is not None:
            self._parent._children.remove(self)
            self._parent = None
        return self

    def getheaders(self, name):
        """Returns this and all childrens' headers for the given section.
        Each header is only included once per type.  Returns an array
        of all of the collected values.

        Also grabs header information from any Controls in self.kwargs.  This
        step must be done after build() and after prerender() so that 
        all children and kwargs can be recognized.
        """

        def getanc(results, cls):
            if not issubclass(cls, Control):
                return
            for p in [ c[0] for c in inspect.getclasstree([cls], unique=True) \
                if type(c) != list \
                ]:
                getanc(results, p)
            #Add the descendant class after the ancestor
            results.append(cls)

        to_process = [ self ]
        processed = set()
        result = []
        while len(to_process) > 0:
            child = to_process.pop(0)
            child_cls = child.__class__

            to_process.extend(child._children)
            for v in child.kwargs.values():
                if isinstance(v, Control):
                    to_process.append(v)

            if child_cls in processed:
                continue
            #We have to maintain ancestors' order in case descendents depend
            #on e.g. the script of the parent.
            temp = []
            getanc(temp, child_cls)
            stemp = set(temp)
            stemp = stemp.difference(processed)

            for cls in temp:
                if cls not in stemp:
                    continue
                if name in cls._headers:
                    result.append(cls._headers[name])
                    print("HEADER {0}: {1}///{2}".format(name, cls._headers[name], child))

            processed.update(stemp)

        return result

    def gethtml(self):
        """Returns the HTML representation of this control.

        Internally, iterates this object so that there is a single
        point of access for rendering.
        """
        return ''.join(self.render())

    def build(self):
        """Hook to allow dynamic appending of children based on a final state.
        """

    def prerender(self):
        """Hook to do something immediately before getting the html.  Maybe 
        setup self.kwargs?

        All children must be created at this point, since children's 
        prerender() is called first.
        """

    def __getitem__(self, key):
        """Returns the corresponding kwarg.. or should it return a child?"""
        raise NotImplementedError()
        return self.kwargs[key]

    def __setitem__(self, key, value):
        """Sets the corresponding kwarg"""
        raise NotImplementedError()
        self.kwargs[key] = value

    def __delitem__(self, key):
        """Removes the specified kwarg"""
        raise NotImplementedError()
        del self.kwargs[key]

    def render(self):
        """Streams the HTML representation of this control.  Note that 
        {children} may be used only once in the template.
        """
        #First call build() in case we need to add any new children
        self.build()

        #Process all children
        child_gen = [ [ d for d in c.render() ] for c in self._children ]
        if self.child_wrapper is not None:
            if isinstance(self.child_wrapper, list) \
                or isinstance(self.child_wrapper, tuple):
                pre,join,post = self.child_wrapper
            else:
                before,after = self.child_wrapper.split('{child}')
                pre = before
                join = after + before
                post = after
            #Array-ize elements so that they survive the single-level
            #flatten.
            pre = [ pre ]
            join = [ join ]
            post = [ post ]
            for i in range(len(child_gen) - 1, 0, -1):
                child_gen.insert(i, join)
            child_gen = [ pre ] \
                + child_gen \
                + [ post ]

        #Flatten child_gen
        child_gen = [ d for c in child_gen for d in c ]

        #Prepare ourselves for rendering
        self._check_template()
        self.prerender()

        #Format kwargs
        kwargs = self.kwargs.copy()
        for k in kwargs:
            v = kwargs[k]
            if isinstance(v, Control):
                kwargs[k] = v.gethtml()

        parts = self.template.split('{children}')
        if len(parts) > 1:
            pre = parts[0]
            post = '{children}'.join(parts[1:])
        else:
            pre = parts[0]
            post = ''

        yield pre.format(**kwargs)
        for c in child_gen:
            yield c
        yield post.format(**kwargs)

