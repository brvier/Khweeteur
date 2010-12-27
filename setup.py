#!/usr/bin/python
# -*- coding: utf-8 -*-

#Khweeteur Setup File

import imp
import sys
reload(sys).setdefaultencoding("UTF-8")

try:
    from sdist_maemo import sdist_maemo as _sdist_maemo
except:
    _sdist_maemo = None
    print 'sdist_maemo command not available'

from distutils.core import setup
import khweeteur
from khweeteur.utils import *

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
      requires=['imaging','simplejson','conic','PySide','oauth2'],
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
      'buildversion':'2',
      'depends':['python2.5, pyside-mobility, python-pyside, python-oauth2, python-simplejson, python-conic, python-imaging, python-dbus' if USE_PYSIDE \
      else 'python2.5, python2.5-mobility-location, python-qt4, python-oauth2, python-simplejson, python-conic, python-imaging, python-dbus'],
      'conflicts':'khweeteur-experimental',
      'XSBC_Bugtracker':'http://khertan.net/khweeteur:bugs',
      'XB_Maemo_Display_Name':'Khweeteur',
      'XB_Maemo_Icon_26':'khweeteur.png',
      'section':'user/network',
      'changelog':'* Fix for PyQt4 binding, revert to PyQt4 binding',
      'architecture':'any',
      'postinst':"""#!/bin/sh
chmod +x /usr/bin/khweeteur_launch.py
python -m compileall /usr/lib/python2.5/site-packages/khweeteur
rm -rf /home/user/.khweeteur/
NOTIFICATIONS_CONF="/etc/hildon-desktop/notification-groups.conf"
NOTIFICATIONS_KEY="khweeteur-new-tweets"
if ! grep -q "$NOTIFICATIONS_KEY" "$NOTIFICATIONS_CONF"; then
echo -n "Updating $NOTIFICATIONS_CONF..."
cat >>$NOTIFICATIONS_CONF << EOF
### BEGIN Added by Khweeteur postinst ###
[khweeteur-new-tweets]
Destination=Khweeteur
Icon=khweeteur
Title-Text-Empty=Khweeteur
Secondary-Text=New tweets available
Text-Domain=khweeteur
LED-Pattern=PatternCommonNotification
### END Added by khweeteur postinst ###
EOF
    echo "done."
fi
""",
      'prere':"""#!/bin/sh
rm -rf /usr/lib/python2.5/site-packages/khweeteur/*.pyc""",
      'copyright':'gpl'},
      'bdist_rpm':{
      'requires':'python, python-setuptools, pyside-mobility, python-pyside,python-qt4-core, python-qt4-maemo5, python-oauth2, python-simplejson, python-conic, python-imaging',
      'conflicts':'khweeteur-experimental',
      'icon':'khweeteur.png',
      'group':'Network',}}
     )

