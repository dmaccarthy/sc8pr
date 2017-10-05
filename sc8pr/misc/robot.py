# Copyright 2015-2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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


from time import sleep, time
from threading import Thread
from sys import stderr
from math import hypot, asin, cos, sqrt, pi
import pygame
from pygame.constants import K_UP, K_DOWN, K_LEFT, K_RIGHT, K_SPACE
from sc8pr import Image, Sketch
from sc8pr.sprite import Sprite
from sc8pr.util import sc8prData, logError, rgba, noise, divAlpha
from sc8pr.geom import vec2d, delta, DEG, dist, sprod, positiveAngle
from sc8pr.shape import Line


class RobotThread(Thread):
    "Control a Robot instance in a separate thread"

    log = True

    def __init__(self, robot):
        super().__init__()
        self.robot = robot

    def run(self):
        r = self.robot
        if self.log:
            args = r, id(self)
            print('{} is running in thread {}.'.format(*args), file=stderr)
        try:
            while r.startup: r.sleep()
            r._startTime = time()
            r.brain()
            if r.shutdown: r.shutdown()
        except: logError()
        if self.log:
            print('{} is shutting down in thread {}.'.format(*args), file=stderr)


class InactiveError(Exception):
    def __init__(self): super().__init__("Robot is no longer active")


