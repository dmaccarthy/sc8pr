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


from os.path import abspath
from tkinter import Tk
from tkinter.messagebox import showinfo, askyesno, askokcancel, askretrycancel
from tkinter.simpledialog import askstring, askinteger, askfloat
from tkinter.filedialog import askopenfilename, asksaveasfilename, askdirectory
from pygame import QUIT
from pygame.event import set_blocked, set_allowed

OPEN = 0
SAVE = 1
FOLDER = 2
YES = 0
OKAY = 1
RETRY = 2


class TkDialog:
    "A class for running simple Tkinter dialogs from pygame"
    root = Tk()
    root.withdraw()

    def __init__(self, response=str, text="", title=None, accept=0, **options):
        if response is bool:
            self.dialog = [askyesno, askokcancel, askretrycancel][accept]
        else: self.dialog = {None:showinfo, str:askstring, int:askinteger, float:askfloat,
            0:askopenfilename, 1:asksaveasfilename, 2:askdirectory}[response]
        self.options = options.copy()
        if "initialdir" in options:
            self.options["initialdir"] = abspath(options["initialdir"])
        if type(response) is int:
            self.args = tuple()
            if title: self.options["title"] = title
        else:
            if title is None:
                title = "Info" if response is None else "Confirm" if response is bool else "Input"
            self.args = title, text

    def run(self, quitAllowed=True):
        "Disable pygame QUIT event while running the dialog"
        set_blocked(QUIT)
        val = self.dialog(*self.args, **self.options)
        if quitAllowed: set_allowed(QUIT)
        return val

    def runAlone(self):
        "Run dialog without pygame"
        return self.dialog(*self.args, **self.options)
