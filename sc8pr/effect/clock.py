import pygame
from sc8pr.effect.stamp import Stamp
from sc8pr.shape import Polygon, Line
from sc8pr.effect import Effect
from sc8pr import Canvas, TOPLEFT
from sc8pr.geom import vec2d
from sc8pr.util import surface


class Clock(Polygon):

    def __init__(self, a):
        super().__init__([(0,0), (0,1), (1,1)])
        self.setAngle(a)

    def setAngle(self, a):
        self._angle = a
        self.vertices = self.clock_vert(a)
        self.config(anchor = 0)
        return self

    def __iadd__(self, a):
        self.setAngle(self._angle + a)

    def __isub__(self, a):
        self.setAngle(self._angle - a)

    @staticmethod
    def clock_vert(a):
        x = 1.01
        view = Polygon([(x, x), (x, -x), (-x, -x), (-x, x)])
        hand = Line((0, 0), vec2d(1.5, 90-a))
        ipt = None
        i = 0
        for s in view.segments:
            pt = hand.intersect(s)
            if pt: ipt = pt, i
            i += 1
        ipt, i = ipt
        if i == 0 and ipt[0] < 0: i = 4
        return [(0, 0), (0, x)] + view.vertices[:i] + [ipt]


class ClockHand(Stamp):

    def __init__(self, size):
        self.stamp = self.clock_stamp(size)

    def get_stamp(self, n, size):
        "Update the stamp canvas and return it"
        if self.stamp.size != size:
            self.stamp = self.clock_stamp(size)
        self.stamp[0].setAngle(360 * n)
        return self.stamp

    @staticmethod
    def clock_stamp(size):
        "Create a canvas for rendering the clock stamp"
        cv = Canvas(size).config(anchor=TOPLEFT)
        a = min(1, cv.aspectRatio)
        cv.attachCS([-a, a])
        Clock(20).config(fill="white", weight=0).setCanvas(cv)
        return cv
