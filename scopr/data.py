# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of "scropr".
#
# "scropr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "scropr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "scropr".  If not, see <http://www.gnu.org/licenses/>.


import csv
from math import log, exp

LINEAR = 0
EXPONENTIAL = 1
POWER = 2

   
class DataTable:

    def __init__(self, data, fields=None, types=None):
        if fields is True:
            self.fields = data[0]
            self.data = data[1:]
        else:
            self.fields = self.numberedFields(range(len(data[0]))) if fields is None else fields
            self.data = data
        self.types = None
        self.validate(types)

    def __len__(self): return len(self.data)
    def __getitem__(self, n): return self.data[n]

    def __iter__(self):
        for s in self.data: yield s

    def fieldType(self, col):
        "Return the data type for the specified column"
        t = self.types
        if t and type(t) in (tuple, list):
            t = t[col]
        return t

    def matchType(self, col, value):
        "Check if value matches column data type"
        ft = self.fieldType(col)
        vt = type(value) 
        return ft in (None, vt) or (ft is float and vt is int)

    def validateRecord(self, row):
        "Verify record size and data type"
        n = len(self.fields)
        if len(row) != n: return "Invalid record size", row
        if self.types:
            for col in range(n):
                if not self.matchType(col, row[col]):
                    return "Invalid data type (column {})".format(col), row
        return True

    def validate(self, types=None):
        "Validate all records"
        if types: self.types = types
        for row in self.data:
            v = self.validateRecord(row)
            if v is not True: return v
        return True

    @staticmethod
    def numberedFields(seq):
        "Auto-name the fields"
        return ["Field{}".format(n) for n in seq]

    @staticmethod
    def load(fn, header=None, types=None, convert=True):
        "Load and validate data from a CSV file"
        with open(fn) as f:
            csvFile = csv.reader(f)
            data = list(csvFile)
        if convert:
            for row in data:
                for i in range(len(row)):
                    try: row[i] = int(row[i])
                    except:
                        try: row[i] = float(row[i])
                        except: pass
        data = DataTable(data, header, types)
#         v = data.validate(types)
#         if v is not True:
#             raise ValueError(str(v))
        return data

    def fieldNumber(self, name):
        "Determine the column number corresponding to a field name"
        if type(name) is int and name >= 0:
            return name
        try: n = self.fields.index(name)
        except: n = None
        return n

    def columns(self, *cols):
        "Generator to extract columns from the table"
        cols = [self.fieldNumber(c) for c in cols] if len(cols) else (0,1)
        for row in self:
            yield [row[i] for i in cols]

#     def column(self, name):
#         "Generator for all data within a column"
#         n = self.fieldNumber(name)
#         if n is None:
#             raise KeyError("Invalid field name '{}'".format(name))
#         for r in self: yield r[n]

    def get(self, row, col):
        "Get one cell from the table"
        try:
            col = self.fieldNumber(col)
            x = self[row][col]
        except: x = None
        return x

    def put(self, row, col, value):
        "Modify one cell of the table"
        col = self.fieldNumber(col)
        if self.matchType(col, value):
            self[row][col] = value
        else:
            raise TypeError("Expecting {}; got {} {}".format(self.fieldType(col).__name__, type(value).__name__, repr(value)))

    def addFields(self, table):
        "Merge two tables"
        self.fields.extend(table.fields)
        if type(self.types) in (list, tuple):
            self.types = list(self.types)
            t = table.types
            if type(t) not in (list, tuple):
                t = [t for i in range(len(table.fields))]
            self.types.extend(t)
        r = 0
        for row in self:
            row.extend(table[r])
            r += 1

    def regression(self, xcol, ycol, model=LINEAR):
        "Perform a simple least squares regression on two columns"
        sx, sy, sx2, sxy = 0.0, 0.0, 0.0, 0.0
        for x, y in self.columns(xcol, ycol):
            if model:
                y = log(y)
                if model == POWER: x = log(x)
            sx += x
            sx2 += x * x
            sy += y
            sxy += x * y
        n = len(self.data)
        b = (sy * sx2 - sx * sxy) / (n * sx2 - sx * sx)
        m = (sxy - sx * sy / n) / (sx2 - sx * sx / n)
        if model:
            return exp(b), exp(m) if model == EXPONENTIAL else m
        return m, b

    @staticmethod
    def locus(t, **kwargs):
        "Return a sequence of points used to plot the model equation"
        m = kwargs.get("model")
        return t, predict(t, kwargs["coeff"], m)


def predict(x, coeff, model=LINEAR):
    a, b = coeff
    return a * x**b if model == POWER else a * b**x if model == EXPONENTIAL else a * x + b
