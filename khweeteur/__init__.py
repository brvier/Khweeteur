#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
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
import datetime
import time
from nwmanager import NetworkManager
import dbus.service
import dbus.mainloop.qt

__version__ = '0.0.17'
AVATAR_CACHE_FOLDER = os.path.join(os.path.expanduser("~"),'.khweeteur','cache')
CACHE_PATH = os.path.join(os.path.expanduser("~"), '.khweeteur')
KHWEETEUR_TWITTER_CONSUMER_KEY = 'uhgjkoA2lggG4Rh0ggUeQ'
KHWEETEUR_TWITTER_CONSUMER_SECRET = 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU'
KHWEETEUR_IDENTICA_CONSUMER_KEY = 'c7e86efd4cb951871200440ad1774413'
KHWEETEUR_IDENTICA_CONSUMER_SECRET = '236fa46bf3f65fabdb1fd34d63c26d28'

class KhweeteurDBus(dbus.service.Object):
    @dbus.service.method("net.khertan.khweeteur",
                         in_signature='', out_signature='')
    def show(self):
        self.win.activateWindow()
        self.win.tweetsModel.getNewAndReset()

    @dbus.service.method("net.khertan.khweeteur",
                         in_signature='s', out_signature='')
    def show_search(self,keyword):
        for win in self.search_win:
            if win.search_keyword == keyword:
                win.activateWindow()
                win.tweetsModel.getNewAndReset()
                
    def attach_win(self,win):
        self.win = win
        
class KhweeteurNotification(QObject):
    def __init__(self):
        QObject.__init__(self)
        self.m_bus = dbus.SystemBus()
        self.m_notify = self.m_bus.get_object('org.freedesktop.Notifications',
                                              '/org/freedesktop/Notifications')
        self.iface = dbus.Interface(self.m_notify,'org.freedesktop.Notifications')
        self.m_id = 0
        
    def warn(self,message):
        self.iface.SystemNoteDialog(message,0,'Nothing')
        
    def info(self,message):
        self.iface.SystemNoteInfoprint('Khweeteur : '+message)
        
    def notify(self,title,message,category='im.received',icon='khweeteur_32',count=1):
        self.m_id = self.iface.Notify('Khweeteur',
                          self.m_id,
                          icon,
                          title,
                          message,
                          ['default','test'],
                          {'category':category,
                          'desktop-entry':'khweeteur',
                          'dbus-callback-default':'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show',
                          'count':count},
                          -1
                          )
    def notify_search(self,keyword,title,message,category='im.received',icon='khweeteur_32',count=1):
        self.m_id = self.iface.Notify('Khweeteur',
                          self.m_id,
                          icon,
                          title,
                          message,
                          ['default','test'],
                          {'category':category,
                          'desktop-entry':'khweeteur',
                          'dbus-callback-default':'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show_search(%s)' % (keyword,),
                          'count':count},
                          -1
                          )
                                                    
#        self.m_notify.Notify(title,
#                             0,
#                             icon,
#                             title,
#                             message,
#                             [],
#                             {'category':category,
#                             'count':count},
#                             -1,
#                             dbus_interface='org.freedesktop.Notifications'
#                             )


class KhweeteurWorker(QThread):

    def __init__(self, parent = None, search_keyword=None):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        self.search_keyword = search_keyword
        
    def run(self):
        self.testCacheFolders()
        if self.search_keyword==None:
            self.refresh()
        else:
            self.refresh_search()

    def testCacheFolders(self):
        if not os.path.isdir(CACHE_PATH):
            os.mkdir(CACHE_PATH)
        if not os.path.isdir(AVATAR_CACHE_FOLDER):
            os.mkdir(AVATAR_CACHE_FOLDER)
        
    def downloadProfileImage(self,status):
        if type(status)!=twitter.DirectMessage:
            cache = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(status.user.profile_image_url.replace('/','_')))
            if not(os.path.exists(cache)):
                try:
                    urlretrieve(status.user.profile_image_url, cache)
