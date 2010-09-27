#!/usr/bin/python
# -*- coding: utf-8 -*-

#Khweeteur Setup File

from distutils.core import setup
import khweeteur

setup(name='Khweeteur',
      version=khweeteur.__version__,
      license='GNU GPLv3',
      description="A simple twitter client designed for Maemo and MeeGo devices.  It showing DMs, mentions and the follower timeline in one window, with a subsequent window for each search. Maemo's notification system is supported, as is auto-update and themeing.",
      author='Benoît HERVIER',
      author_email='khertan@khertan.net',
      requires=['imaging','simplejson','conic','PyQt4'],
      url='http://www.khertan.net/khweeteur',
      packages= ['khweeteur',],
      package_data = {'khweeteur': ['icons/*.png']},
      data_files=[('/usr/share/dbus-1/services', ['khweeteur.service']),
                  ('/usr/share/applications/hildon/', ['khweeteur.desktop']),
                  ('/usr/share/pixmaps', ['khweeteur.png','khweeteur_64.png','khweeteur_32.png']),
                  ('/usr/share/icons/hicolors/128x128/apps', ['khweeteur.png']),],
      scripts=['khweeteur_launch.py'],
     )

