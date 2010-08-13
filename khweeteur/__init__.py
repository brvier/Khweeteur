#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
# 
# Copyright (c) 2010 Benoî HERVIER
# Licenced under GPLv3

"""A simple Twitter client made with pyqt4"""

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtMaemo5 import *

import khweeteur
import twitter
import sys
import os.path
from urllib import urlretrieve
import pickle
import re
import dbus
import dbus.mainloop.qt

__version__ = '0.0.1'
AVATAR_CACHE_FOLDER = os.path.join(os.path.expanduser("~"),'.khweeteur','cache')
CACHE_PATH = os.path.join(os.path.expanduser("~"),'.khweeteur','tweets.cache')

class KhweeteurNotification(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.m_bus = dbus.SystemBus()
        self.m_notify = self.m_bus.get_object('org.freedesktop.Notifications',
                                              '/org/freedesktop/Notifications')

    def send(self,title,message,category='message',icon='khweeteur',count=1):
        self.m_notify.Notify(title,
                             0,
                             icon,
                             title,
                             message,
                             [],
                             {'category':category,
                             'count':count},
                             -1,
                             dbus_interface='org.freedesktop.Notifications'
                             )
        
class KhweeteurWorker(QThread):

    def __init__(self, parent = None):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        
    def run(self):
        self.refresh_timeline()
        
    def downloadProfileImage(self,status):
        if type(status)!=twitter.DirectMessage:
            cache = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(status.user.profile_image_url))
            if not(os.path.exists(cache)):
                try:
                    urlretrieve(status.user.profile_image_url, cache)
                except StandardError,e:
                    print e,status.user.profile_image_url,status.user.screen_name
    
    def refresh_timeline(self):
        print 'Try to refresh'
        try:
            mlist = []
            avatars_url={}
            api = twitter.Api(username=self.settings.value("login").toString(), password=self.settings.value("password").toString())
            for status in api.GetFriendsTimeline(count=100):
                mlist.append((status.created_at_in_seconds,status))
            for status in api.GetReplies():
                mlist.append((status.created_at_in_seconds,status))
            for status in api.GetDirectMessages():
                mlist.append((status.created_at_in_seconds,status))
            mlist.sort()
    
            #DOwnload avatar & add tweet to the model
            for _,status in mlist:
                self.downloadProfileImage(status)
                #We are now in a thread
                self.emit(SIGNAL("newStatus(PyQt_PyObject)"),(_,status))
                        
        except StandardError,e:
            print e
#            KhweeteurNotification().send('Error','Errors occurs during the update :' + str(e))
            
        print 'Refresh ended'

class KhweetsModel(QAbstractListModel):
    
    def __init__(self, mlist=[]):
        QAbstractListModel.__init__(self)

        # Cache the passed data list as a class member.
        self._items = mlist
        self._new_counter = 0
  
    def rowCount(self, parent = QModelIndex()):
        return len(self._items)

    def addStatus(self,variant):
        status_with_secondstamp = variant
        if status_with_secondstamp not in self._items:
            self._items.insert(0,status_with_secondstamp)
            self._new_counter = self._new_counter + 1
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def getNewAndReset(self):
        counter = self._new_counter
        self._new_counter = 0
        return counter
                
    def setData(self,mlist):
        self._items = mlist

        QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
    
    def serialize(self):
        output = open(CACHE_PATH, 'wb')
        pickle.dump(self._items, output)
        output.close()        
        
    def unSerialize(self):
        try:
            pkl_file = open(CACHE_PATH, 'rb')
            self._items = pickle.load(pkl_file)
        except StandardError,e:
            print e
        finally:
            pkl_file.close()        
            self._items.sort()
            self._items.reverse()
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def data(self, index, role = Qt.DisplayRole):        
        if role == Qt.DisplayRole:
            return QVariant(self._items[index.row()][1].text)
        elif role == Qt.DecorationRole:
                try:
                    # return an icon, if the decoration role is used
                    icon = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(self._items[index.row()][1].user.profile_image_url))
                    return QVariant(QIcon(icon))
                except:
                    return QVariant()
        elif role == Qt.BackgroundRole:
            if index.row() % 2 == 0:
                return QVariant(QColor(Qt.gray))
            else:
                return QVariant(QColor(Qt.lightGray))
        else:
           return QVariant()

class KhweetsView(QListView):
    def __init__(self,parent=None):
        QListView.__init__(self,parent)
        self.setIconSize(QSize(128, 128))
        self.setWordWrap(True)
        self.setResizeMode(QListView.Adjust)
        self.setViewMode(QListView.ListMode)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
