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
from sc8pr.gui.dialog import MessageBox

def _title(robot, title):
    if not title:
        name = robot.name
        if name is None: name = "Robot"
        title = "{} says...".format(name)
    return title

def confirm(robot, prompt, title=None, response=True):
    "Synchronous input to the robot brain"
    sk = robot.sketch
    btns = ["Yes", "No"] if response else ["Okay"]
    mb = MessageBox(prompt, None, btns, _title(robot, title))
    mb.config(pos=sk.center).setCanvas(sk)
    while not mb.command: robot.updateSensors()
    if response: return mb.command.name != "Button_No"

def textinput(robot, prompt, title=None, allowCancel=False, dataType=None):
    "Synchronous input to the robot brain"
    sk = robot.sketch
    btns = None if allowCancel else ["Okay"]
    mb = MessageBox(prompt, "", btns, _title(robot, title))
    mb.config(pos=sk.center).setCanvas(sk).bind(onaction=nothing)
    asking = True
    while asking:
        while not mb.command: robot.updateSensors()
        cancel = mb.command.name == "Button_Cancel"
        data = mb["Input"].data
        try:
            if dataType: data = dataType(data)
            asking = False
        except:
            mb.command = None
    mb.remove()
    return None if cancel else data

def numinput(robot, prompt, title=None, allowCancel=False):
    return textinput(robot, prompt, title, allowCancel, float)

def gui(robot): return robot.bind(confirm, numinput, textinput)
