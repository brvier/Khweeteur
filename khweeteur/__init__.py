#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4'''
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4.QtGui import *
from PyQt4.QtCore import *
#from PySide.QtCore import *
#from PySide.QtGui import *

try:
    from PyQt4.QtMobility.QtLocation import *
#    from PySide.QtMobility.QtLocation import *
    noQtLocation = False
except:
    noQtLocation = True

try:
    from PyQt4.QtMaemo5 import *
#    from PySide.QtMaemo5 import *
    isMAEMO = True
except:
    isMAEMO = False

import twitter
import sys
import os.path
from urllib import urlretrieve
import datetime
import time
try:
    import dbus
    import dbus.service
    from dbus.mainloop.qt import DBusQtMainLoop
    from dbusobj import KhweeteurDBus
    noDBUS = False
except:
    noDBUS = True
import pickle
try:
    from PIL import Image
except:
    import Image
import re
import urllib2
import socket
import glob

__version__ = '0.0.48'
    
def write_report(error):
    '''Function to write error to a report file'''
    filename = os.path.join(CACHE_PATH, 'crash_report')
    output = open(filename, 'wb')
    pickle.dump(error, output)
    output.close()

def write_log(log):
    filename = os.path.join('/tmp/khweeteur_log')
    output = open(filename, 'a')
    output.write(str(datetime.datetime.now())+':'+str(log)+'\n')
    output.close()

#Here is the installation of the hook. Each time a untrapped/unmanaged exception will
#happen my_excepthook will be called.
def install_excepthook():
    '''Install an excepthook called at each unexcepted error'''

    def my_excepthook(exctype, value, tb):
        '''Method which replace the native excepthook'''
        #traceback give us all the errors information message like the method, file line ... everything like
        #we have in the python interpreter
        import traceback
        trace_s = ''.join(traceback.format_exception(exctype, value, tb))
        print 'Except hook called : %s' % (trace_s)
        formatted_text = "%s Version %s\nTrace : %s" % ('Khweeteur', __version__, trace_s)
        write_report(formatted_text)

    sys.excepthook = my_excepthook

AVATAR_CACHE_FOLDER = os.path.join(os.path.expanduser("~"),  '.khweeteur', 'cache')
CACHE_PATH = os.path.join(os.path.expanduser("~"), '.khweeteur')

#Close your eyes ... it s a secret !
KHWEETEUR_TWITTER_CONSUMER_KEY = 'uhgjkoA2lggG4Rh0ggUeQ'
KHWEETEUR_TWITTER_CONSUMER_SECRET = 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU'
KHWEETEUR_IDENTICA_CONSUMER_KEY = 'c7e86efd4cb951871200440ad1774413'
KHWEETEUR_IDENTICA_CONSUMER_SECRET = '236fa46bf3f65fabdb1fd34d63c26d28'
KHWEETEUR_STATUSNET_CONSUMER_KEY = '84e768bba2b6625f459a9a19f5d57bd1'
KHWEETEUR_STATUSNET_CONSUMER_SECRET = 'fbc51241e2ab12e526f89c26c6ca5837'
SCREENNAMEROLE = 20
REPLYTOSCREENNAMEROLE = 21
REPLYTEXTROLE = 22
IDROLE = 23
#....

class KhweeteurNotification(QObject):
    '''Notification class interface'''
    def __init__(self):
        QObject.__init__(self)
        if not noDBUS:
            self.m_bus = dbus.SystemBus()
            self.m_notify = self.m_bus.get_object('org.freedesktop.Notifications',
                                                  '/org/freedesktop/Notifications')
            self.iface = dbus.Interface(self.m_notify, 'org.freedesktop.Notifications')
            self.m_id = 0

    def warn(self, message):
        '''Display an Hildon banner'''
        if not noDBUS:
            if isMAEMO:
                try:
                    self.iface.SystemNoteDialog(message,0, 'Nothing')
                except:
                    pass

    def info(self, message):
        '''Display an information banner'''
        if not noDBUS:
            if isMAEMO:
                try:
                    self.iface.SystemNoteInfoprint('Khweeteur : '+message)
                except:
                    pass

    def notify(self,title, message,category='im.received', icon='khweeteur',count=1):
        '''Create a notification in the style of email one'''
        if not noDBUS:
            try:
                self.m_id = self.iface.Notify('Khweeteur',
                                  self.m_id,
                                  icon,
                                  title,
                                  message,
                                  ['default','call'],
                                  {'category':category,
                                  'desktop-entry':'khweeteur',
                                  'dbus-callback-default':'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show_now',
                                  'count':count,
                                  'amount':count},
                                  -1
                                  )
            except:
                pass


