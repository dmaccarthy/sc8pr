import pygame
from pygame.draw import circle, polygon
from math import hypot, ceil, pi, cos, sin
from sc8pr.util import surface, rgba
from sc8pr.effect import Effect
from sc8pr.shape import Polygon

class Stamp(Effect):
    _fill = rgba("white")
    special_flags = pygame.BLEND_RGBA_MIN

    @staticmethod
    def new_surface(size):
        srf = pygame.Surface(size).convert_alpha()
        srf.fill(4*(0,))
        return srf

    def apply(self, img, n=0):
        img = surface(img, True)
        if n <= 0 or n >= 1: return self.nofx(img, n)
        srf = surface(self.get_stamp(n, img.get_size()))
        srf.blit(img, (0, 0), special_flags=self.special_flags)
        return srf


class Pupil(Stamp):
    sides = None
    center = 0.5, 0.5

    def get_stamp(self, t, size):
        w, h = size
        x, y = self.center
        x = (w-1) * x
        y = (h-1) * (1-y)
        r = 1 + ceil(t * hypot(max(x, w-x), max(y, h-y)))
        srf = self.new_surface(size)
        if self.sides is None: circle(srf, self._fill, (x, y), r)
        else:
            angle = 90 - 180 / self.sides
            a = 2 * pi / self.sides
            r /= cos(a/2)
            pts = [(r*cos(i*a), r*sin(i*a)) for i in range(self.sides)]
            poly = Polygon(pts, (0,0)).config(angle=angle).config(pos=(x, y))
            polygon(srf, self._fill, poly.vertices)
        return srf