#                    QPixmap(cache).scaled(70,70,Qt.KeepAspectRatio).save(cache)
                except StandardError,e:
                    print e
        
    def refresh_search(self):
        print 'Try to refresh search : ',unicode(self.search_keyword).encode('UTF-8')
        downloadProfileImage = self.downloadProfileImage
                        
        current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())
        mlist = []
        try:
            avatars_url={}
            if (self.settings.value("twitter_access_token_key").toString()!=''): 
                api = twitter.Api(input_encoding='utf-8',username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, access_token_key=str(self.settings.value("twitter_access_token_key").toString()),access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                for status in api.GetSearch(unicode(self.search_keyword).encode('UTF-8')):
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
                        mlist.append((status.created_at_in_seconds,status))
        except twitter.TwitterError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)

        try:
            if (self.settings.value("twitter_access_token_key").toString()!=''): 
                api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, access_token_key=str(self.settings.value("identica_access_token_key").toString()),access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                for status in api.GetSearch(unicode(self.search_keyword).encode('UTF-8'),per_page=50):
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
                        mlist.append((status.created_at_in_seconds,status))
        except twitter.TwitterError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)

        if len(mlist)>0:
            mlist.sort()
            self.emit(SIGNAL("newStatuses(PyQt_PyObject)"),mlist)

        
    def refresh(self):
        print 'Try to refresh'
        downloadProfileImage = self.downloadProfileImage
        current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())
        mlist = []

        try:
            avatars_url={}
            if (self.settings.value("twitter_access_token_key").toString()!=''): 
                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, access_token_key=str(self.settings.value("twitter_access_token_key").toString()),access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                for status in api.GetFriendsTimeline(count=100):
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
                        mlist.append((status.created_at_in_seconds,status))
                for status in api.GetReplies():
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
                        mlist.append((status.created_at_in_seconds,status))
                for status in api.GetDirectMessages():
                    if status.created_at_in_seconds > current_dt:
                        mlist.append((status.created_at_in_seconds,status))
                for status in api.GetMentions():
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
                        mlist.append((status.created_at_in_seconds,status))                        
        except twitter.TwitterError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except StandardError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)

        try:
            if (self.settings.value("identica_access_token_key").toString()!=''): 
                api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, access_token_key=str(self.settings.value("identica_access_token_key").toString()),access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                for status in api.GetFriendsTimeline(count=100):
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
#                        status.qicon = QVariant(QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(status.user.profile_image_url))))
                        mlist.append((status.created_at_in_seconds,status))
                for status in api.GetReplies():
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
#                        status.qicon = QVariant(QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(status.user.profile_image_url))))
                        mlist.append((status.created_at_in_seconds,status))
                for status in api.GetDirectMessages():
                    if status.created_at_in_seconds > current_dt:
                        mlist.append((status.created_at_in_seconds,status))
                for status in api.GetMentions():
                    if status.created_at_in_seconds > current_dt:
                        downloadProfileImage(status)
#                        status.qicon = QVariant(QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(status.user.profile_image_url))))
                        mlist.append((status.created_at_in_seconds,status))                        
        except twitter.TwitterError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except StandardError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)

        if len(mlist)>0:
            mlist.sort()
            self.emit(SIGNAL("newStatuses(PyQt_PyObject)"),mlist)
            