class KhweeteurActionWorker(QThread):
    '''ActionWorker : Post tweet in background'''
    def __init__(self, parent = None, action=None, data=None, data2=None, data3=None, data4=None, data5=None):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        self.action = action
        self.data = data
        self.tb_text_replyid = data2
        self.tb_text_replytext = data3
        self.tb_text_replysource = data4
        self.geolocation = data5

    def run(self):
        '''Run the background thread'''
        if self.action=='tweet':
            self.tweet()
        elif self.action=='retweet':
            self.retweet()

    def tweet(self):
        '''Post a tweet'''
        try:
            status_text = self.data

            if int(self.settings.value("useBitly"))==2:
                urls = re.findall("(?P<url>https?://[^\s]+)", status_text)
                if len(urls)>0:
                    import bitly
                    a=bitly.Api(login="pythonbitly", apikey="R_06871db6b7fd31a4242709acaf1b6648")

                for url in urls:
                    try:
                        short_url=a.shorten(url)
                        status_text = status_text.replace(url, short_url)
                    except:
                        pass

            if not status_text.startswith(self.tb_text_replytext):
                self.tb_text_replyid = 0
                self.tb_text_reply = ''
                self.tb_text_replysource =''

            if self.geolocation:
                latitude,longitude = self.geolocation
            else:
                latitude,longitude = (None,None)
                
            if ('twitter' in self.tb_text_replysource) or (self.tb_text_replyid == 0):
                if self.settings.value("twitter_access_token_key")!=None:
                    api = twitter.Api(
                                      username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                      access_token_key=str(self.settings.value("twitter_access_token_key")),
                                      access_token_secret=str(self.settings.value("twitter_access_token_secret")))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if int(self.settings.value('useSerialization'))==2:
                        status = api.PostSerializedUpdates(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    else:
                        status = api.PostUpdate(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    self.emit(SIGNAL("info(PyQt_PyObject)"), 'Tweet sent to Twitter')

            if ('http://identi.ca/api/' == self.tb_text_replysource) or (self.tb_text_replyid == 0):
                if self.settings.value("identica_access_token_key")!=None:
                    api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                      password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                      access_token_key=str(self.settings.value("identica_access_token_key")),
                                      access_token_secret=str(self.settings.value("identica_access_token_secret")))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if int(self.settings.value('useSerialization'))==2:
                        status = api.PostSerializedUpdates(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    else:
                        status = api.PostUpdate(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    self.emit(SIGNAL("info(PyQt_PyObject)"), 'Tweet sent to Identica')

            if ('http://khertan.status.net' == self.tb_text_replysource) or (self.tb_text_replyid == 0):
                if self.settings.value("statusnet_access_token_key")!=None:
                    api = twitter.Api(base_url='http://khertan.status.net/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                      password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                      access_token_key=str(self.settings.value("statusnet_access_token_key")),
                                      access_token_secret=str(self.settings.value("statutsnet_access_token_secret")))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if int(self.settings.value('useSerialization'))==2:
                        status = api.PostSerializedUpdates(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    else:
                        status = api.PostUpdate(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    self.emit(SIGNAL("info(PyQt_PyObject)"), 'Tweet sent to Identica')

            self.emit(SIGNAL("tweetSent()"))

        except twitter.TwitterError,e:
            self.emit(SIGNAL("warn(PyQt_PyObject)"),e.message)
            print e.message
        except:
            self.emit(SIGNAL("warn(PyQt_PyObject)"), 'A network error occur')
            print 'A network error occur'            
            import traceback
            traceback.print_exc()


class KhweeteurRefreshWorker(QThread):
    ''' Common Abstract class for the refresh thread '''

    #Signal
    errors = pyqtSignal(Exception)
#    errors = Signal(Exception)
    newStatuses = pyqtSignal(list)
#    newStatuses = Signal(list)

    def __init__(self, parent = None, api=None):
        QThread.__init__(self, None)
        self.api = api
        self.settings = QSettings()

    def run(self):
        pass

    def downloadProfilesImage(self, statuses):
        for status in statuses:
            if type(status)!=twitter.DirectMessage:
                cache = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(status.user.profile_image_url.replace('/', '_')))
                if not(os.path.exists(cache)):
                    try:
                        urlretrieve(status.user.profile_image_url, cache)
                        im = Image.open(cache)
                        im = im.resize((50,50))
                        im.save(os.path.splitext(cache)[0]+'.png', 'PNG')
                    except:
                        pass
#                        print 'DownloadProfileImage Error : ',e

    def getRepliesContent(self, api, statuses):
        items = None
        for status in statuses:
            try:
                if not hasattr(status, 'in_reply_to_status_id'):
                    status.in_reply_to_status_text = None
                elif status.in_reply_to_status_id not in (None,''):
                    status.in_reply_to_status_text = ''
                    #Verify in the new statuses
                    for tw in statuses:
                        #Verify in id of the new statuses
                        if status.in_reply_to_status_id == tw.id:
                            status.in_reply_to_status_text = tw.text
                            break
                        #Verify in reply of new statuses
                        if status.in_reply_to_status_id == tw.in_reply_to_status_id:
                            if tw.in_reply_to_status_text not in (None,''):
                                status.in_reply_to_status_text = tw.in_reply_to_status_text
                                break

                    #Verify in all cache
                    #print '1-<api base_url', api.base_url, ':',status.in_reply_to_status_text,':'
                    if (status.in_reply_to_status_text == '') and (status.origin == api.base_url):
                        if items == None:
                            items = []
                            for path in glob.glob(CACHE_PATH+'/*.cache'):
                                filename = os.path.join(path)
                                try:
                                    pkl_file = open(filename, 'rb')
                                    items_ = pickle.load(pkl_file)
                                    pkl_file.close()
                                    items.extend(items_)
                                except StandardError,e:
                                    pass #print 'getRepliesContent:',e
                        for item in items:
                            if item[1] == status.in_reply_to_status_id:
                                status.in_reply_to_status_text = item[3]
                                break
                            if item[7] == status.in_reply_to_status_id:
                                if item[7] not in (None,''):
                                    status.in_reply_to_status_text = item[7]
                                    break

                    #Else get the tweet from the api
                    #print '2-<api base_url', api.base_url, '==',status.origin,':',status.in_reply_to_status_text,':'
                    if (status.in_reply_to_status_text == '') and (status.origin == api.base_url):
                        #in_reply_to_status = api.GetStatus(status.in_reply_to_status_id)
#                        print 'Get Status ',status.in_reply_to_status_id,':',status.origin
                        try:
                            status.in_reply_to_status_text = api.GetStatus(status.in_reply_to_status_id).text
                        except:
                            pass
#                            import traceback
#                            traceback.print_exc()
#                    print status.in_reply_to_status_text
                else:
                    status.in_reply_to_status_text = None
            except:
                pass
#                import traceback
#                traceback.print_exc()

    def applyOrigin(self, api, statuses):
        for status in statuses:
            status.origin = api.base_url

class KhweeteurHomeTimelineWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):
        #Get Home TimeLine
        try:
            statuses = self.api.GetFriendsTimeline(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetFriendsTimeline'), retweets=True)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses)>0:
                self.newStatuses.emit(statuses)
                self.settings.setValue('last_id/'+self.api.base_url+'_GetFriendsTimeline', statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
            print e
        except:
            self.errors.emit(StandardError('A network error occurs'))
#            import traceback
#            traceback.print_exc()

class KhweeteurRetweetedByMeWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)
    def run(self):
        #Get Retweeted by me
        try:
            statuses = self.api.GetRetweetedByMe(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetRetweetedByMe_last_id'))
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses)>0:
                self.newStatuses.emit(statuses)
                self.settings.setValue('last_id/'+self.api.base_url+'_GetRetweetedByMe', statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError('A network error occurs'))
#            import traceback
#            traceback.print_exc()

class KhweeteurRetweetsOfMeWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)
    def run(self):
        #Get Retweeted of me
        try:
            statuses = []
            mystatuses = self.api.GetRetweetsOfMe(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetRetweetsOfMe_last_id'))
            for mystatus in mystatuses:
                statuses.extend(self.api.GetRetweetsForStatus(mystatus.id))
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses)>0:
                self.newStatuses.emit(statuses)
                self.settings.setValue('last_id/'+self.api.base_url+'_GetRetweetsOfMe', statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs')))
#            import traceback
#            traceback.print_exc()


class KhweeteurRepliesWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)
    def run(self):
        #Get Retweeted by me
        try:
            statuses = self.api.GetReplies(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetReplies'))
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses)>0:
                self.newStatuses.emit(statuses)
                self.settings.setValue('last_id/'+self.api.base_url+'_GetReplies', statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs')))
#            import traceback
#            traceback.print_exc()

class KhweeteurDMWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)
    def run(self):
        try:
            statuses = self.api.GetDirectMessages(since_id=self.settings.value('last_id/'+self.api.base_url+'_DirectMessages'))
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses)>0:
                self.newStatuses.emit(statuses)
                self.settings.setValue('last_id/'+self.api.base_url+'_DirectMessages', statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs')))
#            import traceback
#            traceback.print_exc()

class KhweeteurMentionWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)
    def run(self):
        try:
            statuses = self.api.GetMentions(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetMentions'))
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses)>0:
                self.newStatuses.emit(statuses)
                self.settings.setValue('last_id/'+self.api.base_url+'_GetMentions', statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs')))
#            import traceback
#            traceback.print_exc()

class KhweeteurSearchWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None, keywords=None, geocode=None):
        KhweeteurRefreshWorker.__init__(self, None, api)
        self.keywords = keywords
        self.geocode = geocode
    def run(self):
        try:
            if self.geocode:
                statuses = self.api.GetSearch('',geocode=self.geocode)                
            else:
                statuses = self.api.GetSearch(unicode(self.keywords).encode('UTF-8'), since_id=self.settings.value(self.keywords+'/last_id/'+self.api.base_url))
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api,statuses)
            self.getRepliesContent(self.api,statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses)>0:
                self.newStatuses.emit(statuses)
                if not self.geocode:
                    self.settings.setValue(self.keywords+'/last_id/'+self.api.base_url, statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs')))
            import traceback
            traceback.print_exc()

class KhweeteurWorker(QThread):
    ''' Thread to Refresh in background '''
    def __init__(self, parent = None, search_keyword=None, geocode=None):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        self.search_keyword = search_keyword
        self.geocode = geocode

    def run(self):
        self.testCacheFolders()
        if (self.search_keyword==None) and (not self.geocode):
            self.refresh()
        else:
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

    def refresh_search(self):
        self.error = None

        if (self.settings.value("twitter_access_token_key")!=None):
            api = twitter.Api(input_encoding='utf-8', \
                username=KHWEETEUR_TWITTER_CONSUMER_KEY, \
                password=KHWEETEUR_TWITTER_CONSUMER_SECRET, \
                access_token_key=str(self.settings.value("twitter_access_token_key")), \
                access_token_secret=str(self.settings.value("twitter_access_token_secret")))
            api.SetUserAgent('Khweeteur/%s' % (__version__))
            self.refresh_search_worker1 = KhweeteurSearchWorker(self,api,self.search_keyword,self.geocode)
            self.refresh_search_worker1.errors.connect(self.errors)
            self.refresh_search_worker1.newStatuses.connect(self.newStatuses)
            self.refresh_search_worker1.start()


        if (self.settings.value("identica_access_token_key")!=None):
            api2 = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, access_token_key=str(self.settings.value("identica_access_token_key")), access_token_secret=str(self.settings.value("identica_access_token_secret")))
            api2.SetUserAgent('Khweeteur/%s' % (__version__))
            self.refresh_search_worker2 = KhweeteurSearchWorker(self,api2,self.search_keyword,self.geocode)
            self.refresh_search_worker2.errors.connect(self.errors)
            self.refresh_search_worker2.newStatuses.connect(self.newStatuses)
            self.refresh_search_worker2.start()

        if (self.settings.value("twitter_access_token_key")!=None) and (self.settings.value("identica_access_token_key")!=None):
            while (self.refresh_search_worker1.isRunning()==True) or \
                  (self.refresh_search_worker2.isRunning()==True):
                self.sleep(2)
        elif (self.settings.value("twitter_access_token_key")!=None):
            while (self.refresh_search_worker1.isRunning()==True):
                self.sleep(2)
        elif (self.settings.value("identica_access_token_key")!=None):
            while (self.refresh_search_worker2.isRunning()==True):
                self.sleep(2)

        if self.error != None:
            if type(self.error) == twitter.TwitterError:
                print 'Error during twitter refresh : ',self.error.message
                self.emit(SIGNAL("info(PyQt_PyObject)"),self.error.message) #fix bug#404
            else:
                self.emit(SIGNAL("info(PyQt_PyObject)"), self.tr('A network error occur'))
                
    def errors(self,error):
        self.error = error

    def newStatuses(self,list):
        self.emit(SIGNAL("newStatuses(PyQt_PyObject)"), list)

    def refresh_unified(self, api):


        #print 'Ideal number of thread : ',QThread.idealThreadCount()

        refresh_timeline_worker = KhweeteurHomeTimelineWorker(self,api)
        refresh_timeline_worker.errors.connect(self.errors)
        refresh_timeline_worker.newStatuses.connect(self.newStatuses)
        refresh_timeline_worker.start()

        refresh_retweetsofme_worker = KhweeteurRetweetsOfMeWorker(self,api)
        refresh_retweetsofme_worker.errors.connect(self.errors)
        refresh_retweetsofme_worker.newStatuses.connect(self.newStatuses)
        refresh_retweetsofme_worker.start()

        refresh_retweetedbyme_worker = KhweeteurRetweetedByMeWorker(self,api)
        if 'twitter' in api.base_url:
            refresh_retweetedbyme_worker.errors.connect(self.errors)
            refresh_retweetedbyme_worker.newStatuses.connect(self.newStatuses)
            refresh_retweetedbyme_worker.start()

        refresh_replies_worker = KhweeteurRepliesWorker(self,api)
        refresh_replies_worker.errors.connect(self.errors)
        refresh_replies_worker.newStatuses.connect(self.newStatuses)
        refresh_replies_worker.start()

        refresh_dm_worker = KhweeteurDMWorker(self,api)
        refresh_dm_worker.errors.connect(self.errors)
        refresh_dm_worker.newStatuses.connect(self.newStatuses)
        refresh_dm_worker.start()

        refresh_mention_worker = KhweeteurMentionWorker(self,api)
        refresh_mention_worker.errors.connect(self.errors)
        refresh_mention_worker.newStatuses.connect(self.newStatuses)
        refresh_mention_worker.start()

        # while (self.refresh_timeline_worker.isRunning()==True) or \
              # (self.refresh_retweetedbyme_worker.isRunning()==True) or \
              # (self.refresh_replies_worker.isRunning()==True) or \
              # (self.refresh_dm_worker.isRunning()==True) or \
              # (self.refresh_mention_worker.isRunning()==True):
            # self.sleep(2)

        if 'twitter' in api.base_url:
            return [refresh_timeline_worker,
                    refresh_retweetedbyme_worker,
                    refresh_retweetsofme_worker,
                    refresh_replies_worker,
                    refresh_dm_worker,
                    refresh_mention_worker]
        else:
            return [refresh_timeline_worker,
                    refresh_retweetsofme_worker,
                    refresh_replies_worker,
                    refresh_dm_worker,
                    refresh_mention_worker]

    def refresh(self):
        self.error = None
        threads = []

        try:
            if (self.settings.value("twitter_access_token_key")!=None):
                #Login to twitter
                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY, \
                        password=KHWEETEUR_TWITTER_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("twitter_access_token_key")), \
                        access_token_secret=str(self.settings.value("twitter_access_token_secret")))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                threads.extend(self.refresh_unified(api))

        except twitter.TwitterError,e:
            print 'Error during twitter refresh : ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except StandardError, e:
            self.emit(SIGNAL("info(PyQt_PyObject)"), 'A network error occur')
            print e

        try:
            identica_mlist = []
            if (self.settings.value("identica_access_token_key")!=None):
                api = twitter.Api(base_url='http://identi.ca/api/', \
                        username=KHWEETEUR_IDENTICA_CONSUMER_KEY, \
                        password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("identica_access_token_key")), \
                        access_token_secret=str(self.settings.value("identica_access_token_secret")))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                threads.extend(self.refresh_unified(api))
        except twitter.TwitterError,e:
            print 'Error during identi.ca refresh: ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except:
            self.emit(SIGNAL("info(PyQt_PyObject)"), 'A network error occur')

        try:
            if (self.settings.value("statusnet_access_token_key")!=None):
                api = twitter.Api(base_url='http://khertan.status.net/api/', \
                        username=KHWEETEUR_STATUSNET_CONSUMER_KEY, \
                        password=KHWEETEUR_STATUSNET_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("statusnet_access_token_key")), \
                        access_token_secret=str(self.settings.value("statusnet_access_token_secret")))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                threads.extend(self.refresh_unified(api))
        except twitter.TwitterError,e:
            print 'Error during status.net refresh: ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except:
            self.emit(SIGNAL("info(PyQt_PyObject)"), 'A network error occur')

        while any(thread.isRunning()==True for thread in threads):
            self.sleep(2)

        del threads

        if self.error != None:
            if type(self.error) == twitter.TwitterError:
                print 'Error during twitter refresh : ',self.error.message
                self.emit(SIGNAL("info(PyQt_PyObject)"),self.error.message) #fix bug#404
            else:
                self.emit(SIGNAL("info(PyQt_PyObject)"), 'A network error occur')

