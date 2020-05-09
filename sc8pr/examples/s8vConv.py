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

"Convert S8V videos using imageio and ffmpeg"

try: import imageio
except Exception as e:
    print(e)
    print("Try running 'pip3 install imageio imageio-ffmpeg' on command line")
try:
    from sc8pr import Sketch, TOPLEFT, BOTTOMRIGHT
    from sc8pr.misc.video import ImageIO, Video
    from sc8pr.gui.dialog import ask
    from sc8pr.text import Text, Font
    from sc8pr.util import rgba
except Exception as e:
    print(e)
    print("Try running 'pip3 install sc8pr' on command line")
    exit()
from pygame import K_LEFT, K_RIGHT, K_HOME
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.simpledialog import askfloat

VIDEOTYPES = [("Video", "*.s8v;*.mp4;*.mkv;*.wmv;*.avi;*.mov")]
IMAGETYPES = [("Images", "*.png;*.jpg")]


class VideoPlayer(Sketch):

    def setup(self):
        self.caption = "sc8pr Video Converter"
        self.menu()
        attr = dict(anchor=BOTTOMRIGHT, color="red", bg="#a0a0a080", font=Font.mono(), fontSize=18)
        self["Text"] = Text().config(pos=(self.width-4, self.height-4), **attr) 

    @staticmethod
    def progress(i, n=None):
        if i == 1: print("\n{} frames...".format(n))
        elif i % 50 == 0 or i == n: print("{}".format(i))

    @staticmethod
    def s8v(fn): return fn.split(".")[-1].lower() == "s8v"

    def open(self):
        fn = ask(askopenfilename, filetypes=VIDEOTYPES)
        if fn:
            if "Video" in self: self -= self["Video"]
            if self.s8v(fn):
                vid = Video(fn, progress=self.progress)
            else: vid = ImageIO.decodev(fn, self.progress)
            vid.originalSize = self.size = vid.size
            self["Video"] = vid.config(anchor=TOPLEFT)
            vid.layer = 0
            self.frameRate = vid.meta.get("frameRate", 30)
            self.clip = [0, len(vid) - 1]
            self.caption = fn

    def saveAs(self):
        fn = ask(asksaveasfilename, filetypes=VIDEOTYPES, defaultextension="s8v")
        if fn:
            f0, f1 = self.clip
            f1 += -1 if f1 < f0 else 1
            vid = self["Video"]
            clip = vid.clip(f0, f1).config(size=vid.originalSize)
            if self.s8v(fn): clip.save(fn, self.progress)
            else: ImageIO.encodev(clip, fn, self.frameRate, self.progress)

    def ondraw(self):
        if "Video" in self:
            vid = self["Video"]
            n = vid.costumeNumber
            msg = "{1}/{2} [{3},{4}] @ {0}".format(self.frameRate, n, len(vid), *self.clip)
            if n == len(vid) - 1: vid.costumeTime = 0
        else: msg = "Type 'o' to Open Video"
        txt = self["Text"]
        if txt.data != msg:
            txt.config(data=msg)
            w = 0.98 * self.width
            if txt.width > w: txt.config(width=w)

    def onkeydown(self, ev):
        u = ev.unicode.upper()
        if u == '?': self.menu()
        elif u == 'O': self.open()
        elif u == '\t': self["Text"].config(color=rgba(False))
        elif "Video" in self:
            vid = self["Video"]
            if u == 'S': self.saveAs()
            elif u == 'G':
                fn = ask(asksaveasfilename, filetypes=IMAGETYPES)
                if fn: vid[vid.costumeNumber].save(fn)
            elif u == 'F':
                fps = ask(askfloat, title="Frame Rate", prompt="Enter new frame rate:")
                if fps: self.frameRate = max(1.0, fps)
            elif u == ' ':
                vid.costumeTime = 1 - vid.costumeTime 
            elif ev.key == K_HOME:
                vid.costumeTime = vid.costumeNumber = 0
            elif u == "N":
                vid.costumeTime = 0
                try: vid.costumeNumber = int(input("Go to frame? "))
                except: pass
            elif ev.key in (K_LEFT, K_RIGHT):
                vid.costumeTime = 0
                n = vid.costumeNumber + (1 if ev.key == K_RIGHT else -1)
                if n < 0: n = len(vid) - 1
                elif n >= len(vid): n = 0
                vid.costumeNumber = n
            elif u in "[]":
                self.clip["[]".index(u)] = vid.costumeNumber

    @staticmethod
    def menu():
        m = {'O': "Open Video", 'S': "Save Clip", 'G': "Grab Frame",
            "SPACE":"Pause/Resume", 'LEFT': "Previous Frame",
            'RIGHT': "Next Frame", "HOME": "Rewind", 'N': "Frame Number", '[': "Clip Start",
            ']': "Clip End", 'F': "Frame Rate", "TAB": "Display Color",
            '?': "Show Menu"}
        print("\nKeyboard Commands:")
        for i in m:
            print("{:^5s} = {}".format(i, m[i]))


# Main program...

def main(ffmpeg=False):
    if ffmpeg: ImageIO.ffmpeg(ffmpeg)
    VideoPlayer().play()

if __name__ == "__main__":
    if ImageIO:
        from sys import argv
        ff = argv[1] if len(argv) > 1 else input("Path to ffmpeg? ").strip()
    else: ff = False
    main(ff)
