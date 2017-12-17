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

"Play, import, export, and screen grab to sc8pr Video (s8v) files"

if __name__ == "__main__": import depends
from threading import Thread, active_count
from sys import stderr
from time import time
from os.path import split, exists
from pygame.constants import K_LEFT, K_RIGHT, K_ESCAPE, K_HOME
from sc8pr import Sketch, Image, TOPLEFT, BOTTOMRIGHT
from sc8pr.util import fileExt, nothing
from sc8pr.text import Text, Font
from sc8pr.misc.video import Video
from sc8pr.gui.tkdialog import TkDialog, OPEN, SAVE, FOLDER
try: from sc8pr.misc.grab import Grabber
except: Grabber = None

FONT = Font.mono()
EXTS = [("sc8pr Video", "*.s8v"), ("Image Files", "*.png;*.jpg")]
NO_VID = "Type 'o' to Open a Video"
FFMPEG = "ffmpeg -framerate {} -i frame%%05d.png -pix_fmt yuv420p video.mp4\npause"


class ExportThread(Thread):
    "Export Video as individual frames in a separate thread"

    def __init__(self, vid, fn="save/frame{:05d}.png"):
        super().__init__()
        self.files = fn
        self.vid = vid

    def run(self):
        i = len(self.vid)
        print("Saving as '{}'...".format(self.files), file=stderr)          
        for n in range(i):
            self.vid[n].save(self.files.format(n+1))
            i -= 1
            if i and i % 25 == 0: print("{}".format(i), file=stderr)
        print("Done!", file=stderr)


class ImportThread(Thread):
    "Import frames as a Video in a separate thread"
    vid = None

    def __init__(self, fn, start=1):
        super().__init__()
        self.files = fn
        self.startFrame = start

    def run(self):
        n = self.startFrame
        fn = self.files

        # Load frames into Video instance
        print("Loading '{}'...".format(fn), file=stderr)
        self.vid = Video()
        load = True
        while load:
            try:
                self.vid += Image(fn.format(n))
                n += 1
                if n % 25 == 0: print(n, file=stderr)
            except: load = False

        # Save Video as s8v file
        fn = fn[:fn.index("{")]+ ".s8v"
        print("Saving '{}'...".format(fn), file=stderr)
        self.vid.save(fn)
        print("Done!", file=stderr)


class ConvertThread(Thread):
    "Convert grabbed PIL.Image frames to Video and save as s8v"

    def __init__(self, sk, frames):
        self.sk = sk
        self.fps = sk.frameRate
        self.frames = frames
        super().__init__()

    def filename(self, n):
        return self.sk.recFolder + "/screen_{}.s8v".format(n)

    def run(self):
        # Convert PIL images to Video instance
        sk = self.sk
        vid = Video()
        vid.meta["frameRate"] = self.fps
        print("Converting...", file=stderr)
        n = len(self.frames)
        for f in self.frames:
            vid += sk.grab.image(0, img=f)
            n -= 1
            if n and n % 25 == 0: print(n, file=stderr)

        # Save Video as s8v file
        n = 1
        while exists(self.filename(n)): n += 1
        fn = self.filename(n)
        print("Saving '{}'...".format(fn), file=stderr)
        vid.save(fn)
        print("Done!", file=stderr)


def stopRecord(gr, ev):
    "Event handler to stop screen recording"
    sk = gr.sketch
    if sk.rec is not None:
        frames = sk.rec
        if frames:
            n = len(frames)
            fps = n / (time() - sk._recordStart)
            print("Recorded {} frames @ {:.1f} fps".format(n, fps), file=stderr)
            ConvertThread(sk, frames).start()
        sk.rec = None


