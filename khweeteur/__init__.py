#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with Python and Qt'''

from qwidget_gui import Khweeteur
import os.path
from PySide.QtCore import QSettings

if __name__ == '__main__':
    from subprocess import Popen
    Popen(['/usr/bin/python',os.path.join(os.path.dirname(__file__),'daemon.py'),'start'])
    app = Khweeteur()
    app.exec_()
    settings = QSettings("Khertan Software", "Khweeteur")
    if settings.contains('useDaemon'):
        print settings.value('useDaemon')
        if settings.value('useDaemon') != '2':
            print 'Stop daemon'
            #use system to wait the exec
            os.system('/usr/bin/python '+os.path.join(os.path.dirname(__file__),'daemon.py') + ' stop')
