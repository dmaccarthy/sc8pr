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

"""
	Check if the PYTHONPATH is correctly configured by trying to import sc8pr.
	Modify the PYTHONPATH if an exception occurs.
"""

try:
	import sc8pr
except:
	import sys, os
	p = os.path.abspath(os.path.dirname(__file__))
	sys.path.append(os.path.abspath(p + "/../.."))
