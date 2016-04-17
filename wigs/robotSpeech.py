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


from wigs.chrome.speech import Voice
from wigs.robot import Robot

class TalkingRobot(Robot):
    
    def setVoice(self, **kwargs):
        self.voice = Voice(**kwargs)

    def say(self, *text, **kwargs):
        self.voice.say(*text, **kwargs)
    
    def shutdown(self):
        try: self.voice.server.stop()
        except: pass
        super().shutdown()