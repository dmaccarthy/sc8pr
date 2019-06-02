# Copyright 2015-2019 D.G. MacCarthy <https://dmaccarthy.github.io/sc8pr>
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

from tkinter import Tk

root = None

def init():
    global root
    if root is None:
        root = Tk()
        root.withdraw()

def clipboardPut(text):
    init()
    root.clipboard_clear()
    root.clipboard_append(text)
    root.update()

def clipboardGet():
    init()
    root.update()
    try: s = root.clipboard_get()
    except: s = None
    return s

def screenSize():
    init()
    return root.winfo_screenwidth(), root.winfo_screenheight()
