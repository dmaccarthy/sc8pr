from sc8pr.video.effects import Effect, EqnFilter
from random import uniform
from math import sqrt


class PaintDrops(EqnFilter):
    "Paint drop effect"
    
    def __init__(self, length, frame=None, drops=64):
        Effect.__init__(self, length, frame)
        self.params = {"side": length > 0}
        self.drops = [self.makeDrop() for i in range(drops)]
        n = sum([d[0] for d in self.drops])
        for d in self.drops: d[0] /= n

    def eqn(self, x, n, size, side):
        "Calculate paint boundary"
        if not side: n = 1 - n
        w, h = size
        y = 0
        xc = 0
        for d in self.drops:
            r = d[0] * w / 2
            R = 1.1 * r
            xc += r
            dx = abs(x - xc)
            if dx <= R:
                dy = sqrt(R * R - dx * dx)
                Y = (h + R) * self.posn(n, *d[1:]) + dy - R
                if Y > y: y = Y
            xc += r
        return round(y), side

    def posn(self, n, t1, t2):
        "Calculate drop position"
        if n < t1: return 0
        elif n > t2: return 1
        return (n - t1) / (t2 - t1)

    @staticmethod
    def makeDrop():
        "Create random diameter, start and end time"
        t1 = uniform(0, 0.8)
        t2 = uniform(t1 + 0.1, 1)
        return [uniform(0.1,1), min(t1, t2), max(t1, t2)]
