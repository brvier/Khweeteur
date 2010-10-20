#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4'''

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from PyQt4.QtMobility.QtLocation import *
try:
    from PyQt4.QtMaemo5 import *
    isMAEMO = True
except:
    isMAEMO = False
    
import twitter
import sys
import os.path
from urllib import urlretrieve
import datetime
import time
import dbus
import dbus.service
from dbus.mainloop.qt import DBusQtMainLoop
import pickle
from PIL import Image
import re
import urllib2
import socket
import glob

__version__ = '0.0.39'

def write_report(error):
    '''Function to write error to a report file'''
    filename = os.path.join(CACHE_PATH, 'crash_report')
    output = open(filename, 'wb')
    pickle.dump(error, output)
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
KHWEETEUR_TWITTER_CONSUMER_KEY = 'uhgjkoA2lggG4Rh0ggUeQ'
KHWEETEUR_TWITTER_CONSUMER_SECRET = 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU'
KHWEETEUR_IDENTICA_CONSUMER_KEY = 'c7e86efd4cb951871200440ad1774413'
KHWEETEUR_IDENTICA_CONSUMER_SECRET = '236fa46bf3f65fabdb1fd34d63c26d28'
KHWEETEUR_STATUSNET_CONSUMER_KEY = '84e768bba2b6625f459a9a19f5d57bd1'
KHWEETEUR_STATUSNET_CONSUMER_SECRET = 'fbc51241e2ab12e526f89c26c6ca5837'
SCREENNAMEROLE = 20
REPLYTOSCREENNAMEROLE = 21
REPLYTEXTROLE = 22

class KhweeteurDBus(dbus.service.Object):
    '''DBus Object handle dbus callback'''
    def __init__(self):
        bus_name = dbus.service.BusName('net.khertan.khweeteur', bus=dbus.SessionBus())
#        dbus.service.Object.__init__(self, self.bus, '/net/khertan/khweeteur')
        dbus.service.Object.__init__(self, bus_name, '/net/khertan/khweeteur')
    #activated = pyqtSignal()
        
    @dbus.service.method(dbus_interface='net.khertan.khweeteur')
    def show_now(self):
        '''Callback called to active the window and reset counter'''
        print 'dbus ?'
        self.app.activated_by_dbus.emit()
        return True
        
    def attach_app(self, app):
        self.app = app

        