class KhweetsModel(QAbstractListModel):
    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    def __init__(self, mlist=[]):
        QAbstractListModel.__init__(self)

        # Cache the passed data list as a class member.
        self._items = mlist
        self._avatars = {}
        self._new_counter = 0
        self.now = time.time()

        self.display_screenname = False
        self.display_timestamp = False
        self.display_avatar = True

    def GetRelativeCreatedAt(self,timestamp):
        '''Get a human redable string representing the posting time

        Returns:
          A human readable string representing the posting time
        '''
        fudge = 1.25
        delta  = long(self.now) - long(timestamp)
    
        if delta < (1 * fudge):
            return 'about a second ago'
        elif delta < (60 * (1/fudge)):
            return 'about %d seconds ago' % (delta)
        elif delta < (60 * fudge):
            return 'about a minute ago'
        elif delta < (60 * 60 * (1/fudge)):
            return 'about %d minutes ago' % (delta / 60)
        elif delta < (60 * 60 * fudge) or delta / (60 * 60) == 1:
            return 'about an hour ago'
        elif delta < (60 * 60 * 24 * (1/fudge)):
            return 'about %d hours ago' % (delta / (60 * 60))
        elif delta < (60 * 60 * 24 * fudge) or delta / (60 * 60 * 24) == 1:
            return 'about a day ago'
        else:
            return 'about %d days ago' % (delta / (60 * 60 * 24))
          
    def rowCount(self, parent = QModelIndex()):
        return len(self._items)

    def refreshTimestamp(self):
        print 'Refreshing timestamp'
        for index,item in enumerate(self._items):
            try:
                self._items[index] = (item[0],
                                      item[1],
                                      item[2],
                                      item[3],
                                      item[4],
                                      self.GetRelativeCreatedAt(item[0]))
            except StandardError,e:
                print e,':',item            

        QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
        
    def addStatuses(self,listVariant):
        for _,variant in listVariant:
            try:
                if len([True for item in self._items if item[1]==variant.id])==0:
                    if type(variant) != twitter.DirectMessage:
                        self._items.insert(0,
                            (variant.created_at_in_seconds,
                             variant.id,
                             variant.user.screen_name,
                             variant.text,
                             variant.user.profile_image_url,
                             self.GetRelativeCreatedAt(variant.created_at_in_seconds),))
                    if variant.user.screen_name!=None:
                        self._avatars[variant.user.profile_image_url] = (QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(variant.user.profile_image_url.replace('/','_')))))

                    #                             QVariant(QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(variant.user.profile_image_url))))))
                    else:
                        self._items.insert(0,
                             (variant.created_at_in_seconds,
                              variant.id,
                              variant.sender_screen_name,
                              variant.text,
                              None,
                              self.GetRelativeCreatedAt(variant.created_at_in_seconds),))
                              
                    self._new_counter = self._new_counter + 1
                    self.now = time.time()
            except StandardError, e:
                print "We shouldn't got this error here :",e
        QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

            
    def addStatus(self,variant):
        try:
            if len([True for item in self._items if item[1]==variant.id])==0:
                if type(variant) != twitter.DirectMessage:
                    self._items.insert(0,
                        (variant.created_at_in_seconds,
                         variant.id,
                         variant.user.screen_name,
                         variant.text,
                         variant.user.profile_image_url,
                         self.GetRelativeCreatedAt(variant.created_at_in_seconds),))
                    if variant.user.screen_name!=None:
                        self._avatars[variant.user.profile_image_url] = (QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(variant.user.profile_image_url.replace('/','_')))))
                                                                    
                else:
                    self._items.insert(0,
                         (variant.created_at_in_seconds,
                          variant.id,
                          variant.sender_screen_name,
                          variant.text,
                          None,
                          self.GetRelativeCreatedAt(variant.created_at_in_seconds),))
                self._new_counter = self._new_counter + 1
                self.now = time.time()
                QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
        except StandardError, e:
            print "We shouldn't got this error here :",e
            
    def getNewAndReset(self):
        counter = self._new_counter
        self._new_counter = 0
        return counter

    def getNew(self):
        return self._new_counter
        
    def setData(self,mlist):
        try:
            if len(mlist)>0:
                if type(mlist[0])==tuple:
                    if len(mlist[0])==6:
                        self._items = mlist
                        self._new_counter = 0
                        QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
                    else:
                        print 'Wrong cache format'
                        KhweeteurNotification().info('Old cache format. Reinit cache.')            
        except:
            KhweeteurNotification().info('Wrong cache format. Reinit cache.')
            print 'Wrong cache format'

    def serialize(self,keyword):
        try:
            if keyword==None:
                filename = os.path.join(CACHE_PATH,'tweets.cache')
            else:
                filename = os.path.normcase(unicode(os.path.join(unicode(CACHE_PATH),unicode(keyword.replace('/','_'))+u'.cache'))).encode('UTF-8')               
            output = open(filename, 'wb')
            pickle.dump(self._items, output)
            output.close()
        except StandardError,e:
            KhweeteurNotification().info('An error occurs while saving cache : '+str(e))
            
    def unSerialize(self,keyword):
        try:
            if keyword==None:
                filename = os.path.join(CACHE_PATH,'tweets.cache')
            else:
                filename = os.path.normcase(unicode(os.path.join(unicode(CACHE_PATH),unicode(keyword.replace('/','_'))+u'.cache'))).encode('UTF-8')          
            pkl_file = open(filename, 'rb')
            items = pickle.load(pkl_file)
            self.setData(items)
            pkl_file.close()
        except StandardError,e:
            print 'unSerialize : ',e
            # import traceback
            # print traceback.print_exc()
            # print traceback.print_stack()
        finally:
            #14 Day limitations
            current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())
            for index, item in enumerate(self._items):
                if item[0] < current_dt:
                    self._items = self._items[:index]
                    break
            for item in self._items:
                #self._avatars[item[4]] = QVariant(QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(item[4]))))
                if item[4]!=None:
                    self._avatars[item[4]] = (QIcon(os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(item[4].replace('/','_')))))
 
            self._items.sort()
            self._items.reverse()
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            status = self._items[index.row()][3]
            if self.display_timestamp:
                status = status +'\n'+ self._items[index.row()][5]     
            if self.display_screenname:
                status = self._items[index.row()][2]+ ' : ' + status            
            return QVariant(status)
        elif role == Qt.DecorationRole:            
            if self.display_avatar:
                try:
                    return self._avatars[self._items[index.row()][4]]
                except:
                    return QVariant()
            else:
                return QVariant()
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
        awidget.setMinimumSize(480,700)
        awidget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        aboutScrollArea.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroller = aboutScrollArea.property("kineticScroller").toPyObject()
        scroller.setEnabled(True)

        aboutLayout = QVBoxLayout(awidget)

        aboutIcon = QLabel()
        aboutIcon.setPixmap(QPixmap(os.path.join(khweeteur.__path__[0],'icons','khweeteur.png')).scaledToHeight(128))
        aboutIcon.setAlignment( Qt.AlignCenter or Qt.AlignHCenter )
        aboutIcon.resize(128,128)
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
                                   <br>trebormints on twitter
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
        self.refresh_value.setValue(self.settings.value("refreshInterval").toInt()[0])
        self.displayUser_value.setCheckState(self.settings.value("displayUser").toInt()[0])
        self.displayAvatar_value.setCheckState(self.settings.value("displayAvatar").toInt()[0])
        self.displayTimestamp_value.setCheckState(self.settings.value("displayTimestamp").toInt()[0])
        self.useNotification_value.setCheckState(self.settings.value("useNotification").toInt()[0])
        self.useSerialization_value.setCheckState(self.settings.value("useSerialization").toInt()[0])

    def savePrefs(self):
        self.settings.setValue('refreshInterval',self.refresh_value.value())
        self.settings.setValue('displayUser',self.displayUser_value.checkState())
        self.settings.setValue('useNotification',self.useNotification_value.checkState())
        self.settings.setValue('useSerialization',self.useSerialization_value.checkState())
        self.settings.setValue('displayAvatar',self.displayAvatar_value.checkState())
        self.settings.setValue('displayTimestamp',self.displayTimestamp_value.checkState())
        self.emit(SIGNAL("save()"))

    def closeEvent(self,widget,*args):
        self.savePrefs()

    def request_twitter_access_or_clear(self):
        if self.settings.value('twitter_access_token').toBool():
            self.settings.setValue('twitter_access_token_key',QString())
            self.settings.setValue('twitter_access_token_secret',QString())
            self.settings.setValue('twitter_access_token',False)
            self.twitter_value.setText('Auth on Twitter')
        else:
            import os
            import sys
            try:
                from urlparse import parse_qsl
            except:
                from cgi import parse_qsl
            import oauth2 as oauth
            
            REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
            ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
            AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'

            signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
            oauth_consumer             = oauth.Consumer(key=KHWEETEUR_TWITTER_CONSUMER_KEY, secret=KHWEETEUR_TWITTER_CONSUMER_SECRET)
            oauth_client               = oauth.Client(oauth_consumer)
            
            resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')
            
            if resp['status'] != '200':
                KhweeteurNotification().warn('Invalid respond from Twitter requesting temp token: %s' % resp['status'])
            else:
                request_token = dict(parse_qsl(content))

                QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))
                
                pincode, ok = QInputDialog.getText(self, 'Twitter Authentification', 'Enter the pincode :')

                if ok:
                    self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                    token.set_verifier(str(pincode))

                    oauth_client  = oauth.Client(oauth_consumer, token)
                    resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                    access_token  = dict(parse_qsl(content))

                    if resp['status'] != '200':
                        KhweeteurNotification().warn('The request for a Token did not succeed: %s' % resp['status'])
                        self.settings.setValue('twitter_access_token_key',QString())
                        self.settings.setValue('twitter_access_token_secret',QString())
                        self.settings.setValue('twitter_access_token',False)
                    else:
                        print access_token['oauth_token']
                        print access_token['oauth_token_secret']
                        self.settings.setValue('twitter_access_token_key',QString(access_token['oauth_token']))
                        self.settings.setValue('twitter_access_token_secret',QString(access_token['oauth_token_secret']))
                        self.settings.setValue('twitter_access_token',True)
                        self.twitter_value.setText('Clear Twitter Auth')
                        KhweeteurNotification().info('Khweeteur is now authorized to connect')
                    self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)
                
    def request_identica_access_or_clear(self):

        if self.settings.value('identica_access_token').toBool():
            self.settings.setValue('identica_access_token_key',QString())
            self.settings.setValue('identica_access_token_secret',QString())
            self.settings.setValue('identica_access_token',False)
            self.identica_value.setText('Auth on Identi.ca')
        else:
            import os
            import sys
            try:
                from urlparse import parse_qsl
            except:
                from cgi import parse_qsl
            import oauth2 as oauth
            
            REQUEST_TOKEN_URL = 'http://identi.ca/api/oauth/request_token'
            ACCESS_TOKEN_URL  = 'http://identi.ca/api/oauth/access_token'
            AUTHORIZATION_URL = 'http://identi.ca/api/oauth/authorize'

            signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
            oauth_consumer             = oauth.Consumer(key=KHWEETEUR_IDENTICA_CONSUMER_KEY, secret=KHWEETEUR_IDENTICA_CONSUMER_SECRET)
            oauth_client               = oauth.Client(oauth_consumer)
            
            resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')
            
            if resp['status'] != '200':
                KhweeteurNotification().warn('Invalid respond from Identi.ca requesting temp token: %s' % resp['status'])
            else:
                request_token = dict(parse_qsl(content))

                QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))
                
                pincode, ok = QInputDialog.getText(self, 'Identi.ca Authentification', 'Enter the token :')

                if ok:
                    self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                    token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                    token.set_verifier(str(pincode))

                    oauth_client  = oauth.Client(oauth_consumer, token)
                    resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                    access_token  = dict(parse_qsl(content))

                    if resp['status'] != '200':
                        KhweeteurNotification().warn('The request for a Token did not succeed: %s' % resp['status'])
                        self.settings.setValue('identica_access_token_key',QString())
                        self.settings.setValue('identica_access_token_secret',QString())
                        self.settings.setValue('identica_access_token',False)
                    else:
                        print access_token['oauth_token']
                        print access_token['oauth_token_secret']
                        self.settings.setValue('identica_access_token_key',QString(access_token['oauth_token']))
                        self.settings.setValue('identica_access_token_secret',QString(access_token['oauth_token_secret']))
                        self.settings.setValue('identica_access_token',True)
                        self.identica_value.setText('Clear Identi.ca Auth')
                        KhweeteurNotification().info('Khweeteur is now authorized to connect')
                    self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)
                    
    def setupGUI(self):
