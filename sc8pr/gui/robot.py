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

"GUI methods for robot-user interaction"

from sc8pr.util import nothing
from sc8pr.gui.dialog import MessageBox, NumInputBox
import sc8pr.robot


class Robot(sc8pr.robot.Robot):

    def _title(self, title):
        if not title:
            name = self.name
            if name is None: name = "Robot"
            title = "{} says...".format(name)
        return title
    
    def confirm(self, prompt, title=None, response=True):
        "Synchronous input to the robot brain"
        sk = self.sketch
        btns = ["Yes", "No"] if response else ["Okay"]
        mb = MessageBox(prompt, None, btns, self._title(title))
        mb.config(pos=sk.center).setCanvas(sk)
        while mb.result is None: self.updateSensors()
        return mb.result
    
    def textinput(self, prompt, title=None, allowCancel=False, num=False):
        "Synchronous input to the robot brain"
        sk = self.sketch
        btns = None if allowCancel else ["Okay"]
        cls = NumInputBox if num else MessageBox
        mb = cls(prompt, "", btns, self._title(title))
        mb.config(pos=sk.center).setCanvas(sk).bind(onaction=nothing)
        while mb.result is None: self.updateSensors()
        return mb.remove().result
    
    def numinput(self, prompt, title=None, allowCancel=False):
        return self.textinput(prompt, title, allowCancel, True)


# Robot.confirm = confirm
# Robot.numinput = numinput
# Robot.textinput = textinput

# def gui(robot): return robot.bind(confirm, numinput, textinput)
