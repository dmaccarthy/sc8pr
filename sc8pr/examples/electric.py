# Copyright 2015-2020 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"A simulation of the electric force (Coulomb's Law) between two spheres"

from math import hypot, asin, degrees
from random import uniform
from sc8pr import Sketch, Canvas, Image, BOTTOM, TOPRIGHT, TOPLEFT
from sc8pr.shape import Circle, Line
from sc8pr.text import Text, Font, BOLD
from sc8pr.geom import delta
from sc8pr.util import ondrag
from sc8pr.misc.cursors import hand
from sc8pr.gui.dialog import MessageBox

MONO = Font.mono()


class Simulation(Sketch):

    @property
    def scale(self): return 10 * self.width / 640

    def __init__(self):
        self.mass = uniform(1, 4)
        self.q1 = uniform(0.1, 0.4)
        self.q2 = uniform(0.1, 0.4)
        super().__init__((640,256))

    def setup(self):
        self.caption = "Electric Force Simulation"
        w, h = self.size
        y = h - 40
        x = w / 1.5
        pivot = x, y - 200
        self["string"] = Line(pivot, (x, y)).config(weight=3)
        self += Charge().config(pos=(x, y))
        self["blue"] = Circle(60).config(fill="blue").snapshot().bind(ondrag).config(pos=(40,y), height=24)
        self["angle"] = Text().config(pos=pivot, anchor=TOPRIGHT,
            font=MONO, color="red").config(height=24).bind(ondrag)
        self += Ruler(self.scale).config(pos=self.center)
        msg = "Red Sphere\n m = {:.2f} g\n q = {:.0f} nC\n\nBlue Sphere\n q = {:.0f} nC"
        msg = msg.format(self.mass, 1000*self.q1, 1000*self.q2)
        self += MessageBox(msg, buttons="Close", fontSize=14,
            font=MONO).bind(ondrag).config(pos=(8,8), anchor=TOPLEFT)

    def onmouseover(self, ev): self.cursor = hand

    def ondraw(self):
        if self.evMgr.hover is self: self.cursor = True


class Charge(Image):

    def __init__(self):
        img = Circle(60).config(fill="red").snapshot()
        super().__init__(img)
        self.config(height=24, vel=(0, 0))

    def ondraw(self):

        # Calculate electric force
        sk = self.sketch
        dr = delta(self.pos, sk["blue"].pos)
        r = hypot(*dr) / sk.scale / 100
        F = delta(dr, mag = 8.99e-3 * sk.q1 * sk.q2 / (r * r))

        # Add electric plus gravitational forces 
        F = F[0], F[1] + sk.mass * 9.81e-3

        # Tangential acceleration
        s = sk["string"]
        u = s.u
        t = 1 / sk.frameRate
        F = (F[0] * u[1] - F[1] * u[0]) / (sk.mass / 1000) * (sk.scale / 100) / t ** 2
        ax, ay = F * u[1], -F * u[0]

        # Kinematics
        v1x, v1y = tuple(0.95 * v for v in self.vel)
        v2x = v1x + ax * t
        v2y = v1y + ay * t
        self.vel = v2x, v2y
        x, y = self.pos
        x += (v1x + v2x) * t / 2
        y += (v1y + v2y) * t / 2
        x, y = delta((x,y), s.pos, 20 * sk.scale)
        self.pos = s.pos[0] + x, s.pos[1] + y
        s.__init__(s.pos, self.pos)

        # Protractor
        if s.u[1] > 0:
            a = round(2 * degrees(asin(s.u[0]))) / 2
            a = "Angle = {:.1f}°".format(abs(a))
        else: a = "Angle > 90°"
        sk["angle"].config(data=a)


class Ruler(Canvas):

    def __init__(self, scale=10, size=50, step=5, unit=("cm", 2), **cfg):
        if "bg" not in cfg: cfg["bg"] = Image(bg="#e0e0f0a0")
        if "weight" not in cfg: cfg["weight"] = 1
        coord = lambda x: (x + 1) * scale
        h = 3.5 * scale
        super().__init__((coord(size + 1), h))
        self.config(**cfg)
        x = 0
        cfg = dict(anchor=BOTTOM, font=MONO, fontStyle=BOLD, color="#000000a0")
        while x <= size:
            self += Text(x).config(pos=(coord(x), h-1), **cfg)
            x += step
        if unit: self += Text(unit[0]).config(pos=(coord(unit[1]), h-1), **cfg)
        x = 0
        while x <= size:
            s = coord(x)
            self += Line((s,0), (s, scale / (2 if x % step else 1)))
            x += 1
        for t in self:
            if isinstance(t, Text): t.config(height=h/2)
        self.bind(ondrag)


def play(): Simulation().play()
main = play

if __name__ == "__main__": play()