#        self.aWidget = QWidget()
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.aWidget = QWidget(self.scrollArea)
        self.aWidget.setMinimumSize(480,1000)
        self.aWidget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollArea.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollArea.setWidget(self.aWidget)
        scroller = self.scrollArea.property("kineticScroller").toPyObject()
        scroller.setEnabled(True)
        self._main_layout = QGridLayout(self.aWidget)

        self._main_layout.addWidget(QLabel('Authorizations :'),0,0)
        if self.settings.value('twitter_access_token').toBool():
            self.twitter_value = QPushButton('Clear Twitter Auth')
        else:
            self.twitter_value = QPushButton('Auth on Twitter')
        self._main_layout.addWidget(self.twitter_value,0,1)
        self.connect(self.twitter_value,SIGNAL('clicked()'),self.request_twitter_access_or_clear)

        if self.settings.value('identica_access_token').toBool():
            self.identica_value = QPushButton('Clear Identi.ca Auth')
        else:
            self.identica_value = QPushButton('Auth on Identi.ca')
        self._main_layout.addWidget(self.identica_value,1,1)
        self.connect(self.identica_value,SIGNAL('clicked()'),self.request_identica_access_or_clear)
        
        # self._main_layout.addWidget(QLabel('Password :'),1,0)
        # self.password_value = QLineEdit()
        # self.password_value.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        # self._main_layout.addWidget(self.password_value,1,1)

        self._main_layout.addWidget(QLabel('Refresh Interval (Minutes) :'),2,0)
        self.refresh_value = QSpinBox()
        self._main_layout.addWidget(self.refresh_value,2,1)

        self._main_layout.addWidget(QLabel('Display preferences :'),3,0)
        self.displayUser_value = QCheckBox('Display username')
        self._main_layout.addWidget(self.displayUser_value,3,1)

        self.displayAvatar_value = QCheckBox('Display avatar')
        self._main_layout.addWidget(self.displayAvatar_value,4,1)

        self.displayTimestamp_value = QCheckBox('Display timestamp')
        self._main_layout.addWidget(self.displayTimestamp_value,5,1)

        self._main_layout.addWidget(QLabel('Other preferences :'),6,0)
        self.useNotification_value = QCheckBox('Use Notification')
        self._main_layout.addWidget(self.useNotification_value,6,1)

        self.useSerialization_value = QCheckBox('Use Serialization')
        self._main_layout.addWidget(self.useSerialization_value,7,1)

        self.aWidget.setLayout(self._main_layout)