class KhweetsModel(QAbstractListModel):
    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    def __init__(self, mlist=[],keyword=None):
        QAbstractListModel.__init__(self)
        # Cache the passed data list as a class member.
        self._items = mlist
        self._avatars = {}
        self._new_counter = 0
        self.now = time.time()
        self.khweets_limit = 50
        self.keyword = keyword

    # def flags(self, index):
        # return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled

    def setLimit(self,limit):
        self.khweets_limit = limit
        
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
        if len(self._items)>self.khweets_limit:
            return self.khweets_limit
        else:
            return len(self._items)

    def refreshTimestamp(self):
        self.now = time.time()
        for index, item in enumerate(self._items):
            if index>self.khweets_limit:
                break
            try:
                self._items[index] = (item[0],
                                      item[1],
                                      item[2],
                                      item[3],
                                      item[4],
                                      self.GetRelativeCreatedAt(item[0]),
                                      item[6],
                                      item[7],
                                      item[8])            
            except StandardError,e:
                print e, ':', item

        QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def addStatuses(self,listVariant):
        GetRelativeCreatedAt = self.GetRelativeCreatedAt
        #print 'Debug addstatuses count:',len(listVariant)
        current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())

        for variant in listVariant:
            try:
#                if not variant in self._items:
                if all(item[1]!=variant.id for item in self._items):
                    #self.beginInsertRows(QModelIndex(), 0,1)
                    if variant.created_at_in_seconds >= current_dt:
                        if type(variant) != twitter.DirectMessage:
                            self._items.insert(0,
                                (variant.created_at_in_seconds,
                                 variant.id,
                                 variant.user.screen_name,
                                 variant.text,
                                 variant.user.profile_image_url,
                                 GetRelativeCreatedAt(variant.created_at_in_seconds),
                                 variant.in_reply_to_screen_name,
                                 variant.in_reply_to_status_text,
                                 variant.origin))

                            if variant.user.screen_name!=None:
                                try:
                                    if variant.user.profile_image_url[4]!=None:
                                        path = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(variant.user.profile_image_url.replace('/', '_')))
                                        if not path.endswith('.png'):
                                            path = os.path.splitext(path)[0] + '.png'
                                        pix = QPixmap(path) #.scaled(50,50)
#                                        if pix.isNull():
#                                            print path
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
                                  GetRelativeCreatedAt(variant.created_at_in_seconds),
                                  None,
                                  None,
                                  variant.origin))

                        self._new_counter += 1