class Robot(Sprite):
    _motors = 0, 0
    _updateSensors = True
    startup = True
    sensorNoise = 8
    collision = False
    maxSpeed = 1 / 512
    shutdown = None
    sensorDown = None
    sensorFront = None
    sensorWidth = 10
    proximity = None

    def __init__(self, colors=None):
        img = Image.fromBytes(sc8prData("robot"))
        if colors:
            px = pygame.PixelArray(img.image)
            for i in range(2):
                c = 255 * (1 - i), 0, 255*i
                px.replace(c, rgba(colors[i]))
        img = img.tiles(2)
        super().__init__(img)

    @property
    def uptime(self): return time() - self._startTime

    @property
    def gyro(self):
        return positiveAngle(self.angle - self._gyro)

    @gyro.setter
    def gyro(self, g):
        self._gyro = positiveAngle(g - self.angle)

    @property
    def stopped(self): return self.vel == (0,0)

    def setCanvas(self, sk):
        if not isinstance(sk, Sketch):
            raise Exception("Robot cannot be added to {}".format(type(sk).__name__))
        b = hasattr(self, "brain")
        if b and self.canvas: raise Exception("Robot is already active!")
        super().setCanvas(sk)
        if b:
            self._startFrame = sk.frameCount
            self._gyro = self.angle
            RobotThread(self).start()

    @property
    def active(self):
        try: return not self.sketch.quit
        except: return False

    def updateSensors(self, wait=None):
        self._updateSensors = True
        self.sleep(wait)
        return self

    def sleep(self, t=None):
        "Sleep for the specified time"
        if t: sleep(t)
        else:
            if not self.active: raise InactiveError()
            sleep(1 / self.sketch.frameRate)

    @property
    def motors(self): return self._motors

    @motors.setter
    def motors(self, m):
        if type(m) in (int, float): m = (m, m)
        self._motors = tuple(max(-1, min(1, x)) for x in m)

    @property
    def power(self): return sum(abs(m) for m in self._motors) / 2

    def onbounce(self, sk, wall):
        "Adjust motion upon collision with wall"
        w, h = sk.size
        x, y = self.pos
        r = self.radius
        vx, vy = self.vel
        x1 = w - 1 - r
        y1 = h - 1 - r
        if x < r: x, vx = r, 0
        elif x > x1: x, vx = x1, 0
        if y < r: y, vy = r, 0
        elif y > y1: y, vy = y1, 0
        self.pos = x, y
        self.vel = vx, vy
        self.collision = True

    def oncollide(self): self.collision = True

    def ondraw(self):
        "Update robot sprite each frame"

        if not self.active: raise InactiveError()

        # Target wheel speed...
        sk = self.sketch
        v = self.maxSpeed * sk.width
        v1, v2 = self._motors
        v1 *= v
        v2 *= v

        # Angular speed and turning radius...
        w = (v1 - v2) / (2 * self.radius)
        self.spin = w / DEG
        if w:
            R = (v1 + v2) / (2 * w)
            v = w * R
        else: v = v1

        # Acceleration...
        v = vec2d(v, self.angle)
        a = delta(v, self.vel)
        if hypot(*a) > 0.05:
            self.acc = delta(a, mag=0.05)
        else:
            self.vel = v
            self.acc = 0, 0

        # Adjust wheel speed...
        p = self.power
        self.costumeTime = 0 if p == 0 else round(36 / (1 + 5 * p))

        # Update position and angle...
        super().ondraw()

        # Update sensors if requested...
        if self._updateSensors:
            try:
                self.checkDown()
                self.checkFront()
                self.drawLEDs()
                self._updateSensors = False
            except: logError()
        self.startup = False

    def sensorObjects(self, sk): return list(sk.sprites())

    def checkFront(self):
        "Update the front color sensor"

        # Get sensor position
        pos = delta(self.pos, vec2d(-self.radius, self.angle))

        # Sensor distance to edge of sketch
        sk = self.sketch
        obj = sk
        prox = _distToWall(pos, self.angle, self.sensorWidth, *sk.size)

        # Find closest object within sensor width
        u = vec2d(1, self.angle)
        sw = self.sensorWidth * DEG
        for gr in self.sensorObjects(sk):
            if gr is not self and gr.avgColor and hasattr(gr, "rect"):
                dr = delta(gr.rect.center, pos)
                d = hypot(*dr)
                r = gr.radius
                if r >= d:
                    prox = 0
                    obj = gr
                elif d - r < prox:
                    minDot = cos(min(sw + asin(r/d), pi / 2))
                    x = (1 - sprod(u, dr) / d) / (1 - minDot)
                    if x < 1:
                        obj = gr
                        prox = (d - r) * (1 - x) + x * sqrt(d*d-r*r)

        # Save data
        c = rgba(sk.border if obj is sk else obj.avgColor)
        self.sensorFront = noise(divAlpha(c), self.sensorNoise)
        self.proximity = prox
        self.closestObject = obj

    def checkDown(self):
        "Update the down color sensor"
        x, y = self.rect.center
        r = 0.8 * self.radius
        dx, dy = vec2d(r, self.angle)
        r = max(1, round(0.25 * r))
        d = 2 * r
        sk = self.sketch
        r = pygame.Rect(x + dx - r, y + dy - r, d, d).clip(sk.rect)
        if r.width:
            if isinstance(sk.bg, Image):
                c = pygame.transform.average_color(sk.bg.image.subsurface(r))
            else: c = sk.bg
        else: c = 0, 0, 0
        self.sensorDown = noise(c, self.sensorNoise)

    def drawLEDs(self):
        "Draw LEDs on the robot to indicate color sensor data"
        for costume in self._costumes:
            srfs = costume._srf
            orig = srfs.original
            r0 = orig.get_width() / 2
            r = round(0.18 * r0)
            x = round(1.25 * r0)
            for (c, y) in ((self.sensorDown, 1.3), (self.sensorFront, 0.7)):
                pos = x, round(y * r0)
                pygame.draw.circle(orig, c if c else (0,0,0), pos, r)
                pygame.draw.circle(orig, (0,0,0), pos, r, 1)
            srfs.dumpCache()

    @staticmethod
    def remote(sk, ev):
        try:
            r = sk.remote
            key = ev.key
            if key == K_SPACE: r.motors = 0
            else:
                dm = {K_UP:(1,1), K_DOWN:(-1,-1), K_LEFT:(-1,1), K_RIGHT:(1,-1)}
                r.motors = tuple(0.1 * dm[key][i] + r.motors[i] for i in (0,1))
        except: pass


def _distToWall(pos, angle, sWidth, w, h):
    "Calculate the distance to the sketch walls in the specified direction"
    walls = [(0,0), (w,0), (w,h), (0,h), (0,0)]
    walls = [Line(*walls[i:i+2]) for i in range(4)]
    d = None
    w += h
    for n in (-1, 0, 1):
        v = vec2d(w, angle + n * sWidth)
        pts = [Line(pos, vector=v).intersect(wall) for wall in walls]
        try:
            d1 = min(dist(pos, pt) for pt in pts if pt is not None)
            if d is None or d1 < d: d = d1
        except: pass
    return 0 if d is None else d