#        self.setCentralWidget(self.aWidget)
        self.setCentralWidget(self.scrollArea)

        
class KhweeteurWin(QMainWindow):

    def __init__(self, parent=None, search_keyword=None):
        QMainWindow.__init__(self,None)
        self.parent = parent

        self.search_keyword = search_keyword

        #crappy trick to avoid search win to be garbage collected
        self.search_win = []
            
        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)

        if self.search_keyword != None:
            self.setWindowTitle("Khweeteur:"+unicode(self.search_keyword))      
        else:           
            self.setWindowTitle("Khweeteur")

        self.settings = QSettings()
                    
        self.setupMenu()
        self.setupMain()

        self.worker = None
        self.tweetsModel.display_screenname = self.settings.value("displayUser").toBool()
        self.tweetsModel.display_timestamp = self.settings.value("displayTimestamp").toBool()
        self.tweetsModel.display_avatar = self.settings.value("displayAvatar").toBool()
        self.nw = NetworkManager(self.refresh_timeline)
        self.notifications = KhweeteurNotification()

        self.timer = QTimer()
        self.connect(self.timer, SIGNAL("timeout()"), self.timed_refresh)
        if (self.settings.value("refreshInterval").toInt()[0]>0):
            self.timer.start(self.settings.value("refreshInterval").toInt()[0]*60*1000)

        if self.search_keyword == None:
            self.open_saved_search()

    def enterEvent(self,event):
        """
            Redefine the enter event to refresh timestamp
        """        
        self.tweetsModel.refreshTimestamp()

    def setupMain(self):

        self.tweetsView = KhweetsView(self)
        self.connect(self.tweetsView,SIGNAL('doubleClicked(const QModelIndex&)'),self.reply)
        self.tweetsModel = KhweetsModel([])
        self.tweetsView.setModel(self.tweetsModel)
        self.setCentralWidget(self.tweetsView)