#                    self.now = time.time()
                    #self.endInsertRows()
            except StandardError, e:
                print "We shouldn't got this error here :",e

        if len(listVariant)>0:
            self._items.sort()
            self._items.reverse()
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))
            self.serialize()

    def destroyStatus(self, index):
        self._items.pop(index.row())
        QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def isInModel(self,tweet_id):
        return not all(item[1]!=tweet_id for item in self._items)

    def getNewAndReset(self):
        counter = self._new_counter
        self._new_counter = 0
        return counter

    def getNew(self):
        return self._new_counter

    def setData(self, index,variant,role):
        return True

    def setTweets(self, mlist):
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
            KhweeteurNotification().info(self.tr('Wrong cache format. Reinit cache.'))
            write_report("%s Version %s\nWrong cache format : %s\n" % ('Khweeteur', __version__, err))
            print 'Wrong cache format'
        return False

    def serialize(self):
        try:
            if self.keyword==None:
                filename = os.path.join(CACHE_PATH, 'tweets.cache')
            else:
                filename = os.path.normcase(unicode(os.path.join(unicode(CACHE_PATH), unicode(self.keyword.replace('/', '_'))+u'.cache'))).encode('UTF-8')
            output = open(filename, 'wb')
            self._items = self._items[:self.khweets_limit]
            pickle.dump(self._items, output,pickle.HIGHEST_PROTOCOL)
            output.close()

        except StandardError,e:
            KhweeteurNotification().info(self.tr('An error occurs while saving cache : ')+str(e))

    def unSerialize(self):
        try:
            if self.keyword==None:
                filename = os.path.join(CACHE_PATH, 'tweets.cache')
            else:
                filename = os.path.normcase(unicode(os.path.join(unicode(CACHE_PATH), unicode(self.keyword.replace('/', '_'))+u'.cache'))).encode('UTF-8')
            pkl_file = open(filename, 'rb')
            items = pickle.load(pkl_file)
            self.setTweets(items)
            pkl_file.close()
        except StandardError,e:
            print 'unSerialize : ',e
            self.settings = QSettings()
            if self.keyword == None:
                print 'Cache cleared'
                self.settings.remove('last_id')
            else:
                self.settings.remove(self.keyword+'/last_id')

        finally:
            #14 Day limitations
            self._items.sort()
            self._items.reverse()
            current_dt = time.mktime((datetime.datetime.now() - datetime.timedelta(days=14)).timetuple())
            for index, item in enumerate(self._items):
                if item[0] < current_dt:
                    self._items = self._items[:index]
                    break
            self._items = self._items[:self.khweets_limit]
            for item in self._items:
                try:
                    if item[4]!=None:
                        path = os.path.join(AVATAR_CACHE_FOLDER,os.path.basename(item[4].replace('/', '_')))
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
#            self._items = self._items[:(self.khweets_limit-1)]
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._items[index.row()][3]
        elif role == SCREENNAMEROLE:
            return self._items[index.row()][2]
        elif role == IDROLE:
            return self._items[index.row()][1]
        elif role == REPLYTOSCREENNAMEROLE:
            return self._items[index.row()][6]
        elif role == REPLYTEXTROLE:
            if self._items[index.row()][7]!=None:
                return self._items[index.row()][7]
            return ''
        elif role == Qt.ToolTipRole:
            return self._items[index.row()][5]
        elif role == Qt.DecorationRole:
            try:
                return self._avatars[self._items[index.row()][4]]
            except:
                return None
        else:
            return None

    def wantsUpdate(self):
        QObject.emit(self, SIGNAL("layoutChanged()"))



class WhiteCustomDelegate(QStyledItemDelegate):
    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''
        QStyledItemDelegate.__init__(self, parent)

        self.bg_color = QColor('#FFFFFF')
        self.bg_alternate_color = QColor('#dddddd')
        self.user_color = QColor('#7AB4F5')
        self.time_color = QColor('#7AB4F5')
        self.replyto_color = QColor('#7AB4F5')

        self.text_color = QColor('#000000')
        self.separator_color = QColor('#000000')

class DefaultCustomDelegate(QStyledItemDelegate):
    '''Delegate to do custom draw of the items'''
    memoized_size = {}
    memoized_width = {}    
    
    def __init__(self, parent):
        '''Initialization'''
        QStyledItemDelegate.__init__(self, parent)
        self.show_avatar = True
        self.show_screenname = True
        self.show_timestamp = True
        self.show_replyto = True


        self.bg_color = QColor('#000000')
        self.bg_alternate_color = QColor('#333333')
        self.user_color = QColor('#7AB4F5')
        self.time_color = QColor('#7AB4F5')
        self.replyto_color = QColor('#7AB4F5')

        self.text_color = QColor('#FFFFFF')
        self.separator_color = QColor('#000000')

        self.fm = None
        self.minifm = None

        self.normFont = None
        self.miniFont = None

    def sizeHint (self, option, index):
        '''Custom size calculation of our items'''         
        uid = str(index.data(role=IDROLE)) + 'x' + str(option.rect.width())
        try:
            return(self.memoized_size[uid])
        except:
            size = QStyledItemDelegate.sizeHint(self, option, index)
            tweet = index.data(Qt.DisplayRole)

            #One time is enought sizeHint need to be fast
            if not self.fm:
                self.fm = QFontMetrics(option.font)
            height = self.fm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet).height()+40

            if self.show_replyto:
                if (index.data(REPLYTOSCREENNAMEROLE)!=None) and (index.data(REPLYTOSCREENNAMEROLE) != ''):
                    #One time is enought sizeHint need to be fast
#                    print 'index.data(REPLYTOSCREENNAMEROLE):',index.data(REPLYTOSCREENNAMEROLE)
#                    print 'index.data(REPLYTEXTROLE):',index.data(REPLYTEXTROLE)
                    reply = 'In reply to @'+index.data(REPLYTOSCREENNAMEROLE)+' : '+index.data(REPLYTEXTROLE)
                    if not self.minifm:
                        if not self.miniFont:
                            self.miniFont = QFont(option.font)
                            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)
                        self.minifm = QFontMetrics(self.miniFont)
                    height += self.minifm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), reply).height()

            if height < 70:
                height = 70

            self.memoized_size[uid] = QSize(size.width(), height)
            return self.memoized_size[uid]

    def paint(self, painter, option, index):
        '''Paint our tweet'''
        if not self.fm:
            self.fm = QFontMetrics(option.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole)

        #Instantiate font only one time !
        if not self.normFont:
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
            painter.fillRect(option.rect, option.palette.highlight())

        # Draw icon
        if self.show_avatar:
            icon = index.data(Qt.DecorationRole)
            if icon != None:
                x1,y1,x2,y2 = option.rect.getCoords()
                painter.drawPixmap(x1+10,y1+10,50,50, icon)

        # Draw tweet
        painter.setPen(self.text_color)
        new_rect = painter.drawText(option.rect.adjusted(int(self.show_avatar)*70,5,-4,0),  int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet)

        # Draw Timeline
        if self.show_timestamp:
            time = index.data(Qt.ToolTipRole)
            painter.setFont(self.miniFont)
            painter.setPen(self.time_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignRight), time)

        # Draw screenname
        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE)
            painter.setFont(self.miniFont)
            painter.setPen(self.user_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignLeft), screenname)

        # Draw reply
        if self.show_replyto:
            if index.data(REPLYTOSCREENNAMEROLE)!=None:
                reply = 'In reply to @'+index.data(REPLYTOSCREENNAMEROLE)+' : '+index.data(REPLYTEXTROLE)
                painter.setFont(self.miniFont)
                painter.setPen(self.replyto_color)
                new_rect = painter.drawText(option.rect.adjusted(int(self.show_avatar)*70,new_rect.height()+5,-4,0),  int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), reply)

        # Draw line
        painter.setPen(self.separator_color)
        x1,y1,x2,y2 = option.rect.getCoords()
        painter.drawLine(x1,y2,x2,y2)

        painter.restore()

class CoolWhiteCustomDelegate(DefaultCustomDelegate):
    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''
        DefaultCustomDelegate.__init__(self, parent)

        self.user_color = QColor('#3399cc')
        self.replyto_color = QColor('#3399cc')
        self.time_color = QColor('#94a1a7')
        self.bg_color = QColor('#edf1f2')
        self.bg_alternate_color = QColor('#e6eaeb')
        self.text_color = QColor('#444444')
        self.separator_color = QColor('#c8cdcf')


class CoolGrayCustomDelegate(DefaultCustomDelegate):
    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''
        DefaultCustomDelegate.__init__(self, parent)

        self.user_color = QColor('#3399cc')
        self.time_color = QColor('#94a1a7')
        self.replyto_color = QColor('#94a1a7')
        self.bg_color = QColor('#4a5153')
        self.bg_alternate_color = QColor('#444b4d')
        self.text_color = QColor('#FFFFFF')
        self.separator_color = QColor('#333536')


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
#    def event(self, anEvent):
#        if anEvent.type() == QEvent.Move:
#            if not self.overShootMove:
#                self.overShootMove = True
#                r = QAbstractScrollArea.event(self, anEvent)
#                self.overShootMove = False
#                return r
#        else:
#            return QListView.event(self, anEvent)
#
#    def setScrollPosition(self,point1,point2):
#        self.overShootMove = True
#        r = QAbstractScrollArea.setScrollPosition(self,point1,point2)
#        self.overShootMove = False
#        return r

    def keyPressEvent(self,event):
