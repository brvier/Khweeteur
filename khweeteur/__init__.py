#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4'''

from PyQt4.QtGui import *
from PyQt4.QtCore import *

try:
    from PyQt4.QtMaemo5 import *
    isMAEMO = True
except:
    isMAEMO = False
    
#import khweeteur
import twitter
import sys
import os.path
from urllib import urlretrieve
import datetime
import time
import dbus
import dbus.service
import dbus.mainloop.qt
import pickle
from PIL import Image
import re
import urllib2
import socket

__version__ = '0.0.29'

def write_report(error):
    filename = os.path.join(CACHE_PATH,'crash_report')
    output = open(filename, 'wb')
    pickle.dump(error, output)
    output.close()
        
#Here is the installation of the hook. Each time a untrapped/unmanaged exception will
#happen my_excepthook will be called.
def install_excepthook(app_name,app_version):

    APP_NAME = 'Khweeteur'
    APP_VERSION = __version__
        
    def my_excepthook(exctype, value, tb):
        #traceback give us all the errors information message like the method, file line ... everything like
        #we have in the python interpreter
        import traceback
        s = ''.join(traceback.format_exception(exctype, value, tb))
        print 'Except hook called : %s' % (s)
        formatted_text = "%s Version %s\nTrace : %s\nComments : " % (APP_NAME, APP_VERSION, s)
        write_report(formatted_text)
        
    sys.excepthook = my_excepthook
        
AVATAR_CACHE_FOLDER = os.path.join(os.path.expanduser("~"),'.khweeteur','cache')
CACHE_PATH = os.path.join(os.path.expanduser("~"), '.khweeteur')
KHWEETEUR_TWITTER_CONSUMER_KEY = 'uhgjkoA2lggG4Rh0ggUeQ'
KHWEETEUR_TWITTER_CONSUMER_SECRET = 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU'
KHWEETEUR_IDENTICA_CONSUMER_KEY = 'c7e86efd4cb951871200440ad1774413'
KHWEETEUR_IDENTICA_CONSUMER_SECRET = '236fa46bf3f65fabdb1fd34d63c26d28'
SCREENNAMEROLE = 20

class KhweeteurDBus(dbus.service.Object):
    '''DBus Object handle dbus callback'''
    @dbus.service.method("net.khertan.khweeteur",
                         in_signature='', out_signature='')
    def show(self):
        self.win.tweetsModel.getNewAndReset()
        self.win.activateWindow()

    @dbus.service.method("net.khertan.khweeteur",
                         in_signature='s', out_signature='')
    def show_search(self,keyword):
        for win in self.win.search_win:
            if win.search_keyword == keyword:
                win.activateWindow()
                win.tweetsModel.getNewAndReset()
                
    def attach_win(self,win):
        self.win = win
        
class KhweeteurNotification(QObject):
    '''Notification class interface'''
    def __init__(self):
        QObject.__init__(self)
        self.m_bus = dbus.SystemBus()
        self.m_notify = self.m_bus.get_object('org.freedesktop.Notifications',
                                              '/org/freedesktop/Notifications')
        self.iface = dbus.Interface(self.m_notify,'org.freedesktop.Notifications')
        self.m_id = 0
        
    def warn(self,message):
        if isMAEMO:
            self.iface.SystemNoteDialog(message,0,'Nothing')
        
    def info(self,message):
        if isMAEMO:
            self.iface.SystemNoteInfoprint('Khweeteur : '+message)
        
    def notify(self,title,message,category='im.received',icon='khweeteur',count=1):
        self.m_id = self.iface.Notify('Khweeteur',
                          self.m_id,
                          icon,
                          title,
                          message,
                          ['default',],
                          {'category':category,
                          'desktop-entry':'khweeteur',
                          'dbus-callback-default':'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show',
                          'count':count},
                          -1
                          )
                          
    def notify_search(self,keyword,title,message,category='im.received',icon='khweeteur',count=1):
        self.m_id = self.iface.Notify('Khweeteur',
                          self.m_id,
                          icon,
                          title,
                          message,
                          ['default',],
                          {'category':category,
                          'desktop-entry':'khweeteur',
                          'dbus-callback-default':'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show_search(%s)' % (keyword,),
                          'count':count},
                          -1
                          )
                          
