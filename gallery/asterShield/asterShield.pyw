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


from sc8pr.sketch import Sketch, Sprite, WRAP, REMOVE, USERINPUT
from sc8pr.image import Image, ZImage
from sc8pr.ram import RAMFolder
from sc8pr.util import NO_CURSOR, rgba, Data, CENTER, WEST, EAST, NORTH
from pygame import KEYDOWN, K_LEFT, K_RIGHT, K_UP, K_DOWN, K_SPACE, K_DELETE, K_RETURN, K_a, K_d, K_s, K_w, K_ESCAPE
from pygame.key import set_repeat
from random import randint, random
from json import load, dump
from math import sin, cos, radians
from sys import argv


# Colors...
BLACK, WHITE, TEXTCOLOR = rgba("black", "white", "red")

# Initial screen height...
HEIGHT = 540

# Ratios of screen to sprite height...
TORPEDO = 27
PLAYER = 10
TARGET = 16
SCORE = 15

# Other constants...
LEVELS = 50
STARS = 200
FOLDER = "./"
HIGHSCORES = FOLDER + "score.json"


def starfield(size):
    "Create a background of random stars"
    stars = Image(size, bgColor=BLACK)
    for i in range(STARS):
        xy = randint(0, size[0] - 1), randint(0, size[1] - 1)
        c1 = randint(-96, 96)
        c2 = 255 - abs(c1)
        c = c2 + c1, c2, c2 - c1
        stars.surface.set_at(xy, c)
    return stars


# Intro screen...

def intro_setup(sk):
    sk.setBackground(bgColor=BLACK)
    sk.img = Data()
    sk.misc = Data()
    sk.img.kb = Image(FOLDER + "kb.png")
    msg = "Please honour me with your name, brave pilot."
    sk.prompt(msg, title="Pilot Name", allowCancel=False, posn=NORTH).margin = 32
    sk.animate(intro, {USERINPUT:intro_done})

def intro(sk):
    sk.blit(sk.img.kb, sk.center, CENTER)

def intro_done(sk, ev):
    "Start game when pilot enters name"
    sk.misc.pilot = ev.value
    del sk.img.kb
    setup(sk)


# Main game...

