#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
 Garfio 2.2
 Copyright (C) 2010
 Author: Mario Colque <mario@tuquito.org.ar>
 Tuquito Team! - www.tuquito.org.ar

 This program is free software; you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation; version 3 of the License.
 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.
 You should have received a copy of the GNU General Public License
 along with this program; if not, write to the Free Software
 Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301, USA.
"""

import gtk, pygtk
pygtk.require('2.0')

class About:
	def __init__(self):
		self.glade = gtk.Builder()
		self.glade.add_from_file('/usr/lib/tuquito/garfio/garfio-about.glade')
		self.window = self.glade.get_object('about')
		self.glade.connect_signals(self)
		self.window.show()
		
	def quit(self, widget, data=None):
		gtk.main_quit()
		return True

if __name__ == '__main__':
	About()
	gtk.main()