#        if self.search_keyword == None:
        self.tweetsModel.unSerialize(self.search_keyword)

        self.toolbar = self.addToolBar('Toolbar')

        self.tb_open = QAction(QIcon.fromTheme("general_web"),'Open', self)
        self.connect(self.tb_open, SIGNAL('triggered()'), self.open_url)
        self.toolbar.addAction(self.tb_open)
        
        # self.tb_retweet = QAction(QIcon.fromTheme("general_refresh"),'Retweet', self)
        # self.connect(self.tb_retweet, SIGNAL('triggered()'), self.retweet)
        # self.toolbar.addAction(self.tb_retweet)
        
        self.tb_text = QLineEdit()
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.tb_text.enabledChange(True)
        self.toolbar.addWidget(self.tb_text)

        self.tb_charCounter = QLabel('140')
        self.toolbar.addWidget(self.tb_charCounter)
        self.connect(self.tb_text, SIGNAL('textChanged(const QString&)'), self.countChar)

        self.tb_tweet = QAction(QIcon(QPixmap(os.path.join(khweeteur.__path__[0],'icons','khweeteur.png')).scaledToHeight(128)),'Tweet', self)
        self.connect(self.tb_tweet, SIGNAL('triggered()'), self.tweet)
        self.toolbar.addAction(self.tb_tweet)

    def open_url(self):
        for index in self.tweetsView.selectedIndexes():
            status = self.tweetsModel._items[index.row()][3]
            try:
                urls = re.findall("(?P<url>https?://[^\s]+)", status)
                for url in urls:
                    QDesktopServices.openUrl(QUrl(url))
            except StandardError,e:
                print e


    def countChar(self,text):
        self.tb_charCounter.setText(unicode(140-len(text)))

    def reply(self,index):
        user = self.tweetsModel._items[index.row()][2]
        self.tb_text_replyid = self.tweetsModel._items[index.row()][1]
        self.tb_text_replytext = '@'+user+' '
        self.tb_text.setText('@'+user+' ')

    def retweet(self):
        for index in self.tweetsView.selectedIndexes():
            if ((QMessageBox.question(self,
                       "Khweeteur",
                       "Retweet this : %s ?" % self.tweetsModel._items[index.row()][3],
                       QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                tweetid = self.tweetsModel._items[index.row()][1]
                print 'DEBUG Retweet:',tweetid
                try:
                    if self.settings.value("twitter_access_token_key").toString()!='':     
                        api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                          access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                          access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                        api.PostRetweet(tweetid)
                        self.notifications.info('Retweet send to Twitter')
                except (twitter.TwitterError,StandardError),e:
                    if type(e)==twitter.TwitterError:
                        self.notifications.warn('Retweet to twitter failed : '+(e.message))
                        print e.message
                    else:
                        self.notifications.warn('Retweet to twitter failed : '+str(e))
                        print e                     
                try:
                    if self.settings.value("identica_access_token_key").toString()!='': 
                        api = twitter.Api(base_url='http://identi.ca/api/',username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                          password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                          access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                          access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
                        api.PostRetweet(tweetid)
                        self.notifications.info('Retweet send to Identi.ca')
                except (twitter.TwitterError,StandardError),e:
                    if type(e)==twitter.TwitterError:
                        self.notifications.warn('Retweet to identi.ca failed : '+(e.message))
                        print e.message
                    else:
                        self.notifications.warn('Retweet to identi.ca failed : '+str(e))
                        print e                 

                                              
    def tweet(self):
        try:
                status_text = unicode(self.tb_text.text()).encode('UTF-8')
                if status_text.startswith(self.tb_text_replytext):
                    self.tb_text_replyid = 0
                    
                if self.settings.value("twitter_access_token_key").toString()!='':     
                    api = twitter.Api(
                                      username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                      access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                      access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                    if self.settings.value('useSerialization').toBool():
                        status = api.PostSerializedUpdates(status_text,in_reply_to_status_id=self.tb_text_replyid)
                    else:
                        status = api.PostUpdate(status_text,in_reply_to_status_id=self.tb_text_replyid)
                    self.notifications.info('Tweet send to Twitter')

                if self.settings.value("identica_access_token_key").toString()!='':     
                    api = twitter.Api(base_url='http://identi.ca/api/',username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                      password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                      access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                      access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                    if self.settings.value('useSerialization').toBool():
                        status = api.PostSerializedUpdates(status_text,in_reply_to_status_id=self.tb_text_replyid)
                    else:
                        status = api.PostUpdate(status_text,in_reply_to_status_id=self.tb_text_replyid)
                    self.notifications.info('Tweet send to Identica')
                    
                self.tb_text.setText('')
                self.tb_text_replyid = 0
                self.tb_text_replytext = ''
        except (twitter.TwitterError,StandardError),e:
            import traceback
            print traceback.print_exc()
            print traceback.print_stack()
            if type(e)==twitter.TwitterError:
                self.notifications.warn('Send tweet failed : '+(e.message))
                print e.message
            else:
                self.notifications.warn('Send tweet failed : '+str(e))
                print e 

    def refreshEnded(self):
#        if self.search_keyword == None:
        self.tweetsModel.serialize(self.search_keyword)
        counter=self.tweetsModel.getNew()
        
        if (counter>0) and (self.settings.value('useNotification').toBool()) and not (self.isActiveWindow()):
            if self.search_keyword:
                self.notifications.notify_search(self.search_keyword,'Khweeteur',self.search_keyword+': '+str(counter)+' new tweet(s)',count=counter)
            else:
                self.notifications.notify('Khweeteur',str(counter)+' new tweet(s)',count=counter)
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def do_refresh_now(self):
        print type(self.settings.value('useNotification').toString()),self.settings.value('useNotification').toString()
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
        self.worker = KhweeteurWorker(search_keyword=self.search_keyword)
        self.connect(self.worker, SIGNAL("newStatus(PyQt_PyObject)"), self.tweetsModel.addStatus)
        self.connect(self.worker, SIGNAL("newStatuses(PyQt_PyObject)"), self.tweetsModel.addStatuses)
        self.connect(self.worker, SIGNAL("finished()"), self.refreshEnded)
        self.notifications.connect(self.worker, SIGNAL('info(PyQt_PyObject)'), self.notifications.info)
        self.worker.start()
        
    def request_refresh(self):
        if not self.nw.device_has_networking:
            self.nw.request_connection()
        else:
            self.refresh_timeline()

    def timed_refresh(self):
        print 'Timer refresh'
        self.request_refresh()

    def refresh_timeline(self):
        if self.worker == None:
            self.do_refresh_now()
        elif self.worker.isFinished() == True:
            print 'isFinished()', True, self.worker.isFinished()
            self.do_refresh_now()
        else:
            print 'isFinished()', self.worker.isFinished()

    def restartTimer(self):
        self.tweetsModel.display_screenname = self.settings.value("displayUser").toBool()
        self.tweetsModel.display_timestamp = self.settings.value("displayTimestamp").toBool()
        self.tweetsModel.display_avatar = self.settings.value("displayAvatar").toBool()
        QObject.emit(self.tweetsModel, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.tweetsModel.createIndex(0,0), self.tweetsModel.createIndex(0,len(self.tweetsModel._items)))
        if (self.settings.value("refreshInterval").toInt()[0]>0):
            self.timer.start(self.settings.value("refreshInterval").toInt()[0]*60*1000)
        else:
            self.timer.stop()

    def setupMenu(self):
        fileMenu = QMenu(self.tr("&Menu"), self)

        self.menuBar().addMenu(fileMenu)

        fileMenu.addAction(self.tr("&Preferences"), self.do_show_pref,
                QKeySequence(self.tr("Ctrl+P", "Preferences")))
        fileMenu.addAction(self.tr("&Update"), self.request_refresh,
                QKeySequence(self.tr("Ctrl+R", "Update")))
        fileMenu.addAction(self.tr("&Search"), self.open_search,
                QKeySequence(self.tr("Ctrl+S", "Search")))
        fileMenu.addAction(self.tr("&Retweet"), self.retweet,
                QKeySequence(self.tr("Ctrl+T", "Retweet")))
                
        if self.search_keyword != None:
            keywords = self.settings.value('savedSearch').toPyObject()
            if (keywords != None):
                if self.search_keyword in keywords:
                    fileMenu.addAction(self.tr("&Remove Search"), self.del_search)
                else:
                    fileMenu.addAction(self.tr("&Save Search"), self.save_search)
            else:
                fileMenu.addAction(self.tr("&Save Search"), self.save_search)                                        

        fileMenu.addAction(self.tr("&About"), self.do_about)

    def del_search(self):
        keywords = self.settings.value('savedSearch').toPyObject()
        if (keywords == None):
            keywords = []
        elif (type(keywords)==QString):
            if (self.search_keyword==keywords):
                keywords = []
        else:
            index = keywords.indexOf(self.search_keyword)
            if index>=0:
                keywords.removeAt(index)
        self.settings.setValue('savedSearch',QVariant(keywords))
        self.close()
                                
    def save_search(self):
        keywords = self.settings.value('savedSearch').toPyObject()
        print 'save_search:',keywords
        if (keywords == None):
            keywords = []
        elif (type(keywords)==QString):
            keywords = [keywords,]
        print 'save_search2:',keywords,type(keywords)
        keywords.append(self.search_keyword)
        print 'save_search3:',keywords,type(keywords)
        self.settings.setValue('savedSearch',QVariant(keywords))
                                
    def open_saved_search(self):
        keywords = self.settings.value('savedSearch').toPyObject()
        print 'open_saved_search:',keywords
        if (type(keywords)==QString):
            keywords = [keywords,]

        if (keywords != None):
            for keyword in keywords:
                self.do_search(keyword)
    
    def open_search(self):
        search_keyword, ok = QInputDialog.getText(self, 'Search', 'Enter the search keyword(s) :')
        if ok==1:
            self.do_search(search_keyword)
        
    def do_search(self,search_keyword):
        swin = KhweeteurWin(search_keyword=unicode(search_keyword))
        self.search_win.append(swin)
        swin.show()
        
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

        dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

        session_bus = dbus.SessionBus()
        name = dbus.service.BusName("net.khertan.khweeteur", session_bus)
        self.dbus_object = KhweeteurDBus(session_bus, '/net/khertan/khweeteur')
        self.run()
        
    def run(self):
        self.win = KhweeteurWin()
        self.dbus_object.attach_win(self.win)
        self.win.show()
        sys.exit(self.exec_())

if __name__ == '__main__':
    Khweeteur()

