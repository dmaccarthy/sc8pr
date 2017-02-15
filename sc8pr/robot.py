# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
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


from sc8pr.sketch import Sprite, VISIBLE
from sc8pr.image import Image
from sc8pr.geom import DEG, vsum, add, sub, times, vec2d, distSq, Segment, Polygon2D
from sc8pr.util import sc8prPath, Data, logError, rectAnchor, CENTER, noise
from pygame.draw import circle, line
from pygame import Rect, Color, K_UP, K_DOWN, K_LEFT, K_RIGHT, K_SPACE
from pygame.pixelarray import PixelArray
from math import cos, sin, pi, sqrt
from threading import Thread
from time import sleep
from sys import stderr


class EndOfWorld(Exception):
    "Exception raised after Environment thread is closed"

    def __init__(self):
        msg = "Brain still running {} after Environment closed!"
        msg = msg.format("(awaiting sensor input?)")
        super().__init__(msg)


class RobotThread(Thread):
    "Control a Robot instance in a separate thread"

    log = True

    def __init__(self, robot, brain):
        super().__init__()
        self.robot = robot
        self.brain = brain

    def run(self):
        r = self.robot
        b = self.brain
        if self.log:
            args = "{}.{}".format(b.__module__, b.__name__), r.name, id(self)
            print('{} is controlling "{}" in thread {}.'.format(*args), file=stderr)
        try:
            while r._starting: # Wait for sensors before starting brain
                r.sleep()
            r.startTime = r.sketch.time
            b(r)
        except: logError()
        r.shutdown()
        r.startTime = None
        if self.log:
            print('{} is shutting down in "{}".'.format(*args), file=stderr)


