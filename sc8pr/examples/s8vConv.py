# Copyright 2018 D.G. MacCarthy <http://dmaccarthy.github.io>
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

if __name__ == "__main__": import depends
from sys import argv
from pygame import K_LEFT, K_RIGHT, K_HOME
from sc8pr import Sketch, TOPLEFT, BOTTOMRIGHT
from sc8pr.misc.video import ImageIO, Video
from sc8pr.gui.tkdialog import TkDialog, OPEN, SAVE
from sc8pr.text import Text, Font
from sc8pr.util import rgba

VIDEOTYPES = [("Video", "*.s8v;*.mp4;*.mkv;*.wmv;*.avi;*.mov")]
IMAGETYPES = [("Images", "*.png;*.jpg")]


class VideoPlayer(Sketch):

    def setup(self):
        self.menu()
        attr = dict(anchor=BOTTOMRIGHT, color="red", font=Font.mono())
        self["Text"] = Text().config(pos=(self.width-4, self.height-4), **attr) 

    @staticmethod
    def progress(i, n, encode):
        if i == 1:
            msg = "\nSaving" if encode else "\nLoading"
            if n: msg += " {}".format(n)
            msg += " frames..."
        elif i == n: msg = "Done!"
        elif i and i % 50 == 0: msg = str(i)
        else: return
        print(msg)

    @staticmethod
    def s8v(fn): return fn.split(".")[-1].lower() == "s8v"

    def open(self):
        fn = TkDialog(OPEN, filetypes=VIDEOTYPES).run()
        if fn:
            if "Video" in self: self -= self["Video"]
            if self.s8v(fn): vid = Video(fn, progress=self.progress)
            else: vid = ImageIO.decode(fn, self.progress)
            vid.originalSize = self.size = vid.size
            self["Video"] = vid.config(anchor=TOPLEFT)
            vid.layer = 0
            self.frameRate = vid.meta.get("frameRate", 30)
            self.clip = [0, len(vid) - 1]

    def saveAs(self):
        fn = TkDialog(SAVE, filetypes=VIDEOTYPES, defaultextension="s8v").run()
        if fn:
            f0, f1 = self.clip
            f1 += -1 if f1 < f0 else 1
            vid = self["Video"]
            clip = vid.clip(f0, f1).config(size=vid.originalSize)
            if self.s8v(fn): clip.save(fn, self.progress)
            else: ImageIO.encode(clip, fn, self.frameRate, self.progress)

    def ondraw(self):
        if "Video" in self:
            vid = self["Video"]
            n = vid.costumeNumber
            msg = "{1}/{2} [{3}, {4}] {0} fps".format(self.frameRate, n, len(vid), *self.clip)
        else: msg = "Type 'o' to Open Video"
        txt = self["Text"]
        if txt.data != msg: txt.config(data=msg)

    def onkeydown(self, ev):
        u = ev.unicode.upper()
        if u == '?': self.menu()
        elif u == 'O': self.open()
        elif u == '\t': self["Text"].config(color=rgba(False))
        elif "Video" in self:
            vid = self["Video"]
            if u == 'S': self.saveAs()
            elif u == 'G':
                fn = TkDialog(SAVE, filetypes=IMAGETYPES).run()
                if fn: vid[vid.costumeNumber].save(fn)
            elif u == 'F':
                fps = TkDialog(float, "Enter new frame rate:").run()
                if fps: self.frameRate = max(1.0, fps)
            elif u == ' ':
                vid.costumeTime = 1 - vid.costumeTime 
            elif ev.key == K_HOME:
                vid.costumeTime = vid.costumeNumber = 0
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
            'RIGHT': "Next Frame", "HOME": "Rewind", '[': "Clip Start",
            ']': "Clip End", 'F': "Frame Rate", "TAB": "Display Color",
            '?': "Show Menu"}
        print("\nKeyboard Commands:")
        for i in m:
            print("{:^5s} = {}".format(i, m[i]))


# Run the program...
if __name__ == "__main__":
    if len(argv) > 1: ImageIO.ffmpeg(argv[1])
    VideoPlayer().play("sc8pr Video Converter")