#        self.setAlternatingRowColors(True)
#        self.setUniformItemSizes(True)
#        self.setWrapping(True)
#        self.setFlow(QListView.TopToBottom)
#        self.setGridSize(QSize(-1,200))
        
        
class KhweeteurAbout(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)
        self.parent = parent

        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur About")

        aboutScrollArea = QScrollArea(self)
        aboutScrollArea.setWidgetResizable(True)
        awidget = QWidget(aboutScrollArea)
        awidget.setMinimumSize(480,600)
        awidget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        aboutScrollArea.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroller = aboutScrollArea.property("kineticScroller").toPyObject()
        scroller.setEnabled(True)

        aboutLayout = QVBoxLayout(awidget)
        
        aboutIcon = QLabel()
        aboutIcon.setPixmap(QPixmap(os.path.join(khweeteur.__path__[0],'icons','khweeteur.jpg')).scaledToHeight(128))
        aboutIcon.setAlignment( Qt.AlignCenter or Qt.AlignHCenter )
        aboutIcon.resize(140,140)
        aboutLayout.addWidget(aboutIcon)
        
        aboutLabel = QLabel('''<center><b>Khweeteur</b> %s
                                   <br><br>A Simple twitter client with follower status, reply,
                                   <br>and direct message in a unified view
                                   <br><br>Licenced under GPLv3
                                   <br>By Beno&icirc;t HERVIER (Khertan) 
                                   <br><br><br><b>Site Web : </b>http://khertan.net/khweeteur
                                   <br><br><b>Thanks to :</b>
                                   <br>ddoodie on #pyqt      
                                   <br>xnt14 on #maemo                         
                                   </center>''' % __version__)
        aboutLayout.addWidget(aboutLabel)

        awidget.setLayout(aboutLayout)
        aboutScrollArea.setWidget(awidget)

        self.setCentralWidget(aboutScrollArea)
        self.show()
            
class KhweeteurPref(QMainWindow):
    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)
        self.parent = parent

        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur Prefs")

        self.settings = QSettings()
        
        self.setupGUI()
        self.loadPrefs()
        
    def loadPrefs(self):
        self.login_value.setText(self.settings.value("login").toString())
        self.password_value.setText(self.settings.value("password").toString())
        self.refresh_value.setValue(self.settings.value("refreshInterval").toInt()[0])

    def savePrefs(self):
        self.settings.setValue('login',self.login_value.text())
        self.settings.setValue('password',self.password_value.text())
        self.settings.setValue('refreshInterval',self.refresh_value.value())
        self.emit(SIGNAL("save()"))
        
    def closeEvent(self,widget,*args):
        self.savePrefs()
                     
    def setupGUI(self):
        self.aWidget = QWidget()
        self._main_layout = QGridLayout(self.aWidget)

        self._main_layout.addWidget(QLabel('Login :'),0,0)
        self.login_value = QLineEdit()
        self._main_layout.addWidget(self.login_value,0,1)
                
        self._main_layout.addWidget(QLabel('Password :'),1,0)
        self.password_value = QLineEdit()
        self.password_value.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        self._main_layout.addWidget(self.password_value,1,1)

        self._main_layout.addWidget(QLabel('Refresh Interval (Minutes) :'),2,0)
        self.refresh_value = QSpinBox()
        self._main_layout.addWidget(self.refresh_value,2,1)

        self.aWidget.setLayout(self._main_layout)
        self.setCentralWidget(self.aWidget)
                

class KhweeteurWin(QMainWindow):

    newStatus = pyqtSignal((int, twitter.Status), name='newStatus')
    
    def __init__(self, parent=None):
        QMainWindow.__init__(self,None)
        self.parent = parent

        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur")
        self.setupMenu()
        self.setupMain()

        self.settings = QSettings()
        self.refresh()
        self.timer = QTimer()
        self.connect(self.timer, SIGNAL("timeout()"), self.timer_refresh)
        self.timer.start(self.settings.value("refreshInterval").toInt()[0]*60*1000)
        
    def setupMain(self):
        
        self.tweetsView = KhweetsView(self)
        self.connect(self.tweetsView,SIGNAL('doubleClicked(const QModelIndex&)'),self.reply)
        self.tweetsModel = KhweetsModel([])
        self.tweetsView.setModel(self.tweetsModel)        
        self.setCentralWidget(self.tweetsView)
        self.tweetsModel.unSerialize()
        
        self.toolbar = self.addToolBar('Toolbar')

