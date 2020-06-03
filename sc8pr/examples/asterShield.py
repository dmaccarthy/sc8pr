# Copyright 2015-2020 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

from sc8pr import version
if 100 * version[0] + version[1] < 202:
    raise NotImplementedError("This program requires sc8pr 2.2; installed version is {}.{}.".format(*version[:2]))

import json
from time import time
from math import pow
from random import uniform, randint
from pygame.constants import K_UP, K_DOWN, K_LEFT, K_RIGHT
from sc8pr import Sketch, Image, TOPLEFT, BOTH, RIGHT, LEFT, BOTTOM
from sc8pr.sprite import Sprite, physics, Collisions
from sc8pr.text import Text, Font
from sc8pr.util import randPixel, rgba, resolvePath
from sc8pr.geom import vec2d, delta
from sc8pr.gui.textinput import TextInput
from sc8pr.gui.button import Button
from sc8pr.misc.video import Video


JSON = "asterShield_scores.json"
FONT = Font.mono()

class Ship(Sprite):
    "The spaceship is controlled by the player using the keyboard"

    def reset(self, sk):
        "Configure to start game"
        return self.config(width = sk.width / 15, fired = 0, hits = 0,
            pos = sk.center, vel = (0, 0), angle = 270, spin = 0)

    def controls(self, ev):
        "Control ship with keyboard"
        c = ev.key
        vx, vy = self.vel
        d = 0.5
        if c == 32: # Space bar: fire missile
            sk = self.sketch
            sk += Missile(self)
            self.fired += 1
        elif c == K_UP: # Velocity controls
            vy -= d
        elif c == K_DOWN: vy += d
        elif c == K_LEFT: vx -= d
        elif c == K_RIGHT: vx += d
        else: # Spin controls
            c = ev.unicode.lower()
            s = self.spin
            d = 0.25
            if c in "sw":
                s = vx = vy = 0
                if c == "w": self.angle = 270
            elif c == "a": s -= d
            elif c == "d": s += d
            self.spin = s
        self.vel = vx, vy


class Missile(Sprite):

    def __init__(self, ship):
        "Fire a new missile from the ship"
        super().__init__(self.original)

        # Initial position of missile
        u = vec2d(1.3 * ship.radius, ship.angle)
        pos = ship.pos[0] + u[0], ship.pos[1] + u[1]

        # Initial velocity of missile
        u = delta(u, mag=ship.sketch.height/135)
        vel = ship.vel[0] + u[0], ship.vel[1] + u[1]

        self.config(width=ship.width/4, pos=pos,
            vel=vel, spin=ship.spin, angle=ship.angle)


class Asteroid(Sprite):

    def __init__(self, sk):
        "Create a new asteroid"
        super().__init__(self.original)
       
        # Random size and mass
        m = uniform(1, 100)
        w = pow(m, 1/3) / 100 * sk.width

        # Random position and velocity
        pos = randint(0, sk.width - 1), -w
        vel = uniform(0.25, 1) * sk.asteroidSpeed
        vel = vec2d(vel, uniform(10, 170))

        self.config(width=w, wrap=BOTH, pos=pos,
            vel=vel, spin=uniform(-2,2), mass=m)


