# Copyright 2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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


if __name__ == "__main__": import depends
from random import uniform, randint, choice
from sc8pr import Sketch, Canvas, Image, BOTH,\
    LEFT, RIGHT, TOPLEFT, TOPRIGHT, TOP, BOTTOM
from sc8pr.sprite import Sprite, physics
from sc8pr.geom import vec2d, polar2d, dist
from sc8pr.text import Text, Font
from sc8pr.robot import Robot
from sc8pr.util import resolvePath
from sc8pr.gui.radio import Radio
from sc8pr.gui.button import Button


def isGrey(color):
    s, v = color.hsva[1:3]
    return s < 25 and v > 50

def randomMotor(r):
    r.motors = uniform(-1,1), uniform(-1,1)
    r.schedule = r.uptime + uniform(2, 10)
    r.collision = False

def dumbBrain(r):
    randomMotor(r)
    while r.active:
        r.sleep()
        if r.collision or r.uptime > r.schedule: randomMotor(r)

def followBall(r):
    m = choice((0.5, -0.5))
    while r.active:
        r.updateSensors() 
        r.motors = 1 if isGrey(r.sensorFront) else (m, -m)


class Dialog(Canvas):
    "Choose robot control algorithms at start of program"

    options = "Human (Remote Control)", "Follow the Ball", "Random Motion"

    def __init__(self, sk):

        # Radio buttons
        text = self.options
        attr = {"font":sk.font, "fontSize":16}
        radio = [Radio(text, **attr).config(anchor=TOPLEFT),
            Radio(text[1:], **attr).config(anchor=TOPLEFT)]

        # Play button
        icon = Sprite(SoccerBall.ballImage).config(spin=1, costumeTime=10)
        play = Button((96,36), 2).textIcon("Play", icon, textCfg=attr)

        # Titles
        attr.update(anchor=TOP)
        text = [Text(t + " Robot").config(color=t, **attr)
            for t in ("Red", "Yellow")]

        # Create canvas
        items = radio + text + [play]
        w = max(gr.width for gr in items) + 16
        h = sum(gr.height for gr in items) + 72
        super().__init__((w, h), "#d0d0d0")

        # Position controls
        xc = self.center[0]
        y = 8
        for gr in [text[0], radio[0], text[1], radio[1]]:
            x = xc if isinstance(gr, Text) else 8
            self += gr.config(pos=(x,y))
            y += gr.height + 8
            if gr is radio[0]: y += 16
        self += play.config(pos=(xc,h-8), anchor=BOTTOM)

    def onaction(self, ev):
        "Start game with selected robot controls"
        options = [self[i].selected.layer for i in (1,3)]
        options[1] += 1
        sk = self.sketch
        sk.brains = [SoccerRobot.brains[i] for i in options]
        self.remove()
        sk.start()

    def resize(self, size): pass


class SoccerBall(Sprite):

    def __init__(self):
        img = Image(resolvePath("img/ball.png", __file__))
        SoccerBall.ballImage = img
        super().__init__(img)
        self.config(height = 30, mass = 1, drag = 0.0001, bounce = BOTH)

    def oncollide(self): self.spin = uniform(-2, 2)

    def onbounce(self, wall):
        v, a = polar2d(*self.vel)
        self.vel = vec2d(v, a + uniform(-5, 5))
        self.oncollide()

    def collideRobot(self, pos):
        sk = self.sketch
        r = self.radius
        for s in sk.sprites():
            if isinstance(s, SoccerRobot) and dist(s.pos, pos) < r + s.radius:
                return True
        return False

    def ondraw(self):
        sk = self.sketch
        Sprite.ondraw(self)

        # Check whether a goal has been scored
        player = self.goal(sk)
        if player is not None:
            sk.goal(player)

            # Place ball for "faceoff"
            pos = sk.center
            while self.collideRobot(pos):
                pos = pos[0], pos[1] + 1
            self.config(pos = pos, spin = 0, vel = (0,0))

    def goal(self, sk):
        "Check if ball is in one of the nets"
        r = self.rect
        r = r.midleft, r.midright, r.midtop, r.midbottom
        player = None
        for n in (0, 1):
            net = sk.nets[n]
            score = True
            for p in r:
                if not net.contains(p): score = False
            if score: player = n
        return player


class SoccerRobot(Robot):
    brains = [None, followBall, dumbBrain]

    def __init__(self, color):
        super().__init__(color)
        self.config(mass=20, bounce=BOTH)

    def sensorObjects(self, sk):
        return list(sk.sprites()) + sk.nets


class SoccerGame(Sketch):

    def setup(self):
        netSize = 48, 128
        self += Image(netSize, "yellow").config(anchor=RIGHT, pos=(639,240))
        self += Image(netSize, "red").config(anchor=LEFT, pos=(0,240))
        self.nets = list(self)
        self.config(border="blue", bg="#20b050")
        attr = {"font":self.font, "fontSize":48}
        self += Text(0).config(pos=(8,8), anchor=TOPLEFT, color="red", **attr)
        self += Text(0).config(pos=(631,8), anchor=TOPRIGHT, color="yellow", **attr)
        self.score = list(self)[-2:]
        self += SoccerBall().config(pos=self.center)
        if hasattr(self, "brains"): self.start()
        else: self += Dialog(self).config(pos=self.center)

    def bindBrain(self, robot, brain):
        if brain is None:
            self.bind(onkeydown=Robot.remoteControl).config(remoteRobot=robot)
        else: robot.bind(brain=brain)

    def start(self):
        yellow = SoccerRobot(["#ffd428", "#ff5050"])
        red = SoccerRobot(["#ff5050", "#ffd428"])
        self.bindBrain(red, self.brains[0])
        self.bindBrain(yellow, self.brains[1])
        x, y = self.center
        x += (2 * randint(0, 1) - 1) * 16
        self["Yellow"] = yellow.config(pos=(1.5 * x, y), width=y/4, angle=90)
        self["Red"] = red.config(pos=(0.5 * x, y), width=y/4, angle=270)

    def ondraw(self): physics(self)
    
    def goal(self, player):
        score = self.score[player]
        score.config(data=score.data+1)


def main(*brains, **kwargs):
    sk = SoccerGame((640,480)).config(font=kwargs.get("font"))
    if len(brains) == 1: sk.brains = [brains[0], followBall]
    elif len(brains) == 2: sk.brains = brains
    sk.play("Robot Soccer")

if __name__ == "__main__": main(font=Font.mono())
