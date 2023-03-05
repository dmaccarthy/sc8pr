import pygame
from pygame.draw import circle
from math import hypot, ceil
from sc8pr.util import surface, rgba
from sc8pr.effect import Effect

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
        img = surface(img)
        if n <= 0 or n >= 1: return self.nofx(img, n)
        return self.apply_stamp(img, n)


class Pupil(Stamp):

    def __init__(self, center=(0.5, 0.5), **kwargs):
        self.center = center
        self.config(**kwargs)
    
    def get_stamp(self, t, size):
        w, h = size
        x, y = self.center
        x = (w-1) * x
        y = (h-1) * (1-y)
        r = 1 + ceil(t * hypot(max(x, w-x), max(y, h-y)))
        srf = self.new_surface(size)
        circle(srf, self._fill, (x, y), r)
        return srf
