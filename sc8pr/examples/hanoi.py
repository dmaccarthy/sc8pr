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

"""Animation of the Towers of Hanoi problem. Usage:

from sc8pr.examples.hanoi import play
play(disks=6, speed=1, record="")

The maximum speed is 60 moves per second (the animation frame rate).
When the animation is running, click the mouse to pause or resume.
Set the speed to 0 or None to print the moves to the console only,
without running the animation"""


from sc8pr import Sketch, Image, BOTTOM
from sc8pr.misc.video import Video

def moveDisks(towers, n, start=0, moveTo=1):
    "Recursively generate a sequence of disk movements"
    temp = 3 - start - moveTo
    if n > 1:
        for t in moveDisks(towers, n-1, start, temp): yield t
    towers[moveTo].append(towers[start].pop())
    yield towers
    if n > 1:
        for t in moveDisks(towers, n-1, temp, moveTo): yield t


class Hanoi(Sketch):
    "Animation of the Towers of Hanoi problem"

    def __init__(self, towers, speed, record):
        self.towers = towers
        self.disks = len(towers[0])
        self.hanoi = moveDisks(towers, self.disks)
        self.moves = 0
        self.paused = False
        if speed >= 15:
            self.frameRate = speed
            self.interval = 1
        else:
            self.interval = round(30 / speed)
            self.frameRate = round(speed * self.interval)
        self.update = self.interval
        if record:
            self.vid = Video().autoSave(record)
        else: self.vid = None
        super().__init__((768, 432))

    def setup(self):
        "Add random-color rectangles to the sketch to represent the disks"
        h = min(14, max(1, self.height // self.disks - 1))
        self.height = max(self.height, self.disks * (h + 1))
        width = lambda i: self.width * (0.07 + 0.24 * i / (self.disks - 1))
        for i in range(self.disks):
            w = width(i)
            img = Image((2*w, 2*h), False)
            self += img.snapshot(weight=2).config(anchor=BOTTOM, size=(w,h))
        self.setDiskPositions()

    def ondraw(self):
        "Move one disk at the specified frame interval"
        if self.hanoi and not self.paused and self.frameCount == self.update:
            try:
                vid = self.vid
                if vid is not None: vid += self
                self.moves += 1
                self.update += self.interval
                printState(next(self.hanoi), self.moves)
                self.setDiskPositions()
            except StopIteration: self.hanoi = None
 
    def onquit(self, ev):
        "Write unsaved frames before quitting"
        self.quit = True
        if self.vid: self.vid.autoSave()
 
    def setDiskPositions(self):
        "Update disk positions to match the current state of the towers"
        dx = self.width / 3
        x = dx / 2
        for t in self.towers:
            y = self.height - 1
            for disk in t:
                img = self[disk - 1]
                img.pos = x, y
                y -= img.height - 1
            x += dx
        
    def onclick(self, ev):
        "Pause/Resume animation on mouse click"
        if self.paused: self.update = self.frameCount + 1
        self.paused = not self.paused

def printState(towers, i):
    "Print the current state of the towers"
    print("{:8d}: {} {} {}".format(i, *towers))

def play(disks=6, speed=1, record=""):
    "Run the program"
    towers = list(range(disks, 0, -1)), [], []
    printState(towers, 0)
    if speed: # Play animation
        Hanoi(towers, speed, record).play("Towers of Hanoi")
    else:     # Console only; no animation
        i = 1
        for towers in moveDisks(towers, disks):
            printState(towers, i)
            i += 1

if __name__ == "__main__": play()
