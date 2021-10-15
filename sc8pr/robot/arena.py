# Copyright 2015-2021 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"Robot Arena Simulations"

from math import pi, sin, cos, atan2
from random import randint, uniform, choice, shuffle
from sc8pr import Image, Canvas, BOTH
from sc8pr.geom import shiftAlongNormal, angleDifference, DEG
from sc8pr.shape import Polygon, Line, Circle
from sc8pr.util import rangef
from sc8pr.robot.gui import Robot as _Robot
from sc8pr.sprite import physics, Sprite
from sc8pr.plot import PSketch, PCanvas


class Robot(_Robot):

    def __init__(self, colors=None):
        super().__init__(colors)
        self.gyroSample()

    def gyroSample(self, t=None):
        self.gyroChange = 0.0
        self._gyro_data = []
        self._gyro_sample = t if t is None else round(self.sketch.frameRate * t)

    def ondraw(self):
        _Robot.ondraw(self)
        if self._gyro_sample: self.get_gyro_data()

    def get_gyro_data(self):
        data = self._gyro_data
        data.append(self.gyro)
        n = len(data)
        if n > self._gyro_sample:
            x = sum(cos(g * DEG) for g in data) / n
            y = sum(sin(g * DEG) for g in data) / n
            gyro = atan2(y, x) / DEG
            gyro1 = max(angleDifference(gyro, g) for g in data)
            gyro2 = min(angleDifference(gyro, g) for g in data)
            self.gyroChange = gyro1 - gyro2
            data.pop(0)
        else:
            self.gyroChange = None


def quilt(sk):
    "Draw some colors on the floor in a quilt pattern"
    w, h = sk.size
    w = (w - 64) // 6
    h = (h - 64) // 4
    cv = Canvas(sk.size, "grey")
    c = [
        "pink", "darkgreen", "mintcream", "gold", "white", "cyan",
        "yellow", "blue", "brown", "tan2", "royalblue", "steelblue",
        "violet", "orange", "skyblue", "black", "tomato", "seashell",
        "salmon", "turquoise", "red", "magenta", "purple", "green",
    ]
    shuffle(c)
    for i in range(4):
        for j in range(6):
            color = c[j + 6 * i]
            cv += Image((w, h), color).config(pos=(32 + (j + 0.5) * w, 32 + (i + 0.5) * h))
    return cv.snapshot()

def curve(size, color="blue"):
    size = getattr(size, "size", size)
    cv = PCanvas(size, [-4, 4, -2, 2]).config(bg="white")
    c = lambda *x: 2 * size[0] / size[1] * cos(x[0])
    top = [(x, sin(x)) for x in rangef(-pi, pi, pi/40)]
    bot = [shiftAlongNormal(*x, c, -0.08) for x in top]
    blu = [cv.px(*x) for x in (top + list(reversed(bot)))]
    cv += Polygon(blu).config(fill=color, weight=0)
    return cv.snapshot()


class BrainSketch(PSketch):
    "Sketch class that binds a robot brain OR attaches a robot remote control"

    @staticmethod
    def sensorBrain(robot):
        "Update sensors only"
        while robot.active: robot.updateSensors()

    def bindBrain(self, robot):
        brain = self.brain
        if brain is None:
            self.bind(onkeydown=Robot.remoteControl).config(remoteRobot=robot)
            brain = self.sensorBrain
        return robot.bind(brain=brain)


class Arena(BrainSketch):
    "Empty arena for robot challenges"

    def setup(self):
        try:
            img = self.pattern
            try: self.bg = img(self)
            except: self.bg = Image(img)
        except: self.bg = Image(self.size, "white")
        self.weight = 1
        robo = Robot(["#ff5050", "#ffd428"])
        self["Red"] = self.bindBrain(robo).config(width=64,
            pos=self.center, angle=270, bounce=BOTH)
        robo.gyro = robo.angle

    @classmethod
    def run(cls, brain=None, pattern=None):
        cls((640,480)).config(brain=brain, pattern=pattern).play("Robot Arena")


class ParkingLot(BrainSketch):
    "Sketch that implements a robot parking challenge"

    def __init__(self, size, brain):
        self.brain = brain
        super().__init__(size, [-3, 3, -2, 2])
        self.config(bg="#f0f0f0")

    def drawLot(self):
        px = self.px
        self += Line(px(-2.7, 0), px(2.7, 0)).config(weight=10, stroke="blue")
        attr = dict(stroke="orange", weight=4)
        for x in range(-2, 3):
            self += Line(px(x, 2), px(x, 1)).config(**attr)
            self += Line(px(x, -2), px(x, -1)).config(**attr)
        self.flatten()
        img = Circle(0.4 * self.unit).config(fill="grey", weight=0).snapshot()
        for x in range(-3, 3):
            self += Sprite(img).config(pos=px(x + 0.5, 2.36), mass=50, drag=0.02, wrap=0)
            self += Sprite(img).config(pos=px(x + 0.5, -2.37), mass=50, drag=0.02, wrap=0)
        return self

    def setup(self):
        self.drawLot()
        h = self.height / 4.5
        attr = dict(height = h, mass = 1, wrap=0)
        robot = Robot(["#ffd428", "#ff5050"]).config(
            pos = self.px(uniform(-2, 2), 0), angle = randint(0, 359), **attr)
        self["Crash"] = self.bindBrain(robot)
        c = False, False
        a = 90, 270
        pos = lambda y: self.px(randint(0, 5) - 2.5, y)
        br = lambda *x: self.idle if randint(0, 1) == 0 else (lambda x: None)
        self += Robot(c).bind(brain=br()).config(pos=pos(1.46), angle=choice(a), **attr)
        self += Robot(c).bind(brain=br()).config(pos=pos(-1.46), angle=choice(a), **attr)

    ondraw = physics

    @staticmethod
    def idle(r):
        while r.active: r.updateSensors(0.5)

    @staticmethod
    def run(brain=None):
        ParkingLot((640,360), brain).play("Robot Parking Lot", mode=False)
