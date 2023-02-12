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
from sc8pr import Sketch, Image, Canvas, BOTH
from sc8pr.geom import shiftAlongNormal, angleDifference, DEG
from sc8pr.shape import Polygon, Line, Circle
from sc8pr.util import rangef
from sc8pr.robot.gui import Robot as _Robot
from sc8pr.sprite import Sprite


class Robot(_Robot):

    def __init__(self, colors=None):
        super().__init__(colors)
        self.gyroSample()

    def gyroSample(self, t=None):
        self.gyroChange = 0.0
        self._gyro_data = []
        self._gyro_sample = t if t is None else round(self.sketch.frameRate * t)

    def ondraw(self, ev=None):
        _Robot.ondraw(self, ev)
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
    cv = Canvas(size).config(bg="white").attachCS([-4, 4, -2, 2])
    c = lambda *x: 2 * size[0] / size[1] * cos(x[0])
    top = [(x, sin(x)) for x in rangef(-pi, pi, pi/40)]
    bot = list(reversed([shiftAlongNormal(*x, c, -0.08) for x in top]))
    cv += Polygon(top + bot).config(fill=color, weight=0)
    return cv.snapshot()


class BrainSketch(Sketch):
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
