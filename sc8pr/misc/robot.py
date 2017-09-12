from time import sleep
from threading import Thread
from sys import stderr
import pygame
from sc8pr.sprite import Sprite
from sc8pr.util import sc8prData, logError, rgba, noise
from sc8pr.geom import vec2d, delta, DEG
from sc8pr import Image


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
            args = "{}.{}".format(b.__module__, b.__name__), str(r), id(self)
            print('{} is controlling "{}" in thread {}.'.format(*args), file=stderr)
        try:
            b(r)
            if r.shutdown: r.shutdown()
        except: logError()
        if self.log:
            print('{} is shutting down in "{}".'.format(*args), file=stderr)


class InactiveError(Exception):
    def __init__(self): super().__init__("Robot is no longer active")


class Robot(Sprite):
    _motors = 0, 0
    _updateSensors = False
    _sensorNoise = 4
    maxSpeed = 1
    shutdown = None
    sensorDown = None
    sensorFront = None

    def __init__(self, brain=None, colors=None):
        self.brain = brain
        img = Image.fromBytes(sc8prData("robot"))
        if colors:
            px = pygame.PixelArray(img.image)
            for i in range(2):
                c = 255 * (1 - i), 0, 255*i
                px.replace(c, rgba(colors[i]))
        img = img.tiles(2)
        super().__init__(img)
    
    def setCanvas(self, cv):
        super().setCanvas(cv)
        b = self.brain
        if b:
            self._startFrame = cv.sketch.frameCount
            RobotThread(self, b).start()

    @property
    def active(self):
        try: return not self.sketch.quit
        except: return False

    def updateSensors(self, wait=True):
        self._updateSensors = True
        if wait: self.sleep()
        return self

    def sleep(self, t=None):
        "Sleep for the specified time"
        if t: sleep(t)
        else:
            if not self.active: raise InactiveError()
            sk = self.sketch
            n = sk.frameCount
            t = 0.4 / sk.frameRate
            i = 3
            while sk.frameCount == n and i:
                sleep(t)
                i -= 1

    @property
    def motors(self): return self._motors

    @motors.setter
    def motors(self, m):
        if type(m) in (int, float): m = (m, m)
        self._motors = tuple(max(-1, min(1, x)) for x in m)

    @property
    def power(self): return sum(abs(m) for m in self._motors) / 2

    def ondraw(self, cv):
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
        else: v = v1

        # Acceleration...
        v = vec2d(v, self.angle)
        self.acc = delta(v, self.vel, 0.05)

        # Adjust wheel speed...
        p = self.power
        self.costumeTime = 0 if p == 0 else round(36 / (1 + 5 * p))

        # Update...
        super().ondraw(cv)

        #
        if self._updateSensors:
            try:
                self.checkDown()
                self.drawLEDs()
                self._updateSensors = False
            except: logError()

        # Check sensors...
#         stall = not self.motorsOff and (self.edgeAdjust or self.collideUpdate)
#         if stall:
#             if self._stallTime is None:
#                 self._stallTime = self.sketch.time if stall else None
#         else: self._stallTime = None
#         self.downColor = self._downColor()
#         self._closest_obstacle()
#         if self._starting: self._starting = False


    def checkDown(self):
        "Update the down color sensor"
        sk = self.sketch
        if isinstance(sk.bg, Image):
            x, y = self.rect.center
            r = 0.8 * self.radius
            dx, dy = vec2d(r, self.angle)
            r = max(1, round(0.25 * r))
            d = 2 * r
            r = pygame.Rect(x + dx - r, y + dy - r, d, d).clip(sk.rect)
            if r.width:
                c = noise(pygame.transform.average_color(sk.bg.image.subsurface(r)))
            else: c = None
        else: c = sk.bg
        self.sensorDown = c

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
