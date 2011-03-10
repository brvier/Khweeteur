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
try:
    from PySide import QtOpenGL
    USE_GL = True
except:
    USE_GL = False
    print 'Not using Open_GL'
    
import os
import sys

import twitter
from tweetslist import *

import glob
import pickle
import time

class Khweeteur(QApplication):
    def __init__(self):
        QApplication.__init__(self,sys.argv)
        self.run()

    def run(self):
        self.win = KhweeteurWin()
        self.win.show()
        
class KhweeteurWin(QMainWindow):
    def __init__(self,parent=None):
        QMainWindow.__init__(self,parent)
        self.view = QDeclarativeView()

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
        statusesWrapped.sort()
        
        controller = Controller()
        controller.switch_fullscreen.connect(self.switch_fullscreen)
        statusesList = TweetsListModel(statusesWrapped)
        controller.switch_list.connect(statusesList.load_list)        
         
        self.context = self.view.rootContext()
         
        self.context.setContextProperty('controller', controller)
        self.context.setContextProperty('tweetsListModel', statusesList)
         
        self.view.setSource('qml/tweetslist.qml')
    
        if USE_GL:
            glw = QtOpenGL.QGLWidget()
            self.view.setViewport(glw)
        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)	
        self.setCentralWidget(self.view)

    @Slot()
    def switch_fullscreen(self):
        if self.isFullScreen():                   
            self.showMaximized()
        else:                  
            self.showFullScreen()
                    
if __name__ == '__main__':

    app = Khweeteur()     
    app.exec_()