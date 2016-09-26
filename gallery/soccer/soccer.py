#!python3

# Copyright 2015-2016 D.G. MacCarthy <http://dmaccarthy.github.io>
#
# This file is part of "sc8pr_gallery".
#
# "sc8pr_gallery" is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# "sc8pr_gallery" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "sc8pr_gallery".  If not, see <http://www.gnu.org/licenses/>.


from sc8pr.sketch import Sketch, Sprite, HIDDEN
from sc8pr.robot import Robot, remote_control
from sc8pr.image import Image
from sc8pr.util import rgba, NE, NW, WEST, EAST
from sc8pr.geom import add, neg
from pygame import KEYDOWN, VIDEORESIZE
from random import randint, uniform
from os.path import dirname


BLACK, YELLOW, RED, GREEN = rgba("black", "yellow", "red", "forestgreen")
ROBOT_RED, ROBOT_YELLOW, ROBOT_GREY = rgba("#ff5050", (255, 212, 40), (160, 160, 160))

def goal(sk):
    "Check if the ball is entirely within one of the nets"
    i = 1
    for net in sk.nets:
        if net.contains(sk.ball.posn): return i
        i += 1
    return 0

def field(sk, ball):
    "Draw the soccer field"

    # Field...
    img = Image(sk.size, GREEN)
    sk.wall = BLACK

    # Nets...
    p1, p2 = (0, sk.centerY), (sk.width - 1, sk.centerY)
    w, h = sk.size
    size = w//20, h//5
    netSize = add(size, (ball // 2, ball))
    Image(netSize, RED).blitTo(img, p1, WEST)
    Image(netSize, YELLOW).blitTo(img, p2, EAST)

    # Goal sprites...
    w = size[0] / 2
    net = Image(size)
    net1 = Sprite(sk, net, status=HIDDEN, edge=0, posn=(w, sk.centerY))
    net2 = Sprite(sk, net, status=HIDDEN, edge=0, posn=(sk.width-1-w, sk.centerY))
    sk.nets = net1, net2

    # Net backing color...
    size = 1, netSize[1]
    Sprite(sk, Image(size, RED), posn=p1, edge=0)
    Sprite(sk, Image(size, YELLOW), posn=p2, edge=0)
    return img

def makeScore(sk, ev=None):
    clr = RED, YELLOW
    font = sk.loadFont("mono", sk.height // 12, True)
    sk.scoreText = [Image.text(str(sk.score[i]), font=font, color=clr[i]) for i in range(2)]

def setup(sk):
    r = sk.width // 48
    w = 4 * r
    sk.setBackground(field(sk, 2*r))
    sk.score = [0, 0]
    sk.ball = Sprite(sk, dirname(__file__) + "/ball.png", height=2*r, mass=0.1, drag=0.0, elasticity=1).circle()
    sk.robots = set()
    r1 = Robot(sk, sk.brain[1], (ROBOT_YELLOW, ROBOT_GREY), sk.robots, width=w, id=0, name="Yellow")
    r = round(r1.radius)
    posn = randint(sk.centerX + r, sk.width-1-r), randint(r, sk.height-1-r)
    r1.config(posn=posn)
    brain = sk.brain[0]
    sk.human = brain is None
    Robot(sk, brain, (ROBOT_RED, ROBOT_YELLOW), sk.robots, width=w, angle=180, id=1, name="Red",
        posn=(randint(r, sk.centerX-1-r), randint(r, sk.height-1-r)))#.collideRegions()
    eventMap = {VIDEORESIZE: makeScore, KEYDOWN: keyDown}
    sk.animate(draw, eventMap)
    sk.ball.costumes[0].setAsIcon()

def keyDown(sk, ev):
    if sk.char == "s": sk.save()
    elif sk.human: remote_control(sk, ev)

def draw(sk):
    n = goal(sk)
    if n:
        sk.ball.velocity = 0, 0
        sk.ball.spin = 0
        sk.ball.posn = sk.center
        sk.score[2-n] += 1
        makeScore(sk)
    sk.drawBackground()
    sk.blit(sk.scoreText[0], (2,0), NW)
    sk.blit(sk.scoreText[1], (sk.width-3,0), NE)
    sk.sprites.draw()
    if sk.ball in sk.sprites.physics():
        sk.ball.spin = uniform(0.2, 3.0) * (1 if randint(0,1) else -1)
    edge = tuple(sp.edgeAdjust for sp in sk.sprites)
    if True in edge: print(sk.frameCount, edge)

def isGrey(c):
    return False if c is None else min(c.r, c.g, c.b) > 128

def brain(robot):
    while robot.environ:
        findBall(robot)
        if robot.stallTime > 0.2:
            robot.motors = neg(robot.motors) + (1,)
        else:
            robot.motors = 1, 1
            robot.sleep()

def findBall(robot):
    m = 2 * robot.id - 1
    while not isGrey(robot.frontColor):
        robot.motors = m, -m
        robot.sleep()

def play(brain1=None, brain2=brain):
    sk = Sketch(setup)
    sk.brain = brain1, brain2
    sk.play((960,540), "Robot Soccer")

def demo(): play(brain)


if __name__ == "__main__": play()