def setup(sk):
    "Prepare for first level"

    # Initialize...
    set_repeat()
    sk.cursor = NO_CURSOR
    sk.misc.attr(inertia=True, fontSize=None, highScore=loadHighScores())

    # Sounds, images and sprites...
    sk.loadSounds(("blast.ogg", 0), ("explode.ogg", 1))
    sk.img.torpedo = Image(FOLDER + "missile.png")
    sk.img.target = Image(FOLDER + "target.png").scale(height=HEIGHT//TARGET)
    sp = Sprite(sk, FOLDER + "player.png", height=HEIGHT//PLAYER, edge=WRAP)
    sk.misc.player = sp.circle()

    # Create sprite sets for torpedoes and targets...
    sk.misc.torpedoSet = set()
    sk.misc.targetSet = set()

    # Start the game...
    sk.bgImage = starfield(sk.size)
    sk.animate(draw, {KEYDOWN:keyboard})
    if "--record" in argv:
        sk.captureFolder = RAMFolder("capture")
        sk.record(2)
        print("Recording!")
    start(sk)

def start(sk):
    "Start a new game"
    sk.misc.attr(level=0, score=0)
    player = sk.misc.player
    player.config(posn=sk.center, angle=0, spin=0, height=sk.height//PLAYER, velocity=(0,0))
    sk.sprites.empty()
    sk.sprites.append(player)
    nextLevel(sk)

def nextLevel(sk):
    "Start the next level"
    sk.misc.shots = 0
    if sk.misc.level < LEVELS: sk.misc.level += 1
    for i in range(sk.misc.level): createTarget(sk)

def draw(sk):
    "Draw the screen"
    sk.drawBackground()
    setFont(sk, sk.height // SCORE)
    sk.blit(Image.text(str(sk.misc.score), color=WHITE, font=sk.font))
    if sk.misc.level == 0: drawHighScores(sk)
    else:
        sp = sk.sprites
        sp.draw()
        if removeCollide(sp): # True when ship is destroyed
            sk.misc.level = 0
            saveHighScores(sk)

def keyboard(sk, ev):
    "Event handler for KEYDOWN"
    player = sk.misc.player
    if sk.keyCode == K_ESCAPE: sk.sprites.run = not sk.sprites.run
    elif sk.misc.level == 0 and sk.keyCode == K_RETURN: start(sk)
    elif sk.keyCode == 271: sk.save()
    elif sk.sprites.run:
        if sk.keyCode == K_SPACE: blast(sk)
        elif sk.keyCode == K_DELETE: sk.misc.inertia = not sk.misc.inertia
        elif sk.keyCode in {K_s, K_w}:
            player.spin = 0
            if sk.keyCode == K_w:
                player.angle = 0
                player.velocity = 0, 0
        elif sk.keyCode in {K_a, K_d}:
            player.spin += -0.5 if sk.keyCode == K_a else 0.5
        elif sk.keyCode in {K_LEFT, K_RIGHT, K_UP, K_DOWN}:
            v = speed(sk) / 2
            inert = sk.misc.inertia
            vx, vy = player.velocity
            if sk.keyCode == K_LEFT: v = shipSpeed(vx, -v, inert), vy
            elif sk.keyCode == K_RIGHT: v = shipSpeed(vx, v, inert), vy
            elif sk.keyCode == K_UP: v = vx, shipSpeed(vy, -v, inert)
            else: v = vx, shipSpeed(vy, v, inert)
            player.velocity = v


# Sprite creation and removal...

def blast(sk):
    "Fire the torpedo"

    sk.misc.shots += 1
    player = sk.misc.player

    # Calculate position
    a = player.angle
    ar = radians(a - 90)
    c, s = cos(ar), sin(ar)
    h = sk.height // TORPEDO
    r = (player.height + h) / 2
    x, y = player.posn
    xy = x + r * c, y + r * s

    # Create sprite and calculate velocity
    torpedo = Sprite(sk, sk.img.torpedo, sk.misc.torpedoSet, posn=xy, height=h, edge=REMOVE, angle=a)
    x, y = player.velocity
    r = 2 * speed(sk)
    torpedo.velocity = x + r * c, y + r * s
    sk.sound(0)

def createTarget(sk):
    "Create the sprite for a new target"
    spin = 4 * (random() - 0.5)
    zoom = sk.hRatio * (0.5 + random())
    xy = randint(0, sk.width), 0
    v = speed(sk)
    vx = 2 * v * (random() - 0.5)
    vy = random()
    vy = v * (vy + 0.01 if sk.misc.level < 5 else 2 * (vy - 0.5))
    Sprite(sk, sk.img.target, sk.misc.targetSet, posn=xy, zoom=zoom, velocity=(vx,vy), spin=spin, edge=WRAP).circle()

def removeCollide(sprites):
    "Remove colliding sprites and increase score for targets destroyed"
    sk = sprites.sketch
    player = sk.misc.player
    targetsDestroyed = len(player.collisions(sk.misc.targetSet))
    dead = True if targetsDestroyed else player.colliding(sk.misc.torpedoSet)
    target, torpedo = sprites.collisionsBetween(sk.misc.targetSet, sk.misc.torpedoSet)
    targetsDestroyed += len(target)
    if targetsDestroyed:
        sk.sound(1)
        n = 20 + 5 * (sk.misc.level // 2)
        if sk.misc.shots: sk.misc.shots -= 1
        pts = 10 * (n - min(n, sk.misc.shots))
        sk.misc.score += pts * targetsDestroyed
    if not dead:
        sprites.remove(torpedo)
        sprites.remove(target)
        if len(sk.misc.targetSet) == 0: nextLevel(sk)
    return dead


# Miscellaneous functions...

def setFont(sk, size):
    "Load the specified font size if necessary"
    if size != sk.misc.fontSize:
        sk.font = sk.loadFont("mono", size)
        sk.misc.fontSize = size
    return sk.font

def speed(sk):
    "Determine speed baseline from level and screen size"
    return 2 * sk.hRatio * sk.misc.level ** 0.5

def shipSpeed(v, dv, inert):
    "Calculate new ship speed"
    if inert: return v + dv
    if v * dv < 0: return 0
    return dv


# High score operations...

def saveHighScores(sk):
    "Save the high scores as a JSON file"
    hs = sk.misc.highScore
    hs.append([sk.misc.score, sk.misc.pilot])
    hs = sorted(hs, reverse=True)
    if len(hs) > 10: hs = hs[:10]
    sk.misc.highScore = hs
    with open(HIGHSCORES, "w") as f: dump(hs, f)

def loadHighScores():
    "Load the list of high scores"
    try:
        with open(HIGHSCORES) as f: hs = load(f)
    except: hs = []
    return hs

def drawHighScores(sk):
    "Display the high scores screen"
    h = sk.height // SCORE
    x1 = 0.4 * sk.width
    x2 = x1 + h
    y = 3 * h
    setFont(sk, h)
    img = Image.text("High Scores", color=TEXTCOLOR, font=sk.font)
    sk.blit(img, (sk.centerX, 1.2 * h), CENTER)
    for s in sk.misc.highScore:
        img = Image.text(s[1], color=WHITE, font=sk.font)
        sk.blit(img, (x2, y), WEST)
        img = Image.text(str(s[0]), color=WHITE, font=sk.font)
        sk.blit(img, (x1, y), EAST)
        y += h
    img = Image.text("Press ENTER to play again!", color=TEXTCOLOR, font=sk.font)
    sk.blit(img, (sk.centerX, y + 0.75 * h), CENTER)


# Play!

ZImage.level = 1
fldr = Sketch(intro_setup).play(HEIGHT, "Asteroid Shield", FOLDER + "icon.png").captureFolder
if isinstance(fldr, RAMFolder): fldr.save()
