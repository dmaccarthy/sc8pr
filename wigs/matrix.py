def dim(m, square=False):
    "Validate and return the dimensions of a matrix"
    rows = len(m)
    cols = len(m[0])
    if square and rows != cols:
        raise ValueError("Matrix must be square")
    for row in m:
        if len(row) != cols:
            raise ValueError("Inconsistent row size")
    return rows, cols

def _transpose(m):
    "Generate the transpose of a matrix"
    rows, cols = dim(m)
    for c in range(cols):
        yield [m[r][c] for r in range(rows)]

def _multiply(a, b):
    "Generate the product of two matrices"
    rows, n1 = dim(a)
    n2, cols = dim(b)
    if n1 != n2: raise ValueError("Incompatible sizes")
    for r in range(rows):
        yield [sum([a[r][i]*b[i][c] for i in range(n1)]) for c in range(cols)]

def _minor(m, r, c):
    "Generate a minor matrix"
    rows = dim(m, True)[0]
    for row in range(rows):
        if row != r:
            yield [m[row][col] for col in range(rows) if col != c]

def cofactor(m,r,c):
    "Calculate one cofactor from a square matrix"
    return determinant(minor(m,r,c)) * (-1 if (r+c) % 2 else 1)

def _cofactors(m):
    "Generate the cofactors of a square matrix"
    rows = dim(m, True)[0]
    for r in range(rows):
        yield [cofactor(m,r,c) for c in range(rows)]

def determinant(m):
    "Calculate the determinant of a square matrix"
    rows = dim(m, True)[0]
    if rows == 1: return m[0][0]
    return sum([m[0][c] * cofactor(m,0,c) for c in range(rows)])

def inverse(m):
    "Calculate the inverse of a square matrix"
    rows = dim(m, True)[0]
    if rows == 1: return [[1/m[0][0]]]
    mi = cofactors(m)
    d = determinant(m)
    for row in mi:
        for c in range(rows):
            row[c] /= d
    return mi

def _scalarTimes(m, s):
    "Multiply a matrix by a scalar"
    rows, cols = dim(m)
    for r in range(rows):
        yield [s * m[r][c] for c in range(cols)]

# Convert generators to lists...
def transpose(m): return list(_transpose(m))
def multiply(a,b): return list(_multiply(a,b))
def minor(m,r,c): return list(_minor(m,r,c))
def cofactors(m): return list(_cofactors(m))
def scalarTimes(m,s=1): return list(_scalarTimes(m,s))

    
a = [[5,1,2],[2,1,1]] # (2,5), (1,2)
b = transpose(a)
c = multiply(a,b)
d = inverse(c)
print(d)
d = multiply(c,d)
print(scalarTimes(d,5))