#        print event.key(),Qt.Key_Up, Qt.Key_Down
        if event.key() not in (Qt.Key_Up, Qt.Key_Down):
            self.parent().tb_text.setFocus()
            self.parent().tb_text.keyPressEvent(event)
        else:
            QListView.keyPressEvent(self,event)

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

        self.settings = QSettings()

        if isMAEMO:
            if int(self.settings.value('useAutoRotation'))==2:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle(self.tr("Khweeteur About"))

        aboutScrollArea = QScrollArea(self)
        aboutScrollArea.setWidgetResizable(True)
        awidget = QWidget(aboutScrollArea)
        awidget.setMinimumSize(480,1200)
        awidget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        aboutScrollArea.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        #Kinetic scroller is available on Maemo and should be on meego
        try:
            scroller = aboutScrollArea.property("kineticScroller")
            scroller.setEnabled(True)
        except:
            pass

        aboutLayout = QVBoxLayout(awidget)

        aboutIcon = QLabel()
        aboutIcon.setPixmap(QIcon.fromTheme('khweeteur').pixmap(128,128))
        aboutIcon.setAlignment( Qt.AlignCenter or Qt.AlignHCenter )
        aboutIcon.resize(128,128)
        aboutLayout.addWidget(aboutIcon)

        aboutLabel = QLabel(self.tr('''<center><b>Khweeteur</b> %s
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
                                   <br><br><b>Shortcuts :</b>
                                   <br>Control-R : Refresh current view
                                   <br>Control-M : Reply to selected tweet
                                   <br>Control-Up : To scroll to top
                                   <br>Control-Bottom : To scroll to bottom
                                   <br><br><b>Thanks to :</b>
                                   <br>ddoodie on #pyqt
                                   <br>xnt14 on #maemo
                                   <br>trebormints on twitter
                                   <br>moubaildotcom on twitter
                                   <br>teotwaki on twitter
                                   <br>Jaffa on maemo.org
                                   </center>''') % __version__)
        aboutLayout.addWidget(aboutLabel)
        self.bugtracker_button = QPushButton(self.tr('BugTracker'))
        self.bugtracker_button.clicked.connect(self.open_bugtracker)
        self.website_button = QPushButton(self.tr('Website'))
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

        self.settings = QSettings()

        if isMAEMO:
            try:
                if int(self.settings.value('useAutoRotation'))==2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:#No pref yet default is true
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)

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

        self.settings = QSettings()

        if isMAEMO:
            if int(self.settings.value('useAutoRotation'))==2:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur Prefs")

        self.setupGUI()
        self.loadPrefs()

    def loadPrefs(self):
        if self.settings.value("refreshInterval"):
            self.refresh_value.setValue(int(self.settings.value("refreshInterval")))
        else:
            self.refresh_value.setValue(10)
        if self.settings.value("displayUser"):
            self.displayUser_value.setCheckState(int(self.settings.value("displayUser")))
        else:
            self.displayUser_value.setCheckState(2)
        if self.settings.value("displayAvatar"):
            self.displayAvatar_value.setCheckState(int(self.settings.value("displayAvatar")))
        if self.settings.value("displayTimestamp"):
            self.displayTimestamp_value.setCheckState(int(self.settings.value("displayTimestamp")))
        if self.settings.value("displayReplyTo"):
            self.displayReplyTo_value.setCheckState(int(self.settings.value("displayReplyTo")))
        if self.settings.value("useNotification"):
            self.useNotification_value.setCheckState(int(self.settings.value("useNotification")))
        if self.settings.value("useSerialization"):
            self.useSerialization_value.setCheckState(int(self.settings.value("useSerialization")))
        if self.settings.value("useBitly"):
            self.useBitly_value.setCheckState(int(self.settings.value("useBitly")))
        if not self.settings.value("theme"):
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        if not self.settings.value("theme") in self.THEMES:
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        if not self.settings.value("theme"):
            self.settings.setValue("useAutoRotation",True)
        self.theme_value.setCurrentIndex(self.THEMES.index(self.settings.value("theme")))
        if self.settings.value("useAutoRotation"):
            self.useAutoRotation_value.setCheckState(int(self.settings.value("useAutoRotation")))
        if self.settings.value("useGPS"):
            self.useGPS_value.setCheckState(int(self.settings.value("useGPS")))
        if self.settings.value("tweetHistory"):
            self.history_value.setValue(int(self.settings.value("tweetHistory")))
        else:
            self.history_value.setValue(30)

    def savePrefs(self):
        self.settings.setValue('refreshInterval', self.refresh_value.value())
        self.settings.setValue('displayUser', self.displayUser_value.checkState())
        self.settings.setValue('useNotification', self.useNotification_value.checkState())
        self.settings.setValue('useSerialization', self.useSerialization_value.checkState())
        self.settings.setValue('displayAvatar', self.displayAvatar_value.checkState())
        self.settings.setValue('displayTimestamp', self.displayTimestamp_value.checkState())
        self.settings.setValue('displayReplyTo', self.displayReplyTo_value.checkState())
        self.settings.setValue('useBitly', self.useBitly_value.checkState())
        self.settings.setValue('theme', self.theme_value.currentText())
        self.settings.setValue('useAutoRotation', self.useAutoRotation_value.checkState())
        self.settings.setValue('useGPS', self.useGPS_value.checkState())
        self.settings.setValue('tweetHistory', self.history_value.value())        
        self.emit(SIGNAL("save()"))

    def closeEvent(self,widget,*args):
        self.savePrefs()

    def request_twitter_access_or_clear(self):
        if self.settings.value('twitter_access_token'):
            self.settings.setValue('twitter_access_token_key','')
            self.settings.setValue('twitter_access_token_secret','')
            self.settings.setValue('twitter_access_token',False)
            self.twitter_value.setText(self.tr('Auth on Twitter'))
        else:

            try:
                if not self.parent.nw.device_has_networking:
                    self.parent.nw.request_connection_with_tmp_callback(self.request_twitter_access_or_clear)
                else:
                    raise StandardError(self.tr('No network control'))
            except:
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
                    KhweeteurNotification().warn(self.tr('Invalid respond from Twitter requesting temp token: %s') % resp['status'])
                else:
                    request_token = dict(parse_qsl(content))

                    QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))

                    pincode, ok = QInputDialog.getText(self, self.tr('Twitter Authentification'), self.tr('Enter the pincode :'))

                    if ok:
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                        token.set_verifier(str(pincode))

                        oauth_client  = oauth.Client(oauth_consumer, token)
                        resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                        access_token  = dict(parse_qsl(content))

                        if resp['status'] != '200':
                            KhweeteurNotification().warn(self.tr('The request for a Token did not succeed: %s') % resp['status'])
                            self.settings.setValue('twitter_access_token_key','')
                            self.settings.setValue('twitter_access_token_secret','')
                            self.settings.setValue('twitter_access_token',False)
                        else:
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('twitter_access_token_key',access_token['oauth_token'])
                            self.settings.setValue('twitter_access_token_secret',access_token['oauth_token_secret'])
                            self.settings.setValue('twitter_access_token',True)
                            self.twitter_value.setText(self.tr('Clear Twitter Auth'))
                            KhweeteurNotification().info(self.tr('Khweeteur is now authorized to connect'))
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def request_identica_access_or_clear(self):
        import urllib
        if self.settings.value('identica_access_token'):
            self.settings.setValue('identica_access_token_key','')
            self.settings.setValue('identica_access_token_secret','')
            self.settings.setValue('identica_access_token',False)
            self.identica_value.setText(self.tr('Auth on Identi.ca'))
        else:
            try:
                if not self.parent.nw.device_has_networking:
                    self.parent.nw.request_connection_with_tmp_callback(self.request_identica_access_or_clear)
                else:
                    raise StandardError(self.tr('No network control'))
            except:
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
                oauth_callback_uri = 'oob'
                #Crappy hack for fixing oauth_callback not yet supported by the oauth2 lib but requested by identi.ca
                resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'POST', body=urllib.urlencode(dict(oauth_callback=oauth_callback_uri)))
                write_log(resp)
                write_log(content)
                if resp['status'] != '200':
                    KhweeteurNotification().warn(self.tr('Invalid respond from Identi.ca requesting temp token: %s') % resp['status'])
                else:
                    request_token = dict(parse_qsl(content))

                    QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))

                    pincode, ok = QInputDialog.getText(self, self.tr('Identi.ca Authentification'), self.tr('Enter the token :'))

                    if ok:
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                        token.set_verifier(str(pincode))

                        oauth_client  = oauth.Client(oauth_consumer, token)
                        resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                        write_log(resp)
                        write_log(content)
                        access_token  = dict(parse_qsl(content))

                        if resp['status'] != '200':
                            KhweeteurNotification().warn(self.tr('The request for a Token did not succeed: %s') % resp['status'])
                            self.settings.setValue('identica_access_token_key','')
                            self.settings.setValue('identica_access_token_secret','')
                            self.settings.setValue('identica_access_token',False)
                        else:
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('identica_access_token_key',access_token['oauth_token'])
                            self.settings.setValue('identica_access_token_secret',access_token['oauth_token_secret'])
                            self.settings.setValue('identica_access_token',True)
                            self.identica_value.setText(self.tr('Clear Identi.ca Auth'))
                            KhweeteurNotification().info(self.tr('Khweeteur is now authorized to connect'))
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def request_statusnet_access_or_clear(self):
        QMessageBox.question(self,
           "Khweeteur",
           "Status.net isn't yet fully implemented",
           QMessageBox.Close)
        return

        if self.settings.value('statusnet_access_token'):
            self.settings.setValue('statusnet_access_token_key','')
            self.settings.setValue('statusnet_access_token_secret','')
            self.settings.setValue('statusnet_access_token',False)
            self.status_value.setText(self.tr('Auth on Status.net'))
        else:
            try:
                if not self.parent.nw.device_has_networking:
                    self.parent.nw.request_connection_with_tmp_callback(self.request_identica_access_or_clear)
                else:
                    raise StandardError(self.tr('No network control'))
            except:
                import os
                import sys
                try:
                    from urlparse import parse_qsl
                except:
                    from cgi import parse_qsl
                import oauth2 as oauth

                REQUEST_TOKEN_URL = 'http://khertan.status.net/api/oauth/request_token'
                ACCESS_TOKEN_URL  = 'http://khertan.status.net/api/oauth/access_token'
                AUTHORIZATION_URL = 'http://khertan.status.net/api/oauth/authorize'

                signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
                oauth_consumer             = oauth.Consumer(key=KHWEETEUR_STATUSNET_CONSUMER_KEY, secret=KHWEETEUR_STATUSNET_CONSUMER_SECRET)
                oauth_client               = oauth.Client(oauth_consumer)

                resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')

                if resp['status'] != '200':
                    KhweeteurNotification().warn(self.tr('Invalid respond from Status.net requesting temp token: %s') % resp['status'])
                else:
                    request_token = dict(parse_qsl(content))

                    QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))

                    pincode, ok = QInputDialog.getText(self, self.tr('Status.net Authentification'), self.tr('Enter the token :'))

                    if ok:
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                        token.set_verifier(str(pincode))

                        oauth_client  = oauth.Client(oauth_consumer, token)
                        resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                        access_token  = dict(parse_qsl(content))

                        if resp['status'] != '200':
                            KhweeteurNotification().warn(self.tr('The request for a Token did not succeed: %s') % resp['status'])
                            self.settings.setValue('statusnet_access_token_key','')
                            self.settings.setValue('statusnet_access_token_secret','')
                            self.settings.setValue('statusnet_access_token',False)
                        else:
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('statusnet_access_token_key',access_token['oauth_token'])
                            self.settings.setValue('statusnet_access_token_secret',access_token['oauth_token_secret'])
                            self.settings.setValue('statusnet_access_token',True)
                            self.statusnet_value.setText(self.tr('Clear Status.net Auth'))
                            KhweeteurNotification().info(self.tr('Khweeteur is now authorized to connect'))
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
            scroller = self.scrollArea.property("kineticScroller")
            scroller.setEnabled(True)
        except:
            pass
        self._main_layout = QGridLayout(self.aWidget)

        self._main_layout.addWidget(QLabel(self.tr('Authorizations :')),0,0)
        if self.settings.value(self.tr('twitter_access_token')):
            self.twitter_value = QPushButton(self.tr('Clear Twitter Auth'))
        else:
            self.twitter_value = QPushButton(self.tr('Auth on Twitter'))
        self._main_layout.addWidget(self.twitter_value,0,1)
        self.connect(self.twitter_value, SIGNAL('clicked()'), self.request_twitter_access_or_clear)

        if self.settings.value('identica_access_token'):
            self.identica_value = QPushButton(self.tr('Clear Identi.ca Auth'))
        else:
            self.identica_value = QPushButton(self.tr('Auth on Identi.ca'))
        self._main_layout.addWidget(self.identica_value,1,1)
        self.connect(self.identica_value, SIGNAL('clicked()'), self.request_identica_access_or_clear)

        #Remove statusnet oauth as it didn't support subdomain
        #and require app keys for each subdomain

        self._main_layout.addWidget(QLabel(self.tr('Refresh Interval (Minutes) :')),3,0)
        self.refresh_value = QSpinBox()
        self._main_layout.addWidget(self.refresh_value,3,1)

        self._main_layout.addWidget(QLabel(self.tr('Number of tweet to keep in the view (History) :')),4,0)
        self.history_value = QSpinBox()
        self._main_layout.addWidget(self.history_value,4,1)
        
        self._main_layout.addWidget(QLabel(self.tr('Display preferences :')),5,0)
        self.displayUser_value = QCheckBox(self.tr('Display username'))
        self._main_layout.addWidget(self.displayUser_value,5,1)

        self.displayAvatar_value = QCheckBox(self.tr('Display avatar'))
        self._main_layout.addWidget(self.displayAvatar_value,6,1)

        self.displayTimestamp_value = QCheckBox(self.tr('Display timestamp'))
        self._main_layout.addWidget(self.displayTimestamp_value,7,1)

        self.displayReplyTo_value = QCheckBox(self.tr('Display reply to'))
        self._main_layout.addWidget(self.displayReplyTo_value,8,1)

        self.useAutoRotation_value = QCheckBox(self.tr('Use AutoRotation'))
        self._main_layout.addWidget(self.useAutoRotation_value,9,1)

        self._main_layout.addWidget(QLabel(self.tr('Other preferences :')),9,0)
        self.useNotification_value = QCheckBox(self.tr('Use Notification'))
        self._main_layout.addWidget(self.useNotification_value,10,1)

        self.useSerialization_value = QCheckBox(self.tr('Use Serialization'))
        self._main_layout.addWidget(self.useSerialization_value,11,1)

        self.useBitly_value = QCheckBox(self.tr('Use Bit.ly'))
        self._main_layout.addWidget(self.useBitly_value,12,1)

        self.useGPS_value = QCheckBox(self.tr('Use GPS Geopositionning'))
        self._main_layout.addWidget(self.useGPS_value,13,1)

        self._main_layout.addWidget(QLabel(self.tr('Theme :')),14,0)

        self.theme_value = QComboBox()
        self._main_layout.addWidget(self.theme_value,14,1)
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

        self.settings = QSettings()

        try:
            if int(self.settings.value("useGPS")) == 2:
                if self.parent != None :
                    self.parent.positionStart()
        except:
            pass
            
        if isMAEMO:
            if int(self.settings.value('useAutoRotation'))==2:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)

        if self.search_keyword != None:
            self.setWindowTitle("Khweeteur:"+unicode(self.search_keyword))
        else:
            self.setWindowTitle("Khweeteur")

        self.setupMenu()
        self.setupMain()

        self.worker = None
