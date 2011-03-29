#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with Python and Qt'''

__version__ = '0.5.0'

#import sip
#sip.setapi('QString', 2)
#sip.setapi('QVariant', 2)

from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtMaemo5 import *

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

import re

pyqtSignal = Signal
pyqtSlot = Slot

class KhweeteurDBusHandler(dbus.service.Object):
    def __init__(self,parent):
        dbus.service.Object.__init__(self, dbus.SessionBus(), '/net/khertan/Khweeteur')
        self.parent = parent
        
    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur')
    def require_update(self,optional=None):
        self.parent.setAttribute(Qt.WA_Maemo5ShowProgressIndicator , True)

#    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur',
#            signature='ss')
#    def post_retweet(self, tid='',t_base_url=''):
#        pass

    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur',
            signature='uusssssss')
    def post_tweet(self, \
            shorten_url=1,\
            serialize=1,\
            text='',\
            reply_id = '0', 
            reply_base_url = '',
            lattitude = '0',
            longitude = '0',
            retweet_id = '0',
            retweet_base_url = '',
            ):
        pass

class Khweeteur(QApplication):
    def __init__(self):
        QApplication.__init__(self,sys.argv)
        self.setOrganizationName("Khertan Software")
        self.setOrganizationDomain("khertan.net")
        self.setApplicationName("Khweeteur")
        
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
        self.view.clicked.connect(self.switch_tb_action)

        self.dbus_handler.require_update()
        
        self.toolbar = QToolBar('Toolbar')
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar)

        self.toolbar_mode = 0 #0 - Default , 1 - Edit, 2 - Action

        self.list_tb_action = []
        self.edit_tb_action = []
        self.action_tb_action = []

        #Switch to edit mode (default)
        self.tb_new = QAction(QIcon.fromTheme('khweeteur'
                ), 'New', self)
        self.tb_new.triggered.connect(self.switch_tb_edit)
        self.toolbar.addAction(self.tb_new)
        self.list_tb_action.append(self.tb_new)

        #Back button (Edit + Action)
        self.tb_back = QAction(QIcon.fromTheme('general_back'
                ), 'Back', self)
        self.tb_back.triggered.connect(self.switch_tb_default)
        self.toolbar.addAction(self.tb_back)
        self.edit_tb_action.append(self.tb_back)
        self.action_tb_action.append(self.tb_back)

        self.setupMenu()

        #Twitpic button
        self.tb_twitpic = QAction(QIcon.fromTheme('tasklaunch_images'
                ), 'Twitpic', self)
        self.tb_twitpic.triggered.connect(self.do_tb_twitpic)
        self.toolbar.addAction(self.tb_twitpic)
        self.edit_tb_action.append(self.tb_twitpic)
                
        #Text field (edit)
        self.tb_text = QPlainTextEdit()
        self.tb_text_reply_id = 0
        self.tb_text_reply_base_url = ''
