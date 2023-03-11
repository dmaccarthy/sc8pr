import pygame
from pygame.draw import circle, polygon
from math import hypot, ceil, pi, cos, sin
from sc8pr.util import surface, rgba
from sc8pr.effect import Effect
from sc8pr.shape import Polygon

class Stamp(Effect):
    _fill = rgba("white")

    @staticmethod
    def new_surface(size):
        srf = pygame.Surface(size).convert_alpha()
        srf.fill(4*(0,))
        return srf

    def apply_stamp(self, img, n):
        srf = surface(self.get_stamp(n, img.get_size()))
        srf.blit(img, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        return srf

    def apply(self, img, n=0):
        img = surface(img, True)
        if n <= 0 or n >= 1: return self.nofx(img, n)
        return self.apply_stamp(img, n)


class Pupil(Stamp):
    sides = None

    def __init__(self, center=(0.5, 0.5), **kwargs):
        self.center = center
        self.config(**kwargs)

    def angle(self, t): return 90 - 180 / self.sides

    def get_stamp(self, t, size):
        w, h = size
        x, y = self.center
        x = (w-1) * x
        y = (h-1) * (1-y)
        r = 1 + ceil(t * hypot(max(x, w-x), max(y, h-y)))
        srf = self.new_surface(size)
        if self.sides is None: circle(srf, self._fill, (x, y), r)
        else:
            a = 2 * pi / self.sides
            r /= cos(a/2)
            pts = [(r*cos(i*a), r*sin(i*a)) for i in range(self.sides)]
            poly = Polygon(pts, (0,0)).config(angle=self.angle(t)).config(pos=(x, y))
            polygon(srf, self._fill, poly.vertices)
        return srf
