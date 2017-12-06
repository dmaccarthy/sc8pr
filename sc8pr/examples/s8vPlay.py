# Copyright 2017 D.G. MacCarthy <http://dmaccarthy.github.io>
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


if __name__ == "__main__": import _pypath
else: raise Exception("Example {} must be run as main module".format(__name__))

from sc8pr import Sketch, TOPLEFT
from sc8pr.misc.video import Video
from sc8pr.gui.tkdialog import askopenfilename

def setup(sk):
    vid = Video(sk.filename)
    sk.config(size=vid.size, frameRate=30)
    sk += vid.config(costumeTime=1, anchor=TOPLEFT)

fn = askopenfilename(initialdir="./", filetypes=[("sc8pr Video", "*.s8v")])
if fn: Sketch().config(filename=fn).play("sc8pr Video Player")