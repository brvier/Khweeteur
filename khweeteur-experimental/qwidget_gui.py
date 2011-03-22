#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with Python and Qt'''

__version__ = '0.5.0'

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtMaemo5 import *

import dbus
import dbus.service

import os
import sys

from qbadgebutton import QBadgeButton, QToolBadgeButton

import twitter

import glob
import pickle
import time

from list_view import *
from list_model import *

class KhweeteurDBusHandler(dbus.service.Object):
    def __init__(self,parent):
        dbus.service.Object.__init__(self, dbus.SessionBus(), '/net/khertan/Khweeteur')
        self.parent = parent
        
    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur')
    def require_update(self,optional=None):
        self.parent.setAttribute(Qt.WA_Maemo5ShowProgressIndicator , True)


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

        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle('Khweeteur')

        self.listen_dbus()

        self.view = KhweetsView()
        self.model = KhweetsModel()
        self.view.setModel(self.model)

        self.dbus_handler.require_update()
        
        self.toolbar = QToolBar('Toolbar')
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar)

        self.list_tb_action = []
        self.edit_tb_action = []
        
        self.tb_new = QAction(QIcon.fromTheme('khweeteur'
                ), 'New', self)
        self.tb_new.triggered.connect(self.show_edit)
        self.toolbar.addAction(self.tb_new)

        self.tb_text = QPlainTextEdit()
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.tb_text_replysource = ''
#        self.tb_text.enabledChange(True)
        self.tb_text.setFixedHeight(66)
        self.edit_tb_action.append(self.toolbar.addWidget(self.tb_text))

        self.tb_charCounter = QLabel('140')
        self.edit_tb_action.append(self.toolbar.addWidget(self.tb_charCounter))
        self.tb_text.textChanged.connect(self.countCharsAndResize)

        self.tb_send = QAction(QIcon.fromTheme('khweeteur'
                ), 'Tweet', self)
        self.tb_send.setVisible(False)
        self.toolbar.addAction(self.tb_send)
        
        self.tb_update = QAction(QIcon.fromTheme('general_refresh'
                ), 'Update', self)
        self.tb_update.triggered.connect(self.dbus_handler.require_update)

        self.toolbar.addAction(self.tb_update)
        self.toolbar.addSeparator()
        self.home_button = QToolBadgeButton(self)
	self.home_button.setText("Home")
        self.home_button.setCheckable(True)
        self.home_button.setChecked(True)
        self.home_button.clicked.connect(self.show_hometimeline)
        self.list_tb_action.append(self.toolbar.addWidget(self.home_button))

        self.mention_button = QToolBadgeButton(self)
	self.mention_button.setText("Mentions")
        self.mention_button.setCheckable(True)
        self.mention_button.clicked.connect(self.show_mentions)
        self.list_tb_action.append(self.toolbar.addWidget(self.mention_button))

        self.msg_button = QToolBadgeButton(self)
	self.msg_button.setText("DMs")
        self.msg_button.setCheckable(True)
        self.msg_button.clicked.connect(self.show_dms)
        self.list_tb_action.append(self.toolbar.addWidget(self.msg_button))
#        self.list_button = QToolBadgeButton(self)
#	self.list_button.setText("Lists")
#        self.list_button.setCounter(2)
#        self.list_button.setCheckable(True)
#        self.toolbar.addWidget(self.list_button)
#        self.search_button = QToolBadgeButton(self)
#	self.search_button.setText("Searchs")
#        self.search_button.setCounter(2)
#        self.search_button.setCheckable(True)
#        self.toolbar.addWidget(self.search_button)

        for item in self.edit_tb_action:
            item.setVisible(False)

        self.model.load('HomeTimeline')
        self.setCentralWidget(self.view)

    def listen_dbus(self):
        from dbus.mainloop.qt import DBusQtMainLoop
        self.dbus_loop = DBusQtMainLoop()
        dbus.set_default_main_loop(self.dbus_loop)
        self.bus = dbus.SessionBus()
        #Connect the new tweet signal
        self.bus.add_signal_receiver(self.new_tweets, path='/net/khertan/Khweeteur', dbus_interface='net.khertan.Khweeteur', signal_name='new_tweets')        
        self.bus.add_signal_receiver(self.stop_spinning, path='/net/khertan/Khweeteur', dbus_interface='net.khertan.Khweeteur', signal_name='refresh_ended')        
        self.dbus_handler = KhweeteurDBusHandler(self)

    def stop_spinning(self):
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator , False)
        
    def new_tweets(self,count,msg):
        print 'New Tweets dbus signal received'
        print count,msg
        if msg == 'HomeTimeline':
            self.home_button.setCounter(count)
            QApplication.processEvents()
        elif msg == 'Mentions':
            self.mention_button.setCounter(count)
            QApplication.processEvents()
        elif msg == 'DMs':
            self.msg_button.setCounter(count)
            QApplication.processEvents()

        if self.model.call == msg:
            self.model.load(msg)

    @pyqtSlot()
    def show_hometimeline(self):
        self.home_button.setCounter(0)
        self.home_button.setChecked(True)        
        self.msg_button.setChecked(False)
        self.mention_button.setChecked(False)
        self.model.load('HomeTimeline')
        
    @pyqtSlot()
    def show_edit(self):
#        print self.list_tb_action
        vis = self.tb_update.isVisible()
        self.tb_update.setVisible(not vis)
        self.tb_send.setVisible(vis)
        if vis:
            self.tb_new.setIcon(QIcon.fromTheme('general_back'))
#            self.tb_text.setFocus()
        else:
            self.tb_new.setIcon(QIcon.fromTheme('khweeteur'))
        for item in self.list_tb_action:
            item.setVisible(not vis)
        for item in self.edit_tb_action:
            item.setVisible(vis)
        if vis:
            self.tb_text.setFocus()
        
    @pyqtSlot()
    def show_mentions(self):
        self.mention_button.setCounter(0)
        self.mention_button.setChecked(True)
        self.msg_button.setChecked(False)
        self.home_button.setChecked(False)
        self.model.load('Mentions')

    @pyqtSlot()
    def show_dms(self):
        self.msg_button.setCounter(0)
        self.msg_button.setChecked(True)
        self.home_button.setChecked(False)
        self.mention_button.setChecked(False)
        self.model.load('DMs')
        
    @pyqtSlot()
    def countCharsAndResize(self):
        local_self = self.tb_text
        self.tb_charCounter.setText(unicode(140
                                    - len(local_self.toPlainText())))
        doc = local_self.document()
        cursor = local_self.cursorRect()
        s = doc.size()
        s.setHeight((s.height() + 1)
                    * (local_self.fontMetrics().lineSpacing() + 1)
                    - 21)
        fr = local_self.frameRect()
        cr = local_self.contentsRect()
        local_self.setFixedHeight(min(370, s.height() + fr.height()
                                  - cr.height() - 1))
if __name__ == '__main__':
    os.system('python %s start' % os.path.join(os.path.dirname(__file__),'daemon.py'))
    app = Khweeteur()     
    app.exec_()