class Game(Sketch):

    def setup(self):

        # Draw star field
        self.bg = img = Image(self.size, "black")
        img = img.image
        for i in range(150):
            img.set_at(randPixel(self.size), rgba(False))

        # Load high scores
        try:
            with open(JSON) as f: self.highScores = json.load(f)
        except: self.highScores = []

        # Load images
        Missile.original = Image(self.imgFldr + "/missile.png")
        Asteroid.original = Image(self.imgFldr + "/target.png")
        self.player = Ship(self.imgFldr + "/ship.png").config(wrap=BOTH)

        # Start the game
        self.playerName = None
        self.score = Score()
        self.collisions = Collisions(self)
        self.start()

    def start(self):
        "Start the game"
        self.purge()
        self += self.score.config(data=0)
        self += self.player.reset(self)
        self.time = time()

    def onkeydown(self, ev):
        "Send keyboard commands to Ship instance"
        p = self.player
        if p in self: p.controls(ev)

    def ondraw(self):
        p = self.player
        if p in self: # Game in progress

            # Asteroid collisions
            physics(self)
            c = self.collisions
            m, a = c.between(self.instOf(Missile), self.instOf(Asteroid))

            # Remove sprites and update score
            if a:
                self -= m + a
                a = len(a)
                p.hits += a
                self.score.add(a * round(10 + 40 * p.hits / p.fired))

            # Detect ship collision
            if c.involving(p, asBool=True):
                self.gameover()

            # Create new asteroids
            elif len(list(self.instOf(Asteroid))) == 0 or randint(0, self.frequency) == 0:
                self += Asteroid(self)

    @property
    def asteroidSpeed(self):
        "Increase asteroid velocity as play time increases"
        return (2 + (time() - self.time) / 60) * self.height / 540

    @property
    def frequency(self):
        "Increase asteroid frequency as play time increases"
        f = 3 - (time() - self.time) / 60
        return round(max(0.5, f) * self.frameRate)

    def gameover(self):
        "Delete all sprites; run gameover sequence"
        self.purge()
        self += self.score
        self.ongameover()

    def ongameover(self):
        "Display high scores or start a new game"
        score = self.score.data
        isHigh = len(self.highScores) < 10 or score > self.highScores[-1][0]
        if isHigh and self.playerName is None:
            self += PlayerName().config(pos=self.center, fontSize=self.height/12)
        elif isHigh:
            score = sorted(self.highScores + [[score, self.playerName]], reverse=True)
            if len(score) > 10: score = score[:10]
            try:
                with open(JSON, "w") as f: json.dump(score, f)
            except: pass
            self.highScores = score
            self.drawHighScores(score)
        else: self.start()

    def drawHighScores(self, score):
        "Draw the Top 10 scores on the screen"
        w, h = self.size
        x = w / 6
        y = h / 5
        attr = dict(color="blue", font=FONT, fontSize=self.height/15)
        for i in range(len(score)):
            if i == 5:
                x += 0.5 * w
                y = h / 5
            s = score[i]
            s, name = s
            if len(name) > 12: name = name[:12]
            self += Text(data=s).config(anchor=RIGHT, pos=(x-20, y), **attr)
            self += Text(data=name).config(anchor=LEFT, pos=(x, y), **attr)
            y += self[-1].height + 8

        icon = Sprite(Asteroid.original).config(spin=0.4)
        okay = Text("Okay").config(font=FONT)
        self += Button((w/7, h/10)).bind(onmousedown=restart).textIcon(okay,
            icon, 10).config(pos=(self.center[0], 0.9 * h),
            anchor=BOTTOM, border="blue", weight=3)


def restart(gr, ev):
    "Restart the game when OKAY button is clicked"
    gr.sketch.start()


class PlayerName(TextInput):
    "GUI control for obtaining the player's name"
    
    def __init__(self):
        super().__init__("", "Please enter your name")
        self.config(font=FONT, color="red",
            promptColor="black", bg="white", padding=8)

    def onaction(self, ev):
        if len(self.data):
            sk = self.sketch
            sk.playerName = self.data
            self.remove()
            sk.ongameover()


class Score(Text):
    "Display player's score at upper left of screen"

    def __init__(self):
        super().__init__()
        self.config(anchor=TOPLEFT, pos=(8,0),
            color="red", font=FONT, fontSize=36)

    def add(self, n):
        self.config(data = self.data + n, fontSize=round(self.sketch.height/15))


def play(size=(720, 480), record="", auto=4096):
    sk = Game(size).config(imgFldr=resolvePath("img", __file__))
    if record:
        sk.capture = Video().config(interval=2).autoSave(record, auto)
    sk.play("Asteroid Shield", sk.imgFldr + "/target.png")
    if record: sk.capture.autoSave()

if __name__ == "__main__": play()
