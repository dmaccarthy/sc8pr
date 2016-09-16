# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This file is part of "sc8pr".
#
# "sc8pr" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "sc8pr" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "sc8pr".  If not, see <http://www.gnu.org/licenses/>.


class Matrix:
    "A class for performing arithmetic with matrices"

    def __init__(self, data):
        "Wrap a 2D list as a Matrix instance without copying data"
        cols = len(data[0])
        for row in data:
            if len(row) != cols: raise ValueError("Data must be rectangular")
        self._rows = data

    def __repr__(self): return "Matrix({})".format(str(self._rows))

    def format(self, frmt="{:9.2f}", pre="Matrix ({}×{}) [\n", post="]\n"):
        "Compose a formatted string to display the matrix"
        s = pre.format(*self.dims)
        for row in self:
            s += "\t["
            for v in row:
                s += frmt.format(v)
            s += "]\n"
        return s + post.format(*self.dims)

    __str__ = format

    def __getitem__(self, i): return self._rows[i]

    @property
    def rows(self): return len(self._rows)

    @property
    def cols(self): return len(self[0])
    
    @property
    def dims(self): return self.rows, self.cols

    def _assertSquare(self):
        "Raise an exception if the matrix is not square"
        n = self.rows
        if n != self.cols: raise ValueError("Matrix must be square")
        return n

    @staticmethod
    def sum(*args):
        "Calculate the sum of any number of matrices"
        s = None
        for m in args:
            s = m.clone() if s is None else (s + m)
        return s

    def clone(self):
        "Copy the data as a new Matrix"
        return Matrix([row[:] for row in self])

    def calc(self, fn):
        "Create a new Matrix by calling the function on each element"
        return Matrix([[fn(row[c]) for c in range(self.cols)] for row in self])

    def apply(self, fn):
        "Apply a function in-place to a matrix"
        cols = self.cols
        for row in self._rows:
            for c in range(cols):
                row[c] = fn(row[c])
        return self

    def __matmult__(self, other):
        "Multiply matrices"
        rows, n = self.dims
        if n != other.rows: raise ValueError("Incompatible dimensions for matrix multiplication")
        cols = other.cols
        return Matrix([[sum([self[r][i] * other[i][c] for i in range(n)])
            for c in range(cols)] for r in range(rows)])
    
    def __mul__(self, other):
        "Multiple by a matrix or number"
        if isinstance(other, Matrix):
            return self.__matmult__(other)
        else:
            return Matrix([[other*self[r][c] for c in range(self.cols)]
                for r in range(self.rows)])

    def __truediv__(self, other): return self * (1/other)
    __rmul__ = __mul__
    __rtruediv__ = __truediv__

    def __imul__(self, other): return self * other

    def __add__(self, other, subtract=False):
        "Add or subtract two matrices"
        if self.dims != other.dims:
            raise ValueError("Matrices must be of the same size")
        f = (lambda x, y: x - y) if subtract else (lambda x, y: x + y)
        rows, cols = self.dims
        return Matrix([[f(self[r][c], other[r][c]) for c in range(cols)]
            for r in range(rows)])

    def __sub__(self, other): return self.__add__(other, True)
    def __neg__(self): return self * (-1)

    def tr(self):
        "Transpose a matrix"
        rows, cols = self.dims
        return Matrix([[self[r][c] for r in range(rows)] for c in range(cols)])

    def minor(self, r, c):
        "Calculate a minor matrix"
        rows, cols = self.dims
        return Matrix([[self[row][col] for col in range(cols) if col != c]
            for row in range(rows) if row != r])

    def cof(self, r, c):
        "Calculate a single cofactor"
        d = self.minor(r, c).det
        return -d if (r + c) % 2 else d

    def cofactors(self):
        "Calculate a cofactor matrix"
        rows, cols = self.dims
        return Matrix([[self.cof(r,c) for c in range(cols)]
            for r in range(rows)])

    @property
    def det(self):
        "Calculate the determinant of a square matrix"
        rows = self._assertSquare()
        if rows == 1: return self[0][0]
        return sum([self[0][c] * self.cof(0, c) for c in range(rows)])

    def inv(self):
        "Calculate the inverse of a square matrix"
        rows = self._assertSquare()
        if rows == 1: return Matrix([[1/self[0][0]]])
        m = self.cofactors().tr()
        d = self.det
        return m.apply(lambda x: x/d)

    def leastSquares(self, y):
        "Find the coefficients for a linear least squares fit: [y] = [self][c]"
        if not isinstance(y, Matrix):
            y = Matrix([y]).tr()
        t = self.tr()
        return ((t * self).inv() * t * y).tr()[0]


# Simple regressions (x and y are lists)...

from math import log, exp

def linReg(x, y):
    "Calculate [b, m] for y = mx+b model"
    return Matrix([[1, a] for a in x]).leastSquares(y)

def powReg(x, y):
    "Calculate [a, n] for y = ax^n model"
    a, n = linReg([log(a) for a in x], [log(a) for a in y])
    return exp(a), n

def expReg(x, y):
    "Calculate [a, b] for y = ab^x model"
    a, b = linReg(x, [log(a) for a in y])
    return exp(a), exp(b)

def quadReg(x, y):
    "Calculate [c, b, a] for y = ax^2+bx+c model"
    return Matrix([[1, a, a**2] for a in x]).leastSquares(y)
