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
from PySide.QtMaemo5 import *

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
        self.win.showFullScreen()
        
class KhweeteurWin(QMainWindow):
    def __init__(self,parent=None):
        QMainWindow.__init__(self,parent)
        self.view = QDeclarativeView()

        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle(self.tr('Khweeteur'))        

        self.listen()

        controller = Controller()
        controller.switch_fullscreen.connect(self.switch_fullscreen)
        statusesList = TweetsListModel()
        controller.switch_list.connect(statusesList.load_list)
        statusesList.load_list('HomeTimeline')
        
        self.context = self.view.rootContext()
        
        self.context.setContextProperty('controller', controller)
        self.context.setContextProperty('tweetsListModel', statusesList)

        self.buttonList = ToolbarListModel()
        self.context.setContextProperty('toolbarListModel', self.buttonList)
        
        self.view.setSource('qml/tweetslist.qml')

        if USE_GL:
            glw = QtOpenGL.QGLWidget()
            self.view.setViewport(glw)
        self.view.setResizeMode(QDeclarativeView.SizeRootObjectToView)	
        self.setCentralWidget(self.view)
        
    def listen(self):
        import dbus
        import dbus.service
        from dbus.mainloop.qt import DBusQtMainLoop
        self.dbus_loop = DBusQtMainLoop()
        dbus.set_default_main_loop(self.dbus_loop)
        self.bus = dbus.SessionBus() #should connect to system bus instead of session because the former is where the incoming signals come from
        self.bus.add_signal_receiver(self.new_tweets, path='/net/khertan/Khweeteur/NewTweets', dbus_interface='net.khertan.Khweeteur', signal_name=None)
         
    def new_tweets(self,count,msg):
        print 'New Tweets dbus signal received'
        print count,msg
        self.buttonList.setCount(msg,count)
        #TODO
        #Do something with the signal
        
         
    @Slot()
    def switch_fullscreen(self):
        if self.isFullScreen():                   
            self.showMaximized()
        else:                  
            self.showFullScreen()
                    
if __name__ == '__main__':

    from subprocess import Popen
    Popen(['/usr/bin/python',os.path.join(os.path.dirname(__file__),'daemon.py'),'start'])
    app = Khweeteur()    
    app.exec_()

    