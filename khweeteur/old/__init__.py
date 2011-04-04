#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with PySide and QML'''

__version__ = '0.2.0'

from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtDeclarative import *
#from PySide import QtOpenGL

import os
import sys

import twitter
from tweetslist import *

if __name__ == '__main__':

    app = QApplication(sys.argv)
     
    mainWin = QMainWindow()    
    mainView = QDeclarativeView()

    import glob
    import pickle
    import time
    print 'load tweets'
    start = time.time()
    TIMELINE_PATH = '/home/user/.khweeteur/HomeTimeline'
    cach_path = TIMELINE_PATH
    uids = glob.glob(cach_path + '/*')[:60]
    statuses = []
    for uid in uids:
        uid = os.path.basename(uid)
        try:
            pkl_file = open(os.path.join(cach_path, uid), 'rb')
            status = pickle.load(pkl_file)
            pkl_file.close()
            statuses.append(status)
        except:
            pass
    print time.time() - start
    print len(statuses) 
    statusesWrapped = [StatusWrapper(status) for status in statuses]
    controller = Controller()
    statusesList = TweetsListModel(statusesWrapped)
     
    mainViewContext = mainView.rootContext()
     
    mainViewContext.setContextProperty('controller', controller)
    mainViewContext.setContextProperty('tweetsListModel', statusesList)
     
    mainView.setSource('tweetslist.qml')

#    glw = QtOpenGL.QGLWidget()
#    mainView.setViewport(glw)
    mainView.setResizeMode(QDeclarativeView.SizeRootObjectToView)	
    mainWin.setCentralWidget(mainView)    
    mainWin.show()
    app.exec_()