class KhweeteurActionWorker(QThread):
    '''ActionWorker : Post tweet in background'''
    def __init__(self, parent = None, action=None, data=None, data2=None, data3=None):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        self.action = action
        self.data = data
        self.tb_text_replyid = data2
        self.tb_text_replytext = data3

    def run(self):
        if self.action=='tweet':
            self.tweet()
        elif self.action=='retweet':
            self.retweet()

    def tweet(self):
        try:
                status_text = self.data

                if self.settings.value("useBitly").toBool():
                    urls = re.findall("(?P<url>https?://[^\s]+)", status_text)
                    if len(urls)>0:
                        import bitly                 
                        a=bitly.Api(login="pythonbitly",apikey="R_06871db6b7fd31a4242709acaf1b6648")

                    for url in urls:
                        try:
                            short_url=a.shorten(url)
                            status_text = status_text.replace(url,short_url)
                        except:
                            pass

                if status_text.startswith(self.tb_text_replytext):
                    self.tb_text_replyid = 0
                    
                if self.settings.value("twitter_access_token_key").toString()!='':     
                    api = twitter.Api(
                                      username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                      access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                      access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if self.settings.value('useSerialization').toBool():
                        status = api.PostSerializedUpdates(status_text,in_reply_to_status_id=self.tb_text_replyid)
                    else:
                        status = api.PostUpdate(status_text,in_reply_to_status_id=self.tb_text_replyid)
#                    self.notifications.info('Tweet send to Twitter')
                    self.emit(SIGNAL("info(PyQt_PyObject)"),'Tweet send to Twitter')

                if self.settings.value("identica_access_token_key").toString()!='':     
                    api = twitter.Api(base_url='http://identi.ca/api/',username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                      password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                      access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                      access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if self.settings.value('useSerialization').toBool():
                        status = api.PostSerializedUpdates(status_text,in_reply_to_status_id=self.tb_text_replyid)
                    else:
                        status = api.PostUpdate(status_text,in_reply_to_status_id=self.tb_text_replyid)
#                    self.notifications.info('Tweet send to Identica')
                    self.emit(SIGNAL("info(PyQt_PyObject)"),'Tweet send to Identica')
                                        
                self.emit(SIGNAL("tweetSent()"))

#                self.tb_text.setText('')
#                self.tb_text_replyid = 0
#                self.tb_text_replytext = ''
        except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
            if type(e)==twitter.TwitterError:
#                self.notifications.warn('Send tweet failed : '+(e.message))
                self.emit(SIGNAL("warn(PyQt_PyObject)"),e.message)
                print e.message
            else:
#                self.notifications.warn('Send tweet failed : '+str(e))
                self.emit(SIGNAL("warn(PyQt_PyObject)"),'A network error occur')
                print e 

                          
class KhweeteurWorker(QThread):
    ''' Thread to Refresh in background '''
    def __init__(self, parent = None, search_keyword=None):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        self.search_keyword = search_keyword
        
    def run(self):
        self.testCacheFolders()
        if self.search_keyword==None:
            self.refresh()
        else:
#            print 'Worker Refresh search : '+self.search_keyword 
            self.refresh_search()

    def testCacheFolders(self):
        try:
            if not os.path.isdir(CACHE_PATH):
                os.mkdir(CACHE_PATH)
        except:
            pass
        try:
            if not os.path.isdir(AVATAR_CACHE_FOLDER):
                os.mkdir(AVATAR_CACHE_FOLDER)
        except:
            pass
        
    def downloadProfileImage(self,status):
        if type(status)!=twitter.DirectMessage:
            cache = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(status.user.profile_image_url.replace('/','_')))
            if not(os.path.exists(cache)):
                try:
                    urlretrieve(status.user.profile_image_url, cache)                    
                    #print 'try to convert to png'
                    im = Image.open(cache)
                    im = im.resize((50,50))
                    #transparency = im.info['transparency'] 
                    #im.save(os.path.splitext(cache)[0]+'.png', 'PNG', transparency=transparency)
                    im.save(os.path.splitext(cache)[0]+'.png', 'PNG')
#                    print os.path.splitext(cache)[0]+'.png'
                except (StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                    print 'DownloadProfileImage Error : ',e
        
    def refresh_search(self):
        downloadProfileImage = self.downloadProfileImage
        search_keyword = self.search_keyword                       
        current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())
        mlist = []
        try:
            twitter_last_id = None        
            if (self.settings.value("twitter_access_token_key").toString()!=''): 
                api = twitter.Api(input_encoding='utf-8', \
                    username=KHWEETEUR_TWITTER_CONSUMER_KEY, \
                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET, \
                    access_token_key=str(self.settings.value("twitter_access_token_key").toString()), \
                    access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                for status in api.GetSearch(unicode(search_keyword).encode('UTF-8'),since_id=self.settings.value("twitter_last_id_"+search_keyword).toString()):
                    #if status.created_at_in_seconds > current_dt:
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > twitter_last_id:
                        twitter_last_id = status.GetId()
        except twitter.TwitterError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except (StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
            self.emit(SIGNAL("info(PyQt_PyObject)"),'A network error occur')

        try:
            identica_last_id = None
            if (self.settings.value("twitter_access_token_key").toString()!=''): 
                api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, access_token_key=str(self.settings.value("identica_access_token_key").toString()),access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                for status in api.GetSearch(unicode(search_keyword).encode('UTF-8'),since_id=self.settings.value("identica_last_id_"+search_keyword).toString()):
                    #if status.created_at_in_seconds > current_dt:
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > identica_last_id:
                        identica_last_id = status.GetId()
        except twitter.TwitterError,e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except (StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
            print 'Error during refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),'A network error occur')


        if len(mlist)>0:
            if (twitter_last_id != None):
                self.settings.setValue('twitter_last_id_'+search_keyword,twitter_last_id)
                #print 'DEBUG SAVED SEARCH Last twiter id : ',twitter_last_id
            if (identica_last_id != None):
                self.settings.setValue('identica_last_id_'+search_keyword,identica_last_id)
            mlist.sort()            
            self.emit(SIGNAL("newStatuses(PyQt_PyObject)"),mlist)
        
    def refresh(self):
        downloadProfileImage = self.downloadProfileImage
        current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())
        mlist = []
        try:
            #avatars_url={}
            twitter_last_id = None
            if (self.settings.value("twitter_access_token_key").toString()!=''): 
                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY, \
                        password=KHWEETEUR_TWITTER_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("twitter_access_token_key").toString()), \
                        access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                for status in api.GetFriendsTimeline(since_id=self.settings.value("twitter_last_id").toString(), retweets=True):
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > twitter_last_id:
                        twitter_last_id = status.GetId()
                for status in api.GetRetweetedByMe(since_id=self.settings.value("twitter_last_id").toString()):
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > twitter_last_id:
                        twitter_last_id = status.GetId()
                for status in api.GetReplies(since_id=self.settings.value("twitter_last_id").toString()):
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > twitter_last_id:
                        twitter_last_id = status.GetId()
                for status in api.GetDirectMessages(since_id=self.settings.value("twitter_last_id").toString()):
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > twitter_last_id:
                        twitter_last_id = status.GetId()
                for status in api.GetMentions(since_id=self.settings.value("twitter_last_id").toString()):
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))                        
                    if status.GetId() > twitter_last_id:
                            twitter_last_id = status.GetId()
                            
                #Moved here to avoid partial refresh
                if (twitter_last_id != None):
                    self.settings.setValue('twitter_last_id',twitter_last_id)
                    
        except twitter.TwitterError,e:
            print 'Error during twitter refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except (StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
            print 'Error during twitter refresh : ',e
            self.emit(SIGNAL("info(PyQt_PyObject)"),'A network error occur')

        try:
            identica_last_id = None
            if (self.settings.value("identica_access_token_key").toString()!=''): 
                api = twitter.Api(base_url='http://identi.ca/api/', \
                        username=KHWEETEUR_IDENTICA_CONSUMER_KEY, \
                        password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("identica_access_token_key").toString()), \
                        access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                for status in api.GetFriendsTimeline(count=100,since_id=self.settings.value("identica_last_id").toString(),retweets=True):
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > identica_last_id:
                        identica_last_id = status.GetId()
                # Not yet supported by identi.ca
                # for status in api.GetRetweetedByMe(since_id=self.settings.value("twitter_last_id").toString()):
                    # downloadProfileImage(status)
                    # mlist.append((status.created_at_in_seconds,status))
                    # if status.GetId() > twitter_last_id:
                        # twitter_last_id = status.GetId()
                for status in api.GetReplies(since_id=self.settings.value("identica_last_id").toString()):
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > identica_last_id:
                        identica_last_id = status.GetId()                        
                for status in api.GetDirectMessages(since_id=self.settings.value("identica_last_id").toString()):
                    mlist.append((status.created_at_in_seconds,status))
                    if status.GetId() > identica_last_id:
                        identica_last_id = status.GetId()
                for status in api.GetMentions(since_id=self.settings.value("identica_last_id").toString()):
                    if status.GetId() > identica_last_id:
                        identica_last_id = status.GetId()
                    downloadProfileImage(status)
                    mlist.append((status.created_at_in_seconds,status))                   
                if (identica_last_id != None):
                    self.settings.setValue('identica_last_id',identica_last_id)      
        except twitter.TwitterError,e:
            print 'Error during identi.ca refresh: ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except (StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
            print 'Error during identi.ca refresh : ',e
            self.emit(SIGNAL("info(PyQt_PyObject)"),'A network error occur')
                

        if len(mlist)>0:
            mlist.sort()            
            self.emit(SIGNAL("newStatuses(PyQt_PyObject)"),mlist)
                        
