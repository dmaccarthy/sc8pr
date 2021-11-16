# Copyright 2015-2021 D.G. MacCarthy <http://dmaccarthy.github.io>
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

"""
The sc8pr examples are being moved online and will no longer be
included in the sc8pr package itself, with the exception of the
robotics simulations which are being moved as follows...

sc8pr.examples.soccer -> sc8pr.robot.soccer
sc8pr.examples.robotSim (Parking Lot simulation) -> sc8pr.robot.park
sc8pr.examples.robotSim (Other simulations) -> sc8pr.robot.arena

"""

from sys import stderr

print("WARNING: sc8pr.examples is deprecated. See sc8pr.examples.__init__.py for details", file=stderr)
