# Copyright 2015-2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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


"Play, import, and export sc8pr Video (s8v) files"

if __name__ == "__main__": import _pypath
from threading import Thread, active_count
from sys import stderr
from os.path import split
from pygame.constants import K_LEFT, K_RIGHT, K_ESCAPE, K_HOME
from sc8pr import Sketch, Image, TOPLEFT, BOTTOMRIGHT
from sc8pr.util import fileExt
from sc8pr.text import Text, Font
from sc8pr.misc.video import Video
from sc8pr.gui.tkdialog import askopenfilename, askinteger,\
    askfloat, askdirectory, asksaveasfilename, showinfo

FONT = Font.mono()
EXTS = [("sc8pr Video", "*.s8v"), ("Image Files", "*.png;*.jpg")]
NO_VID = "Type 'o' to Open a Video"
FFMPEG = "ffmpeg -framerate {} -i frame%%05d.png -pix_fmt yuv420p video.mp4\npause"

def noresize(gr, size): pass


class ExportThread(Thread):
    "Export Video as individual frames in a separate thread"

    def __init__(self, vid, fn="save/frame{:05d}.png"):
        super().__init__()
        self.files = fn
        self.vid = vid

    def run(self):
        for f in range(len(self.vid)):
            frame = self.vid.costume(f)
            self.progress(f)
            frame.save(self.files.format(f+1))
        self.onsave()

    def progress(self, n):
        if n == 0: print("Saving as '{}'...".format(self.files), file=stderr)          
        elif n % 25 == 0:
            print("{}/{}".format(n, len(self.vid)), file=stderr)

    def onsave(self): print("Done!", file=stderr)


class ImportThread(Thread):
    "Import frames as a Video in a separate thread"
    vid = None

    def __init__(self, fn, start=1):
        super().__init__()
        self.files = fn
        self.startFrame = start

    def run(self):
        self.vid = Video()
        n = self.startFrame
        load = True
        while load:
            try:
                self.progress(n - 1)
                self.vid += Image(self.files.format(n))
                n += 1
            except: load = False
        self.onload()

    def progress(self, n):
        if n == self.startFrame - 1:
            print("Loading '{}'...".format(self.files), file=stderr)          
        elif n % 25 == 0: print(n, file=stderr)

    def onload(self):
        fn = self.files
        i = self.files.index("{")
        fn = fn[:i]+ ".s8v"
        print("Saving '{}'...".format(fn), file=stderr)
        self.vid.save(fn)
        print("Done!", file=stderr)


class Player(Sketch):
    "s8v Video Player"

    def __init__(self):
        super().__init__()
        self.vid = None
        self.help()

    def setup(self):
        w, h = self.size
        cfg = dict(anchor=BOTTOMRIGHT, pos=(w-4,h-4),
            font=FONT, color="#ff0000a0", name="status")
        self += Text().config(**cfg).bind(resize=noresize)

    def onkeydown(self, ev):
        c = ev.unicode.lower()
        vid = self.vid
        if c == "o": self.open()
        elif c == "?": self.help()
        elif vid:
            if c == "x": self.export()
            elif c == "s": self.saveVid()
            elif c == "g": self.grab()
            elif c == "h":
                h = askinteger("Resize", "New height?")
                if h > 63: self.height = h
            elif c == " ":
                vid.costumeTime = 1 - vid.costumeTime
            elif c == "[":
                self.clip[0] = vid.costumeNumber
            elif c == "]":
                self.clip[1] = vid.costumeNumber + 1
            elif c == "f":
                fps = askfloat("Frame Rate", "New frame rate in frames per second?")
                if fps and fps > 0: self.frameRate = fps
            else:
                k = ev.key
                if k == K_ESCAPE: self.clip = [0, len(vid) + 1]
                elif k == K_HOME:
                    vid.costumeNumber = vid.costumeTime = 0
                elif k in (K_LEFT, K_RIGHT):
                    vid.costumeTime = 0
                    vid.costumeNumber += 1 if k == K_RIGHT else -1

    def ondraw(self):
        st = self["status"]
        if self.vid:
            data = "{} [{}:{}] {} fps".format(self.vid.costumeNumber + 1,
                self.clip[0] + 1, self.clip[1], self.frameRate)
        else: data = NO_VID 
        st.config(data=data)

    def onquit(self, ev):
        if active_count() > 1:
            showinfo("Info", "Please wait until conversions are complete")
        else: self.quit = True

    def open(self):
        fn = askopenfilename(initialdir=".", filetypes=EXTS)
        if fn:
            if fn.split(".")[-1].lower() == "s8v":
                try:
                    vid = Video(fn)
                    vid.config(anchor=TOPLEFT, costumeTime=1)
                    self.size = vid.size
                    if self.vid: self -= self.vid
                    self.vid = vid
                    self += vid
                    vid.layer = 0
                    self.frameRate = 30
                    self.clip = [0, len(vid)]
                    fps = vid.meta.get("frameRate")
                    if fps: self.frameRate = fps
                except: print("Unable to open '{}'".format(fn), file=stderr)
            else:
                fn = self.parse(fn)
                if fn: ImportThread(*fn).start()

    @property
    def vidClip(self):
        start, end = self.clip
        if end < start:
            end -= 1
            start += 1
        if self.vid: return self.vid.clip(start, end)

    def saveVid(self):
        if self.vid:
            fn = asksaveasfilename(initialdir=".", filetypes=EXTS[:1])
            if fn:
                vid = self.vidClip
                vid.meta["frameRate"] = self.frameRate
                vid.save(fileExt(fn, "s8v"))

    def export(self):
        if self.vid:
            path = askdirectory()
            if path:
                with open(path + "/convert.bat", "w") as f:
                    f.write(FFMPEG.format(self.frameRate))
                path += "/frame{:05d}.png"
                ExportThread(self.vidClip, path).start()

    def grab(self):
        if self.vid:
            fn = asksaveasfilename(initialdir=".", filetypes=EXTS[1:])
            if fn:
                try: self.vid.costume().save(fileExt(fn, ("png", "jpg")))
                except: print("Unable to save '{}'".format(fn), file=stderr)

    @staticmethod
    def parse(fn):
        path, fn = split(fn)
        if not path: path = "."
        ftype = fn.split(".")[-1]
        fn = fn[:-1-len(ftype)]
        n = None
        i = 0
        for c in fn:
            if c in "0123456789":
                n = i
                break
            else: i += 1
        if n is None: return None
        start = int(fn[n:])
        if fn[n] == "0":
            d = len(fn) - n
            fn = fn[:n] + "{:0" + str(d) + "d}." + ftype
        else:
            fn = fn[:n] + "{}." + ftype
        return path + "/" + fn, start

    @staticmethod
    def help():
        msg = """(c) 2015-2017 by D.G. MacCarthy
http://dmaccarthy.github.io\n
Keyboard Controls...\n\n"""
        ctrl = {"o":"Open / Convert", "Space":"Play/Pause",
            "Left Arrow":"Previous Frame", "Right Arrow":"Next Frame",
            "Home":"First Frame", "[":"Mark Clip Start", "]":"Mark Clip End",
            "Escape":"Reset Clip", "x":"Export Clip Frames",
            "s":"Save Clip as s8v", "g":"Grab Frame", "f":"Frame Rate",
            "h":"Playback Height", "?":"Show this screen again"}
        for i in ctrl.items():
            msg += "{:>11s} = {}\n".format(*i)
        print(msg)


Player().play("sc8pr Video Utility")