#        self.tb_text_retweet_id = 0
#        self.tb_text_retweet_base_url = ''
        self.tb_text.setFixedHeight(66)
        self.edit_tb_action.append(self.toolbar.addWidget(self.tb_text))

        #Char count (Edit) 
        self.tb_charCounter = QLabel('140')
        self.edit_tb_action.append(self.toolbar.addWidget(self.tb_charCounter))
        self.tb_text.textChanged.connect(self.countCharsAndResize)

        #Send tweet (Edit)
        self.tb_send = QAction(QIcon.fromTheme('khweeteur'
                ), 'Tweet', self)
        self.tb_send.triggered.connect(self.do_tb_send)
        self.tb_send.setVisible(False)
        self.toolbar.addAction(self.tb_send)
        self.edit_tb_action.append(self.tb_send)
         
        #Refresh (Default)
        self.tb_update = QAction(QIcon.fromTheme('general_refresh'
                ), 'Update', self)
        self.tb_update.triggered.connect(self.dbus_handler.require_update)
        self.toolbar.addAction(self.tb_update)
        self.list_tb_action.append(self.tb_update)

        #Home (Default)
        self.home_button = QToolBadgeButton(self)
	self.home_button.setText("Home")
        self.home_button.setCheckable(True)
        self.home_button.setChecked(True)
        self.home_button.clicked.connect(self.show_hometimeline)
        self.list_tb_action.append(self.toolbar.addWidget(self.home_button))

        #Mentions (Default)
        self.mention_button = QToolBadgeButton(self)
	self.mention_button.setText("Mentions")
        self.mention_button.setCheckable(True)
        self.mention_button.clicked.connect(self.show_mentions)
        self.list_tb_action.append(self.toolbar.addWidget(self.mention_button))

        #DM (Default)
        self.msg_button = QToolBadgeButton(self)
	self.msg_button.setText("DMs")
        self.msg_button.setCheckable(True)
        self.msg_button.clicked.connect(self.show_dms)
        self.list_tb_action.append(self.toolbar.addWidget(self.msg_button))

        #Reply button (Action)
        self.tb_reply = QAction('Reply', self)
        self.toolbar.addAction(self.tb_reply)
        self.tb_reply.triggered.connect(self.do_tb_reply)
        self.action_tb_action.append(self.tb_reply)

        #Retweet (Action)
        self.tb_retweet = QAction('Retweet', self)
        self.toolbar.addAction(self.tb_retweet)
        self.tb_retweet.triggered.connect(self.do_tb_retweet)
        self.action_tb_action.append(self.tb_retweet)

        #Follow (Action)
        self.tb_follow = QAction('Follow', self)
        self.toolbar.addAction(self.tb_follow)
        self.action_tb_action.append(self.tb_follow)

        #UnFollow (Action)
        self.tb_unfollow = QAction('Unfollow', self)
        self.toolbar.addAction(self.tb_unfollow)
        self.action_tb_action.append(self.tb_unfollow)

        #Favorite (Action)
        self.tb_favorite = QAction('Favorite', self)
        self.toolbar.addAction(self.tb_favorite)
        self.action_tb_action.append(self.tb_favorite)

        #Open URLs (Action)
        self.tb_urls = QAction('Open URLs', self)
        self.toolbar.addAction(self.tb_urls)
        self.tb_urls.triggered.connect(self.do_tb_openurl)
        self.action_tb_action.append(self.tb_urls)

        #Delete (Action)
        self.tb_delete = QAction('Delete', self)
        self.toolbar.addAction(self.tb_delete)
        self.action_tb_action.append(self.tb_delete)

        self.switch_tb_default()
        
        self.model.load('HomeTimeline')
        self.setCentralWidget(self.view)

    def enterEvent(self,event):
        """
            Redefine the enter event to refresh recent file list
        """        
        self.model.refreshTimestamp()

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
    def switch_tb_default(self):
        print 'Switch tb default'
        self.tb_text.setPlainText('')
        self.tb_text_reply_id = 0
        self.tb_text_reply_base_url = ''
        self.toolbar_mode = 0
        self.switch_tb()

    @pyqtSlot()
    def switch_tb_edit(self):
        print 'Switch tb edit'
        self.toolbar_mode = 1
        self.switch_tb()

    @pyqtSlot()
    def switch_tb_action(self):
        if self.toolbar_mode != 2:
            self.toolbar_mode = 2
            self.switch_tb()
        for index in self.view.selectedIndexes():
            isme = self.model.data(index, role=ISMEROLE)
        if isme:
            self.tb_follow.setVisible(False)
            self.tb_unfollow.setVisible(False)
            self.tb_delete.setVisible(True)
        else:
            self.tb_delete.setVisible(False)
            self.tb_follow.setVisible(True)
            self.tb_unfollow.setVisible(True)
 
    def switch_tb(self):
        mode = self.toolbar_mode
        print mode,type(mode)
        for item in self.list_tb_action:
            item.setVisible(mode == 0)
        for item in self.edit_tb_action:
            item.setVisible(mode == 1)
            if mode == 1:
                self.tb_text.setFocus()
        for item in self.action_tb_action:
            item.setVisible(mode == 2)
        if mode in (1, 2):
            self.tb_back.setVisible(True)

    @pyqtSlot()
    def do_tb_twitpic(self):
        pass
        
    @pyqtSlot()
    def do_tb_openurl(self):
        for index in self.view.selectedIndexes():
            status = self.model.data(index)
            try:
                urls = re.findall("(?P<url>https?://[^\s]+)", status)
                for url in urls:                  
                    QDesktopServices.openUrl(QUrl(url))
            except:
                raise
#                    QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur/bugs'
        
    @pyqtSlot()
    def do_tb_send(self):
        self.dbus_handler.post_tweet( \
            1,#shorten_url=\
            1,#serialize=\
            self.tb_text.toPlainText(),#text=\
            str(self.tb_text_reply_id), #reply_id =  
            self.tb_text_reply_base_url,  #reply_base_url = 
            '', #lattitude =
            '', #longitude = 
            '0', #retweet_id = 
            '', #retweet_base_url = 
            )
        self.switch_tb_default()
        self.dbus_handler.require_update()

    @pyqtSlot()
    def do_tb_reply(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_screenname = self.model.data(index, role=SCREENNAMEROLE)
        if tweet_id:
            self.tb_text.setPlainText('@'+tweet_screenname+self.tb_text.toPlainText())
            self.tb_text_reply_id = tweet_id
            self.tb_text_reply_base_url = tweet_source
            self.switch_tb_edit()

    @pyqtSlot()
    def do_tb_retweet(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
        if tweet_id:
            self.dbus_handler.post_tweet( \
                0,#shorten_url=\
                0,#serialize=\
                '',#text=\
                '0', #reply_id =  
                '',  #reply_base_url = 
                '', #lattitude =
                '', #longitude = 
                str(tweet_id), #retweet_id = 
                tweet_source, #retweet_base_url = 
                )
            self.switch_tb_default()
            self.dbus_handler.require_update()

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

    def setupMenu(self):
        """
            Initialization of the maemo menu
        """
        
        fileMenu =  QMenu(self.tr("&Menu"), self)
        self.menuBar().addMenu(fileMenu)

        fileMenu.addAction(self.tr("&Preferences..."), self.showPrefs)
        fileMenu.addAction(self.tr("&About"), self.showAbout)

    def showPrefs(self):
        khtsettings = KhweeteurPref(parent=self)
        khtsettings.save.connect(self.refreshPrefs)
        khtsettings.show()

    @pyqtSlot()
    def refreshPrefs(self):
        self.view.refreshCustomDelegate()
                
    def showAbout(self):
        pass
        
if __name__ == '__main__':
    os.system('python %s start' % os.path.join(os.path.dirname(__file__),'daemon.py'))
    app = Khweeteur()     
    app.exec_()