class KhweeteurNotification(QObject):
    '''Notification class interface'''
    def __init__(self):
        QObject.__init__(self)
        self.m_bus = dbus.SystemBus()
        self.m_notify = self.m_bus.get_object('org.freedesktop.Notifications',
                                              '/org/freedesktop/Notifications')
        self.iface = dbus.Interface(self.m_notify, 'org.freedesktop.Notifications')
        self.m_id = 0
        
    def warn(self, message):
        '''Display an Hildon banner'''
        if isMAEMO:
            self.iface.SystemNoteDialog(message,0, 'Nothing')
        
    def info(self, message):
        '''Display an information banner'''
        if isMAEMO:
            self.iface.SystemNoteInfoprint('Khweeteur : '+message)
        
    def notify(self,title, message,category='im.received', icon='khweeteur',count=1):
        '''Create a notification in the style of email one'''
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

            if self.settings.value("useBitly").toBool():
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

            print 'test'
            if self.geolocation:
                latitude,longitude = self.geolocation
            else:
                latitude,longitude = (None,None)                
            
            if ('twitter' in self.tb_text_replysource) or (self.tb_text_replyid == 0):
                if self.settings.value("twitter_access_token_key").toString()!='':     
                    api = twitter.Api(
                                      username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                      access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                      access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if self.settings.value('useSerialization').toBool():
                        status = api.PostSerializedUpdates(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    else:
                        status = api.PostUpdate(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    self.emit(SIGNAL("info(PyQt_PyObject)"), 'Tweet sent to Twitter')

            if ('http:/identi.ca/api/' == self.tb_text_replysource) or (self.tb_text_replyid == 0):
                if self.settings.value("identica_access_token_key").toString()!='':     
                    api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                      password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                      access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                      access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if self.settings.value('useSerialization').toBool():
                        status = api.PostSerializedUpdates(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    else:
                        status = api.PostUpdate(status_text, in_reply_to_status_id=self.tb_text_replyid,
                                                           latitude=latitude,longitude=longitude)
                    self.emit(SIGNAL("info(PyQt_PyObject)"), 'Tweet sent to Identica')

            if ('http://khertan.status.net' == self.tb_text_replysource) or (self.tb_text_replyid == 0):
                if self.settings.value("statusnet_access_token_key").toString()!='':     
                    api = twitter.Api(base_url='http://khertan.status.net/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                      password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                      access_token_key=str(self.settings.value("statusnet_access_token_key").toString()),
                                      access_token_secret=str(self.settings.value("statutsnet_access_token_secret").toString()))
                    api.SetUserAgent('Khweeteur/%s' % (__version__))
                    if self.settings.value('useSerialization').toBool():
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
#            import traceback
#            traceback.print_exc()
            

class KhweeteurRefreshWorker(QThread):
    ''' Common Abstract class for the refresh thread '''
    
    #Signal
    errors = pyqtSignal(Exception)
    newStatuses = pyqtSignal(list)
    
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
                                status.in_reply_to_status_text = tw.in_reply_to_status_id
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
                                if item[8] not in (None,''):
                                    status.in_reply_to_status_text = item[8]
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
            statuses = self.api.GetFriendsTimeline(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetFriendsTimeline').toString(), retweets=True)
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
            statuses = self.api.GetRetweetedByMe(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetRetweetedByMe_last_id').toString())
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
            mystatuses = self.api.GetRetweetsOfMe(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetRetweetsOfMe_last_id').toString())
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
            self.errors.emit(StandardError('A network error occurs'))
#            import traceback
#            traceback.print_exc()
            

class KhweeteurRepliesWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)        
    def run(self):
        #Get Retweeted by me    
        try:
            statuses = self.api.GetReplies(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetReplies').toString())
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
            self.errors.emit(StandardError('A network error occurs'))
#            import traceback
#            traceback.print_exc()
            
class KhweeteurDMWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)        
    def run(self):
        try:
            statuses = self.api.GetDirectMessages(since_id=self.settings.value('last_id/'+self.api.base_url+'_DirectMessages').toString())
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
            self.errors.emit(StandardError('A network error occurs'))
#            import traceback
#            traceback.print_exc()
            
class KhweeteurMentionWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)        
    def run(self):
        try:
            statuses = self.api.GetMentions(since_id=self.settings.value('last_id/'+self.api.base_url+'_GetMentions').toString())
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
            self.errors.emit(StandardError('A network error occurs'))
#            import traceback
#            traceback.print_exc()
            
class KhweeteurSearchWorker(KhweeteurRefreshWorker):
    def __init__(self, parent = None, api=None, keywords=None):
        KhweeteurRefreshWorker.__init__(self, None, api)      
        self.keywords = keywords
        
    def run(self):
        try:
            statuses = self.api.GetSearch(unicode(self.keywords).encode('UTF-8'), since_id=self.settings.value(self.keywords+'/last_id/'+self.api.base_url).toString())
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api,statuses)
            self.getRepliesContent(self.api,statuses)
            statuses.sort()
            statuses.reverse()        
            if len(statuses)>0:                                                        
                self.newStatuses.emit(statuses)
                self.settings.setValue(self.keywords+'/last_id/'+self.api.base_url, statuses[0].id)
        except twitter.TwitterError,e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError('A network error occurs'))
#            import traceback
#            traceback.print_exc()
            
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
        
        if (self.settings.value("twitter_access_token_key").toString()!=''): 
            api = twitter.Api(input_encoding='utf-8', \
                username=KHWEETEUR_TWITTER_CONSUMER_KEY, \
                password=KHWEETEUR_TWITTER_CONSUMER_SECRET, \
                access_token_key=str(self.settings.value("twitter_access_token_key").toString()), \
                access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
            api.SetUserAgent('Khweeteur/%s' % (__version__))
            self.refresh_search_worker1 = KhweeteurSearchWorker(self,api,self.search_keyword)
            self.refresh_search_worker1.errors.connect(self.errors)
            self.refresh_search_worker1.newStatuses.connect(self.newStatuses)
            self.refresh_search_worker1.start()
                

        if (self.settings.value("twitter_access_token_key").toString()!=''): 
            api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, access_token_key=str(self.settings.value("identica_access_token_key").toString()), access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
            api.SetUserAgent('Khweeteur/%s' % (__version__))
            self.refresh_search_worker2 = KhweeteurSearchWorker(self,api,self.search_keyword)
            self.refresh_search_worker2.errors.connect(self.errors)
            self.refresh_search_worker2.newStatuses.connect(self.newStatuses)
            self.refresh_search_worker2.start()

        while (self.refresh_search_worker1.isRunning()==True) or \
              (self.refresh_search_worker2.isRunning()==True):
            self.sleep(2)
                
        if self.error != None:
            raise self.error
        
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
            
        return [refresh_timeline_worker,
                refresh_retweetedbyme_worker,
                refresh_retweetsofme_worker,
                refresh_replies_worker,
                refresh_dm_worker,
                refresh_mention_worker]
        
    def refresh(self):
        self.error = None
        threads = []
        
        try:
            if (self.settings.value("twitter_access_token_key").toString()!=''): 
                #Login to twitter
                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY, \
                        password=KHWEETEUR_TWITTER_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("twitter_access_token_key").toString()), \
                        access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
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
            if (self.settings.value("identica_access_token_key").toString()!=''): 
                api = twitter.Api(base_url='http://identi.ca/api/', \
                        username=KHWEETEUR_IDENTICA_CONSUMER_KEY, \
                        password=KHWEETEUR_IDENTICA_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("identica_access_token_key").toString()), \
                        access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))
                api.SetUserAgent('Khweeteur/%s' % (__version__))
                threads.extend(self.refresh_unified(api))                     
        except twitter.TwitterError,e:
            print 'Error during identi.ca refresh: ',e.message
            self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
        except:
            self.emit(SIGNAL("info(PyQt_PyObject)"), 'A network error occur')
                
        try:
            if (self.settings.value("statusnet_access_token_key").toString()!=''): 
                api = twitter.Api(base_url='http://khertan.status.net/api/', \
                        username=KHWEETEUR_STATUSNET_CONSUMER_KEY, \
                        password=KHWEETEUR_STATUSNET_CONSUMER_SECRET, \
                        access_token_key=str(self.settings.value("statusnet_access_token_key").toString()), \
                        access_token_secret=str(self.settings.value("statusnet_access_token_secret").toString()))
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
                print 'Error during twitter refresh : ',e.message
                self.emit(SIGNAL("info(PyQt_PyObject)"),e.message)
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
        for index, item in enumerate(self._items):
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
            KhweeteurNotification().info('Wrong cache format. Reinit cache.')
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
            pickle.dump(self._items, output,pickle.HIGHEST_PROTOCOL)
            output.close()
            
        except StandardError,e:
            KhweeteurNotification().info('An error occurs while saving cache : '+str(e))
            
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
            QObject.emit(self, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.createIndex(0,0), self.createIndex(0,len(self._items)))

    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return QVariant(self._items[index.row()][3])
        elif role == SCREENNAMEROLE:
            return QVariant(self._items[index.row()][2])
        elif role == REPLYTOSCREENNAMEROLE:
            return QVariant(self._items[index.row()][6])            
        elif role == REPLYTEXTROLE:
            return QVariant(self._items[index.row()][7])
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
        size = QStyledItemDelegate.sizeHint(self, option, index)
        tweet = index.data(Qt.DisplayRole).toString()

        #One time is enought sizeHint need to be fast
        if self.fm == None:
            self.fm = QFontMetrics(option.font)
        height = self.fm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet).height()+40
            
        if self.show_replyto:
            if (index.data(REPLYTOSCREENNAMEROLE)!=QVariant()) and (index.data(REPLYTOSCREENNAMEROLE).toString() != ''):
                #One time is enought sizeHint need to be fast
                reply = 'In reply to @'+index.data(REPLYTOSCREENNAMEROLE).toString()+' : '+index.data(REPLYTEXTROLE).toString()
                if self.minifm == None:
                    if self.miniFont == None:
                        self.miniFont = QFont(option.font)
                        self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)            
                self.minifm = QFontMetrics(self.miniFont)
                height += self.minifm.boundingRect(0,0,option.rect.width()-75,800, int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), reply).height()

        if height < 70:
            height = 70

        return QSize(size.width(), height)
        

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
            painter.fillRect(option.rect, option.palette.highlight())
                    
        # Draw icon
        if self.show_avatar:
            icon = index.data(Qt.DecorationRole).toPyObject()
            if icon != None:
                x1,y1,x2,y2 = option.rect.getCoords()
                painter.drawPixmap(x1+10,y1+10,50,50, icon)
                                                
        # Draw tweet
        painter.setPen(self.text_color)
        new_rect = painter.drawText(option.rect.adjusted(int(self.show_avatar)*70,5,-4,0),  int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), tweet)
                
        # Draw Timeline
        if self.show_timestamp:
            time = index.data(Qt.ToolTipRole).toString()
            painter.setFont(self.miniFont)
            painter.setPen(self.time_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignRight), time)

        # Draw screenname
        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE).toString()
            painter.setFont(self.miniFont)
            painter.setPen(self.user_color)
            painter.drawText(option.rect.adjusted(70,10,-10,-9),  int(Qt.AlignBottom) | int(Qt.AlignLeft), screenname)

        # Draw reply
        if self.show_replyto:
            if index.data(REPLYTOSCREENNAMEROLE).toString()!='':
                reply = 'In reply to @'+index.data(REPLYTOSCREENNAMEROLE).toString()+' : '+index.data(REPLYTEXTROLE).toString()
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
        print event.key(),Qt.Key_Up, Qt.Key_Down
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
            if self.settings.value('useAutoRotation').toInt()[0]:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur About")

        aboutScrollArea = QScrollArea(self)
        aboutScrollArea.setWidgetResizable(True)
        awidget = QWidget(aboutScrollArea)
        awidget.setMinimumSize(480,1200)
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

        self.settings = QSettings()

        if isMAEMO:
            if self.settings.value('useAutoRotation').toInt()[0]:
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
            if self.settings.value('useAutoRotation').toInt()[0]:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur Prefs")

        self.setupGUI()
        self.loadPrefs()

    def loadPrefs(self):
        self.refresh_value.setValue(self.settings.value("refreshInterval").toInt()[0])
        self.displayUser_value.setCheckState(self.settings.value("displayUser").toInt()[0])
        self.displayAvatar_value.setCheckState(self.settings.value("displayAvatar").toInt()[0])
        self.displayTimestamp_value.setCheckState(self.settings.value("displayTimestamp").toInt()[0])
        self.displayReplyTo_value.setCheckState(self.settings.value("displayReplyTo").toInt()[0])
        self.useNotification_value.setCheckState(self.settings.value("useNotification").toInt()[0])
        self.useSerialization_value.setCheckState(self.settings.value("useSerialization").toInt()[0])
        self.useBitly_value.setCheckState(self.settings.value("useBitly").toInt()[0])
        if not self.settings.value("theme"):
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        if not self.settings.value("theme").toString() in self.THEMES:
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        if not self.settings.value("theme"):
            self.settings.setValue("useAutoRotation",True)            
        self.theme_value.setCurrentIndex(self.THEMES.index(self.settings.value("theme").toString()))
        self.useAutoRotation_value.setCheckState(self.settings.value("useAutoRotation").toInt()[0])
        self.useGPS_value.setCheckState(self.settings.value("useGPS").toInt()[0])

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

    def request_statusnet_access_or_clear(self):
        QMessageBox.question(self,
           "Khweeteur",
           "Status.net isn't yet fully implemented",
           QMessageBox.Close)
        return
        
        if self.settings.value('statusnet_access_token').toBool():
            self.settings.setValue('statusnet_access_token_key',QString())
            self.settings.setValue('statusnet_access_token_secret',QString())
            self.settings.setValue('statusnet_access_token',False)
            self.status_value.setText('Auth on Status.net')
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
                
                REQUEST_TOKEN_URL = 'http://khertan.status.net/api/oauth/request_token'
                ACCESS_TOKEN_URL  = 'http://khertan.status.net/api/oauth/access_token'
                AUTHORIZATION_URL = 'http://khertan.status.net/api/oauth/authorize'
    
                signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
                oauth_consumer             = oauth.Consumer(key=KHWEETEUR_STATUSNET_CONSUMER_KEY, secret=KHWEETEUR_STATUSNET_CONSUMER_SECRET)
                oauth_client               = oauth.Client(oauth_consumer)
                
                resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')
                
                if resp['status'] != '200':
                    KhweeteurNotification().warn('Invalid respond from Status.net requesting temp token: %s' % resp['status'])
                else:
                    request_token = dict(parse_qsl(content))
    
                    QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))
                    
                    pincode, ok = QInputDialog.getText(self, 'Status.net Authentification', 'Enter the token :')
    
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
                            self.settings.setValue('statusnet_access_token_key',QString())
                            self.settings.setValue('statusnet_access_token_secret',QString())
                            self.settings.setValue('statusnet_access_token',False)
                        else:
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('statusnet_access_token_key',QString(access_token['oauth_token']))
                            self.settings.setValue('statusnet_access_token_secret',QString(access_token['oauth_token_secret']))
                            self.settings.setValue('statusnet_access_token',True)
                            self.statusnet_value.setText('Clear Status.net Auth')
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
        self.connect(self.twitter_value, SIGNAL('clicked()'), self.request_twitter_access_or_clear)

        if self.settings.value('identica_access_token').toBool():
            self.identica_value = QPushButton('Clear Identi.ca Auth')
        else:
            self.identica_value = QPushButton('Auth on Identi.ca')
        self._main_layout.addWidget(self.identica_value,1,1)
        self.connect(self.identica_value, SIGNAL('clicked()'), self.request_identica_access_or_clear)

        if self.settings.value('statusnet_access_token').toBool():
            self.statusnet_value = QPushButton('Clear Status.net Auth')
        else:
            self.statusnet_value = QPushButton('Auth on Status.net')
        self._main_layout.addWidget(self.statusnet_value,2,1)
        self.connect(self.statusnet_value, SIGNAL('clicked()'), self.request_statusnet_access_or_clear)
        
        # self._main_layout.addWidget(QLabel('Password :'),1,0)
        # self.password_value = QLineEdit()
        # self.password_value.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        # self._main_layout.addWidget(self.password_value,1,1)

        self._main_layout.addWidget(QLabel('Refresh Interval (Minutes) :'),3,0)
        self.refresh_value = QSpinBox()
        self._main_layout.addWidget(self.refresh_value,3,1)

        self._main_layout.addWidget(QLabel('Display preferences :'),4,0)
        self.displayUser_value = QCheckBox('Display username')
        self._main_layout.addWidget(self.displayUser_value,4,1)

        self.displayAvatar_value = QCheckBox('Display avatar')
        self._main_layout.addWidget(self.displayAvatar_value,5,1)

        self.displayTimestamp_value = QCheckBox('Display timestamp')
        self._main_layout.addWidget(self.displayTimestamp_value,6,1)

        self.displayReplyTo_value = QCheckBox('Display reply to')
        self._main_layout.addWidget(self.displayReplyTo_value,7,1)

        self.useAutoRotation_value = QCheckBox('Use AutoRotation')
        self._main_layout.addWidget(self.useAutoRotation_value,8,1)

        self._main_layout.addWidget(QLabel('Other preferences :'),8,0)
        self.useNotification_value = QCheckBox('Use Notification')
        self._main_layout.addWidget(self.useNotification_value,9,1)

        self.useSerialization_value = QCheckBox('Use Serialization')
        self._main_layout.addWidget(self.useSerialization_value,10,1)

        self.useBitly_value = QCheckBox('Use Bit.ly')
        self._main_layout.addWidget(self.useBitly_value,11,1)

        self.useGPS_value = QCheckBox('Use GPS Geopositionning')
        self._main_layout.addWidget(self.useGPS_value,12,1)
 
        self._main_layout.addWidget(QLabel('Theme :'),13,0)
        self.theme_value = QComboBox()
        self._main_layout.addWidget(self.theme_value,13,1)
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

        if self.settings.value('useGPS').toInt()[0]:
            self.parent.positionStart()

        if isMAEMO:            
            if self.settings.value('useAutoRotation').toInt()[0]:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)

        if self.search_keyword != None:
            self.setWindowTitle("Khweeteur:"+unicode(self.search_keyword))      
        else:           
            self.setWindowTitle("Khweeteur")
                    
        self.setupMenu()
        self.setupMain()

        self.worker = None
        self.tweetsModel.display_screenname = self.settings.value("displayUser").toBool()
        self.tweetsModel.display_timestamp = self.settings.value("displayTimestamp").toBool()
        self.tweetsModel.display_avatar = self.settings.value("displayAvatar").toBool()

        self.tweetActionDialog = None
        
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
        self.tweetsView.custom_delegate.show_replyto = self.settings.value("displayReplyTo").toBool()
