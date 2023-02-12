# Copyright 2015-2023 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"Robot Parking Lot Simulation"

from random import randint, uniform, choice
from sc8pr.shape import Line, Circle
from sc8pr.sprite import physics, Sprite
from sc8pr.robot.arena import BrainSketch, Robot


class ParkingLot(BrainSketch):
    "Sketch that implements a robot parking challenge"

    def __init__(self, size, brain):
        self.brain = brain
        super().__init__(size)
        self.config(bg="#f0f0f0")

    def drawLot(self):
        self += Line((-2.7, 0), (2.7, 0)).config(weight=10, stroke="blue")
        attr = dict(stroke="orange", weight=4)
        for x in range(-2, 3):
            self += Line((x, 2), (x, 1)).config(**attr)
            self += Line((x, -2), (x, -1)).config(**attr)
        self.flatten()
        img = Circle(0.4 * self.unit).config(fill="grey", weight=0).snapshot()
        for x in range(-3, 3):
            self += Sprite(img).config(xy=(x + 0.5, 2.36), mass=50, drag=0.02, wrap=0)
            self += Sprite(img).config(xy=(x + 0.5, -2.37), mass=50, drag=0.02, wrap=0)
        return self

    def setup(self):
        self.attachCS([-3, 3, -2, 2]).drawLot()
        h = self.height / 4.5
        attr = dict(height = h, mass = 1, wrap=0)
        robot = Robot(["#ffd428", "#ff5050"]).config(
            xy = (uniform(-2, 2), 0), angle = randint(0, 359), **attr)
        self["Crash"] = self.bindBrain(robot)
        c = False, False
        a = 90, 270
        pos = lambda y: (randint(0, 5) - 2.5, y)
        br = lambda *x: self.idle if randint(0, 1) == 0 else (lambda x: None)
        self += Robot(c).bind(brain=br()).config(xy=pos(1.46), angle=choice(a), **attr)
        self += Robot(c).bind(brain=br()).config(xy=pos(-1.46), angle=choice(a), **attr)

    def ondraw(self, ev=None): return physics(self)

    @staticmethod
    def idle(r):
        while r.active: r.updateSensors(0.5)

    @staticmethod
    def run(brain=None):
        ParkingLot((640,360), brain).play("Robot Parking Lot", mode=False)
