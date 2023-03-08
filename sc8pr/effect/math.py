from math import sin, tan, pi, sqrt
from random import uniform
import pygame
from pygame.pixelarray import PixelArray
from sc8pr.util import rgba, surface
from sc8pr.effect import Effect

TWO_PI = 2 * pi


class MathEffect(Effect):
    amplitude = middle = 0
    invert = False
    scaled = True
    above = True
    _fill = rgba("#00000000")

    @property
    def rising(self): return not self.above

    def limits(self, a, b):
        a, b = min(a,b), max(a, b)
        self.amplitude = (b - a) / 2
        self.middle = (a + b) / 2
        return self

    def apply(self, img, n=0):
        "Modify image based on equation provided"
        srf = surface(img)
        if n <= 0 or n >= 1: return self.nofx(srf, n)
        if self.invert: srf = pygame.transform.rotate(srf, 90)
        w, h = size = srf.get_size()
        if self.amplitude is None: y0 = 0
        else:
            h_adj = (1 if self.scaled else h) + 2 * self.amplitude
            y0 = 0 if self.rising is None else (n if self.rising else (1 - n)) * h_adj - self.amplitude - self.middle

        # Fill using PixelArray
        pxa = PixelArray(srf)
        x = 0
        for pxCol in pxa:
            y = self.func(x / (w - 1) if self.scaled else x, n, size)
            if type(y) is tuple:
                y, above = y
            else: above = self.above
            y += y0
            y = h - 1 - round((h - 1) * y if self.scaled else y)
            if above:
                if y < h - 1:
                    if y < 0: y = 0
                    pxCol[y:] = self.fill
            elif y > 0:
                if y > h: y = h
                pxCol[:y] = self.fill
            x += 1

        return pygame.transform.rotate(srf, -90) if self.invert else srf


class Noise(MathEffect):

    def __init__(self, noise=0.15, **kwargs):
        self.amplitude = noise / 2
        self.config(**kwargs)

    def func(self, x, t, size):
        r = self.amplitude
        return uniform(-r, r)


class Wedge(MathEffect):

    def __init__(self, point=0.5, slope=2, **kwargs):
        self.point = point
        self.slope = slope
        self.amplitude = self.middle = slope * max(point, 1 - point) / 2
        self.config(**kwargs)

    def func(self, x, t, size):
        y = self.slope * (self.point - x) * (1 if x < self.point else -1)
        return y if self.above else -y


class Wipe(MathEffect):

    @property
    def rising(self): return None if type(self.slope) is bool else not self.above

    def __init__(self, slope=True, **kwargs):
        self.slope = slope
        self.amplitude = abs(slope) / 2
        self.config(**kwargs)

    def func(self, x, t, size):
        m = self.slope
        if m is False: x = 1 - x
        return (-1 if x < t else 1) if type(m) is bool else m * (x - 0.5)


class Waves(MathEffect):
    "Rising waves"
    speed = 0.6
    above = False

    def __init__(self, *args, **kwargs):
        # speed is total displacement over transition as fraction of width
        # arg = (amplitude, wavelength, shift) as fraction of width/height
        # (0.03, -0.2, 0.1)... A is 3% of height, wavelength  is 20% of width, shift is 10% of width
        if not args: args = 6, 0.10, 0.15      # 6 waves, total A around 10%, wavelength around 15%
        if type(args[0]) in (float, int):
            N, A, wl = args
            args = [(A / N * uniform(0.5, 1.5), wl * uniform(0.5, 1.5) * (-1 if i % 2 else 1)) for i in range(N)]
        self.args = args = [list(a) for a in args]
        for a in args: a[1] = TWO_PI / a[1]
        self.amplitude = sum(abs(a[0]) for a in args)
        self.config(**kwargs)

    def func(self, x, t, size):
        p = self.args
        s = self.speed
        f = lambda a: a[0] * sin(abs(a[1]) * ((x + (-s if a[1] < 0 else s) * t) - (a[2] if len(a) > 2 else 0)))
        return sum(f(p[i]) for i in range(len(p)))

    def copy(self, n=-1):
        "Return the 'reversed' or copied wave"
        args = [[a[0], n * TWO_PI / a[1]] + list(a[2:]) for a in self.args]
        return WaterWaves(*args, speed=self.speed, fill=self.fill, above=self.above)


class PaintDrops(MathEffect):
    scaled = reverse = False
    amplitude = middle = None
    maxDrop = 6

    @property
    def rising(self): return None

    def __init__(self, drops=48, **kwargs):
        self.config(**kwargs)
        self.drops = list(self.makeDrops(drops))
    
    def makeDrops(self, n):
        drops = [uniform(1, self.maxDrop) for i in range(n)]
        f = sum(drops)
        x = None
        for d in drops:
            d /= f
            t1 = uniform(0, 0.5)
            t2 = uniform(t1 + 0.2, 0.98)
            if x is None: x = d / 2
            else: x += (d  + d0) / 2
            d0 = d
            yield x, d, t1, t2

    @staticmethod
    def dropPosn(drop, t, w, h):
        x, d, t1, t2 = drop
        y = (t - t1) / (t2 - t1)
        return (x * w, (y-d) * h), w * d / 1.9

    def func(self, x, t, size):
        drops = self.drops
        w, h = size
        i = 0
        y = 0
        for d in drops:
            (xc, yc), r = self.dropPosn(d, t, w, h)
            dx = abs(x - xc)
            if dx < r:
                yd = yc + (-1 if self.reverse else 1) * sqrt(r*r - dx*dx)
                if yd > y: y = yd
        return h - y if self.above else y


class ClockHand(MathEffect):
    clockwise = True

    @property
    def rising(self): return None

    def apply(self, img, n=0):
        try: self.m = tan(TWO_PI * (0.25 - n))
        except: self.m = None
        return super().apply(img, n)

    def func(self, x, t, size):
        if not self.clockwise: x = 1 - x
        if t < 0.5:
            return (-1, False) if x < 0.5 else self.m * (x - 0.5) + 0.5
        else:
            return -1 if x >= 0.5 else (-1 if t == 0.5 else self.m * (x - 0.5) + 0.5, False)