#        self.tb_refresh = QAction(QIcon.fromTheme("general_backup"),'Refresh', self)
#        self.connect(self.tb_refresh, SIGNAL('triggered()'), self.refresh_timeline)
#        self.toolbar.addAction(self.tb_refresh)

        self.tb_open = QAction(QIcon.fromTheme("general_web"),'Open', self)
        self.connect(self.tb_open, SIGNAL('triggered()'), self.open_url)
        self.toolbar.addAction(self.tb_open)

        self.tb_text = QLineEdit()        
        self.tb_text.enabledChange(True)        
        self.toolbar.addWidget(self.tb_text)

        self.tb_charCounter = QLabel('140')
        self.toolbar.addWidget(self.tb_charCounter)
        self.connect(self.tb_text, SIGNAL('textChanged(const QString&)'), self.countChar)

        self.tb_tweet = QAction(QIcon.fromTheme("general_add"),'Tweet', self)
        self.connect(self.tb_tweet, SIGNAL('triggered()'), self.tweet)
        self.toolbar.addAction(self.tb_tweet)

    def open_url(self):
        for index in self.tweetsView.selectedIndexes():
            status = self.tweetsModel._items[index.row()][1].text
            try:
                url = re.search("(?P<url>https?://[^\s]+)", status).group("url")
                QDesktopServices.openUrl(QUrl(url))
            except StandardError,e:
                print e
                
        
    def countChar(self,text):
        self.tb_charCounter.setText(str(140-text.count()))
        
    def reply(self,index):        
        self.tb_text.setText('@'+self.tweetsModel._items[index.row()][1].user.screen_name)
               
    def tweet(self):
        print 'try to tweet'
        try:
            api = twitter.Api(username=self.settings.value("login").toString(), password=self.settings.value("password").toString())
            api.SetSource('Khweeteur')
            status = api.PostUpdate(self.tb_text.text())
            self.tb_text.setText('')
        except StandardError,e:            
            print e
#            KhweeteurNotification().send('Error','Errors occurs during the publication of your tweet :' + str(e))

    
    def refreshEnded(self):        
        self.tweetsModel.serialize()
        counter=self.tweetsModel.getNewAndReset()
        if counter>0:
            KhweeteurNotification().send('Khweeteur',str(counter)+' new tweet(s)',count=counter)
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def refresh(self):
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
        self.worker = KhweeteurWorker()
        self.connect(self.worker, SIGNAL("newStatus(PyQt_PyObject)"), self.tweetsModel.addStatus)
        self.connect(self.worker, SIGNAL("finished()"), self.refreshEnded)
        self.worker.start()
        
    def timer_refresh(self):
        print 'Timer refresh'
        self.refresh_timeline()
        
    def refresh_timeline(self):
        if self.worker == None:
            self.refresh()
        elif self.worker.isFinished() == True:
            print 'isFinished()', True, self.worker.isFinished()
            self.refresh()      
        else:
            print 'isFinished()', self.worker.isFinished()
                                                                            
    def restartTimer(self):
        self.timer.start(self.settings.value("refreshInterval").toInt()[0]*60*1000)
        print 'restart timer'
        
    def setupMenu(self):
        fileMenu = QMenu(self.tr("&Menu"), self)
        self.menuBar().addMenu(fileMenu)

        fileMenu.addAction(self.tr("&Preferences"), self.do_show_pref,
                QKeySequence(self.tr("Ctrl+P", "Preferences")))
        fileMenu.addAction(self.tr("&Update"), self.refresh_timeline,
                QKeySequence(self.tr("Ctrl+R", "Update")))
        fileMenu.addAction(self.tr("&About"), self.do_about)
        
    def do_show_pref(self):
        self.pref_win = KhweeteurPref(self)
        self.connect(self.pref_win, SIGNAL("save()"), self.restartTimer)
        self.pref_win.show()        
        
    def do_about(self):
        self.aboutWin = KhweeteurAbout(self)
               
class Khweeteur(QApplication):
    def __init__(self):
        QApplication.__init__(self,sys.argv)
        self.setOrganizationName("Khertan Software")
        self.setOrganizationDomain("khertan.net")
        self.setApplicationName("Khweeteur")
        self.version = __version__
        self.run()

    def run(self):
        self.win = KhweeteurWin()
        self.win.show()        
        sys.exit(self.exec_())

if __name__ == '__main__':
    Khweeteur()
        