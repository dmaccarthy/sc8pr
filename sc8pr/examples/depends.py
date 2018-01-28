# Copyright 2017-2018 D.G. MacCarthy <http://dmaccarthy.github.io>
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


def check():
	"Check if pygame and sc8pr are available."
	depend = 0
	try: import pygame
	except: depend = 1
	try: import sc8pr
	except: depend = 2
	if depend:
		print("Missing dependencies! Run the following to correct...\n")
		if depend == 1: url = "pygame"
		if depend == 2: url = "https://github.com/dmaccarthy/sc8pr/archive/master.zip"
		input("  pip3 install {}\n\nPress ENTER to exit...".format(url))
		exit()

check()
