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
import gettext, os, commands, sys
from subprocess import Popen, PIPE
import pynotify, threading, locale, gobject
from time import sleep

# i18n
gettext.install('garfio', '/usr/share/tuquito/locale')

codificacion = locale.getpreferredencoding()
utf8conv = lambda x : unicode(x, codificacion).encode('utf8')

#-Variables
user = os.environ.get('SUDO_USER')
config = '/usr/lib/tuquito/garfio/garfio.conf'

class Language:
	def __init__(self, code, description):
		self.code = code
		self.description = description

class Garfio(threading.Thread):
	def __init__(self, glade, action, file=None, lang=None):
		threading.Thread.__init__(self)
		self.builder = glade
		self.action = action
		self.file = file
		self.lang = lang
		self.cmd = ['garfio', self.action]

		self.label = self.builder.get_object('pblabel')
		self.pb = self.builder.get_object('progressbar')
		self.sw = self.builder.get_object('scrolled')
		self.sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.builder.get_object('lexp').set_label(_('View details'))
		self.buffer = self.builder.get_object('textbuffer')
		self.textarea = self.builder.get_object('textarea')

		self.builder.get_object('window').hide()
		self.builder.get_object('progress').show()
		self.builder.get_object('progress').connect('delete-event', self.quitStop)

	def pulse(self):
		while not self.quit:
			sleep(0.05)
			gtk.gdk.threads_enter()
			self.pb.pulse()
			gtk.gdk.threads_leave()
		self.pb.set_fraction(0.0)

	def terminate(self):
		self.quit = True
		try:
			os.kill(self.popen.pid, 9)
		except Exception, d:
			print 'Error: ' + str(d)
		print "Terminate threads"

	def quitStop(self, widget, data=None):
		#self.terminate()
		#gtk.main_quit()
		if self.quit:
			self.builder.get_object('progress').hide()
		return True

	def setStatus(self, txt):
		self.label.set_markup('<i>%s</i>' % txt)

	def newThread(self, method):
		t = threading.Thread(target=method, args=())
		t.start()

	def execCmd(self):
		self.popen = Popen(self.cmd, stdout=PIPE, stderr=PIPE, close_fds=True)
		while True:
			out = self.popen.stdout.readline()
			if not out:
				self.terminate()
				break
			gtk.gdk.threads_enter()
			iter = self.buffer.get_end_iter()
			self.buffer.place_cursor(iter)
			self.buffer.insert(iter, utf8conv(out))
			self.textarea.scroll_to_mark(self.buffer.get_insert(), 0.1)
			gtk.gdk.threads_leave()

		gtk.gdk.threads_enter()
		self.builder.get_object('progress').hide()
		self.builder.get_object('window').show()
		gtk.gdk.threads_leave()

		if os.path.exists('/tmp/finish-garfio') and self.action != 'clean' and self.action != 'backh':
			data = commands.getoutput('cat /tmp/finish-garfio')
			# i18n dialogFinish
			gtk.gdk.threads_enter()
			self.builder.get_object('finish').set_markup('<big><b>' + _('Finished!') + '</b></big>')
			if self.action == 'rest':
				self.builder.get_object('finish').format_secondary_text(_('Your backup has been restored correctly\n'))
			else:
				self.builder.get_object('finish').format_secondary_text(_('His image has been generated successfully\n') + data)
			self.builder.get_object('finish').show()
			gtk.gdk.threads_leave()

	def run(self):
		print "Start threads"
		self.quit = False
		self.newThread(self.pulse)
		
		if self.action == 'rest':
			self.cmd.append(self.file)
			self.setStatus(_('Restoring file...'))
			self.over = self.builder.get_object('check-restore').get_active()
			self.cmd.append(str(self.over))
		elif self.action == 'trans':
			self.cmd.append(self.file)
			self.cmd.append(self.lang)

		self.setStatus(_('Working... Please be patient'))
		self.newThread(self.execCmd)

class Translate(threading.Thread):
	def __init__(self, glade):
		threading.Thread.__init__(self)
		self.builder = glade
		self.builder.get_object('label_lang_trans').set_label(_('Please select a language: '))
		self.builder.get_object('label_iso_trans').set_label(_('Select a ISO image: '))
		self.builder.get_object('btn_start').connect('clicked', self.testTranslate)
		self.builder.get_object('btn_cancel').connect('clicked', self.closeTrans)
		self.builder.get_object('trans').connect('delete-event', self.closeTrans)

	def run(self):
		self.combobox = self.builder.get_object('combobox')
		self.combobox.set_model(None)
		self.model = gtk.ListStore(gobject.TYPE_STRING)
		self.languages = []
		self.languageCodes = []
		f = open('/usr/lib/tuquito/garfio/languages.list', 'r')
		for line in f:
			parts = line.strip().split(':')
			if len(parts) == 2:
				language = Language(parts[0], parts[1])
				self.languages.append(language)
				self.languageCodes.append(language.code)
		f.close()
		for language in self.languages:
			self.model.append(['%s (%s)' % (language.code, language.description)])
		self.combobox.set_model(self.model)
		cell = gtk.CellRendererText()
		self.combobox.pack_start(cell, True)
		self.combobox.add_attribute(cell, 'text', 0)
		self.combobox.set_active(0)
		self.builder.get_object('trans').show()

	def testTranslate(self, widget):
		language = self.combobox.get_active()
		self.language = self.model[language][0]
		self.language = self.language.split(' ')[0].strip()
		if not self.language in self.languageCodes:
			print "Unkown language code: " + self.language
			sys.exit(1)
		self.filename = self.builder.get_object('filechooserbutton').get_filename()
		if self.filename and self.filename.endswith('.iso'):
			self.closeTrans(self)
			hilo = Garfio(self.builder, 'trans', self.filename, self.language)
			hilo.start()

	def closeTrans(self, widget, data=None):
		self.builder.get_object('trans').hide()
		return True

