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

    multError = ValueError("Incompatible dimensions for matrix multiplication")

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
            for v in row: s += frmt.format(v)
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
        if n != other.rows: raise Matrix.multError
        cols = other.cols
        return Matrix([[sum([row[i] * other[i][c] for i in range(n)])
            for c in range(cols)] for row in self])
    
    def __mul__(self, other):
        "Multiple by a matrix or number"
        return (self.__matmult__(other) if isinstance(other, Matrix) else
            Matrix([[other * row[c] for c in range(self.cols)] for row in self]))

    def __truediv__(self, other): return self * (1/other)
    def __imul__(self, other): return self * other
    __rmul__ = __mul__

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

    def __eq__(self, other):
        "Compare matrices"
        if self.dims != other.dims: return False
        for i in range(self.rows):
            if self[i] != other[i]: return False
        return True

    def tr(self):
        "Transpose a matrix"
        return Matrix([[row[c] for row in self] for c in range(self.cols)])

    def inv(self):
        "Invert by Gauss-Jordan elimination"
        rows = self._assertSquare()
        a = self.clone()
        for r in range(rows):
            a[r].extend([1 if i == r else 0 for i in range(rows)])
        a = a.rref()
        for r in range(rows):
            for c in range(rows):
                if a[r][c] != 1 if r == c else 0:
                    return None
            a._rows[r] = a[r][rows:]
        return a

    def trx(self, other, rev=False):
        "Faster version of self.tr() * other"
        n, rows = self.dims
        m, cols = other.dims
        if n != m: raise Matrix.multError
        if rev:
            fn = lambda a, b, r, c, n: sum(a[r][i]*b[c][i] for i in range(n))
        else:
            fn = lambda a, b, r, c, n: sum(a[i][r]*b[i][c] for i in range(n))
        return Matrix([[fn(self, other, r, c, n) for c in range(cols)] for r in range(rows)])

    def xtr(self, other):
        "Faster version of self * other.tr()"
        return self.trx(other, True)

    def rowAdd(self, a, b, s=None):
        "Add a (multiple of) row 'b' to row 'a'"
        a = self[a]
        b = self[b]
        for i in range(self.cols):
            a[i] += b[i] if s is None else s * b[i]
        return self

    def rowNorm(self, *args):
        "Make first non-zero element equal to 1"
        if len(args) == 0: args = range(self.rows)
        for r in args:
            r = self[r]
            s = None
            for i in range(self.cols):
                if r[i] != 0:
                    if s is None:
                        s = r[i]
                        r[i] = 1
                    else: r[i] /= s
        return self

    @staticmethod
    def _echelonKey(row):
        "Key for sorting rows in row echelon form algorithm"
        i = 0
        n = len(row)
        while i < n and row[i] == 0:
            i += 1
        return i

    def _zero(self, n):
        "Elimination of one variable"
        k = self._echelonKey(self[n])
        for i in range(self.rows):
            s = self[i][k]
            if s and i != n:
                self.rowAdd(i, n, -s)
                self.rowNorm(i)
        return self

    def _ref(self, reduced=False):
        "Row echelon form; in-place"
        self.rowNorm()
        for r in range(self.rows - 1):
            self._rows.sort(key=self._echelonKey)
            self._zero(r)
        if reduced:
            for r in range(self.rows - 1, 0, -1):
                self._zero(r)
        return self

    def ref(self, reduced=False):
        "Row echelon form; new matrix"
        return self.clone()._ref(reduced)

    def rref(self):
        "Reduced row echelon form; new matrix"
        return self.ref(True)

    def leastSquares(self, y):
        "Find the coefficients for a linear least squares fit: [y] = [self][c]"
        if not isinstance(y, Matrix):
            y = Matrix([y]).tr()
        t = self.tr()
        return [c[0] for c in (t * self).inv() * t * y]

# Inefficient methods involving the determinant...
#
#     def minor(self, r, c):
#         "Calculate a minor matrix"
#         rows, cols = self.dims
#         return Matrix([[self[row][col] for col in range(cols) if col != c]
#             for row in range(rows) if row != r])
# 
#     def cof(self, r, c):
#         "Calculate a single cofactor"
#         d = self.minor(r, c).det
#         return -d if (r + c) % 2 else d
# 
#     def cofactors(self):
#         "Calculate a cofactor matrix"
#         rows, cols = self.dims
#         return Matrix([[self.cof(r,c) for c in range(cols)]
#             for r in range(rows)])
# 
#     @property
#     def det(self):
#         "Calculate the determinant of a square matrix"
#         rows = self._assertSquare()
#         if rows == 1: return self[0][0]
#         return sum([self[0][c] * self.cof(0, c) for c in range(rows)])
# 
#     def invc(self):
#         "Invert by cofactor method"
#         rows = self._assertSquare()
#         if rows == 1: return Matrix([[1/self[0][0]]])
#         m = self.cofactors().tr()
#         d = self.det
#         return m.apply(lambda x: x/d)


# Simple regressions (x and y are lists)...

from math import log, exp

def _regData(xy):
    return [x[0] for x in xy], [x[1] for x in xy]

def linReg(x, y=None):
    "Calculate [b, m] for y = mx+b model"
    if y is None: x, y = _regData(x)
    return Matrix([[1, a] for a in x]).leastSquares(y)

def powReg(x, y=None):
    "Calculate [a, n] for y = ax^n model"
    if y is None: x, y = _regData(x)
    a, n = linReg([log(a) for a in x], [log(a) for a in y])
    return exp(a), n

def expReg(x, y=None):
    "Calculate [a, b] for y = ab^x model"
    if y is None: x, y = _regData(x)
    a, b = linReg(x, [log(a) for a in y])
    return exp(a), exp(b)

def quadReg(x, y=None):
    "Calculate [c, b, a] for y = ax^2+bx+c model"
    if y is None: x, y = _regData(x)
    return Matrix([[1, a, a**2] for a in x]).leastSquares(y)
