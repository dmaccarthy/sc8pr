# Copyright 2015-2016 D.G. MacCarthy <devwigs@gmail.com>
#
# This file is part of WIGS.
#
# WIGS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# WIGS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WIGS.  If not, see <http://www.gnu.org/licenses/>.


"""Change the default styles for various Widget classes"""

from wigs.util import copyAttr
from wigs.widgets import Widget, Container, BaseButton, Button, Slider, MsgBox
from wigs.grid import MenuItem, FileItem, FileBrowser


def applyStyles(font=None):

    copyAttr({"font": font, "border": 0, "pad": 0, "color": (0,0,0), "borderColor": (144,144,144), "altColor": (144,144,144),
        "bgColor": None, "colors": {
            Widget.DEFAULT: (232,232,232),
            Widget.HOVER: (230,241,255),
            Widget.SELECT: (176,176,255),
            Widget.FOCUS: (255,255,255),
            Widget.DISABLE: (232,232,232)
        }
    }, Widget)
    
    copyAttr({"color":(255,255,255), "borderColor":(0,0,255), "altBdColor":(192,192,192)} , Container)
    copyAttr({"border":1, "pad":4} , BaseButton) # Button, TextInput
    copyAttr({"border":1, "pad":4, "bgColor":Widget.colors[Widget.DEFAULT], "fgColor":Widget.colors[Widget.HOVER]} , Slider)
    copyAttr({"border":3, "pad":8, "bgColor": (224,224,224)}, MsgBox)
    copyAttr({"border":1, "borderColor":Widget.borderColor, "altBdColor":Widget.borderColor}, FileBrowser)
    
    copyAttr({"border":Button.border, "pad": Button.pad, "borderColor": (255,255,255)}, MenuItem)
    copyAttr({"colors":{
        Widget.DEFAULT: (255,255,255),
        Widget.HOVER: Widget.colors[Widget.HOVER],
        Widget.SELECT: Widget.colors[Widget.SELECT]
    }}, FileItem)


# Call applyStyles AFTER initializing Pygame if you to set font properties
applyStyles()