class Robot(Sprite):
    "Simulate a simple robot"

    _costumes = None
    _motors = 0.0, 0.0
    _obstacleCone = 8
    _proximity = None, None, None, None
    _starting = True
    _thread = None
    _downRect = None
    _stallTime = None
    _name = None
    sensorNoise = 12
    downColor = None
    mass = 1.0
    elasticity = 0.9
    arenaTime = 12
    startTime = None
    centerPen = False

    def __init__(self, sprites, brain=None, colors=None, *group, **kwargs):
        self.penColor = None
        costumes = self._makeCostumes(colors)
        super().__init__(sprites, costumes, *group, **kwargs)
        if "gyro" not in kwargs: self.gyro = 0
        self.circle()
        if brain is not None:
            self._thread = RobotThread(self, brain)
            self._thread.start()

    def __str__(self): return "<Robot [{}]>".format(self.name)

    @property
    def radius(self): return self.shape.radius

    @property
    def name(self):
        return self._name if self._name else "Robot_{}".format(id(self))

    @name.setter
    def name(self, name): self._name = name

    @property
    def stall(self):
        "Stall status as bool"
        return self._stallTime is not None

    @property
    def stallTime(self):
        "Return duration of current stall event"
        t = self._stallTime
        return 0.0 if t is None else (self.sketch.time - t)

    @property
    def gyro(self):
        "Gyroscope sensor"
        return self.angle + self._gyro

    @gyro.setter
    def gyro(self, v): self._gyro = v - self.angle

    def gyroCompass(self):
        "Calibrate gyroscope to axis directions"
        self._gyro = 0

    @property
    def state(self):
        "Return the state of the robot as a dictionary"
        return dict(environ=self.environ, motors=self.motors, stall=self.stall, stallTime=self.stallTime, proximity=self.proximity,
            downColor=self.downColor, frontColor=self.frontColor, uptime=self.uptime, gyro=self.gyro, penColor=self.penColor)

    @classmethod
    def _makeCostumes(cls, colors=None):
        "Create robot costumes from the specified colours"
        if cls._costumes is None:
            cls._costumes = Image(sc8prPath("robot/robot.png"))
        img = cls._costumes.clone()
        if colors:
            px = PixelArray(img.surface)
            px.replace((255,0,0), colors[0])
            px.replace((0,0,255), colors[1])
        return img.tiles(2)

    @property
    def environ(self):
        "Check if robot is in an active Environment"
        sk = self.sketch
        return not sk._quit and self in sk.sprites

    def _sleep(self):
        "Wait for the next sensor update"
        if not self.environ: raise EndOfWorld()
        sk = self.sketch
        n = sk.frameCount
        t = 0.4 / sk.frameRate
        i = 3
        while sk.frameCount == n and i:
            sleep(t)
            i -= 1

    def sleep(self, t=None, stop=False):
        "Sleep for the specified time"
        if t: sleep(t)
        else: self._sleep()
        if stop: self.motors = 0, 0

    def loadSounds(self, *args):
        self.sketch.loadSounds(*args)
        
    def sound(self, key, **kwargs):
        return self.sketch.sound(key, **kwargs)

    def shutdown(self):
        "Override if robot requires any shutdown actions"
        pass

    @property
    def penRadius(self): return round(self.radius / 10)

    @property
    def penColor(self): return self._pen

    @penColor.setter
    def penColor(self, c):
        self._pen = c if isinstance(c, Color) or c is None else Color(c)

    @property
    def motorsOff(self):
        "Return motor on/off status"
        m1, m2 = self.motors
        return m1 == 0.0 and m2 == 0.0

    def leds(self):
        "Draw luminous LED indicators"
        fc = self.frontColor
        colors = [self.downColor, fc if fc else (0,0,0), self.penColor]
        r1 = self.width / 5
        r2 = r1 / 2.5
        a = (self.angle + 60) * DEG
        x0, y0 = self.posn
        led = []
        for c in colors:
            x = x0 + r1 * cos(a)
            y = y0 + r1 * sin(a)
            if c is not None:
                img = Image.ellipse(r2, c, (0,0,0))
                xy = rectAnchor((x,y), img.size, CENTER).topleft
                led.append((img, xy))
            a -= pi / 1.5
        if c: self._penPosn = True if self.centerPen else (round(x), round(y))
        return led

    def update(self):
        "Draw LEDs before update"
        self.sketch._lumin.extend(self.leds())
        self.frameStep()

    @property
    def uptime(self):
        t = self.startTime
        return self.sketch.time - t if t else None

    @property
    def maxSpeed(self):
        "Calculate the maximum robot speed corresponding to full power"
        sk = self.sketch
        return (sk.width - 2 * self.radius) / (self.arenaTime * 60) #sk.frameRate)

    @property
    def averagePower(self):
        "Calculate average motor power"
        m1, m2 = self.motors[:2]
        return (abs(m1) + abs(m2)) / 2

    @property
    def motors(self): return self._motors

    @motors.setter
    def motors(self, value):
        "Set the motor power and (optional) shut-off time"
        m1, m2 = value[:2]
        if m1 < -1: m1 = -1
        elif m1 > 1: m1 = 1
        if m2 < -1: m2 = -1
        elif m2 > 1: m2 = 1
        self._motors = float(m1), float(m2)
        if len(value) > 2:
            self.sleep(value[2], True)

    @property
    def proximity(self):
        "Return distance in pixels to closes obstacle"
        return self._proximity[0]

    @property
    def frontColor(self):
        "Return front colour-sensor value"
        try:
            c = self._proximity[3]
            if self.sketch.light:
                x = times(self.sketch.light, 1 / 255)
                c = [round(c[i] * x[i]) for i in range(4)]
        except: c = None
        c = noise(c if c else (0, 0, 0), self.sensorNoise, alpha=255)
        return c

    def say(self, text): print("{}: {}".format(self.name, text))

    def _detectObstacles(self, cone=0, steps=None, group=None):
        "Detect obstacles in front of the robot"
        sk = self.sketch
        if steps is None: steps = max(1, cone)
        if group is None:
#            group = self.spriteList.search(status=VISIBLE)
            group = [s for s in self.spriteList if s.status == VISIBLE]
        if sk.wall:
            group = set(group) | set(self.sketch._wallPoly.segments)

        obst = {}
        r = sum(sk.size)
        stepAngle = cone / steps
        angle = -cone / 2
        while steps >= 0:
            a = (self.angle + angle) * DEG
            seg = Segment(self.posn, add(self.posn, vec2d(r, a)))
            if sk.sprites._debugCollide:
                line(sk.surface, (0,0,0), self.posn, seg.eval())
            for s in group:
                if s is not self:
                    shape = s.shape if isinstance(s, Sprite) else s
                    pts = shape.intersect2d(seg)
                    minSep = None
                    for pt in pts:
                        r2 = distSq(pt, self.posn)
                        if minSep is None or r2 < minSep:
                            minSep = r2
                    if minSep:
                        obst[None if s is shape else s] = sqrt(minSep)
            if cone:
                angle += stepAngle
                steps -= 1
            else: steps = -1
        return obst

    def _closest_obstacle(self):
        "Locate nearest obstacle"
        obst = self._detectObstacles(self._obstacleCone)
        prox = None
        sprite = None
        for s in obst:
            r = obst[s]
            if prox is None or r < prox:
                prox = r
                sprite = s
        r = self.radius
        if prox is not None:
            prox -= self.radius
            if prox < 0: prox = None
        if isinstance(sprite, Sprite):
            img = sprite._image
            if self._proximity and img is self._proximity[2]:
                c = self._proximity[3]
            else:
                if hasattr(img, "_avgColor"): c = img._avgColor
                else:
                    c = img.averageColor()
                    c.a = 255
                    img._avgColor = c
        else:
            img = None
            c = self.sketch.wall
            if type(c) is bool: c = None
        self._proximity = prox, sprite, img, c

    def _downColor(self):
        "Calculate downward colour-sensor value"
        d = self.radius // 8
        r = 2 * d
        size = r, r
        r = 0.75 * self.radius
        posn = vsum(vec2d(r, self.angle * DEG), self.posn, (-d, -d))
        sk = self.sketch
        self._downRect = Rect(posn + size)
        if sk.sprites._debugCollide:
            Image(size, self.downColor).blitTo(posn=posn)
        try:
            if sk.bgImage:
                srf = sk.scaledBgImage.surface.subsurface(posn + size)
            else: srf = None
            if sk.bgColor:
                img = Image(size, sk.bgColor)
                if srf: img.surface.blit(srf, (0,0))
            else:
                img = Image(srf)
            return noise(img.averageColor(), self.sensorNoise, alpha=255)
        except: return None

    def frameStep(self):
        "Update robot sprite each frame"

        # Target wheel speed...
        v = self.maxSpeed
        v1, v2 = self._motors
        v1 *= v
        v2 *= v

        # Angular speed and turning radius...
        w = (v1 - v2) / (2 * self.radius)
        self.spin = w / DEG
        if w:
            R = (v1 + v2) / (2 * w)
            v = w * R
        else:
            v = v1

        # Acceleration...
        v = vec2d(v, self.angle * DEG)
        self.accel = times(sub(v, self.velocity), 0.05)

        # Update...
        super().frameStep()

        # Draw penColor on background...
        if self.penColor:# and self._penPosn:
            srf = self.sketch.scaledBgImage.surface
            x, y = self.posn
            xy = (round(x), round(y)) if self.centerPen else self._penPosn
            circle(srf, self.penColor, xy, self.penRadius)

        # Check sensors...
        stall = not self.motorsOff and (self.edgeAdjust or self.collideUpdate)
        if stall:
            if self._stallTime is None:
                self._stallTime = self.sketch.time if stall else None
        else: self._stallTime = None
        self.downColor = self._downColor()
        self._closest_obstacle()
        if self._starting: self._starting = False

        # Adjust wheel speed...
        self.costumeTime = 0 if self.motorsOff else round(36 / (1 + 5 * self.averagePower))

        # Log destruction of robot...
        if self._thread is not None and self._thread.log and self in self.sketch.sprites._toRemove:
            print("{} has been destroyed... there goes a billion dollars!".format(self._thread))

    _update = frameStep


def control_robot(robot, k, d=0.1):
    "Adjust motors based on key code"
    m1, m2 = robot.motors
    if k == K_UP:
        m1 += d
        m2 += d
    elif k == K_DOWN:
        m1 -= d
        m2 -= d
    elif k == K_LEFT:
        m1 -= d
        m2 += d
    elif k == K_RIGHT:
        m1 += d
        m2 -= d
    elif k == K_SPACE:
        m1 = m2 = 0
    robot.motors = d * round(m1 / d), d * round(m2 / d)

_rc_robot = None

def remote_control(sk, ev):
    "Use keyboard to control robot motors"
    global _rc_robot
    if _rc_robot is None:
        robots = [s for s in sk.sprites if isinstance(s, Robot)]
#        match = lambda r: isinstance(r, Robot)
#        robots = sk.sprites.search(match=match)
        _rc_robot = robots[-1]
    control_robot(_rc_robot, sk.keyCode)
