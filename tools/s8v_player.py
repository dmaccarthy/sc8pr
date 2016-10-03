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

from sc8pr.sketch import Sketch, OPEN, SAVE, USERINPUT
from sc8pr.video import Video, VideoSprite
from pygame import KEYDOWN, K_LEFT, K_RIGHT, K_UP, K_DOWN
from json import load, dump
from threading import Thread
from sys import argv

fps = 10, 12, 15, 20, 24, 30, 60


class ExportVid(Thread):

    def __init__(self, vid, movie, clip):
        super().__init__()
        self.vid = vid
        self.movie = movie
        self.clip = clip
    
    def run(self):
        self.vid.export(movie=self.movie, clip=self.clip, start=self.clip[0])


def menu():
    print("""ESC > Open
 TAB   > Change Frame Rate
 SPC   > Play/Pause
Arrows > Back/Forward/Start/End

 S/E   > Clip Start/End
  C    > Clip Reset
  G    > Grab Frame
  X    > Export
  F    > FFMPEG location = {}\n""".format(Video.ffmpeg))

def setup(sk):
    try:
        with open("s8v_player.json", "r") as f:
            cfg = load(f)
            Video.ffmpeg = cfg["ffmpeg"]
    except: pass
    menu()
    sk.frameRate = 30
    sk.setBackground(bgColor=(255,255,255))
    if len(argv) > 1: openVid(sk, None)
    else: runDialog(sk)

def resetClip(sp):
    sp.mark = [0, len(sp.video)-1]
    return sp
    
def openVid(sk, ev):
    "Open a s8v video as a VideoSprite instance; fit sketch to video"
    try:
        if isinstance(ev, VideoSprite):
            sp = ev
            sk.sprites.append(sp)
            sp.costumeTime = 0
        else:
            sp = VideoSprite(sk, Video(ev.value if ev else argv[1]))
        sk.user_vid = sp
        sk.size = sp.size
        resetClip(sp).config(zoom=1, posn=sk.center)
    except: pass
    sk.animate(draw, {KEYDOWN:keyDown})

def draw(sk):
    sp = sk.sprites[0]
    if sp.costumeTime and sp.currentCostume == len(sp.video) - 1:
        sp.costumeTime = 0
        print("[End]")
    sk.simpleDraw()

def runDialog(sk, handler=openVid, initFilter="*.s8v", mode=OPEN):
    "Run a file dialog to choose a video or located ffmpeg.exe"
    sk.sprites.empty()
    sk.size = 768, 432
    sk.fileDialog(mode, initFilter=initFilter, allowCancel=(handler is export))
    sk.animate(sk.simpleDraw, eventMap={USERINPUT:handler})

def printFrame(sp): print("[{}]".format(sp.currentCostume))

def keyDown(sk, ev):
    "Event handler for keyboard commands"
    k = ev.key
    sp = sk.sprites[0]
    f = sp.currentCostume
    n = len(sp.video)
    if k == 32: # Space bar
        sp.costumeTime = n = 1 - sp.costumeTime
    elif k in (K_LEFT, K_RIGHT): # Arrows
        sp.costumeTime = 0
        if k == K_LEFT: f -= 1
        elif k == K_RIGHT: f += 1
        if f < 0: f += n
        elif f >= n: f -= n
        sp.currentCostume = f
    elif k == 27: # Escape
        runDialog(sk)
    elif k == 9: # Tab
        sk.frameRate = fps[(1 + fps.index(sk.frameRate)) % len(fps)]
        print("fps =", sk.frameRate)
    elif k == 120: # X
        runDialog(sk, export, "*.mp4", SAVE)
    elif k == 102: # F
        runDialog(sk, setFF, "ffmpeg.exe")
    elif k == 103: # G
        runDialog(sk, grab, "*.png", SAVE)
    elif k == K_DOWN: # A
        sp.currentCostume = 0
    elif k == K_UP: # Z
        sp.currentCostume = len(sp.video) - 1
    elif k in (101, 115): # E, S
        mark = sp.mark[:]
        mark[0 if k == 115 else 1] = sp.currentCostume
        if mark[0] < mark[1]:
            sp.mark = mark
        else: print("Cannot have Start > End!")
        print("Clip", sp.mark)
    elif k == 99: # C
        resetClip(sp)
        print("Clip", sp.mark)
    else: print(k)
    printFrame(sp)
    
def setFF(sk, ev):
    "Handler for Locate ffmpeg.exe dialog"
    if ev.value:
        Video.ffmpeg = '"{}"'.format(ev.value)
        try:
            with open("s8v_player.json", "w") as f:
                dump({"ffmpeg":Video.ffmpeg}, f)
        except: pass
    runDialog(sk)

def export(sk, ev):
    "Save the entire Video as image files and encode with ffmpeg"
#    if ev.value:
    sp = sk.user_vid
    ExportVid(sp.video, ev.value, sp.mark).start()
    openVid(sk, sp)

def grab(sk, ev):
    "Save a single frame"
    if ev.value:
        sp = sk.user_vid
        n = sp.currentCostume
        sp.video[n].image.saveAs(ev.value)
        openVid(sk, sp)

Sketch(setup).play(432, "sc8pr Video Player", mode=0)
    