#        print 'DEBUG:',self.settings.value("displayUser"),type(self.settings.value("displayUser"))
        self.tweetsModel.display_screenname = self.settings.value("displayUser")=='2'
        self.tweetsModel.display_timestamp = self.settings.value("displayTimestamp")=='2'
        self.tweetsModel.display_avatar = self.settings.value("displayAvatar")=='2'

        self.tweetActionDialog = None

        QTimer.singleShot(200, self.justAfterInit)

    def closeEvent(self,widget,*args):
        for win in self.search_win:
            win.close()

    def justAfterInit(self):
        if not noDBUS:
            from nwmanager import NetworkManager
            self.nw = NetworkManager(self.refresh_timeline)
        else:
            self.refresh_timeline

        self.notifications = KhweeteurNotification()

        self.timer = QTimer()
        self.connect(self.timer, SIGNAL("timeout()"), self.timed_refresh)
        if int(self.settings.value("refreshInterval")>0):
            self.timer.start(int(self.settings.value("refreshInterval"))*60*1000)

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
        try:
            self.tweetsView.custom_delegate.show_screenname = int(self.settings.value("displayUser"))==2
            self.tweetsView.custom_delegate.show_timestamp = int(self.settings.value("displayTimestamp"))==2
            self.tweetsView.custom_delegate.show_avatar = int(self.settings.value("displayAvatar"))==2
            self.tweetsView.custom_delegate.show_replyto = int(self.settings.value("displayReplyTo"))==2
        except:
            pass
