import cherrypy

from ..common import *
from .common import *

__all__ = [ 'Table' ]

class Table(Control):

    template = """<table>{children}</table>"""

    def __init__(self, columns, **kwargs):
        Control.__init__(self, **kwargs)
        self.columns = columns
        self._new_row()
        self._cur_cell = 0

    def add_cell(self, control):
        cell = self._get_cell()
        cell.append(control)
        self._cur_row.append(cell)
        self._cur_cell += 1
        if self._cur_cell == self.columns:
            self._cur_cell = 0
            self._new_row()

    def add_row(self, row_array):
        if len(row_array) != self.columns:
            raise Exception("Invalid number of columns")
        for c in row_array:
            self._cur_row.append(c)
        self._new_row()

    def _get_cell(self):
        return GenericControl("<td>{children}</td>")

    def _new_row(self):
        row = GenericControl("<tr>{children}</tr>")
        self.append(row)
        self._cur_row = row