class KhweetsModel(QAbstractListModel):
    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    def __init__(self, mlist=[],keyword=None):
        QAbstractListModel.__init__(self)
        # Cache the passed data list as a class member.
        self._items = mlist
        self._avatars = {}
        self._new_counter = 0
        self.now = time.time()
        
        self.keyword = keyword

    # def flags(self, index):
        # return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled
        
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
        self.now = time.time()
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
        GetRelativeCreatedAt = self.GetRelativeCreatedAt
        #print 'Debug addstatuses count:',len(listVariant)
        for _,variant in listVariant:
            try:
                if all(item[1]!=variant.id for item in self._items):
                    self.beginInsertRows(QModelIndex(), 0,1)  
                    if type(variant) != twitter.DirectMessage:
                        self._items.insert(0,
                            (variant.created_at_in_seconds,
                             variant.id,
                             variant.user.screen_name,
                             variant.text,
                             variant.user.profile_image_url,
                             GetRelativeCreatedAt(variant.created_at_in_seconds),))

                        if variant.user.screen_name!=None:
                            try:
                                if variant.user.profile_image_url[4]!=None:
                                    path = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(variant.user.profile_image_url.replace('/','_')))
                                    if not path.endswith('.png'):
                                        path = os.path.splitext(path)[0] + '.png'
                                    pix = QPixmap(path) #.scaled(50,50)
                                    if pix.isNull():
                                        print path
                                    self._avatars[variant.user.profile_image_url] = (pix)
                            except StandardError, err:
                                print 'error on loading avatar :',err
                    else:
                        self._items.insert(0,
                             (variant.created_at_in_seconds,
                              variant.id,
                              variant.sender_screen_name,
                              variant.text,
                              None,
                              GetRelativeCreatedAt(variant.created_at_in_seconds),))
                    self._new_counter = self._new_counter + 1
                    self.now = time.time()
                    self.endInsertRows()
            except StandardError, e:
                print "We shouldn't got this error here :",e

        if len(listVariant):
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
            self.serialize()

    def destroyStatus(self,index):
        self._items.pop(index.row())
        QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
            
    def getNewAndReset(self):
        counter = self._new_counter
        self._new_counter = 0
        return counter

    def getNew(self):
        return self._new_counter
    
    def setData(self,index,variant,role):
        return True
        
    def setTweets(self,mlist):
        try:
            if len(mlist)>0:
                #if type(mlist[0])==tuple:
                #    if len(mlist[0])==6:
                self._items = mlist
                self._new_counter = 0
                QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
                return True
                 #   else:
                 #       print 'Wrong cache format'
                 #       write_report("%s Version %s\nOld cache format : %s\n" % ('Khweeteur', __version__, ''))
                 #       KhweeteurNotification().info('Old cache format. Reinit cache.')            
        except StandardError,err:
            KhweeteurNotification().info('Wrong cache format. Reinit cache.')
            write_report("%s Version %s\nWrong cache format : %s\n" % ('Khweeteur', __version__, err))
            print 'Wrong cache format'
        return False
        
    def serialize(self):
        try:
            if self.keyword==None:
                filename = os.path.join(CACHE_PATH,'tweets.cache')
            else:
                filename = os.path.normcase(unicode(os.path.join(unicode(CACHE_PATH),unicode(self.keyword.replace('/','_'))+u'.cache'))).encode('UTF-8')               
            output = open(filename, 'wb')
            pickle.dump(self._items, output)
            output.close()
            
        except StandardError,e:
            KhweeteurNotification().info('An error occurs while saving cache : '+str(e))
            
    def unSerialize(self):
        try:
            if self.keyword==None:
                filename = os.path.join(CACHE_PATH,'tweets.cache')
            else:
                filename = os.path.normcase(unicode(os.path.join(unicode(CACHE_PATH),unicode(self.keyword.replace('/','_'))+u'.cache'))).encode('UTF-8')          
            pkl_file = open(filename, 'rb')
            items = pickle.load(pkl_file)
            self.setTweets(items)
            pkl_file.close()
        except StandardError,e:
            print 'unSerialize : ',e
            self.settings = QSettings()
            if self.keyword == None:
                self.settings.setValue('twitter_last_id','')
                self.settings.setValue('identica_last_id','')
            else:
                self.settings.setValue('twitter_last_id_'+self.keyword,'')
                self.settings.setValue('identica_last_id_'+self.keyword,'')
                
        finally:
            #14 Day limitations
            current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())
            for index, item in enumerate(self._items):
                if item[0] < current_dt:
                    self._items = self._items[:index]
                    break
            for item in self._items:
                try:
                    if item[4]!=None:
                        path = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(item[4].replace('/','_')))
                        if not path.endswith('.png'):
                            path = os.path.splitext(path)[0]+'.png'
                        pix = (QPixmap(path)) #.scaled(50,50)
#                        if pix.isNull():
#                            print path
                        self._avatars[item[4]] = (pix)
                except StandardError, err:
                    print 'error on loading avatar :',err 
            self._items.sort()
            self._items.reverse()
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return QVariant(self._items[index.row()][3])
        elif role == SCREENNAMEROLE:
            return QVariant(self._items[index.row()][2])
        elif role == Qt.ToolTipRole:
            return self._items[index.row()][5]
        elif role == Qt.DecorationRole:            
            try:
                return self._avatars[self._items[index.row()][4]]
            except:
                return QVariant()
        else:
            return QVariant()
     
    def wantsUpdate(self):
        QObject.emit(self, SIGNAL("layoutChanged()"))

