#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with Python and Qt'''

from qwidget_gui import Khweeteur
import sys

#Here is the installation of the hook. Each time a untrapped/unmanaged exception will
#happen my_excepthook will be called.
def install_excepthook():
    '''Install exception hook for the bug reporter'''

    def write_report(error):
        import pickle
        import os.path
        filename = os.path.join(os.path.join(os.path.expanduser("~"),'.khweeteur_crash_report'))
        output = open(filename, 'wb')
        pickle.dump(error, output)
        output.close()

    def my_excepthook(exctype, value, tb):
        #traceback give us all the errors information message like the method, file line ... everything like
        #we have in the python interpreter
        import traceback
        from qwidget_gui import __version__
        s = ''.join(traceback.format_exception(exctype, value, tb))
        print 'Except hook', exctype
        print 'Except hook called : %s' % (s)
        formatted_text = "%s Version %s\nTrace : %s\nComments : " % ('Khweeteur', __version__, s)
        write_report(formatted_text)

    sys.excepthook = my_excepthook

def takeScreenShot(app):
    from PySide.QtGui import QPixmap
    pvr = "/home/user/.cache/launch/net.khertan.khweeteur.pvr"
    QPixmap.grabWidget(app.win).save(pvr, 'png') # tell it to grab only your self.centralwidget screen, which is just window screen without the menu status bar on top. 

if __name__ == '__main__':
    from subprocess import Popen
    import os.path
    Popen(['/usr/bin/python',
           os.path.join(os.path.dirname(__file__),
           'daemon.py'),
           'start'])
    install_excepthook()
    app = Khweeteur()
    app.exec_()
    takeScreenShot(app)
    from PySide.QtCore import QSettings
    settings = QSettings("Khertan Software", "Khweeteur")
    if settings.contains('useDaemon'):
        print settings.value('useDaemon')
        if settings.value('useDaemon') != '2':
            print 'Stop daemon'
            #use system to wait the exec
            os.system('/usr/bin/python ' + \
                os.path.join(os.path.dirname(__file__), 'daemon.py') + ' stop')