#        self.connect(self.tweetsView, SIGNAL('Clicked(const QModelIndex&)'), self.tweet_do_ask_action)

        self.connect(self.tweetsView, SIGNAL('doubleClicked(const QModelIndex&)'), self.tweet_do_ask_action)
        self.tweetsModel = KhweetsModel([], self.search_keyword)
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
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel._items[index.row()][2]            
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
                    #print 'DEBUG Follow:', user_screenname
                    if 'twitter' in self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("twitter_access_token_key").toString()!='':     
                                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                                  access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                                  access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                                api.SetUserAgent('Khweeteur/%s' % (__version__))
                                api.CreateFriendship(user_screenname)
                                self.notifications.info('You are now following %s on Twitter' % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn('Add %s to friendship failed on Twitter : %s' %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn('Add %s to friendship failed on Twitter : %s' %(user_screenname, str(e)))
                                print e   
                                                  
                    if 'http://identi.ca/api/' == self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("identica_access_token_key").toString()!='': 
                                api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                                  password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                                  access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                                  access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
                                api.SetUserAgent('Khweeteur/%s' % (__version__))    
                                api.CreateFriendship(user_screenname)
                                self.notifications.info('You are now following %s on Identi.ca' % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn('Add %s to friendship failed on Identi.ca : %s' %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn('Add %s to friendship failed on Identi.ca : %s' %(user_screenname, str(e)))
                                print e                                   

    def unfollow(self):  
        self.tweetActionDialog.accept()
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.unfollow)
        else:
            for index in self.tweetsView.selectedIndexes():
                if ((QMessageBox.question(self,
                           "Khweeteur",
                           "Unfollow : %s ?" % self.tweetsModel._items[index.row()][2],
                           QMessageBox.Yes|QMessageBox.Close)) == QMessageBox.Yes):
                    user_screenname = self.tweetsModel._items[index.row()][2]
                    #print 'DEBUG Follow:', user_screenname
                    if 'twitter' in self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("twitter_access_token_key").toString()!='':     
                                api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                                  access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                                  access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                                api.SetUserAgent('Khweeteur/%s' % (__version__))
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Twitter' % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn('Remove %s to friendship failed on Twitter : %s' %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn('Remove %s to friendship failed on Twitter : %s' %(user_screenname, str(e)))
                                print e                     

                    if 'http://identi.ca/api/' == self.tweetsModel._items[index.row()][8]:
                        try:
                            if self.settings.value("identica_access_token_key").toString()!='': 
                                api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                                  password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                                  access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                                  access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
                                api.SetUserAgent('Khweeteur/%s' % (__version__))    
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Identi.ca' % (user_screenname))
                        except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                            if type(e)==twitter.TwitterError:
                                self.notifications.warn('Remove %s to friendship failed on Identi.ca : %s' %(user_screenname,e.message))
                                print e.message
                            else:
                                self.notifications.warn('Remove %s to friendship failed on Identi.ca : %s' %(user_screenname, str(e)))
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
                        if self.settings.value("twitter_access_token_key").toString()!='':     
                            api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                              access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
                            api.SetUserAgent('Khweeteur/%s' % (__version__))
                            api.PostRetweet(tweetid)
                            self.notifications.info('Retweet sent to Twitter')
                    except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
                        if type(e)==twitter.TwitterError:
                            self.notifications.warn('Retweet to twitter failed : '+(e.message))
                            print e.message
                        else:
                            self.notifications.warn('Retweet to twitter failed : '+str(e))
                            print e                     

                if 'http://identi.ca/api/' == self.tweetsModel._items[index.row()][8]:
                    try:
                        if self.settings.value("identica_access_token_key").toString()!='': 
                            api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                              password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
                            api.SetUserAgent('Khweeteur/%s' % (__version__))    
                            api.PostRetweet(tweetid)
                            self.notifications.info('Retweet sent to Identi.ca')
                    except (twitter.TwitterError, StandardError, urllib2.HTTPError, urllib2.httplib.BadStatusLine, socket.timeout, socket.sslerror),e:
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
                if 'twitter' in self.tweetsModel._items[index.row()][8]:
                    try:
                        if self.settings.value("twitter_access_token_key").toString()!='':     
                            api = twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,password=KHWEETEUR_TWITTER_CONSUMER_SECRET, 
                                              access_token_key=str(self.settings.value("twitter_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("twitter_access_token_secret").toString()))
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
                        if self.settings.value("identica_access_token_key").toString()!='': 
                            api = twitter.Api(base_url='http://identi.ca/api/', username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                              password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                              access_token_key=str(self.settings.value("identica_access_token_key").toString()),
                                              access_token_secret=str(self.settings.value("identica_access_token_secret").toString()))    
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
            print 'test0'
            if self.parent.coordinates:
                print 'test1'
                geoposition = (self.parent.coordinates)
                print 'test2'
            else:
                geoposition = None
            self.tweetAction = KhweeteurActionWorker(self, 'tweet', unicode(self.tb_text.text()).encode('utf-8'), self.tb_text_replyid, self.tb_text_replytext, self.tb_text_replysource,geoposition)
            self.connect(self.tweetAction, SIGNAL("tweetSent()"), self.tweetSent)
            self.connect(self.tweetAction, SIGNAL("finished()"), self.tweetSentFinished)
            self.notifications.connect(self.tweetAction, SIGNAL('info(PyQt_PyObject)'), self.notifications.info)
            self.notifications.connect(self.tweetAction, SIGNAL('warn(PyQt_PyObject)'), self.notifications.warn)
            self.tweetAction.start()

    def refreshEnded(self):
        counter=self.tweetsModel.getNew()
        
        if (counter>0) and (self.settings.value('useNotification').toBool()) and not (self.isActiveWindow()):
            if self.search_keyword == None:
                self.notifications.notify('Khweeteur', str(counter)+' new tweet(s)',count=counter)
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def do_refresh_now(self):
        #print type(self.settings.value('useNotification').toString()), self.settings.value('useNotification').toString()
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
        self.worker = KhweeteurWorker(self, search_keyword=self.search_keyword)
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
        if isMAEMO:
            if self.settings.value('useAutoRotation').toInt()[0]:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.tweetsView.refreshCustomDelegate()
        self.tweetsView.custom_delegate.show_screenname = self.settings.value("displayUser").toBool()
        self.tweetsView.custom_delegate.show_timestamp = self.settings.value("displayTimestamp").toBool()
        self.tweetsView.custom_delegate.show_avatar = self.settings.value("displayAvatar").toBool()
        QObject.emit(self.tweetsModel, SIGNAL("dataChanged(const QModelIndex&, const QModelIndex &)"), self.tweetsModel.createIndex(0,0), self.tweetsModel.createIndex(0,len(self.tweetsModel._items)))
        if (self.settings.value("refreshInterval").toInt()[0]>0):
            self.timer.start(self.settings.value("refreshInterval").toInt()[0]*60*1000)
        else:
            self.timer.stop()
        if (self.settings.value("useGPS").toInt()[0]):
            self.parent.positionStart()
        else:
            self.parent.positionStop()
        for search_win in self.search_win:
            search_win.restartTimer()
#        if type(self.parent()) == KhweeteurWin:
#            self.parent().restartTimer()

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
        
    def do_search(self, search_keyword):
        swin = KhweeteurWin(search_keyword=unicode(search_keyword))
        self.search_win.append(swin)
        swin.show()
        
    def do_show_pref(self):        
        self.pref_win = KhweeteurPref(self)
        self.connect(self.pref_win, SIGNAL("save()"), self.restartTimer)
        self.pref_win.show()

    def do_about(self):
        self.aboutWin = KhweeteurAbout(self)

    @pyqtSlot()
    def activated_by_dbus(self):
        self.tweetsModel.getNewAndReset()
        self.activateWindow()

class Khweeteur(QApplication):

    activated_by_dbus = pyqtSignal()
    
    def __init__(self):
        
        QApplication.__init__(self, sys.argv)
        self.setOrganizationName("Khertan Software")
        self.setOrganizationDomain("khertan.net")
        self.setApplicationName("Khweeteur")
        self.version = __version__

        self.dbus_loop = DBusQtMainLoop()
        dbus.set_default_main_loop(self.dbus_loop)     
        install_excepthook()
        self.dbus_object = KhweeteurDBus()

        self.coordinates = None
        self.source = None
        
        self.run()

    def positionStart(self):
        if self.source is None:
            self.source = QGeoPositionInfoSource.createDefaultSource(None)
            if self.source is not None:
                self.source.setUpdateInterval(5000)
                self.source.positionUpdated.connect(self.positionUpdated)
                self.source.startUpdates()
                print "Waiting for a fix..."
    
    def positionStop(self):
        if self.source is not None:
            self.source.stopUpdates()
            self.source = None

    def positionUpdated(self,update):
        if update.isValid():
            self.coordinates = (update.coordinate().latitude(),update.coordinate().longitude())
            print 'Position Updated:',self.coordinates

    def handle_signal(self,*args):
        print 'received signal:', args        

    def crash_report(self):
        if os.path.isfile(os.path.join(CACHE_PATH, 'crash_report')):
            import urllib2
            import urllib
            if ((QMessageBox.question(None,
                "Khweeteur Crash Report",
                "An error occur on khweeteur in the previous launch. Report this bug on the bug tracker ?",
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
                os.remove(os.path.join(CACHE_PATH, 'crash_report'))
            except:
                pass
                
    def run(self):
        self.win = KhweeteurWin(self)
        self.dbus_object.attach_app(self)
        self.activated_by_dbus.connect(self.win.activated_by_dbus)
        self.crash_report()
        self.win.show()
        
if __name__ == '__main__':
    sys.exit(Khweeteur().exec_())