class DefaultCustomDelegate(QStyledItemDelegate):
    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''
        QStyledItemDelegate.__init__(self, parent)
        self.show_avatar = True
        self.show_screenname = True
        self.show_timestamp = True

        self.tips_color = QColor('#7AB4F5')
        self.bg_color = QColor('#333333')
                
        self.fm = None
        
        self.normFont = None
        self.miniFont = None

    def sizeHint (self, option, index):
        '''Custom size calculation of our items'''
        size = QStyledItemDelegate.sizeHint(self, option, index)
        tweet = index.data(Qt.DisplayRole).toString()
        #One time is enought sizeHint need to be fast
        if self.fm == None:
            self.fm = QFontMetrics(option.font)
        height = self.fm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet).height()
        if height<37:
            height=37        
        return QSize(size.width(), height+25)
        

    def paint(self, painter, option, index):
        '''Paint our tweet'''
        self.fm = QFontMetrics(option.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole).toString()
        
        #Instantiate font only one time !
        if self.normFont == None:
            self.normFont = QFont(option.font)
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)            
        
        painter.save()
        
        # Draw alternate ?
        if (index.row()%2)==0:
            painter.fillRect(option.rect, self.bg_color)

        # highlight selected items
        if option.state & QStyle.State_Selected: 
            painter.fillRect(option.rect, option.palette.highlight());
                    
        # Draw icon
        if self.show_avatar:
            icon = index.data(Qt.DecorationRole).toPyObject();
            if icon != None:
                x1,y1,x2,y2 = option.rect.getCoords()
                painter.drawPixmap(x1+10,y1+6,50,50,icon)
                                                
        # Draw tweet
        new_rect = painter.drawText(option.rect.adjusted(int(self.show_avatar)*70,0,-4,0),  int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet); 
                
        # Draw Timeline
        if self.show_timestamp:
            time = index.data(Qt.ToolTipRole).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.tips_color)
            painter.drawText(option.rect.adjusted(70,0,-2,0),  int(Qt.AlignBottom) | int(Qt.AlignRight), time);

        # Draw screenname
        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.tips_color)
            painter.drawText(option.rect.adjusted(70,0,-2,0),  int(Qt.AlignBottom) | int(Qt.AlignLeft), screenname);

        painter.restore()

class WhiteCustomDelegate(QStyledItemDelegate):
    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''
        QStyledItemDelegate.__init__(self, parent)
        self.show_avatar = True
        self.show_screenname = True
        self.show_timestamp = True

        self.tips_color = QColor('#7AB4F5')
        self.bg_color = QColor('#FFFFFF')
        self.bg_alternate_color = QColor('#dddddd')
        self.text_color = QColor('#000000')
                
        self.fm = None
        
        self.normFont = None
        self.miniFont = None

    def sizeHint (self, option, index):
        '''Custom size calculation of our items'''
        size = QStyledItemDelegate.sizeHint(self, option, index)
        tweet = index.data(Qt.DisplayRole).toString()
        #One time is enought sizeHint need to be fast
        if self.fm == None:
            self.fm = QFontMetrics(option.font)
        height = self.fm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet).height()
        if height<37:
            height=37        
        return QSize(size.width(), height+25)
        

    def paint(self, painter, option, index):
        '''Paint our tweet'''
        self.fm = QFontMetrics(option.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole).toString()
        
        #Instantiate font only one time !
        if self.normFont == None:
            self.normFont = QFont(option.font)
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)            
        
        painter.save()
        
        # Draw alternate ?
        if (index.row()%2)==0:
            painter.fillRect(option.rect, self.bg_color)
        else:
            painter.fillRect(option.rect, self.bg_alternate_color)            

        # highlight selected items
        if option.state & QStyle.State_Selected: 
            painter.fillRect(option.rect, option.palette.highlight());
                    
        # Draw icon
        if self.show_avatar:
            icon = index.data(Qt.DecorationRole).toPyObject();
            if icon != None:
                x1,y1,x2,y2 = option.rect.getCoords()
                painter.drawPixmap(x1+10,y1+6,50,50,icon)
                                                
        # Draw tweet
        painter.setPen(self.text_color)
        new_rect = painter.drawText(option.rect.adjusted(int(self.show_avatar)*70,0,-4,0),  int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet); 
                
        # Draw Timeline
        if self.show_timestamp:
            time = index.data(Qt.ToolTipRole).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.tips_color)
            painter.drawText(option.rect.adjusted(70,0,-2,0),  int(Qt.AlignBottom) | int(Qt.AlignRight), time);

        # Draw screenname
        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.tips_color)
            painter.drawText(option.rect.adjusted(70,0,-2,0),  int(Qt.AlignBottom) | int(Qt.AlignLeft), screenname);

        painter.restore()

class CoolWhiteCustomDelegate(QStyledItemDelegate):
    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''
        QStyledItemDelegate.__init__(self, parent)
        self.show_avatar = True
        self.show_screenname = True
        self.show_timestamp = True

        self.user_color = QColor('#3399cc')
        self.time_color = QColor('#94a1a7')
        self.bg_color = QColor('#edf1f2')
        self.bg_alternate_color = QColor('#e6eaeb')
        self.text_color = QColor('#444444')
        self.separator_color = QColor('#c8cdcf')
                
        self.fm = None
        
        self.normFont = None
        self.miniFont = None

    def sizeHint (self, option, index):
        '''Custom size calculation of our items'''
        size = QStyledItemDelegate.sizeHint(self, option, index)
        tweet = index.data(Qt.DisplayRole).toString()
        #One time is enought sizeHint need to be fast
        if self.fm == None:
            self.fm = QFontMetrics(option.font)
        height = self.fm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet).height()
        if height<40:
            height=40        
        return QSize(size.width(), height+44)
        

    def paint(self, painter, option, index):
        '''Paint our tweet'''
        self.fm = QFontMetrics(option.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole).toString()
        
        #Instantiate font only one time !
        if self.normFont == None:
            self.normFont = QFont(option.font)
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)            
        
        painter.save()
        
        # Draw alternate ?
        if (index.row()%2)==0:
            painter.fillRect(option.rect, self.bg_color)
        else:
            painter.fillRect(option.rect, self.bg_alternate_color)            

        # highlight selected items
        if option.state & QStyle.State_Selected: 
            painter.fillRect(option.rect, option.palette.highlight());
                    
        # Draw icon
        if self.show_avatar:
            icon = index.data(Qt.DecorationRole).toPyObject();
            if icon != None:
                x1,y1,x2,y2 = option.rect.getCoords()
                painter.drawPixmap(x1+10,y1+10,50,50,icon)
                                                
        # Draw tweet
        painter.setPen(self.text_color)
        new_rect = painter.drawText(option.rect.adjusted(int(self.show_avatar)*70,5,-4,0),  int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet); 
                
        # Draw Timeline
        if self.show_timestamp:
            time = index.data(Qt.ToolTipRole).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.time_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignRight), time);

        # Draw screenname
        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.user_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignLeft), screenname);

        # Draw line
        painter.setPen(self.separator_color)
        x1,y1,x2,y2 = option.rect.getCoords()
        painter.drawLine(x1,y2,x2,y2) 

        painter.restore()

