#!/usr/bin/python
# -*- coding: utf-8 -*-

#Khweeteur Setup File

import sys
reload(sys).setdefaultencoding("UTF-8")

try:
    from sdist_maemo import sdist_maemo as _sdist_maemo
except:
    _sdist_maemo = None
    print 'sdist_maemo command not available'

from distutils.core import setup
import khweeteur

#Remove pyc and pyo file
import glob,os
for fpath in glob.glob('*/*.py[c|o]'):
    os.remove(fpath)

changes = '* Add on demand gps feature, * Fix GPS Feature, * Add more recent pyside version as dependancy.'

setup(name='khweeteur',
      version=khweeteur.qwidget_gui.__version__,
      license='GNU GPLv3',
      description="A twitter client for Maemo and MeeGo.",
      long_description="Khweeteur is a small twitter client for Maemo and MeeGo. It showing DMs, mentions, searchs, lists, and the follower timeline in one window. Maemo's notification system is supported and can notify for dmsse or mentions even when the ui is not launched, as is auto-update and themeing.",
      author='Benoît HERVIER',
      author_email='khertan@khertan.net',
      maintainer=u'Benoît HERVIER',
      maintainer_email='khertan@khertan.net',
      requires=['imaging','simplejson','conic','PySide','PySide.QtMobility', \
                'httplib2'],
      url='http://www.khertan.net/khweeteur',
      packages= ['khweeteur','khweeteur.oauth', 'khweeteur.oauth2'],
      package_data = {'khweeteur': ['icons/*.png']},
      data_files=[('/usr/share/dbus-1/services', ['khweeteur.service']),
                  ('/usr/share/applications/hildon/', ['khweeteur.desktop']),
                  ('/usr/share/pixmaps', ['khweeteur.png','khweeteur_64.png','khweeteur_32.png']),
                  ('/usr/share/icons/hicolor/128x128/apps', ['khweeteur.png']),
                  ('/usr/share/icons/hicolor/64x64/apps', ['icons/hicolor/64x64/apps/khweeteur.png']),
                  ('/usr/share/icons/hicolor/32x32/apps', ['icons/hicolor/32x32/apps/khweeteur.png']),
                  ('/etc/event.d', ['khweeteurd']),],
      scripts=['scripts/khweeteur'],
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
      'debian_package':'khweeteur',
      'buildversion':'1',
      'depends':'python2.5, pyside-mobility, python-pyside.qtmaemo5 (>=1.0.2), python-pyside.qtwebkit (>=1.0.2), python-pyside.qtcore (>=1.0.2), python-pyside.qtgui (>=1.0.2), python-simplejson, python-conic, python-imaging, python-dbus, python-httplib2',
      'conflicts':'khweeteur-experimental',
      'XSBC_Bugtracker':'http://khertan.net/khweeteur:bugs',
      'XB_Maemo_Display_Name':'Khweeteur',
      'XB_Maemo_Icon_26':'khweeteur.png',
      'XB_Maemo_Upgrade_Description':'%s' % changes,
      'section':'user/network',
      'changelog':changes,
      'architecture':'any',
      'postinst':"""#!/bin/sh
chmod +x /usr/bin/khweeteur
python -m compileall /usr/lib/python2.5/site-packages/khweeteur
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
su user -c "run-standalone.sh /usr/bin/python /usr/lib/python2.5/site-packages/khweeteur/daemon.py stop"
su user -c "run-standalone.sh /usr/bin/python /usr/lib/python2.5/site-packages/khweeteur/daemon.py startfromprefs"
""",
      'prere':"""#!/bin/sh
rm -rf /usr/lib/python2.5/site-packages/khweeteur/*.pyc""",
      'copyright':'gpl'},
      'bdist_rpm':{
      'requires':'python, python-setuptools, python-qtmobility, python-pyside.qtcore, python-pyside.qtgui, python-pyside.qtmaemo5, python-pyside.qtwebkit, pyside-mobility-bearer, python-simplejson, python-conic, python-imaging',
      'conflicts':'khweeteur-experimental',
      'icon':'khweeteur.png',
      'group':'Network',}}
     )
