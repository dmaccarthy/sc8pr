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

"""
Screen recording program using PIL.ImageGrab. Recordings are saved
as sc8pr Video (S8V). If ffmpeg and ImageIO are available, recordings
can be saved in other formats; run the program with the desired container
format and ffmpeg path as command line arguments: e.g.

python3 scrRec.py mp4 "C:\ffmpeg\bin\ffmpeg.exe"

You can omit the ffmpeg path if your system recognizes 'ffmpeg' as a system
command. The default video codec and pixel format for the chosen container
will be used. For MP4, this will probably be libx264 and yuv420p.
"""

# from sc8pr import version
# if 100 * version[0] + version[1] < 202:
#     raise NotImplementedError("This program requires sc8pr 2.2; installed version is {}.{}.".format(*version[:2]))

try: import numpy, imageio as im
except Exception as e:
    print(e)
    print("Try running 'pip3 install imageio imageio-ffmpeg' on command line")

from sys import argv
from datetime import datetime
from time import time
from threading import Thread
from tkinter.filedialog import askdirectory

from sc8pr import Sketch, Image, PixelData, LEFT
from sc8pr.text import Font, BOLD
from sc8pr.util import logError
from sc8pr.shape import Circle
from sc8pr.sprite import Sprite
from sc8pr.gui.button import Button
from sc8pr.gui.textinput import TextInput
from sc8pr.gui.dialog import ask
from sc8pr.misc.video import Video, Grabber, ImageIO


def timeStr():
    "Create a string that can be used as the recording file name"
    s = str(datetime.now()).split(".")[0]
    for c in " -:": s = s.replace(c, "_")
    return s

def onclick(btn, ev):
    "Toggle recording mode when record button is pressed"
    sk = btn.sketch
    if sk.grab:
        blink(sk, False)
        SaveThread(sk).start()
    else:
        sk.record()
        blink(sk)

def blink(sk, b=True):
    "Set record button to (not) blink"
    s = sk["Record"][0]
    if b: s.config(costumeTime=sk.frameRate//2)
    else: s.config(costumeTime=0, costumeNumber=0)


class Recorder(Sketch):
    output = argv[1] if len(argv) > 1 else "s8v"

    def setup(self):
        x, y = self.center
        attr = dict(font=Font.mono(), fontSize=18, fontStyle=BOLD, weight=1,
            padding=4, border="#c0c0c0", promptColor="#c0c0c0")
        self["Param"] = TextInput("","fps w h x y").config(pos=(x+16,y), **attr)
        self["Record"] = self.recordButton(y)
        self.grab = None

    def recordButton(self, y):
        "Compose the record button"
        sz = 21, 21
        btn = Button(sz, ["#ffffff00", "#ffc0c0"]).config(anchor=LEFT,
            pos=(12,y), weight=0).bind(onclick)
        img = Circle(76).config(fill="red", weight=6).snapshot(), Image((19,19))
        btn += Sprite(img).config(pos=btn.center, height=19)
        return btn

    def onquit(self, ev):
        "Disable QUIT while recording"
        if not self.grab: self.quit = True

    def ondraw(self):
        "Capture screen if recording"
        if self.grab:
            self.rec.append(self.grab.pil)
            f = self.frameTimes
            f.append(time() - (f[0] if len(f) else 0))

    def record(self):
        "Begin screen recording"
        self.rec = []
        self.recTime = datetime.now()
        self.frameTimes = []
        try:
            param = self["Param"].data.split(" ")
            param = [abs(int(c)) for c in param if c]
            if len(param) not in (0,1,3,5):
                raise ValueError("Parameters not valid")
            self.frameRate = max(1, param[0]) if param else 15
            if len(param) == 5: r = param[3:] + param[1:3]
            elif len(param) == 3: r = [0, 0] + param[1:3]
            else: r = None
            self.grab = Grabber(r)
        except: # Abort!
            blink(self, False)
            self.grab = None
            logError()


class SaveThread(Thread):
    "Save recording using a separate thread"

    def __init__(self, rec):
        super().__init__()
        self.output = rec.output
        self.frames = rec.rec
        self.frameTimes = rec.frameTimes
        self.fps = rec.frameRate
        t = (datetime.now() - rec.recTime).total_seconds()
        n = len(self.frames)
        print("{} frames recorded at average rate of {:.1f} fps.".format(n, n/t))
        self.fn = "{}/{}.{}".format(rec.recFolder, timeStr(), rec.output)
        print("Saving {}...".format(self.fn))
        rec.rec = []
        rec.grab = None

    def run(self):
        if self.output == "s8v" or ImageIO is None: self.s8v(self.fn, self.frames, self.fps, self.frameTimes)
        else:
            with im.get_writer(self.fn, fps=self.fps) as writer:
                for img in self.frames:
                    writer.append_data(numpy.array(img))
        print("Done!")

    @staticmethod
    def s8v(fn, data, fps, t):
        "Convert frames to compressed bytes; save recording in S8V format"
        t[0] = 0
        vid = Video().config(size=data[0].size, frameTimes=t)
#         vid.meta["frameRate"] = fps
        print("Compressing...")
        i = 0
        for frame in data:
            vid._costumes.append(PixelData(frame, True))
            i += 1
            if i % 50 == 0: print(i)
        fps = 30
        vid.removeGaps(2*0.3, 1/fps).sync(fps).save(fn)


def main():
    fldr = ask(askdirectory, allowQuit=None,
        title="Select Recordings Folder", initialdir="./")
    if fldr:
        if len(argv) > 2: ImageIO.ffmpeg(argv[2])
        Recorder((288, 56)).config(recFolder=fldr).play("Screen Recorder")

main()