class CoolGrayCustomDelegate(QStyledItemDelegate):
    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''
        QStyledItemDelegate.__init__(self, parent)
        self.show_avatar = True
        self.show_screenname = True
        self.show_timestamp = True

        self.user_color = QColor('#3399cc')
        self.time_color = QColor('#94a1a7')
        self.bg_color = QColor('#4a5153')
        self.bg_alternate_color = QColor('#444b4d')
        self.text_color = QColor('#FFFFFF')
        self.separator_color = QColor('#333536')
                
        self.fm = None
        
        self.normFont = None
        self.miniFont = None

    def sizeHint (self, option, index):
        '''Custom size calculation of our items'''
        size = QStyledItemDelegate.sizeHint(self, option, index)
        tweet = index.data(Qt.DisplayRole).toString()
        #One time is enought sizeHint need to be fast
        if self.fm == None:
            self.fm = QFontMetrics(option.font)
        height = self.fm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet).height()
        if height<16:
            height=16        
        return QSize(size.width(), height+44)
        

    def paint(self, painter, option, index):
        '''Paint our tweet'''
        self.fm = QFontMetrics(option.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole).toString()
        
        #Instantiate font only one time !
        if self.normFont == None:
            self.normFont = QFont(option.font)
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)            
        
        painter.save()
        
        # Draw alternate ?
        if (index.row()%2)==0:
            painter.fillRect(option.rect, self.bg_color)
        else:
            painter.fillRect(option.rect, self.bg_alternate_color)            

        # highlight selected items
        if option.state & QStyle.State_Selected: 
            painter.fillRect(option.rect, option.palette.highlight());
                    
        # Draw icon
        if self.show_avatar:
            icon = index.data(Qt.DecorationRole).toPyObject();
            if icon != None:
                x1,y1,x2,y2 = option.rect.getCoords()
                painter.drawPixmap(x1+10,y1+10,50,50,icon)
                                                
        # Draw tweet
        painter.setPen(self.text_color)
        new_rect = painter.drawText(option.rect.adjusted(int(self.show_avatar)*70,5,-4,0),  int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet); 
                
        # Draw Timeline
        if self.show_timestamp:
            time = index.data(Qt.ToolTipRole).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.time_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignRight), time);

        # Draw screenname
        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE).toString();
            painter.setFont(self.miniFont)
            painter.setPen(self.user_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignLeft), screenname);

        # Draw line
        painter.setPen(self.separator_color)
        x1,y1,x2,y2 = option.rect.getCoords()
        painter.drawLine(x1,y2,x2,y2) 

        painter.restore()
        
class KhweetsView(QListView):
    ''' Model View '''
    def __init__(self,parent=None):
        QListView.__init__(self,parent)
        #self.setIconSize(QSize(128, 128))
        #self.setStyleSheet('QListView { background-color: rgb(241, 245, 250); border: 0; }')
        self.setWordWrap(True)
        self.refreshCustomDelegate()
        self.setEditTriggers(QAbstractItemView.SelectedClicked)
        self.setSpacing(0)
        self.setUniformItemSizes(False)
        self.setResizeMode(QListView.Adjust)
        #self.setViewMode(QListView.ListMode)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
#        self.overShootMove = False
        #self.setWrapping(True)
        #self.setFlow(QListView.TopToBottom)
#        self.setAlternatingRowColors(True)  
#        self.setAlternatingRowColors(True)

    #Work around for qt4.6 scrollarea bug which didn't work
#    def event(self,anEvent):        
#        if anEvent.type() == QEvent.Move:
#            if not self.overShootMove:
#                self.overShootMove = True
#                r = QAbstractScrollArea.event(self,anEvent)
#                self.overShootMove = False
#                return r
#        else:
#            return QListView.event(self,anEvent)
#            
#    def setScrollPosition(self,point1,point2):
#        self.overShootMove = True
#        r = QAbstractScrollArea.setScrollPosition(self,point1,point2)
#        self.overShootMove = False
#        return r
        
    def refreshCustomDelegate(self):
        theme = self.parent().settings.value('theme')
        if theme == KhweeteurPref.WHITETHEME:
            self.custom_delegate = WhiteCustomDelegate(self)
        elif theme == KhweeteurPref.DEFAULTTHEME:
            self.custom_delegate = DefaultCustomDelegate(self)
        elif theme == KhweeteurPref.COOLWHITETHEME:
            self.custom_delegate = CoolWhiteCustomDelegate(self)
        elif theme == KhweeteurPref.COOLGRAYTHEME:
            self.custom_delegate = CoolGrayCustomDelegate(self)
        else:
            self.custom_delegate = DefaultCustomDelegate(self)
        self.setItemDelegate(self.custom_delegate)


