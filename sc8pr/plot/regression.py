# Copyright 2015-2021 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

"Regression (least squares) analysis"

from math import exp, log

def leastSq(x, y):
    "Perform a simple least squares linear regression"
    n = len(x)
    if len(y) != n: raise ValueError("x and y data must be the same size")
    xav = sum(x) / n
    yav = sum(y) / n
    m = sum((x[i] - xav) * (y[i] - yav) for i in range(n))
    m /= sum((xi - xav) ** 2 for xi in x)
    b = yav - m * xav
    return (lambda x: m * x + b), (m, b)

def power(x, y):
    "Least squares fit to model y = a x**n"
    x = [log(xi) for xi in x]
    y = [log(xi) for xi in y]
    n, a = leastSq(x, y)[1]
    a = exp(a)
    return (lambda x:a * x**n), (a, n)

def expon(x, y):
    "Least squares fit to model y = a b**x"
    y = [log(xi) for xi in y]
    b, a = [exp(a) for a in leastSq(x, y)[1]]
    return (lambda x:a * b**x), (a, b)