#        self.connect(self.tweetsView, SIGNAL('Clicked(const QModelIndex&)'), self.tweet_do_ask_action)

        self.connect(self.tweetsView, SIGNAL('doubleClicked(const QModelIndex&)'), self.tweet_do_ask_action)
        self.tweetsModel = KhweetsModel([], self.search_keyword)
        try: #If pref didn't exist
            self.tweetsModel.setLimit(int(self.settings.value("tweetHistory")))
        except: 
            self.tweetsModel.setLimit(50)
        self.tweetsView.setModel(self.tweetsModel)
        self.setCentralWidget(self.tweetsView)

        self.toolbar = self.addToolBar('Toolbar')

        self.tb_update = QAction(QIcon.fromTheme("general_refresh"), 'Update', self)
        self.tb_update.setShortcut('Ctrl+R')
        self.connect(self.tb_update, SIGNAL('triggered()'), self.request_refresh)
        self.toolbar.addAction(self.tb_update)

        self.tb_text = QLineEdit()
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.tb_text_replysource = ''
        self.tb_text.enabledChange(True)
        self.toolbar.addWidget(self.tb_text)

        self.tb_charCounter = QLabel('140')
        self.toolbar.addWidget(self.tb_charCounter)
        self.connect(self.tb_text, SIGNAL('textChanged(const QString&)'), self.countChar)

        self.tb_tweet = QAction(QIcon.fromTheme('khweeteur'), 'Tweet', self)
        self.connect(self.tb_tweet, SIGNAL('triggered()'), self.tweet)
        self.toolbar.addAction(self.tb_tweet)

        #Actions not in toolbar
        self.tb_reply = QAction('Reply', self)
        self.tb_reply.setShortcut('Ctrl+M')
        self.connect(self.tb_reply,
             SIGNAL('triggered()'), self.reply)
        self.addAction(self.tb_reply)

        self.tb_scrolltop = QAction('Scroll to top', self)
        self.tb_scrolltop.setShortcut(Qt.CTRL + Qt.Key_Up)
        self.connect(self.tb_scrolltop,
             SIGNAL('triggered()'), self.scrolltop)
        self.addAction(self.tb_scrolltop)

        self.tb_scrollbottom = QAction('Scroll to bottom', self)
        self.tb_scrollbottom.setShortcut(Qt.CTRL + Qt.Key_Down)
        self.connect(self.tb_scrollbottom,
             SIGNAL('triggered()'), self.scrollbottom)
        self.addAction(self.tb_scrollbottom)

        QTimer.singleShot(200, self.timedUnserialize)

    def scrolltop(self):
        self.tweetsView.scrollToTop()

    def scrollbottom(self):
        self.tweetsView.scrollToBottom()

    def tweet_do_ask_action(self):
        user = None
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel._items[index.row()][2]
        if user:
            self.tweetActionDialog = KhweetAction(self, user)
            self.connect(self.tweetActionDialog.reply, SIGNAL('clicked()'), self.reply)
            self.connect(self.tweetActionDialog.openurl, SIGNAL('clicked()'), self.open_url)
            self.connect(self.tweetActionDialog.retweet, SIGNAL('clicked()'), self.retweet)
            self.connect(self.tweetActionDialog.follow, SIGNAL('clicked()'), self.follow)
            self.connect(self.tweetActionDialog.unfollow, SIGNAL('clicked()'), self.unfollow)
            self.connect(self.tweetActionDialog.destroy_tweet, SIGNAL('clicked()'), self.destroy_tweet)
            self.tweetActionDialog.exec_()

    def countChar(self,text):
        self.tb_charCounter.setText(unicode(140-len(text)))

    def reply(self):
        if self.tweetActionDialog != None:
            self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel._items[index.row()][2]
            self.tb_text_replyid = self.tweetsModel._items[index.row()][1]
            self.tb_text_replytext = '@'+user+' '
            self.tb_text.setText('@'+user+' ')
            self.tb_text_replysource = self.tweetsModel._items[index.row()][8]
#            print self.tb_text_replysource, self.tb_text_replyid, self.tweetsModel._items[index.row()][3]
            
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
                           self.tr("Follow : %s ?") % self.tweetsModel._items[index.row()][2],
                           QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                    user_screenname = self.tweetsModel._items[index.row()][2]
                    #print 'DEBUG Follow:', user_screenname
                    if 'twitter' in self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("twitter_access_token_key")!=None:
                                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                                  access_token_key=str(self.settings.value("twitter_access_token_key")),
                                                  access_token_secret=str(self.settings.value("twitter_access_token_secret")))
                                api.SetUserAgent('Khweeteur/%s' % (__version__))
                                api.CreateFriendship(user_screenname)
                                self.notifications.info(self.tr('You are now following %s on Twitter') % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Twitter : %s') %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Twitter : %s') %(user_screenname, str(e)))
                                print e

                    if 'http://identi.ca/api/' == self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("identica_access_token_key")!=None:
                                api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                                  password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                                  access_token_key=str(self.settings.value("identica_access_token_key")),
                                                  access_token_secret=str(self.settings.value("identica_access_token_secret")))
                                api.SetUserAgent('Khweeteur/%s' % (__version__))
                                api.CreateFriendship(user_screenname)
                                self.notifications.info(self.tr('You are now following %s on Identi.ca') % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Identi.ca : %s') %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Identi.ca : %s') %(user_screenname, str(e)))
                                print e

    def unfollow(self):
        self.tweetActionDialog.accept()
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.unfollow)
        else:
            for index in self.tweetsView.selectedIndexes():
                if ((QMessageBox.question(self,
                           "Khweeteur",
                           self.tr("Unfollow : %s ?") % self.tweetsModel._items[index.row()][2],
                           QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                    user_screenname = self.tweetsModel._items[index.row()][2]
                    #print 'DEBUG Follow:', user_screenname
                    if 'twitter' in self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("twitter_access_token_key")!=None:
                                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                                  access_token_key=str(self.settings.value("twitter_access_token_key")),
                                                  access_token_secret=str(self.settings.value("twitter_access_token_secret")))
                                api.SetUserAgent('Khweeteur/%s' % (__version__))
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Twitter' % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Twitter : %s') %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Twitter : %s') %(user_screenname, str(e)))
                                print e

                    if 'http://identi.ca/api/' == self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("identica_access_token_key")!=None:
                                api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                                  password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                                  access_token_key=str(self.settings.value("identica_access_token_key")),
                                                  access_token_secret=str(self.settings.value("identica_access_token_secret")))
                                api.SetUserAgent('Khweeteur/%s' % (__version__))
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Identi.ca' % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Identi.ca : %s') %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Identi.ca : %s') %(user_screenname, str(e)))
                                print e

    def retweet(self):
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            if ((QMessageBox.question(self,
                       "Khweeteur",
                       "Retweet this : %s ?" % self.tweetsModel._items[index.row()][3],
                       QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                tweetid = self.tweetsModel._items[index.row()][1]
                if 'twitter' in self.tweetsModel._items[index.row()][8]:
                    try:
                        if self.settings.value("twitter_access_token_key")!=None:
                            api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("twitter_access_token_key")),
                                              access_token_secret=str(self.settings.value("twitter_access_token_secret")))
                            api.SetUserAgent('Khweeteur/%s' % (__version__))
                            api.PostRetweet(tweetid)
                            self.notifications.info(self.tr('Retweet sent to Twitter'))
                    except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn(self.tr('Retweet to twitter failed : ')+(e.message))
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Retweet to twitter failed : ')+str(e))
                            print e

                if 'http://identi.ca/api/' == self.tweetsModel._items[index.row()][8]:
                    try:
                        if self.settings.value("identica_access_token_key")!=None:
                            api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                              password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("identica_access_token_key")),
                                              access_token_secret=str(self.settings.value("identica_access_token_secret")))
                            api.SetUserAgent('Khweeteur/%s' % (__version__))
                            api.PostRetweet(tweetid)
                            self.notifications.info(self.tr('Retweet sent to Identi.ca'))
                    except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn(self.tr('Retweet to identi.ca failed : ')+(e.message))
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Retweet to identi.ca failed : ')+str(e))
                            print e

    def destroy_tweet(self):
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            if ((QMessageBox.question(self,
                       "Khweeteur",
                       self.tr("Destroy this : %s ?") % self.tweetsModel._items[index.row()][3],
                       QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                tweetid = self.tweetsModel._items[index.row()][1]
                #print 'DEBUG Retweet:',tweetid
                if 'twitter' in self.tweetsModel._items[index.row()][8]:
                    try:
                        if self.settings.value("twitter_access_token_key")!=None:
                            api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("twitter_access_token_key")),
                                              access_token_secret=str(self.settings.value("twitter_access_token_secret")))
                            api.SetUserAgent('Khweeteur/%s' % (__version__))
                            api.DestroyStatus(tweetid)
                            self.tweetsModel.destroyStatus(index)
                            self.notifications.info('Status destroyed on Twitter')
                    except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn('Destroy status from twitter failed : '+(e.message))
                            print e.message
                        else:
                            self.notifications.warn('Destroy status from twitter failed : '+str(e))
                            print e

                if 'http://identi.ca/api/' == self.tweetsModel._items[index.row()][8]:
                    try:
                        if self.settings.value("identica_access_token_key")!=None:
                            api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                              password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("identica_access_token_key")),
                                              access_token_secret=str(self.settings.value("identica_access_token_secret")))
                            api.SetUserAgent('Khweeteur/%s' % (__version__))
                            api.DestroyStatus(tweetid)
                            self.tweetsModel.destroyStatus(index)
                            self.notifications.info('Status destroyed on Identi.ca')
                    except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
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
            try:
                geoposition = (self.parent.coordinates)
            except:
                geoposition = None
            self.tweetAction = KhweeteurActionWorker(self, 'tweet', unicode(self.tb_text.text()).encode('utf-8'), self.tb_text_replyid, self.tb_text_replytext, self.tb_text_replysource,geoposition)
            self.connect(self.tweetAction, SIGNAL("tweetSent()"), self.tweetSent)
            self.connect(self.tweetAction, SIGNAL("finished()"), self.tweetSentFinished)
            self.notifications.connect(self.tweetAction, SIGNAL('info(PyQt_PyObject)'), self.notifications.info)
            self.notifications.connect(self.tweetAction, SIGNAL('warn(PyQt_PyObject)'), self.notifications.warn)
            self.tweetAction.start()

    def refreshEnded(self):
        counter=self.tweetsModel.getNew()

        if (counter>0) and (int(self.settings.value('useNotification'))==2) and not (self.isActiveWindow()):
            if self.search_keyword == None:
                self.notifications.notify('Khweeteur', str(counter)+' new tweet(s)',count=counter)
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def do_refresh_now(self):
        #print type(self.settings.value('useNotification')), self.settings.value('useNotification')
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
        if self.search_keyword=='GeOSearH':
            if self.parent.coordinates:           
                geocode = '%f,%f,1Km' %(self.parent.coordinates[0],self.parent.coordinates[1]) #FIXME
            else:
                geocode = None
        else:
            geocode = None            
        self.worker = KhweeteurWorker(self, search_keyword=self.search_keyword, geocode=geocode)
        self.connect(self.worker, SIGNAL("newStatuses(PyQt_PyObject)"), self.tweetsModel.addStatuses)
        self.connect(self.worker, SIGNAL("finished()"), self.refreshEnded)
        self.notifications.connect(self.worker, SIGNAL('info(PyQt_PyObject)'), self.notifications.info)
        self.worker.start()

    def request_refresh(self):
        try:
            if not self.nw.device_has_networking:
                self.nw.request_connection()
            else:
                raise StandardError('No network control')
        except:
            self.refresh_timeline()

    def timed_refresh(self):
        self.request_refresh()

    def refresh_timeline(self):
        if self.worker == None:
            self.do_refresh_now()
        elif self.worker.isFinished() == True:
            self.do_refresh_now()

    def restartTimer(self):
        if isMAEMO:
            if int(self.settings.value('useAutoRotation'))==2:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.tweetsView.refreshCustomDelegate()