class KhweeteurAbout(QMainWindow):
    '''About Window'''
    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)
        self.parent = parent

        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur About")

        aboutScrollArea = QScrollArea(self)
        aboutScrollArea.setWidgetResizable(True)
        awidget = QWidget(aboutScrollArea)
        awidget.setMinimumSize(480,1000)
        awidget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        aboutScrollArea.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        #Kinetic scroller is available on Maemo and should be on meego
        try:
            scroller = aboutScrollArea.property("kineticScroller").toPyObject()
            scroller.setEnabled(True)
        except:
            pass

        aboutLayout = QVBoxLayout(awidget)

        aboutIcon = QLabel()
        aboutIcon.setPixmap(QIcon.fromTheme('khweeteur').pixmap(128,128))
        aboutIcon.setAlignment( Qt.AlignCenter or Qt.AlignHCenter )
        aboutIcon.resize(128,128)
        aboutLayout.addWidget(aboutIcon)

        aboutLabel = QLabel('''<center><b>Khweeteur</b> %s                                   
                                   <br><br>A Simple twitter client with follower status, reply,
                                   <br>and direct message in a unified view
                                   <br><br>Licenced under GPLv3
                                   <br>By Beno&icirc;t HERVIER (Khertan)
                                   <br><br><b>Khweeteur try to be simple and fast identi.ca and twitter client,</b>
                                   <br>your timeline, reply and direct message arer displayed in a unified view.
                                   <br><br><b>To reply, retweet, open a url, follow/unfollow an account :</b>
                                   <br>double click on a status and choose the action in the dialog which appear.
                                   <br><br>To activate automatic update set a refresh interval different of zero.
                                   <br><br>Use preferences from dialog to set your account with oauth,
                                   <br>and to display or not timestamp, username or avatar.                                   
                                   <br><br><b>Thanks to :</b>
                                   <br>ddoodie on #pyqt                                   
                                   <br>xnt14 on #maemo
                                   <br>trebormints on twitter
                                   <br>moubaildotcom on twitter
                                   <br>teotwaki on twitter
                                   </center>''' % __version__)
        aboutLayout.addWidget(aboutLabel)
        self.bugtracker_button = QPushButton('BugTracker')
        self.bugtracker_button.clicked.connect(self.open_bugtracker)
        self.website_button = QPushButton('Website')
        self.website_button.clicked.connect(self.open_website)
        awidget2 = QWidget()
        buttonLayout = QHBoxLayout(awidget2)        
        buttonLayout.addWidget(self.bugtracker_button)
        buttonLayout.addWidget(self.website_button)
        aboutLayout.addWidget(awidget2)
        
        awidget.setLayout(aboutLayout)
        aboutScrollArea.setWidget(awidget)
        self.setCentralWidget(aboutScrollArea)
        self.show()        
        
    def open_website(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur'))
    def open_bugtracker(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur/bugs'))
        
            
class KhweetAction(QDialog):
    def __init__(self,parent = None,title = ''):
        QDialog.__init__(self,parent)
        #if name == None:
        self.setWindowTitle('Khweeteur : '+title)
        _layout = QGridLayout(self)
        _layout.setSpacing(6)
        _layout.setMargin(11)
        
        self.reply = QPushButton('Reply')
        self.reply.setText(self.tr('&Reply'))
        _layout.addWidget(self.reply,0,0)
        
        self.retweet = QPushButton('Retweet')
        self.retweet.setText(self.tr('&Retweet'))
        _layout.addWidget(self.retweet,0,1)

        self.destroy_tweet = QPushButton('Destroy')
        self.destroy_tweet.setText(self.tr('&Destroy'))
        _layout.addWidget(self.destroy_tweet,1,1)

        self.openurl = QPushButton('Open URL')
        self.openurl.setText(self.tr('&Open URL'))
        _layout.addWidget(self.openurl,1,0)
        
        self.follow = QPushButton('Follow')
        self.follow.setText(self.tr('&Follow'))
        _layout.addWidget(self.follow,0,2)

        self.unfollow = QPushButton('Unfollow')
        self.unfollow.setText(self.tr('&Unfollow'))
        _layout.addWidget(self.unfollow,1,2)        
        
class KhweeteurPref(QMainWindow):
    DEFAULTTHEME = 'Default'
    WHITETHEME = 'White'
    COOLWHITETHEME = 'CoolWhite'
    COOLGRAYTHEME = 'CoolGray'
    THEMES = [DEFAULTTHEME, WHITETHEME, COOLWHITETHEME, COOLGRAYTHEME]

    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)
        self.parent = parent

        if isMAEMO:
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
        self.useBitly_value.setCheckState(self.settings.value("useBitly").toInt()[0])
        if not self.settings.value("theme"):
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        if not self.settings.value("theme").toString() in self.THEMES:
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)

        self.theme_value.setCurrentIndex(self.THEMES.index(self.settings.value("theme").toString()))

    def savePrefs(self):
        self.settings.setValue('refreshInterval',self.refresh_value.value())
        self.settings.setValue('displayUser',self.displayUser_value.checkState())
        self.settings.setValue('useNotification',self.useNotification_value.checkState())
        self.settings.setValue('useSerialization',self.useSerialization_value.checkState())
        self.settings.setValue('displayAvatar',self.displayAvatar_value.checkState())
        self.settings.setValue('displayTimestamp',self.displayTimestamp_value.checkState())
        self.settings.setValue('useBitly',self.useBitly_value.checkState())
        self.settings.setValue('theme',self.theme_value.currentText())
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
            if not self.parent.nw.device_has_networking:
                self.parent.nw.request_connection_with_tmp_callback(self.request_twitter_access_or_clear)
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
                        if isMAEMO:
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
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('twitter_access_token_key',QString(access_token['oauth_token']))
                            self.settings.setValue('twitter_access_token_secret',QString(access_token['oauth_token_secret']))
                            self.settings.setValue('twitter_access_token',True)
                            self.twitter_value.setText('Clear Twitter Auth')
                            KhweeteurNotification().info('Khweeteur is now authorized to connect')
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)
                    
    def request_identica_access_or_clear(self):

        if self.settings.value('identica_access_token').toBool():
            self.settings.setValue('identica_access_token_key',QString())
            self.settings.setValue('identica_access_token_secret',QString())
            self.settings.setValue('identica_access_token',False)
            self.identica_value.setText('Auth on Identi.ca')
        else:
            if not self.parent.nw.device_has_networking:
                self.parent.nw.request_connection_with_tmp_callback(self.request_identica_access_or_clear)
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
                        if isMAEMO:
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
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('identica_access_token_key',QString(access_token['oauth_token']))
                            self.settings.setValue('identica_access_token_secret',QString(access_token['oauth_token_secret']))
                            self.settings.setValue('identica_access_token',True)
                            self.identica_value.setText('Clear Identi.ca Auth')
                            KhweeteurNotification().info('Khweeteur is now authorized to connect')
                        if isMAEMO:                        
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
        #Available on maemo but should be too on Meego
        try:
            scroller = self.scrollArea.property("kineticScroller").toPyObject()
            scroller.setEnabled(True)
        except:
            pass
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

        self.useBitly_value = QCheckBox('Use Bit.ly')
        self._main_layout.addWidget(self.useBitly_value,8,1)

        self._main_layout.addWidget(QLabel('Theme :'),9,0)
        self.theme_value = QComboBox()
        self._main_layout.addWidget(self.theme_value,9,1)
        for theme in self.THEMES:
            self.theme_value.addItem(theme)
        
        self.aWidget.setLayout(self._main_layout)
        self.setCentralWidget(self.scrollArea)
        
