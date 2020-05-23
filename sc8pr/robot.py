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


from time import sleep, time
from threading import Thread
from sys import stderr
from math import hypot, cos
import pygame
from pygame.constants import K_UP, K_DOWN, K_LEFT, K_RIGHT, K_SPACE
from sc8pr import Image, Sketch
from sc8pr.sprite import Sprite
from sc8pr.util import sc8prData, logError, rgba, noise, divAlpha
from sc8pr.geom import vec2d, delta, DEG, dist, positiveAngle, angleDifference,\
    subtend
from sc8pr.shape import Line, Polygon


class RobotThread(Thread):
    "Control a Robot instance in a separate thread"

    log = True

    def __init__(self, robot):
        super().__init__()
        self.robot = robot

    def run(self):
        r = self.robot
        args = r, id(self)
        if self.log:
            print('{} is running in thread {}.'.format(*args), file=stderr)
        try:
            while r._startup: r.sleep()
            r._startTime = time()
            r.brain()
            if hasattr(r, "shutdown"): r.shutdown()
        except: logError()
        if self.log:
            print('{} is shutting down in thread {}.'.format(*args), file=stderr)


class InactiveError(Exception):
    def __init__(self): super().__init__("Robot is no longer active")


def _tempColor(px, color, *args):
    "Replace one color with a random RGB color"
    c = color
    while c in args: c = rgba(False)
    if c != color: px.replace(color, c)
    return c


class Robot(Sprite):
    _motors = 0, 0
    _updateSensors = True
    _startup = True
    sensorNoise = 8
    collision = False
    maxSpeed = 1 / 512
    sensorDown = None
    sensorFront = None
    sensorWidth = 10.0
    sensorResolution = 2.0
    proximity = None

    def __init__(self, colors=None):
        img = Image.fromBytes(sc8prData("robot"))
        if colors:  # Replace body and nose colors
            px = pygame.PixelArray(img.image)
            body0, nose0, body, nose = rgba("red", "blue", *colors)
            orig = body0, nose0
            if body in orig or nose in orig:
                colors = body0, nose0, body, nose
                body0 = _tempColor(px, body0, *colors)
                nose0 = _tempColor(px, nose0, *colors)
            if nose != nose0: px.replace(nose0, nose)
            if body != body0: px.replace(body0, body)
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
    def stopped(self):
        return self.vel == (0,0) and self.motors == (0,0)

    def setCanvas(self, sk, key=None):
        "Add Robot instance to the sketch"
        if not isinstance(sk, Sketch):
            raise Exception("Robot cannot be added to {}".format(type(sk).__name__))
        b = hasattr(self, "brain")
        if b and self.canvas: raise Exception("Robot is already active!")
        super().setCanvas(sk, key)
        if b:
            self._startFrame = sk.frameCount
            self._gyro = self.angle
            RobotThread(self).start()

    @property
    def active(self):
        try:
            sk = self.sketch
            return not sk.quit and self in sk
        except: return False

    def updateSensors(self, wait=None):
        self._updateSensors = True
        self.sleep(wait)
        return self

    def sleep(self, t=None):
        "Sleep for the specified time"
        if not self.active: raise InactiveError()
        if t: sleep(t)
        else: sleep(1 / self.sketch.frameRate)

    @property
    def motors(self): return self._motors

    @motors.setter
    def motors(self, m):
        if type(m) is int: m = float(m)
        if type(m) is float: m = (m, m)
        self._motors = tuple(max(-1.0, min(1.0, x)) for x in m)

    @property
    def power(self): return sum(abs(m) for m in self._motors) / 2

    def onbounce(self, wall):
        "Adjust motion upon collision with wall"
        w, h = self.sketch.size
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
                self._checkDown()
                self._checkFront()
                self._drawLEDs()
                self._updateSensors = False
            except: logError()
        self._startup = False

    def sensorObjects(self, sk):
        "Defines the list of objects detectable by sensorFront and proximity"
        return list(sk.sprites())

    def _checkFront(self):
        "Update the front color sensor"

        # Sensor info
        sw = self.sensorWidth
        res = 0.5 * self.sensorResolution
        pos = delta(self.pos, vec2d(-self.radius, self.angle))
    
        # Distance from sensor to edge of sketch
        obj = prox = None
        sk = self.sketch
        if sk.weight:
            prox = _distToWall(pos, self.angle, self.sensorWidth, *sk.size)
            if prox: obj = sk

        # Find closest object within "sensor cone"
        for gr in self.sensorObjects(sk):
            if gr is not self and gr.avgColor and hasattr(gr, "rect"):
                r = gr.radius
                view = subtend(pos, gr.rect.center, r, None if prox is None else prox + r)
                if view:
                    # Object may be closer than the current closest object
                    sep, direct, half = view
                    if not res or half > res:
                        # Object size meets sensor resolution threshold
                        beta = abs(angleDifference(self.angle, direct)) - sw
                        if beta < half or sep < r:
                            # Object is in sensor cone
                            pr = sep - r
                            if beta > 0:
                                # CLOSEST point is NOT in sensor cone
                                dr = r + sep * (cos(half * DEG) - 1)
                                pr += dr * (beta / half) ** 2
                            if prox is None or pr < prox:
                                # Object is closest (so far)
                                prox = pr
                                obj = gr

        # Save data
        self.closestObject = obj
        c = rgba(sk.border if obj is sk else obj.avgColor if obj else (0,0,0))
        self.sensorFront = noise(divAlpha(c), self.sensorNoise, 255)
        self.proximity = None if prox is None else max(0, round(prox))

    def _checkDown(self):
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
        self.sensorDown = noise(c, self.sensorNoise, 255)

    def _drawLEDs(self):
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

#     def say(self, msg=""):
#         "Display a message in the 'chat' area"
#         try: self.chat.config(data="", prompt=msg)
#         except: raise AttributeError("ChatRobot I/O is unavailable")
#         return self
# 
#     def listen(self, msg=None, validate=None):
#         "Wait for a chat response"
#         ti = self.chat
#         waiting = True
#         while waiting:
#             while ti.focussed or not ti.data: self.sleep()
#             data = ti.data
#             try:
#                 if validate: data = validate(ti.data)
#                 waiting = False
#             except: pass
#         if msg is not None: self.say(msg)
#         return data
# 
#     def ask(self, prompt, msg=None, validate=None):
#         "Display a chat message and await a response"
#         self.say(prompt)
#         return self.listen(msg, validate)

    @staticmethod
    def remoteControl(sk, ev):
        "ONKEYDOWN handler to operate robot by space and arrow keys"
        try:
            r = sk.remoteRobot
            key = ev.key
            if key == K_SPACE: r.motors = 0
            else:
                dm = {K_UP:(1,1), K_DOWN:(-1,-1), K_LEFT:(-1,1), K_RIGHT:(1,-1)}
                r.motors = tuple(0.1 * dm[key][i] + r.motors[i] for i in (0,1))
        except: pass


def _distToWall(pos, angle, sWidth, w, h):
    "Calculate the distance to the sketch walls in the specified direction"
    walls = Polygon([(0,0), (w,0), (w,h), (0,h)])
    w += h
    pts = []
    for n in (-1, 0, 1):
        v = vec2d(w, angle + n * sWidth)
        line = Line(pos, vector=v)
        pts.extend(walls.intersect(line))
    return min(dist(pos, pt) for pt in pts) if len(pts) else None
