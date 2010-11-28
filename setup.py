#!/usr/bin/python
# -*- coding: utf-8 -*-

#Khweeteur Setup File

import imp
import sys
reload(sys).setdefaultencoding("UTF-8")

from sdist_maemo import sdist_maemo as _sdist_maemo
from distutils.core import setup
import khweeteur

#Remove pyc and pyo file
import glob,os
for fpath in glob.glob('*/*.py[c|o]'):
    os.remove(fpath)

setup(name='khweeteur',
      version=khweeteur.__version__,
      license='GNU GPLv3',
      description="A twitter client for Maemo and MeeGo.",
      long_description="Khweeteur is a small twitter client for Maemo and MeeGo. It showing DMs, mentions and the follower timeline in one window, with a subsequent window for each search. Maemo's notification system is supported, as is auto-update and themeing.",
      author='Benoît HERVIER',
      author_email='khertan@khertan.net',
      maintainer=u'Benoît HERVIER',
      maintainer_email='khertan@khertan.net',
      requires=['imaging','simplejson','conic','PyQt4'],
      url='http://www.khertan.net/khweeteur',
      packages= ['khweeteur',],
      package_data = {'khweeteur': ['icons/*.png']},
      data_files=[('/usr/share/dbus-1/services', ['khweeteur.service']),
                  ('/usr/share/applications/hildon/', ['khweeteur.desktop']),
                  ('/usr/share/pixmaps', ['khweeteur.png','khweeteur_64.png','khweeteur_32.png']),
                  ('/usr/share/icons/hicolor/128x128/apps', ['khweeteur.png']),
                  ('/usr/share/icons/hicolor/64x64/apps', ['icons/hicolor/64x64/apps/khweeteur.png']),
                  ('/usr/share/icons/hicolor/32x32/apps', ['icons/hicolor/32x32/apps/khweeteur.png']),],
      scripts=['khweeteur_launch.py'],
      classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Qt",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: Other",
        "Operating System :: Other OS",
        "Intended Audience :: End Users/Desktop",],
      cmdclass={'sdist_maemo': _sdist_maemo},      
      options = { 'sdist_maemo':{
      'buildversion':'1',
      'depends':'python2.5, python-setuptools, python2.5-mobility-location, python2.5-qt4-gui,python2.5-qt4-core, python2.5-qt4-maemo5, python-oauth2, python-simplejson, python-conic, python-imaging',
      'conflicts':'khweeteur-experimental',
      'XSBC_Bugtracker':'http://khertan.net/khweeteur:bugs',
      'XB_Maemo_Display_Name':'Khweeteur',
      'XB_Maemo_Icon_26':'khweeteur.png',
      'section':'user/network',
      'changelog':'* Fixes for desktop * Fix removing saved search * Fix QMessageBox called twice',
      'architecture':'any',
      'postinst':"""#!/bin/sh
chmod +x /usr/bin/khweeteur_launch.py
python -m compileall /usr/lib/python2.5/site-packages/khweeteur
rm -rf /home/user/.khweeteur/""",
      'copyright':'gpl'},
      'bdist_rpm':{
      'requires':'python, python-setuptools, python-mobility-location, python-qt4-gui,python-qt4-core, python-qt4-maemo5, python-oauth2, python-simplejson, python-conic, python-imaging',
      'conflicts':'khweeteur-experimental',
      'icon':'khweeteur.png',
      'group':'Network',}}
     )