class KhweeteurWin(QMainWindow):

    def __init__(self, parent=None, search_keyword=None):
        QMainWindow.__init__(self,None)
        self.parent = parent

        self.search_keyword = search_keyword

        #crappy trick to avoid search win to be garbage collected
        self.search_win = []

        if isMAEMO:            
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
            
        QTimer.singleShot(200, self.justAfterInit)

    def closeEvent(self,widget,*args):
        for win in self.search_win:
            win.close()
        
    def justAfterInit(self):
        from nwmanager import NetworkManager

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

    def timedUnserialize(self):
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
        self.tweetsModel.unSerialize()
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def setupMain(self):

        self.tweetsView = KhweetsView(self)
        self.tweetsView.custom_delegate.show_screenname = self.settings.value("displayUser").toBool()
        self.tweetsView.custom_delegate.show_timestamp = self.settings.value("displayTimestamp").toBool()
        self.tweetsView.custom_delegate.show_avatar = self.settings.value("displayAvatar").toBool()

        self.connect(self.tweetsView,SIGNAL('doubleClicked(const QModelIndex&)'),self.tweet_do_ask_action)
        self.tweetsModel = KhweetsModel([],self.search_keyword)
        self.tweetsView.setModel(self.tweetsModel)
        self.setCentralWidget(self.tweetsView)

        self.toolbar = self.addToolBar('Toolbar')

        self.tb_update = QAction(QIcon.fromTheme("general_refresh"),'Update', self)
        self.connect(self.tb_update, SIGNAL('triggered()'), self.request_refresh)
        self.toolbar.addAction(self.tb_update)
        
        self.tb_text = QLineEdit()
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.tb_text.enabledChange(True)
        self.toolbar.addWidget(self.tb_text)

        self.tb_charCounter = QLabel('140')
        self.toolbar.addWidget(self.tb_charCounter)
        self.connect(self.tb_text, SIGNAL('textChanged(const QString&)'), self.countChar)

        self.tb_tweet = QAction(QIcon.fromTheme('khweeteur'),'Tweet', self)
        self.connect(self.tb_tweet, SIGNAL('triggered()'), self.tweet)
        self.toolbar.addAction(self.tb_tweet)

        QTimer.singleShot(200, self.timedUnserialize)

    def tweet_do_ask_action(self):
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel._items[index.row()][2]            
        self.tweetActionDialog = KhweetAction(self, user)
        self.connect(self.tweetActionDialog.reply,SIGNAL('clicked()'),self.reply)
        self.connect(self.tweetActionDialog.openurl,SIGNAL('clicked()'),self.open_url)
        self.connect(self.tweetActionDialog.retweet,SIGNAL('clicked()'),self.retweet)
        self.connect(self.tweetActionDialog.follow,SIGNAL('clicked()'),self.follow)
        self.connect(self.tweetActionDialog.unfollow,SIGNAL('clicked()'),self.unfollow)
        self.connect(self.tweetActionDialog.destroy_tweet,SIGNAL('clicked()'),self.destroy_tweet)
        self.tweetActionDialog.exec_()
        
    def countChar(self,text):
        self.tb_charCounter.setText(unicode(140-len(text)))

    def reply(self):
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel._items[index.row()][2]
            self.tb_text_replyid = self.tweetsModel._items[index.row()][1]
            self.tb_text_replytext = '@'+user+' '
            self.tb_text.setText('@'+user+' ')

    def open_url(self):
        import re
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            status = self.tweetsModel._items[index.row()][3]
            try:
                urls = re.findall("(?P<url>https?://[^\s]+)", status)
                for url in urls:
                    QDesktopServices.openUrl(QUrl(url))
            except StandardError,e:
                print e
                
    def follow(self):       
        self.tweetActionDialog.accept()
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.follow)
        else:
            for index in self.tweetsView.selectedIndexes():
                if ((QMessageBox.question(self,
                           "Khweeteur",
                           "Follow : %s ?" % self.tweetsModel._items[index.row()][2],
                           QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                    user_screenname = self.tweetsModel._items[index.row()][2]
                    #print 'DEBUG Follow:',user_screenname
                    try:
                        if self.settings.value("twitter_access_token_key").toString()!='':     
                            api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                              access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                            api.SetUserAgent('Khweeteur/%s' % (__version__))
                            api.CreateFriendship(user_screenname)
                            self.notifications.info('You are now following %s on Twitter' % (user_screenname))
                    except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn('Add %s to friendship failed on Twitter : %s' %(user_screenname,e.message))
                            print e.message
                        else:
                            self.notifications.warn('Add %s to friendship failed on Twitter : %s' %(user_screenname,str(e)))
                            print e                     
                    try:
                        if self.settings.value("identica_access_token_key").toString()!='': 
                            api = twitter.Api(base_url='http://identi.ca/api/',username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                              password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
                            api.SetUserAgent('Khweeteur/%s' % (__version__))    
                            api.CreateFriendship(user_screenname)
                            self.notifications.info('You are now following %s on Identi.ca' % (user_screenname))
                    except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn('Add %s to friendship failed on Identi.ca : %s' %(user_screenname,e.message))
                            print e.message
                        else:
                            self.notifications.warn('Add %s to friendship failed on Identi.ca : %s' %(user_screenname,str(e)))
                            print e                                   

    def unfollow(self):  
        self.tweetActionDialog.accept()
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.unfollow)
        else:
            for index in self.tweetsView.selectedIndexes():
                if ((QMessageBox.question(self,
                           "Khweeteur",
                           "Follow : %s ?" % self.tweetsModel._items[index.row()][2],
                           QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                    user_screenname = self.tweetsModel._items[index.row()][2]
                    #print 'DEBUG Follow:',user_screenname
                    try:
                        if self.settings.value("twitter_access_token_key").toString()!='':     
                            api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                              access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                            api.SetUserAgent('Khweeteur/%s' % (__version__))
                            api.DestroyFriendship(user_screenname)
                            self.notifications.info('You didn\'t follow %s anymore on Twitter' % (user_screenname))
                    except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn('Remove %s to friendship failed on Twitter : %s' %(user_screenname,e.message))
                            print e.message
                        else:
                            self.notifications.warn('Remove %s to friendship failed on Twitter : %s' %(user_screenname,str(e)))
                            print e                     
                    try:
                        if self.settings.value("identica_access_token_key").toString()!='': 
                            api = twitter.Api(base_url='http://identi.ca/api/',username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                              password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
                            api.SetUserAgent('Khweeteur/%s' % (__version__))    
                            api.DestroyFriendship(user_screenname)
                            self.notifications.info('You didn\'t follow %s anymore on Identi.ca' % (user_screenname))
                    except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn('Remove %s to friendship failed on Identi.ca : %s' %(user_screenname,e.message))
                            print e.message
                        else:
                            self.notifications.warn('Remove %s to friendship failed on Identi.ca : %s' %(user_screenname,str(e)))
                            print e                           
                            
    def retweet(self):
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            if ((QMessageBox.question(self,
                       "Khweeteur",
                       "Retweet this : %s ?" % self.tweetsModel._items[index.row()][3],
                       QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                tweetid = self.tweetsModel._items[index.row()][1]
                #print 'DEBUG Retweet:',tweetid
                try:
                    if self.settings.value("twitter_access_token_key").toString()!='':     
                        api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                          access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                          access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                        api.SetUserAgent('Khweeteur/%s' % (__version__))
                        api.PostRetweet(tweetid)
                        self.notifications.info('Retweet send to Twitter')
                except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
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
                        api.SetUserAgent('Khweeteur/%s' % (__version__))    
                        api.PostRetweet(tweetid)
                        self.notifications.info('Retweet send to Identi.ca')
                except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                    if type(e)==twitter.TwitterError:
                        self.notifications.warn('Retweet to identi.ca failed : '+(e.message))
                        print e.message
                    else:
                        self.notifications.warn('Retweet to identi.ca failed : '+str(e))
                        print e                 

    def destroy_tweet(self):
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            if ((QMessageBox.question(self,
                       "Khweeteur",
                       "Destroy this : %s ?" % self.tweetsModel._items[index.row()][3],
                       QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                tweetid = self.tweetsModel._items[index.row()][1]
                #print 'DEBUG Retweet:',tweetid
                try:
                    if self.settings.value("twitter_access_token_key").toString()!='':     
                        api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                          access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                          access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                        api.SetUserAgent('Khweeteur/%s' % (__version__))
                        api.DestroyStatus(tweetid)
                        self.tweetsModel.destroyStatus(index)
                        self.notifications.info('Status destroyed on Twitter')
                except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                    if type(e)==twitter.TwitterError:
                        self.notifications.warn('Destroy status from twitter failed : '+(e.message))
                        print e.message
                    else:
                        self.notifications.warn('Destroy status from twitter failed : '+str(e))
                        print e                     
                try:
                    if self.settings.value("identica_access_token_key").toString()!='': 
                        api = twitter.Api(base_url='http://identi.ca/api/',username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                          password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                          access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                          access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
                        api.SetUserAgent('Khweeteur/%s' % (__version__))    
                        api.DestroyStatus(tweetid)
                        self.tweetsModel.destroyStatus(index)
                        self.notifications.info('Status destroyed on Identi.ca')
                except (twitter.TwitterError,StandardError,urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                    if type(e)==twitter.TwitterError:
                        self.notifications.warn('Destroy status from identi.ca failed : '+(e.message))
                        print e.message
                    else:
                        self.notifications.warn('Destroy status from identi.ca failed : '+str(e))
                        print e                 

    def tweetSent(self):
        self.tb_text.setText('')
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.request_refresh() #Feature Request : 201

    def tweetSentFinished(self):
        self.tb_text.setEnabled(True)
        self.tb_tweet.setEnabled(True)

    def tweet(self):
        if not self.nw.device_has_networking:
            self.nw.request_connection_with_tmp_callback(self.tweet)
        else:
            self.tb_text.setDisabled(True)
            self.tb_tweet.setDisabled(True)
            self.tweetAction = KhweeteurActionWorker(self,'tweet',unicode(self.tb_text.text()).encode('utf-8'),self.tb_text_replyid,self.tb_text_replytext)
            self.connect(self.tweetAction, SIGNAL("tweetSent()"), self.tweetSent)
            self.connect(self.tweetAction, SIGNAL("finished()"), self.tweetSentFinished)
            self.notifications.connect(self.tweetAction, SIGNAL('info(PyQt_PyObject)'), self.notifications.info)
            self.notifications.connect(self.tweetAction, SIGNAL('warn(PyQt_PyObject)'), self.notifications.warn)
            self.tweetAction.start()

    def refreshEnded(self):
        counter=self.tweetsModel.getNew()
        
        if (counter>0) and (self.settings.value('useNotification').toBool()) and not (self.isActiveWindow()):
            if self.search_keyword == None:
                self.notifications.notify('Khweeteur',str(counter)+' new tweet(s)',count=counter)
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def do_refresh_now(self):
        #print type(self.settings.value('useNotification').toString()),self.settings.value('useNotification').toString()
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
        self.worker = KhweeteurWorker(self,search_keyword=self.search_keyword)
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
        self.request_refresh()

    def refresh_timeline(self):
        if self.worker == None:
            self.do_refresh_now()
        elif self.worker.isFinished() == True:
            self.do_refresh_now()
 
    def restartTimer(self):
        self.tweetsView.refreshCustomDelegate()
        self.tweetsView.custom_delegate.show_screenname = self.settings.value("displayUser").toBool()
        self.tweetsView.custom_delegate.show_timestamp = self.settings.value("displayTimestamp").toBool()
        self.tweetsView.custom_delegate.show_avatar = self.settings.value("displayAvatar").toBool()
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
#        fileMenu.addAction(self.tr("&Update"), self.request_refresh,
#                QKeySequence(self.tr("Ctrl+R", "Update")))
        fileMenu.addAction(self.tr("&Search"), self.open_search,
                QKeySequence(self.tr("Ctrl+S", "Search")))
#        fileMenu.addAction(self.tr("&Retweet"), self.retweet,
#                QKeySequence(self.tr("Ctrl+T", "Retweet")))
                
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
        elif (type(keywords)==QStringList):
            index = keywords.indexOf(self.search_keyword)
            if index>=0:
                keywords.removeAt(index)
        else:
            keywords.remove(self.search_keyword)
        self.settings.setValue('savedSearch',QVariant(keywords))
        self.close()
                                
    def save_search(self):
        keywords = self.settings.value('savedSearch').toPyObject()
        if (keywords == None):
            keywords = []
        elif (type(keywords)==QString):
            keywords = [keywords,]
        keywords.append(self.search_keyword)
        self.settings.setValue('savedSearch',QVariant(keywords))
                                
    def open_saved_search(self):
        keywords = self.settings.value('savedSearch').toPyObject()
        if (type(keywords)==QString):
            keywords = [keywords,]

        if (keywords != None):
            for keyword in keywords:
                self.do_search(keyword)
        self.activateWindow()
            
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

        install_excepthook(self.applicationName(),self.version)

        dbus.mainloop.qt.DBusQtMainLoop(set_as_default=True)

        session_bus = dbus.SessionBus()
        name = dbus.service.BusName("net.khertan.khweeteur", session_bus)
        self.dbus_object = KhweeteurDBus(session_bus, '/net/khertan/khweeteur')        
        self.run()
        
    def crash_report(self):
        if os.path.isfile(os.path.join(CACHE_PATH,'crash_report')):
            import urllib2
            import urllib
            if ((QMessageBox.question(None,
                "Khweeteur Crash Report",
                "An error occur on khweeteur in the previous launch. Report this bug on the bug tracker ?",
                QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                url = 'http://khertan.net/report.php' # write ur URL here
                try:
                    filename = os.path.join(CACHE_PATH,'crash_report')
                    output = open(filename, 'rb')
                    error = pickle.load(output)
                    output.close()

                    values = {
                          'project' : 'khweeteur',
                          'version': __version__,
                          'description':error,
                      }    
        
                    data = urllib.urlencode(values)
                    req = urllib2.Request(url, data)
                    response = urllib2.urlopen(req)
                    the_page = response.read()
                except Exception, detail:
                    QMessageBox.question(None,
                    "Khweeteur Crash Report",
                    "An error occur during the report : %s" % detail,
                    QMessageBox.Close)
                    return False

                if 'Your report have been successfully stored' in the_page:
                    QMessageBox.question(None,
                    "Khweeteur Crash Report",
                    "%s" % the_page,
                    QMessageBox.Close)
                    return True
                else:
                    QMessageBox.question(None,
                    "Khweeteur Crash Report",
                    QMessageBox.Close)
                    return False
            try:
                os.remove(os.path.join(CACHE_PATH,'crash_report'))
            except:
                pass
                
    def run(self):
        self.win = KhweeteurWin()
        self.dbus_object.attach_win(self.win)
        self.crash_report()
        self.win.show()
        
if __name__ == '__main__':
    sys.exit(Khweeteur().exec_())

