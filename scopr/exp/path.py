class Path:

    def __init__(self, *args): self.data = list(args)
    def append(self, x): self.data.append(x)
    def extend(self, x): self.data.extend(x)

    @staticmethod
    def scale(path, size, closed=False):
        w, h = size
        path = [(w*x, h*y) for x,y in path]
        if closed: path.append(path[0])
        return Path(path)

    def segments(self):
        "Generator for all line segments within the path"
        for p in self.data:
            i = 1
            while i < len(p):
                yield p[i-1], p[i]
                i += 1

    def closest(self, pt, within=None):
        "Return tuple (distance, (x,y), segment) for closest point on path to pt"
        found = None
        for s in self.segments():
            r, p = pointSegment(s[0], s[1], pt)
            if within and r <= within: return True
            if not found or r < found[0]:
                found = r, p, s
        return False if within else found

    def transform(self, shift=(0,0), factor=1):
        "Transform all of the points within a path instance"
        sx, sy = shift
        for i in range(len(self.data)):
            path = self.data[i]
            self.data[i] = [(factor * x + sx, factor * y + sy) for x,y in path]