class WinGarfio:
	def __init__(self):
		self.glade = gtk.Builder()
		self.glade.add_from_file('/usr/lib/tuquito/garfio/garfio.glade')
		self.window = self.glade.get_object('window')
		self.glade.connect_signals(self)

		# i18n
		self.glade.get_object('frase').set_label(_('Your live CD to a single click'))
		self.glade.get_object('ldist').set_label(_('Make a custom distribution'))
		self.glade.get_object('l2dist').set_label(_('<small>Create your own distro</small>'))
		self.glade.get_object('lback').set_label(_('Make a backup of the system'))
		self.glade.get_object('l2back').set_label(_('<small>Creates a copy of your hard drive</small>'))
		self.glade.get_object('lbackh').set_label(_('Make a backup of the environment'))
		self.glade.get_object('l2backh').set_label(_('<small>Creates a copy of your home directory</small>'))
		self.glade.get_object('ltrans').set_label(_('Make an ISO in your language'))
		self.glade.get_object('l2trans').set_label(_('<small>Make Tuquito speaks your language</small>'))	
		#self.window.show()

	def rest(self, garfioFile):
		self.action = 'rest'
		# i18n dialogRest
		self.file = garfioFile
		self.glade.get_object('restoreBackup').set_title('Garfio')
		self.glade.get_object('label-restore').set_markup('<big><b>' + _('Want to restore your home directory?') + '</b></big>')
		self.glade.get_object('label-s-restore').set_label(_('This option allows you to restore your files and settings from a backup.'))
		self.glade.get_object('check-restore').set_label(_('Overwrite existing files?'))
		self.glade.get_object('restoreBackup').show()

	def dist(self, widget):
		self.action = 'dist'
		# i18n dialogDist
		self.glade.get_object('dialog').set_title(_('Confirmation'))
		self.glade.get_object('dialog').set_markup('<big><b>' + _('Want to create a custom distribution?') + '</b></big>')
		self.glade.get_object('dialog').format_secondary_text(_('This option allows you to create a distribution based on your system installed, creating an ISO image that will not include the /home directory, settings and user files. You can then burn the image to use as a CD/DVD/USB live and share with all your friends.'))
		self.glade.get_object('dialog').show()

	def back(self, widget):
		self.action = 'back'
		# i18n dialogBack
		self.glade.get_object('dialog').set_title(_('Confirmation'))
		self.glade.get_object('dialog').set_markup('<big><b>' + _('Want to create a backup of your system?') + '</b></big>')
		self.glade.get_object('dialog').format_secondary_text(_('This option allows you to create an ISO image of your entire system, including the /home directory, configurations files and all existing users. You can then burn the image to use as a CD / DVD live or installable and always have a copy of your entire system.'))
		self.glade.get_object('dialog').show()

	def backh(self, widget):
		self.action = 'backh'
		# i18n dialogBackh
		self.glade.get_object('dialog').set_title(_('Confirmation'))
		self.glade.get_object('dialog').set_markup('<big><b>' + _('Would you like to create a backup of your environment?') + '</b></big>')
		self.glade.get_object('dialog').format_secondary_text(_('This option allows you to create a backup of your / home. This may include whether or not your existing settings and files saved. To configure this option go to Preferences\n\nThen you can restore it by double click.'))
		self.glade.get_object('dialog').show()

	def clean(self, widget):
		self.action = 'clean'
		# i18n dialogClean
		self.glade.get_object('dialog').set_title(_('Confirmation'))
		self.glade.get_object('dialog').set_markup('<big><b>' + _('Would you like to clean up temporary files?') + '</b></big>')
		self.glade.get_object('dialog').format_secondary_text(_('This option allows you to clean the temporary working directory, deleting all the files that are created to generate an ISO image.'))
		self.glade.get_object('dialog').show()

	def trans(self, widget):
		self.action = 'trans'
		# i18n dialogTrans
		self.glade.get_object('dialog').set_title(_('Confirmation'))
		self.glade.get_object('dialog').set_markup('<big><b>' + _('Do you want to change the language of an ISO image?') + '</b></big>')
		self.glade.get_object('dialog').format_secondary_text(_('This option allows you to modify an ISO image Tuquito, leaving the default language selected.'))
		self.glade.get_object('dialog').show()

	def confirm(self, widget, data=None):
		self.glade.get_object('dialog').hide()
		if self.action == 'rest':
			self.glade.get_object('restoreBackup').hide()
			hilo = Garfio(self.glade, self.action, self.file)
			hilo.start()
		elif self.action == 'trans':
			if data == -8:
				t = Translate(self.glade)
				t.start()
		else:
			if data == -8:
				hilo = Garfio(self.glade, self.action)
				hilo.start()
			
	def notify(self, text):
		sh = 'su ' + user + ' -c "notify-send \'Garfio\' \'' + text + '\' -i /usr/lib/tuquito/garfio/logo.png"'
		os.system(sh)

	def pref(self, widget):
		f = open(config, 'r')
		g = f.readlines()
		f.close()
		for stri in g:
			stringa = stri.split('=')
			par = stringa[0].strip()
			val = stringa[1].strip()
			val = val.replace('"','')
			if par == 'TMPDIR':
				if val == '':
					workdir = '/home'
				else:
					workdir = val
			elif par == 'LIVEUSER':
				if val == '':
					liveuser = 'tuquito'
				else:
					liveuser = val
			elif par == 'EXCLUDES':
				excludes = val
			if par == 'LIVECDLABEL':
				if val == '':
					livecdlabel = 'Tuquito LiveCD'
				else:
					livecdlabel = val
			elif par == 'CUSTOMISO':
				if val == '':
					iso = 'tuquito.iso'
				else:
					iso = val
			elif par == 'NOHIDDEN':
				if val == 'YES':
					nohidden = True
				else:
					nohidden = False

		self.glade.get_object('workdir').set_text(workdir)
		self.glade.get_object('excludes').set_text(excludes)
		self.glade.get_object('liveuser').set_text(liveuser)
		self.glade.get_object('livecdlabel').set_text(livecdlabel)
		self.glade.get_object('iso').set_text(iso)
		self.glade.get_object('check-backup').set_active(nohidden)
		#i18n pref
		self.glade.get_object('pref').set_title(_('Preferences'))
		self.glade.get_object('label-workdir').set_text(_('Temporary working directory'))
		self.glade.get_object('workdir').set_tooltip_text(_('This is the directory where the ISO image to be stored and, temporarily, the necessary files as you work.'))
		self.glade.get_object('label-excludes').set_text('\n' + _('Files and directories to exclude, separated by commas'))
		self.glade.get_object('label-liveuser').set_text('\n' + _('Username for live CD/DVD'))
		self.glade.get_object('liveuser').set_tooltip_text(_('Username generated by default when you start in live mode.'))
		self.glade.get_object('label-livecdlabel').set_text('\n' + _('Name of the live CD/DVD'))
		self.glade.get_object('livecdlabel').set_tooltip_text(_('This is the name of the mounted unit that contains the iso image.'))
		self.glade.get_object('label-iso').set_text('\n' + _('Name of iso file'))
		self.glade.get_object('iso').set_tooltip_text(_('This is the name of your file .iso'))
		self.glade.get_object('check-backup').set_label(_('Backup of /home without files or hidden directories'))
		self.glade.get_object('check-backup').set_tooltip_text(_('If you enable this option, when you generate a backup of the environment (/home), do not store the files or hidden directories.'))
		self.glade.get_object('pref').show()

	def prefSave(self, widget, data=None):
		workdir = self.glade.get_object('workdir').get_text().strip()
		excludes = self.glade.get_object('excludes').get_text().strip()
		liveuser = self.glade.get_object('liveuser').get_text().strip()
		livecdlabel = self.glade.get_object('livecdlabel').get_text().strip()
		iso = self.glade.get_object('iso').get_text().strip()
		nohidden = self.glade.get_object('check-backup').get_active()

		if nohidden == True:
			nohidden = 'YES'
		else:
			nohidden = 'NO'

		if os.path.exists(config):
			f = open(config, 'w')
			f.write('TMPDIR="' + workdir + '"\n')
			f.write('EXCLUDES="' + excludes + '"\n')
			f.write('LIVEUSER="' + liveuser + '"\n')
			f.write('LIVECDLABEL="' + livecdlabel + '"\n')
			f.write('CUSTOMISO="' + iso + '"\n')
			f.write('NOHIDDEN="' + nohidden + '"\n')
			f.close()
		self.prefHide(self)

	def closeFinish(self, widget, data=None):
		self.glade.get_object('finish').hide()
		self.glade.get_object('window').show()
		return True

	def dialogHide(self, widget, data=None):
		self.glade.get_object('dialog').hide()
		return True

	def prefHide(self, widget, data=None):
		self.glade.get_object('pref').hide()
		return True

	def about(self, widget, data=None):
		os.system('/usr/lib/tuquito/garfio/garfio-about.py &')

	def quit(self, widget, data=None):
		gtk.main_quit()
		return True

if __name__ == '__main__':
	gtk.gdk.threads_init()
	w = WinGarfio()
	if len(sys.argv) != 2:
		w.window.show()
	else:
		w.rest(sys.argv[1])
	gtk.main()