class Player(Sketch):
    "s8v Video Utility"

    def __init__(self):
        super().__init__()
        self.vid = None  # Video instance
        self.rec = None  # [PIL.Image, ...]
        self.recFolder = None
        self.help()

    def setup(self):
        "Add status text to sketch"
        w, h = self.size
        cfg = dict(anchor=BOTTOMRIGHT, pos=(w-4,h-4),
            font=FONT, color="#ff0000a0", name="status")
        self += Text().bind(onclick=stopRecord, resize=nothing).config(**cfg)

    def onkeydown(self, ev):
        "Detect keyboard actions when not recording"
        if self.rec is None:
            self.command(ev.unicode.lower(), ev.key)

    def command(self, c, k):
        "Process keyboard commands"
        vid = self.vid
        if c == "?": self.help()
        elif c == "o": self.open()
        elif c == "r": self.record()
        elif vid:
            if c == "x": self.export()
            elif c == "s": self.saveVid()
            elif c == "g": self.grab()
            elif c == "h":
                h = TkDialog(int, "New height?", "Resize").run()
                if h > 63: self.height = h
            elif c == " ":
                vid.costumeTime = 1 - vid.costumeTime
            elif c == "[":
                self.clip[0] = vid.costumeNumber
            elif c == "]":
                self.clip[1] = vid.costumeNumber + 1
            elif c == "f":
                fps = TkDialog(float, "New frame rate in frames per second?",
                    "Frame Rate").run()
                if fps and fps > 0: self.frameRate = fps
            else:
                if k == K_ESCAPE: self.clip = [0, len(vid) + 1]
                elif k == K_HOME:
                    vid.costumeNumber = vid.costumeTime = 0
                elif k in (K_LEFT, K_RIGHT):
                    vid.costumeTime = 0
                    vid.costumeNumber += 1 if k == K_RIGHT else -1

    def ondraw(self):
        "Update status text each frame; grab screen if recording"
        if self.vid:
            data = "{} [{}:{}] {} fps".format(self.vid.costumeNumber + 1,
                self.clip[0] + 1, self.clip[1], self.frameRate)
        elif self.rec is not None:
            self.rec.append(self.grab.image(None))
            data = "Recording: {}\nClick to Stop".format(len(self.rec))
        else: data = NO_VID
        self["status"].config(data=data)

    def onquit(self, ev):
        "Check if program is busy before quitting"
        if active_count() > 1:
            TkDialog(None, "Please wait until conversions are complete!", "Info").run()
        elif self.rec is None: self.quit = True

    def open(self):
        "Open an s8v file or import a sequence of images and convert to s8v"
        fn = TkDialog(OPEN, filetypes=EXTS).run()
        if fn:
            if fn.split(".")[-1].lower() == "s8v":
                try: self.initVid(Video(fn))
                except: print("Unable to open '{}'".format(fn), file=stderr)
            else:
                fn = self.parse(fn)
                if fn: ImportThread(*fn).start()

    def record(self):
        "Begin screen grab recording"
        if self.recFolder is None:
            fldr = TkDialog(FOLDER).run()
            if fldr: self.recFolder = fldr
            else: return
        try:
            param = TkDialog(str, "Enter recording " +
                "parameters using one of these formats:\n" +
                "fps\nfps w h\nfps x y w h", "Record", initialvalue="15").run()
            param = [int(c) for c in param.split(" ") if c]
            self.frameRate = param[0]
            self.grab = Grabber(param[1:] if len(param) > 1 else None)
            self.rec = []
            vid = self.vid
            if vid is not None:
                self.vid = None
                self -= vid
            self._recordStart = time()
        except: pass # Abort!

    def initVid(self, vid):
        "Initialize loaded Video in player"
        if self.vid: self -= self.vid
        self.vid = vid
        self.size = vid.size
        self.clip = [0, len(vid)]
        self += vid.config(anchor=TOPLEFT)
        vid.layer = 0
        fps = vid.meta.get("frameRate")
        if fps: self.frameRate = fps if fps else 30

    @property
    def vidClip(self):
        "Extract the current clip as a new Video instance"
        start, end = self.clip
        if end < start:
            end -= 1
            start += 1
        if self.vid: return self.vid.clip(start, end)

    def saveVid(self):
        "Save the current clip as an s8v file"
        if self.vid:
            fn = TkDialog(SAVE, filetypes=EXTS[:1]).run()
            if fn:
                vid = self.vidClip
                vid.meta["frameRate"] = self.frameRate
                vid.save(fileExt(fn, "s8v"))

    def export(self):
        "Export the current clip as a sequence off images"
        if self.vid:
            path = TkDialog(FOLDER).run()
            if path:
                with open(path + "/convert.bat", "w") as f:
                    f.write(FFMPEG.format(self.frameRate))
                path += "/frame{:05d}.png"
                ExportThread(self.vidClip, path).start()

    def grab(self):
        "Save the current frame of the video as an image file"
        if self.vid:
            fn = TkDialog(SAVE, filetypes=EXTS[:1]).run()
            if fn:
                try: self.vid.costume().save(fileExt(fn, ("png", "jpg")))
                except: print("Unable to save '{}'".format(fn), file=stderr)

    @staticmethod
    def parse(fn):
        """Parse a file name into a pattern; for example...
        'img007.png' --> ('img{:03d}.png', 7)"""
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
        "Display help screen"
        ctrl = {"o":"Open/Convert", "Space":"Play/Pause",
            "Left Arrow":"Previous Frame", "Right Arrow":"Next Frame",
            "Home":"First Frame", "[":"Mark Clip Start", "]":"Mark Clip End",
            "Escape":"Reset Clip", "x":"Export Clip Frames",
            "s":"Save Clip as s8v", "g":"Grab Frame", "f":"Frame Rate",
            "h":"Playback Height", "r":"Record Screen",
            "?":"Show this screen again"}
        if Grabber is None:
            del ctrl["r"]
            print("Screen recording disabled.")
            print("Ensure PIL is installed to use this feature:")
            print("  pip3 install pillow\n")
        msg = "Keyboard Controls...\n\n"
        for i in ctrl.items(): msg += "{:>11s} = {}\n".format(*i)
        print(msg)


Player().play("sc8pr Video Utility")