#        print 'DEBUG2:',(self.settings.value("displayUser")),type((self.settings.value("displayUser")))

        self.tweetsView.custom_delegate.show_screenname = int(self.settings.value("displayUser")) == 2
        self.tweetsView.custom_delegate.show_timestamp = int(self.settings.value("displayTimestamp")) == 2
        self.tweetsView.custom_delegate.show_avatar = int(self.settings.value("displayAvatar")) == 2
        self.tweetsView.custom_delegate.show_replyto = int(self.settings.value("displayReplyTo")) == 2
        QObject.emit(self.tweetsModel, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.tweetsModel.createIndex(0,0), self.tweetsModel.createIndex(0,len(self.tweetsModel._items)))
        if (int(self.settings.value("refreshInterval"))>0):
            self.timer.start(int(self.settings.value("refreshInterval"))*60*1000)
        else:
            self.timer.stop()
        if self.parent != None: #We are in a search so no need to start gps #Fix bug#399
            if int(self.settings.value("useGPS")) == 2:
                self.parent.positionStart()
            else:
                self.parent.positionStop()
        for search_win in self.search_win:
            search_win.restartTimer()

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
            keywords = self.settings.value('savedSearch')
            if (keywords != None):
                if self.search_keyword in keywords:
                    fileMenu.addAction(self.tr("&Remove Search"), self.del_search)
                else:
                    fileMenu.addAction(self.tr("&Save Search"), self.save_search)
            else:
                fileMenu.addAction(self.tr("&Save Search"), self.save_search)

        fileMenu.addAction(self.tr("&About"), self.do_about)

    def del_search(self):
        keywords = self.settings.value('savedSearch')
        if (keywords == None):
            keywords = []
        elif (type(keywords)==str):
            if (self.search_keyword==keywords):
                keywords = []
        elif (type(keywords)==list):
            index = keywords.indexOf(self.search_keyword)
            if index>=0:
                keywords.removeAt(index)
        else:
            keywords.remove(self.search_keyword)
        self.settings.setValue('savedSearch',keywords)
        self.close()

    def save_search(self):
        keywords = self.settings.value('savedSearch')
        if (keywords == None):
            keywords = []
        elif (type(keywords)==str):
            keywords = [keywords,]
        keywords.append(self.search_keyword)
        self.settings.setValue('savedSearch',keywords)

    def open_saved_search(self):
        keywords = self.settings.value('savedSearch')
        if (type(keywords)==str):
            keywords = [keywords,]

        if (keywords != None):
            for keyword in keywords:
                self.do_search(keyword)
        self.activateWindow()

    def open_search(self):
        search_keyword, ok = QInputDialog.getText(self, self.tr('Search'), self.tr('Enter the search keyword(s) :'))
        if ok==1:
            self.do_search(search_keyword)

    def do_search(self, search_keyword):
        swin = KhweeteurWin(search_keyword=unicode(search_keyword),parent=self.parent)
        self.search_win.append(swin)
        swin.show()

    def do_show_pref(self):
        self.pref_win = KhweeteurPref(self)
        self.connect(self.pref_win, SIGNAL("save()"), self.restartTimer)
        self.pref_win.show()

    def do_about(self):
        self.aboutWin = KhweeteurAbout(self)

    @pyqtSlot()
#    @Slot()
    def activated_by_dbus(self):
        self.tweetsModel.getNewAndReset()
        self.activateWindow()

class Khweeteur(QApplication):

    activated_by_dbus = pyqtSignal()
#    activated_by_dbus = Signal()

    def __init__(self):

        QApplication.__init__(self, sys.argv)
        self.setOrganizationName("Khertan Software")
        self.setOrganizationDomain("khertan.net")
        self.setApplicationName("Khweeteur")
        self.version = __version__

        if not noDBUS:
            try:
                self.dbus_loop = DBusQtMainLoop()
                dbus.set_default_main_loop(self.dbus_loop)
            except:
                pass

        install_excepthook()

        if not noDBUS:
            self.dbus_object = KhweeteurDBus()

        self.coordinates = None
        self.source = None

        self.run()

    def positionStart(self):
        if self.source is None:
            self.source = QGeoPositionInfoSource.createDefaultSource(None)
            if self.source is not None:
                self.source.setUpdateInterval(50000)
                self.source.positionUpdated.connect(self.positionUpdated)
#                if QSettings().
                self.source.startUpdates()
                print "Waiting for a fix..."

    def positionStop(self):
        if self.source is not None:
            self.source.stopUpdates()
            self.source = None

    def positionUpdated(self,update):
        if update.isValid():
            self.coordinates = (update.coordinate().latitude(),update.coordinate().longitude())
#            print 'Position Updated:',self.coordinates

    def handle_signal(self,*args):
        print 'received signal:', args

    def crash_report(self):
        if os.path.isfile(os.path.join(CACHE_PATH, 'crash_report')):
            import urllib
            if ((QMessageBox.question(None,
                self.tr("Khweeteur Crash Report"),
                self.tr("An error occur on khweeteur in the previous launch. Report this bug on the bug tracker ?"),
                QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                url = 'http://khertan.net/report.php' # write ur URL here
                try:
                    filename = os.path.join(CACHE_PATH, 'crash_report')
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
                    self.tr("Khweeteur Crash Report"),
                    self.tr("An error occur during the report : %s") % detail,
                    QMessageBox.Close)
                    return False

                if 'Your report have been successfully stored' in the_page:
                    QMessageBox.question(None,
                    self.tr("Khweeteur Crash Report"),
                    "%s" % the_page,
                    QMessageBox.Close)
                    return True
                else:
                    QMessageBox.question(None,
                    self.tr("Khweeteur Crash Report"),
                    QMessageBox.Close)
                    return False
            try:
                os.remove(os.path.join(CACHE_PATH, 'crash_report'))
            except:
                pass

    def run(self):
        self.win = KhweeteurWin(self)
        if not noDBUS:
            self.dbus_object.attach_app(self)
            self.activated_by_dbus.connect(self.win.activated_by_dbus)
        self.crash_report()
        self.win.show()

if __name__ == '__main__':
    sys.exit(Khweeteur().exec_())
