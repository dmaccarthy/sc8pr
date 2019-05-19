# Copyright 2015-2019 D.G. MacCarthy <http://dmaccarthy.github.io>
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

try:
    from sc8pr import Sketch, Canvas, Image, BOTH,\
        LEFT, RIGHT, TOPLEFT, TOPRIGHT, TOP, BOTTOM, CENTER
    from sc8pr.sprite import Sprite, physics
    from sc8pr.geom import vec2d, polar2d, dist
    from sc8pr.text import Text, Font
    from sc8pr.robot import Robot
    from sc8pr.util import resolvePath
    from sc8pr.gui.radio import Radio
    from sc8pr.gui.button import Button
except Exception as e:
    print(e)
    print("Try running 'pip3 install sc8pr' on command line")
    exit()
from random import uniform, randint, choice


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
        r.updateSensors()
        if r.collision or r.uptime > r.schedule: randomMotor(r)

def followBall(r):
    m = choice((0.5, -0.5))
    while r.active:
        r.updateSensors() 
        r.motors = 1 if isGrey(r.sensorFront) else (m, -m)

def remote(r):
    while r.active: r.updateSensors()

def boxSize(w, h):
    "Size of the goal box"
    return round(0.075 * w), round(0.3 * h)


class Dialog(Canvas):
    "Choose robot control algorithms at start of program"

    options = "Human (Remote Control)", "Follow the Ball", "Random Motion"

    def __init__(self, sk):

        # Radio buttons
        text = self.options
        attr = {"font":sk.font, "fontSize":16}
        radio = [Radio(text, txtConfig=attr).config(anchor=TOPLEFT),
            Radio(text[1:], txtConfig=attr).config(anchor=TOPLEFT)]

        # Play button
        icon = Sprite(SoccerBall.ballImage).config(spin=1)
        play = Text("Play").config(**attr)
        play = Button((96,36), 2).textIcon(play, icon)
        x, y = icon.pos
        x += icon.width / 2
        icon.config(anchor=CENTER, pos=(x,y))

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
        self.config(height=30, mass=1, drag=0.00025, bounce=BOTH)

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
        x, y = self.pos
        r = self.radius
        yn = sk.center[1]
        dy = abs(y - yn)
        w, h = boxSize(*sk.size)
        player = None
        if dy < h/2 - r:
            if x < w - r: player = 1
            elif x > sk.width - 1 + r - w: player = 0
        return player


class SoccerRobot(Robot):
    brains = [remote, followBall, dumbBrain]

    def __init__(self, color):
        super().__init__(color)
        self.config(mass=20, bounce=BOTH)


class SoccerGame(Sketch):

    def setup(self):
        self.config(border="blue", weight=1, bg=self.field())
        
        # Display the score
        attr = {"font":self.font, "fontSize":48}
        self += Text(0).config(pos=(8,8), anchor=TOPLEFT, color="red", **attr)
        self += Text(0).config(pos=(631,8), anchor=TOPRIGHT, color="yellow", **attr)
        self.score = list(self)[-2:]

        # Paint the back of the nets so the robots can see them
        w, h = self.size
        d = h / 8
        r = 0.65 * boxSize(w, h)[1]
        h = (h - 1) / 2
        self += Sprite(Image((2,2), "red")).config(pos=(-d, h), wrap=0)
        self += Sprite(Image((2,2), "yellow")).config(pos=(w+d, h), wrap=0)
        for s in self[-2:]: s.radiusFactor *= r / s.radius

        # Get a soccer ball
        self += SoccerBall().config(pos=self.center)

        # Start the simulation
        if hasattr(self, "brains"): self.start()
        else: self += Dialog(self).config(pos=self.center)

    def field(self):
        "Draw red and yellow goal boxes on green turf"
        w, h = self.size
        y = self.center[1]
        sz = boxSize(w, h)
        cv = Canvas((w, h), "#20b050")
        cv += Image(sz, "red").config(pos=(0, y), anchor=LEFT)
        cv += Image(sz, "yellow").config(pos=(w-1, y), anchor=RIGHT)
        return cv.snapshot()

    def bindBrain(self, robot, brain):
        if brain is remote:
            self.bind(onkeydown=Robot.remoteControl).config(remoteRobot=robot)
        robot.bind(brain=brain)

    def start(self):
        "Robots take the field"
        yellow = SoccerRobot(["#ffd428", "#ff5050"])
        red = SoccerRobot(["#ff5050", "#ffd428"])
        self.bindBrain(red, self.brains[0])
        self.bindBrain(yellow, self.brains[1])
        x, y = self.center
        x += (2 * randint(0, 1) - 1) * 16
        self["Yellow"] = yellow.config(pos=(1.5 * x, y), width=y/4, angle=90)
        self["Red"] = red.config(pos=(0.5 * x, y), width=y/4, angle=270)

    ondraw = physics
    
    def goal(self, player):
        "Change the scoreboard"
        score = self.score[player]
        score.config(data=score.data+1)


def play(*brains, **kwargs):
    sk = SoccerGame((640,480)).config(font=kwargs.get("font"))
    if len(brains) == 1: sk.brains = [brains[0], followBall]
    elif len(brains) == 2: sk.brains = brains
    sk.play("Robot Soccer")

main = play

if __name__ == "__main__": play(font=Font.mono())
