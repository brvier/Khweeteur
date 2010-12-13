#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4'''

USE_PYSIDE = False

if not USE_PYSIDE:
    import sip
    sip.setapi('QString', 2)
    sip.setapi('QVariant', 2)

    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

    try:
        from PyQt4.QtMobility.QtLocation import *
        noQtLocation = False
    except:
        noQtLocation = True

    try:   
        from PyQt4.QtMaemo5 import *
        isMAEMO = True
    except:
        isMAEMO = False

else:
    from PySide.QtCore import * #PySide
    from PySide.QtGui import * #PySide
    pyqtSlot = Slot
    pyqtSignal = Signal
    try:
        from PySide.QtMobility.QtLocation import * #PySide
        noQtLocation = False
    except:
        noQtLocation = True

    try:   
        from PySide.QtMaemo5 import * #PySide        
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

from settings import KhweeteurPref
from utils import *
from notifications import KhweeteurNotification

__version__ = '0.0.61'

# ~ class KhweeteurSingleNotify(QObject):
     # ~ def __init__(self,title,message,iconpath):
        # ~ QObject.__init__(self)

        # ~ n = pynotify.Notification(title, message, "khweeteur")
        # ~ n.set_icon_from_pixbuf(icon)


class KhweeteurActionWorker(QThread):

    '''ActionWorker : Post tweet in background'''

    def __init__(
        self,
        parent=None,
        action=None,
        data=None,
        data2=None,
        data3=None,
        data4=None,
        data5=None,
        ):
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

        if self.action == 'tweet':
            self.tweet()
        elif self.action == 'retweet':
            self.retweet()

    def tweet(self):
        '''Post a tweet'''

        try:
            status_text = self.data

            if int(self.settings.value('useBitly')) == 2:
                urls = re.findall("(?P<url>https?://[^\s]+)",
                                  status_text)
                if len(urls) > 0:
                    import bitly
                    a = bitly.Api(login='pythonbitly',
                                  apikey='R_06871db6b7fd31a4242709acaf1b6648'
                                  )

                for url in urls:
                    try:
                        short_url = a.shorten(url)
                        status_text = status_text.replace(url,
                                short_url)
                    except:
                        pass

            if not status_text.startswith(self.tb_text_replytext):
                self.tb_text_replyid = 0
                self.tb_text_replytext = ''
                self.tb_text_replysource = ''

            if self.geolocation:
                (latitude, longitude) = self.geolocation
            else:
                (latitude, longitude) = (None, None)

            if 'twitter' in self.tb_text_replysource \
                or self.tb_text_replyid == 0:
                if self.settings.value('twitter_access_token_key') \
                    != None:
                    api = \
                        twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                    api.SetUserAgent('Khweeteur/%s' % __version__)
                    if int(self.settings.value('useSerialization')) \
                        == 2:
                        api.PostSerializedUpdates(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    else:
                        api.PostUpdate(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    self.emit(SIGNAL('info(PyQt_PyObject)'),
                              'Tweet sent to Twitter')

            if 'http://identi.ca/api/' == self.tb_text_replysource \
                or self.tb_text_replyid == 0:
                if self.settings.value('identica_access_token_key') \
                    != None:
                    api = twitter.Api(base_url='http://identi.ca/api/',
                            username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                            password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                            access_token_key=str(self.settings.value('identica_access_token_key'
                            )),
                            access_token_secret=str(self.settings.value('identica_access_token_secret'
                            )))
                    api.SetUserAgent('Khweeteur/%s' % __version__)
                    if int(self.settings.value('useSerialization')) \
                        == 2:
                        api.PostSerializedUpdates(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    else:
                        api.PostUpdate(status_text,
                                in_reply_to_status_id=self.tb_text_replyid,
                                latitude=latitude, longitude=longitude)
                    self.emit(SIGNAL('info(PyQt_PyObject)'),
                              'Tweet sent to Identica')

            self.emit(SIGNAL('tweetSent()'))
        except twitter.TwitterError, e:

            self.emit(SIGNAL('warn(PyQt_PyObject)'), e.message)
            print e.message
        except:
            self.emit(SIGNAL('warn(PyQt_PyObject)'),
                      'A network error occur')
            print 'A network error occur'
            import traceback
            traceback.print_exc()


class KhweeteurCacheCleaner(QThread):

    ''' Thread class to remove old replies cached'''

    def __init__(self, parent=None, keyword=None):
        QThread.__init__(self, None)
        self.keyword = keyword

    def run(self):
        now = datetime.datetime.now()
        if self.keyword:
            for filepath in glob.glob(os.path.join(CACHE_PATH,
                    os.path.normcase(unicode(self.keyword.replace('/',
                    '_'))).encode('UTF-8')) + '/*'):  # FIXME
                filecdate = \
                    datetime.datetime.fromtimestamp(os.path.getctime(filepath))
                if (now - filecdate).days > 45:
                    os.remove(filepath)
        else:
            for filepath in glob.glob(REPLY_PATH + '/*'):
                filecdate = \
                    datetime.datetime.fromtimestamp(os.path.getctime(filepath))
                if (now - filecdate).days > 45:
                    os.remove(filepath)
            for filepath in glob.glob(TIMELINE_PATH + '/*'):
                filecdate = \
                    datetime.datetime.fromtimestamp(os.path.getctime(filepath))
                if (now - filecdate).days > 45:
                    os.remove(filepath)


class KhweeteurRefreshWorker(QThread):

    ''' Common Abstract class for the refresh thread '''

    # Signal

    errors = pyqtSignal(Exception)
    newStatuses = pyqtSignal(list)

    def __init__(self, parent=None, api=None):
        QThread.__init__(self, None)
        self.api = api
        self.settings = QSettings()

    def run(self):
        pass

    def getCacheFolder(self):
        if not hasattr(self, 'keywords'):
            folder_path = TIMELINE_PATH
        else:
            folder_path = os.path.join(CACHE_PATH,
                    os.path.normcase(unicode(self.keywords.replace('/',
                    '_'))).encode('UTF-8'))

        if not os.path.isdir(folder_path):
            try:
                os.makedirs(folder_path)
            except IOError, e:
                print 'getCacheFolder:', e

        return folder_path

    def serialize(self, statuses):

        folder_path = self.getCacheFolder()

        for status in statuses:
            pkl_file = open(os.path.join(folder_path, str(status.id)),
                            'wb')
            pickle.dump(status, pkl_file, pickle.HIGHEST_PROTOCOL)
            pkl_file.close()

    def downloadProfilesImage(self, statuses):
        for status in statuses:
            if type(status) != twitter.DirectMessage:
                cache = os.path.join(AVATAR_CACHE_FOLDER,
                        os.path.basename(status.user.profile_image_url.replace('/'
                        , '_')))
                if not os.path.exists(cache):
                    try:
                        urlretrieve(status.user.profile_image_url,
                                    cache)
                        im = Image.open(cache)
                        im = im.resize((50, 50))
                        im.save(os.path.splitext(cache)[0] + '.png',
                                'PNG')
                    except:
                        pass

    def removeAlreadyInCache(self, statuses):

        # Load cached statuses

        try:
            folder_path = self.getCacheFolder()

            for status in statuses:
                if os.path.exists(os.path.join(folder_path,
                                  str(status.id))):
                    statuses.remove(status)
        except StandardError, e:

            print e

    def getOneReplyContent(self, api, tid):
        rpath = os.path.join(self.getCacheFolder(), unicode(tid))
        rpath_reply = os.path.join(REPLY_PATH, unicode(tid))

        try:
            if os.path.exists(rpath):
                fhandle = open(rpath, 'rb')
                status = pickle.load(fhandle)
                fhandle.close()
                return status.text
            if os.path.exists(rpath_reply):
                fhandle = open(rpath_reply, 'rb')
                status = pickle.load(fhandle)
                fhandle.close()
                return status.text
            raise StandardError('Need to get it')
        except:
            try:
                status = api.GetStatus(tid)
                pkl_file = open(os.path.join(REPLY_PATH,
                                unicode(status.id)), 'wb')
                pickle.dump(status, pkl_file, pickle.HIGHEST_PROTOCOL)
                pkl_file.close()
                return status.text
            except:
                import traceback
                traceback.print_exc()

        return None

    def getRepliesContent(self, api, statuses):
        for status in statuses:
            if not hasattr(status, 'in_reply_to_status_id'):
                status.in_reply_to_status_text = None
            elif not status.in_reply_to_status_text \
                and status.in_reply_to_status_id:
                status.in_reply_to_status_text = \
                    self.getOneReplyContent(api,
                        status.in_reply_to_status_id)
            else:
                status.in_reply_to_status_text = None

    def applyOrigin(self, api, statuses):
        for status in statuses:
            status.origin = api.base_url


class KhweeteurHomeTimelineWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):

        # Get Home TimeLine

        try:
            statuses = \
                self.api.GetFriendsTimeline(since_id=self.settings.value('last_id/'
                     + self.api.base_url + '_GetFriendsTimeline'),
                    retweets=True)
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_GetFriendsTimeline', statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
            print e
        except:
            self.errors.emit(StandardError('A network error occurs'))
            import traceback
            traceback.print_exc()


class KhweeteurRetweetedByMeWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):

        # Get Retweeted by me

        try:
            statuses = \
                self.api.GetRetweetedByMe(since_id=self.settings.value('last_id/'
                     + self.api.base_url + '_GetRetweetedByMe_last_id'))
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_GetRetweetedByMe', statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError('A network error occurs'))
            import traceback
            traceback.print_exc()


class KhweeteurRetweetsOfMeWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):

        # Get Retweeted of me

        try:
            statuses = []
            mystatuses = \
                self.api.GetRetweetsOfMe(since_id=self.settings.value('last_id/'
                     + self.api.base_url + '_GetRetweetsOfMe_last_id'))
            for mystatus in mystatuses:
                statuses.extend(self.api.GetRetweetsForStatus(mystatus.id))
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_GetRetweetsOfMe', statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs'
                             )))
            import traceback
            traceback.print_exc()


class KhweeteurRepliesWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):

        # Get Retweeted by me

        try:
            statuses = \
                self.api.GetReplies(since_id=self.settings.value('last_id/'
                                     + self.api.base_url + '_GetReplies'
                                    ))
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_GetReplies', statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs'
                             )))
            import traceback
            traceback.print_exc()


class KhweeteurDMWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):
        try:
            statuses = \
                self.api.GetDirectMessages(since_id=self.settings.value('last_id/'
                     + self.api.base_url + '_DirectMessages'))
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_DirectMessages', statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs'
                             )))
            import traceback
            traceback.print_exc()


class KhweeteurMentionWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):
        try:
            statuses = \
                self.api.GetMentions(since_id=self.settings.value('last_id/'
                     + self.api.base_url + '_GetMentions'))
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_GetMentions', statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs'
                             )))
            import traceback
            traceback.print_exc()


class KhweeteurSearchWorker(KhweeteurRefreshWorker):

    def __init__(
        self,
        parent=None,
        api=None,
        keywords=None,
        geocode=None,
        ):
        KhweeteurRefreshWorker.__init__(self, None, api)
        self.keywords = keywords
        self.geocode = geocode

    def run(self):
        try:
            if self.geocode:
                statuses = self.api.GetSearch('', geocode=self.geocode)
            else:
                statuses = \
                    self.api.GetSearch(unicode(self.keywords).encode('UTF-8'
                        ), since_id=self.settings.value(self.keywords
                        + '/last_id/' + self.api.base_url))
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                if not self.geocode:
                    self.settings.setValue(self.keywords + '/last_id/'
                            + self.api.base_url, statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
        except:
            self.errors.emit(StandardError(self.tr('A network error occurs'
                             )))
            import traceback
            traceback.print_exc()


class KhweeteurWorker(QThread):

    ''' Thread to Refresh in background '''

    def __init__(
        self,
        parent=None,
        search_keyword=None,
        geocode=None,
        ):
        QThread.__init__(self, parent)
        self.settings = QSettings()
        self.search_keyword = search_keyword
        self.geocode = geocode

    def run(self):
        self.testCacheFolders()
        if not self.search_keyword and not self.geocode:
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
        try:
            if not os.path.isdir(REPLY_PATH):
                os.mkdir(REPLY_PATH)
        except:
            pass

    def refresh_search(self):
        self.error = None

        if self.settings.value('twitter_access_token_key') != None:
            api = twitter.Api(input_encoding='utf-8',
                              username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                              password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                              access_token_key=str(self.settings.value('twitter_access_token_key'
                              )),
                              access_token_secret=str(self.settings.value('twitter_access_token_secret'
                              )))
            api.SetUserAgent('Khweeteur/%s' % __version__)
            self.refresh_search_worker1 = KhweeteurSearchWorker(self,
                    api, self.search_keyword, self.geocode)
            self.refresh_search_worker1.errors.connect(self.errors)
            self.refresh_search_worker1.newStatuses.connect(self.newStatuses)
            self.refresh_search_worker1.start()

        if self.settings.value('identica_access_token_key') != None:
            api2 = twitter.Api(base_url='http://identi.ca/api/',
                               username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                               password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                               access_token_key=str(self.settings.value('identica_access_token_key'
                               )),
                               access_token_secret=str(self.settings.value('identica_access_token_secret'
                               )))
            api2.SetUserAgent('Khweeteur/%s' % __version__)
            self.refresh_search_worker2 = KhweeteurSearchWorker(self,
                    api2, self.search_keyword, self.geocode)
            self.refresh_search_worker2.errors.connect(self.errors)
            self.refresh_search_worker2.newStatuses.connect(self.newStatuses)
            self.refresh_search_worker2.start()

        if self.settings.value('twitter_access_token_key') != None \
            and self.settings.value('identica_access_token_key') \
            != None:
            while self.refresh_search_worker1.isRunning() == True \
                or self.refresh_search_worker2.isRunning() == True:
                self.sleep(2)
        elif self.settings.value('twitter_access_token_key') != None:
            while self.refresh_search_worker1.isRunning() == True:
                self.sleep(2)
        elif self.settings.value('identica_access_token_key') != None:
            while self.refresh_search_worker2.isRunning() == True:
                self.sleep(2)

        if self.error != None:
            if type(self.error) == twitter.TwitterError:
                print 'Error during twitter refresh : ', \
                    self.error.message
                self.emit(SIGNAL('info(PyQt_PyObject)'),
                          self.error.message)  # fix bug#404
            else:
                self.emit(SIGNAL('info(PyQt_PyObject)'),
                          self.tr('A network error occur'))

    def errors(self, error):
        self.error = error
        print 'errors : ', error

    def newStatuses(self, list):
        self.emit(SIGNAL('newStatuses(PyQt_PyObject)'), list)

    def refresh_unified(self, api):
        refresh_timeline_worker = KhweeteurHomeTimelineWorker(self, api)
        refresh_timeline_worker.errors.connect(self.errors)
        refresh_timeline_worker.newStatuses.connect(self.newStatuses)
        refresh_timeline_worker.start()

        refresh_retweetsofme_worker = KhweeteurRetweetsOfMeWorker(self,
                api)
        refresh_retweetsofme_worker.errors.connect(self.errors)
        refresh_retweetsofme_worker.newStatuses.connect(self.newStatuses)
        refresh_retweetsofme_worker.start()

        refresh_retweetedbyme_worker = \
            KhweeteurRetweetedByMeWorker(self, api)
        if 'twitter' in api.base_url:
            refresh_retweetedbyme_worker.errors.connect(self.errors)
            refresh_retweetedbyme_worker.newStatuses.connect(self.newStatuses)
            refresh_retweetedbyme_worker.start()

        refresh_replies_worker = KhweeteurRepliesWorker(self, api)
        refresh_replies_worker.errors.connect(self.errors)
        refresh_replies_worker.newStatuses.connect(self.newStatuses)
        refresh_replies_worker.start()

        refresh_dm_worker = KhweeteurDMWorker(self, api)
        refresh_dm_worker.errors.connect(self.errors)
        refresh_dm_worker.newStatuses.connect(self.newStatuses)
        refresh_dm_worker.start()

        refresh_mention_worker = KhweeteurMentionWorker(self, api)
        refresh_mention_worker.errors.connect(self.errors)
        refresh_mention_worker.newStatuses.connect(self.newStatuses)
        refresh_mention_worker.start()

        if 'twitter' in api.base_url:
            return [
                refresh_timeline_worker,
                refresh_retweetedbyme_worker,
                refresh_retweetsofme_worker,
                refresh_replies_worker,
                refresh_dm_worker,
                refresh_mention_worker,
                ]
        else:
            return [refresh_timeline_worker,
                    refresh_retweetsofme_worker,
                    refresh_replies_worker, refresh_dm_worker,
                    refresh_mention_worker]

    def refresh(self):
        self.error = None
        threads = []

        try:
            if self.settings.value('twitter_access_token_key') != None:

                # Login to twitter

                if not hasattr(self, 'twitter_api'):
                    self.twitter_api = \
                        twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                    self.twitter_api.SetUserAgent('Khweeteur/%s'
                            % __version__)
                threads.extend(self.refresh_unified(self.twitter_api))
        except twitter.TwitterError, e:

            print 'Error during twitter refresh : ', e.message
            self.emit(SIGNAL('info(PyQt_PyObject)'), e.message)
        except StandardError, e:
            self.emit(SIGNAL('info(PyQt_PyObject)'),
                      'A network error occur')
            print e

        try:
            identica_mlist = []
            if self.settings.value('identica_access_token_key') != None:
                if not hasattr(self, 'identica_api'):
                    self.identica_api = \
                        twitter.Api(base_url='http://identi.ca/api/',
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                    self.identica_api.SetUserAgent('Khweeteur/%s'
                            % __version__)
                threads.extend(self.refresh_unified(self.identica_api))
        except twitter.TwitterError, e:
            print 'Error during identi.ca refresh: ', e.message
            self.emit(SIGNAL('info(PyQt_PyObject)'), e.message)
        except:
            self.emit(SIGNAL('info(PyQt_PyObject)'),
                      'A network error occur')

        while any(thread.isRunning() == True for thread in threads):
            self.sleep(2)

        del threads

        if self.error != None:
            if type(self.error) == twitter.TwitterError:
                print 'Error during twitter refresh : ', \
                    self.error.message
                self.emit(SIGNAL('info(PyQt_PyObject)'),
                          self.error.message)  # fix bug#404
            else:
                self.emit(SIGNAL('info(PyQt_PyObject)'),
                          'A network error occur')


class KhweetsModel(QAbstractListModel):

    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    def __init__(self, keyword=None):
        QAbstractListModel.__init__(self)

        # Cache the passed data list as a class member.

        self._items = []  # Created_at, Status.id, ScreenName, Text, Rel_Created_at, Profile Image, Reply_ID, Reply_ScreenName, Reply_Text
        self._uids = []

        self._avatars = {}
        self._new_counter = 0
        self.now = time.time()
        self.khweets_limit = 50
        self.keyword = keyword

    def setLimit(self, limit):
        self.khweets_limit = limit

    def GetRelativeCreatedAt(self, timestamp):
        '''Get a human redable string representing the posting time

        Returns:
          A human readable string representing the posting time
        '''

        fudge = 1.25
        delta = long(self.now) - long(timestamp)

        if delta < 1 * fudge:
            return 'about a second ago'
        elif delta < 60 * (1 / fudge):
            return 'about %d seconds ago' % delta
        elif delta < 60 * fudge:
            return 'about a minute ago'
        elif delta < 60 * 60 * (1 / fudge):
            return 'about %d minutes ago' % (delta / 60)
        elif delta < 60 * 60 * fudge or delta / (60 * 60) == 1:
            return 'about an hour ago'
        elif delta < 60 * 60 * 24 * (1 / fudge):
            return 'about %d hours ago' % (delta / (60 * 60))
        elif delta < 60 * 60 * 24 * fudge or delta / (60 * 60 * 24) \
            == 1:
            return 'about a day ago'
        else:
            return 'about %d days ago' % (delta / (60 * 60 * 24))

    def rowCount(self, parent=QModelIndex()):
        if len(self._items) > self.khweets_limit:
            return self.khweets_limit
        else:
            return len(self._items)

    def refreshTimestamp(self):
        self.now = time.time()
        for (index, item) in enumerate(self._items):
            if index > self.khweets_limit:
                break
            try:

                # Created_at, Status.id, ScreenName, Text, Rel_Created_at, Profile Image, Reply_ID, Reply_ScreenName, Reply_Text

                self._items[index] = (
                    item[0],
                    item[1],
                    item[2],
                    item[3],
                    self.GetRelativeCreatedAt(item[0]),
                    item[5],
                    item[6],
                    item[7],
                    item[8],
                    item[9],
                    )
            except StandardError, e:
                print e

        QObject.emit(self,
                     SIGNAL('dataChanged(const QModelIndex&, const QModelIndex &)'
                     ), self.createIndex(0, 0), self.createIndex(0,
                     len(self._uids)))

    def addStatuses(self, uids):
        try:
            keys = []
            for uid in uids:
                try:
                    pkl_file = open(os.path.join(TIMELINE_PATH,
                                    str(uid)), 'rb')
                    status = pickle.load(pkl_file)
                    pkl_file.close()

                    self._appendStatusInList(status)

                    keys.append(status.id)
                except IOError, e:
                    print e
        except StandardError, e:

            print "We shouldn't got this error here :", e
            import traceback
            traceback.print_exc()

        if len(keys) > 0:
            self._items.sort()
            self._items.reverse()
            self._items = self._items[:self.khweets_limit]
            self._new_counter += len(keys)

            QObject.emit(self,
                         SIGNAL('dataChanged(const QModelIndex&, const QModelIndex &)'
                         ), self.createIndex(0, 0), self.createIndex(0,
                         len(self._items)))

            # self.serialize()

    def destroyStatus(self, index):
        self._items.pop(index.row())
        QObject.emit(self,
                     SIGNAL('dataChanged(const QModelIndex&, const QModelIndex &)'
                     ), self.createIndex(0, 0), self.createIndex(0,
                     len(self._items)))

    def getNewAndReset(self):
        counter = self._new_counter
        self._new_counter = 0
        return counter

    def getNew(self):
        return self._new_counter

    def setData(
        self,
        index,
        variant,
        role,
        ):
        return True

    def _appendStatusInList(self, status):
        if status.id in self._uids:
            return

        # Created_at, Status.id, ScreenName, Text, Rel_Created_at, Profile Image, Reply_ID, Reply_ScreenName, Reply_Text

        status.rel_created_at = \
            self.GetRelativeCreatedAt(status.created_at_in_seconds)

        if hasattr(status, 'user'):
            screen_name = status.user.screen_name
            profile_image = \
                os.path.basename(status.user.profile_image_url.replace('/'
                                 , '_'))
            if profile_image:
                if profile_image not in self._avatars:
                    try:
                        self._avatars[profile_image] = \
                            QPixmap(os.path.join(AVATAR_CACHE_FOLDER,
                                    profile_image))
                    except:
                        import traceback
                        traceback.print_exc()
        else:
            screen_name = status.sender_screen_name
            profile_image = None

        if not hasattr(status, 'in_reply_to_status_id'):
            status.in_reply_to_status_id = None

        if not hasattr(status, 'in_reply_to_screen_name'):
            status.in_reply_to_screen_name = None

        if not hasattr(status, 'in_reply_to_status_text'):
            status.in_reply_to_status_text = None

        # Created_at, Status.id, ScreenName, Text, Rel_Created_at, Profile Image, Reply_ID, Reply_ScreenName, Reply_Text, Origin

        self._items.append((  # 0
                              # 1
                              # 2
                              # 3
                              # 4
                              # 5
                              # 6
                              # 7
                              # 8
                              # 9
            status.created_at_in_seconds,
            status.id,
            screen_name,
            status.text,
            status.rel_created_at,
            profile_image,
            status.in_reply_to_status_id,
            status.in_reply_to_screen_name,
            status.in_reply_to_status_text,
            status.origin,
            ))

        self._uids.append(status.id)

    def _createCacheList(self, cach_path, uids):
        for uid in uids:
            uid = os.path.basename(uid)
            try:
                pkl_file = open(os.path.join(cach_path, uid), 'rb')
                status = pickle.load(pkl_file)
                pkl_file.close()

                self._appendStatusInList(status)
            except StandardError, e:

                KhweeteurNotification().info(self.tr('An error occurs while loading tweet : '
                        ) + str(uid))
                os.remove(os.path.join(cach_path, uid))

    def unSerialize(self):
        try:
            if not self.keyword:
                cach_path = TIMELINE_PATH
                uids = glob.glob(cach_path + '/*')
                self.cachecleanerworker = KhweeteurCacheCleaner()
                self.cachecleanerworker.start()
            else:
                self.cachecleanerworker = \
                    KhweeteurCacheCleaner(keyword=self.keyword)
                self.cachecleanerworker.start()
                cach_path = \
                    os.path.normcase(unicode(os.path.join(unicode(CACHE_PATH),
                        unicode(self.keyword.replace('/', '_')))))
                uids = glob.glob(cach_path + u'/*')

            if len(uids) == 0:
                print 'Cache cleared'
                self.settings = QSettings()
                if not self.keyword:
                    self.settings.remove('last_id')
                else:
                    self.settings.remove(self.keyword + '/last_id')
            else:
                self._createCacheList(cach_path, uids)
                self._items.sort()
                self._items.reverse()
        except StandardError, e:
            print 'unSerialize : ', e
            QObject.emit(self,
                         SIGNAL('dataChanged(const QModelIndex&, const QModelIndex &)'
                         ), self.createIndex(0, 0), self.createIndex(0,
                         len(self._items)))

    def data(self, index, role=Qt.DisplayRole):

        # 0 -> Created_at,
        # 1 -> Status.id,
        # 2 -> ScreenName,
        # 3 -> Text,
        # 4 -> Rel_Created_at,
        # 5 -> Profile Image,
        # 6 -> Reply_ID,
        # 7 -> Reply_ScreenName,
        # 8 -> Reply_Text
        # 9 -> Origine

        if role == Qt.DisplayRole:
            return self._items[index.row()][3]
        elif role == SCREENNAMEROLE:
            return self._items[index.row()][2]
        elif role == IDROLE:
            return self._items[index.row()][1]
        elif role == REPLYIDROLE:
            return self._items[index.row()][6]
        elif role == REPLYTOSCREENNAMEROLE:
            return self._items[index.row()][7]
        elif role == REPLYTEXTROLE:
            return self._items[index.row()][8]
        elif role == ORIGINROLE:
            return self._items[index.row()][9]
        elif role == Qt.ToolTipRole:
            return self._items[index.row()][4]
        elif role == Qt.DecorationRole:
            try:
                return self._avatars[self._items[index.row()][5]]
            except KeyError, keye:
                pass
        else:
            return None

    def wantsUpdate(self):
        QObject.emit(self, SIGNAL('layoutChanged()'))


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

    def sizeHint(self, option, index):
        '''Custom size calculation of our items'''

        uid = str(index.data(role=IDROLE)) + 'x' \
            + str(option.rect.width())
        try:
            return self.memoized_size[uid]
        except:
            size = QStyledItemDelegate.sizeHint(self, option, index)
            tweet = index.data(Qt.DisplayRole)

            # One time is enought sizeHint need to be fast

            if not self.fm:
                self.fm = QFontMetrics(option.font)
            height = self.fm.boundingRect(
                0,
                0,
                option.rect.width() - 75,
                800,
                int(Qt.AlignTop) | int(Qt.AlignLeft)
                    | int(Qt.TextWordWrap),
                tweet,
                ).height() + 40

            if self.show_replyto:
                reply_name = index.data(role=REPLYTOSCREENNAMEROLE)
                reply_text = index.data(role=REPLYTEXTROLE)
                if reply_name and reply_text:

                    # One time is enought sizeHint need to be fast

                    reply = 'In reply to @' + reply_name + ' : ' \
                        + reply_text
                    if not self.minifm:
                        if not self.miniFont:
                            self.miniFont = QFont(option.font)
                            self.miniFont.setPointSizeF(option.font.pointSizeF()
                                    * 0.80)
                        self.minifm = QFontMetrics(self.miniFont)
                    height += self.minifm.boundingRect(
                        0,
                        0,
                        option.rect.width() - 75,
                        800,
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap),
                        reply,
                        ).height()
                elif reply_name:
                    reply = 'In reply to @' + reply_name
                    if not self.minifm:
                        if not self.miniFont:
                            self.miniFont = QFont(option.font)
                            self.miniFont.setPointSizeF(option.font.pointSizeF()
                                    * 0.80)
                        self.minifm = QFontMetrics(self.miniFont)
                    height += self.minifm.boundingRect(
                        0,
                        0,
                        option.rect.width() - 75,
                        800,
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap),
                        reply,
                        ).height()

            if height < 70:
                height = 70

            self.memoized_size[uid] = QSize(size.width(), height)
            return self.memoized_size[uid]

    def paint(
        self,
        painter,
        option,
        index,
        ):
        '''Paint our tweet'''

        # Ugly hack ?

        (x1, y1, x2, y2) = option.rect.getCoords()
        if y1 < 0 and y2 < 0:
            return

        if not self.fm:
            self.fm = QFontMetrics(option.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole)

        # Instantiate font only one time !

        if not self.normFont:
            self.normFont = QFont(option.font)
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)

        painter.save()

        # Draw alternate ?

        if index.row() % 2 == 0:
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
                painter.drawPixmap(x1 + 10, y1 + 10, 50, 50, icon)

        # Draw tweet

        painter.setPen(self.text_color)
        new_rect = \
            painter.drawText(option.rect.adjusted(int(self.show_avatar)
                             * 70, 5, -4, 0), int(Qt.AlignTop)
                             | int(Qt.AlignLeft)
                             | int(Qt.TextWordWrap), tweet)

        # Draw Timeline

        if self.show_timestamp:
            time = index.data(Qt.ToolTipRole)
            painter.setFont(self.miniFont)
            painter.setPen(self.time_color)
            painter.drawText(option.rect.adjusted(70, 10, -10, -9),
                             int(Qt.AlignBottom) | int(Qt.AlignRight),
                             time)

        # Draw screenname

        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE)
            painter.setFont(self.miniFont)
            painter.setPen(self.user_color)
            painter.drawText(option.rect.adjusted(70, 10, -10, -9),
                             int(Qt.AlignBottom) | int(Qt.AlignLeft),
                             screenname)

        # Draw reply

        if self.show_replyto:
            reply_name = index.data(role=REPLYTOSCREENNAMEROLE)
            reply_text = index.data(role=REPLYTEXTROLE)
            if reply_name and reply_text:
                reply = 'In reply to @' + reply_name + ' : ' \
                    + reply_text
                painter.setFont(self.miniFont)
                painter.setPen(self.replyto_color)
                new_rect = \
                    painter.drawText(option.rect.adjusted(int(self.show_avatar)
                        * 70, new_rect.height() + 5, -4, 0),
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                        | int(Qt.TextWordWrap), reply)
            elif reply_name:
                reply = 'In reply to @' + reply_name
                painter.setFont(self.miniFont)
                painter.setPen(self.replyto_color)
                new_rect = \
                    painter.drawText(option.rect.adjusted(int(self.show_avatar)
                        * 70, new_rect.height() + 5, -4, 0),
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                        | int(Qt.TextWordWrap), reply)

        # Draw line

        painter.setPen(self.separator_color)
        painter.drawLine(x1, y2, x2, y2)

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

    def __init__(self, parent=None):
        QListView.__init__(self, parent)
        self.setWordWrap(True)
        self.refreshCustomDelegate()
        self.setEditTriggers(QAbstractItemView.SelectedClicked)
        self.setSpacing(0)
        self.setUniformItemSizes(False)
        self.setResizeMode(QListView.Adjust)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def keyPressEvent(self, event):
        if event.key() not in (Qt.Key_Up, Qt.Key_Down):
            self.parent().tb_text.setFocus()
            self.parent().tb_text.keyPressEvent(event)
        else:
            QListView.keyPressEvent(self, event)

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
        QMainWindow.__init__(self, parent)
        self.parent = parent

        self.settings = QSettings()

        if isMAEMO:
            try:  # Preferences not set yet
                if int(self.settings.value('useAutoRotation')) == 2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)

            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle(self.tr('Khweeteur About'))

        if isMAEMO:
            aboutScrollArea = QScrollArea(self)
            aboutScrollArea.setWidgetResizable(True)
            awidget = QWidget(aboutScrollArea)
            awidget.setMinimumSize(480, 1200)
            awidget.setSizePolicy(QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
            aboutScrollArea.setSizePolicy(QSizePolicy.Expanding,
                    QSizePolicy.Expanding)

        # Kinetic scroller is available on Maemo and should be on meego

            try:
                scroller = aboutScrollArea.property('kineticScroller')
                scroller.setEnabled(True)
            except:
                pass

            aboutLayout = QVBoxLayout(awidget)
        else:
            awidget = QWidget(self)
            aboutLayout = QVBoxLayout(awidget)

        aboutIcon = QLabel()
        if isMAEMO:
            aboutIcon.setPixmap(QIcon.fromTheme('khweeteur'
                                ).pixmap(128, 128))
        else:
            aboutIcon.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'icons', 'khweeteur.png')).pixmap(128,
                                128))

        aboutIcon.setAlignment(Qt.AlignCenter or Qt.AlignHCenter)
        aboutIcon.resize(128, 128)
        aboutLayout.addWidget(aboutIcon)

        aboutLabel = \
            QLabel(self.tr('''<center><b>Khweeteur</b> %s
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
                                   <br>creip on Twitter
                                   </center>''')
                   % __version__)
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

        if isMAEMO:
            awidget.setLayout(aboutLayout)
            aboutScrollArea.setWidget(awidget)
            self.setCentralWidget(aboutScrollArea)
        else:
            self.setCentralWidget(awidget)

        self.show()

    def open_website(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur'))

    def open_bugtracker(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur/bugs'
                                 ))


class KhweetAction(QDialog):

    def __init__(self, parent=None, title=''):
        QDialog.__init__(self, parent)

        self.setWindowTitle('Khweeteur : ' + title)

        self.settings = QSettings()

        if isMAEMO:
            try:
                if int(self.settings.value('useAutoRotation')) == 2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:

                   # No pref yet default is true

                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)

        _layout = QGridLayout(self)
        _layout.setSpacing(6)
        _layout.setMargin(11)

        self.reply = QPushButton('Reply')
        self.reply.setText(self.tr('&Reply'))
        _layout.addWidget(self.reply, 0, 0)

        self.retweet = QPushButton('Retweet')
        self.retweet.setText(self.tr('&Retweet'))
        _layout.addWidget(self.retweet, 0, 1)

        self.destroy_tweet = QPushButton('Destroy')
        self.destroy_tweet.setText(self.tr('&Destroy'))
        _layout.addWidget(self.destroy_tweet, 1, 1)

        self.openurl = QPushButton('Open URL')
        self.openurl.setText(self.tr('&Open URL'))
        _layout.addWidget(self.openurl, 1, 0)

        self.follow = QPushButton('Follow')
        self.follow.setText(self.tr('&Follow'))
        _layout.addWidget(self.follow, 0, 2)

        self.unfollow = QPushButton('Unfollow')
        self.unfollow.setText(self.tr('&Unfollow'))
        _layout.addWidget(self.unfollow, 1, 2)


class KhweeteurWin(QMainWindow):

    def __init__(self, parent=None, search_keyword=None):
        QMainWindow.__init__(self, None)
        self.parent = parent
        self.timer = QTimer()  # Fix bug #451

        self.search_keyword = search_keyword

        # crappy trick to avoid search win to be garbage collected

        self.search_win = []

        self.settings = QSettings()

        try:
            if int(self.settings.value('useGPS')) == 2:
                if self.parent != None:
                    self.parent.positionStart()
        except:
            pass

        if isMAEMO:
            try:  # Pref not set yet
                if int(self.settings.value('useAutoRotation')) == 2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        else:
            self.resize(300, 600)

        if self.search_keyword != None:
            if self.search_keyword != 'GeOSearH':
                self.setWindowTitle('Khweeteur:'
                                    + unicode(self.search_keyword))
            else:
                self.setWindowTitle('Khweeteur: Near Tweets')
        else:
            self.setWindowTitle('Khweeteur')

        self.setupMenu()
        self.setupMain()

        self.worker = None
        self.tweetsModel.display_screenname = \
            self.settings.value('displayUser') == '2'
        self.tweetsModel.display_timestamp = \
            self.settings.value('displayTimestamp') == '2'
        self.tweetsModel.display_avatar = \
            self.settings.value('displayAvatar') == '2'

        self.tweetActionDialog = None

        if self.search_keyword != None:
            if self.search_keyword == 'GeOSearH':
                if int(self.settings.value('useGPS')) != 2:  # FIX446
                    if QMessageBox.question(self, 'Khweeteur',
                            self.tr('This feature require activation of the gps, did you want to continue ?'
                            ), QMessageBox.Yes | QMessageBox.Close) \
                        == QMessageBox.Yes:
                        self.settings.setValue('useGPS', 2)
                        self.parent.positionStart()
                    else:
                        self.close()
                        return

        QTimer.singleShot(200, self.justAfterInit)

    def closeEvent(self, widget, *args):
        for win in self.search_win:
            win.close()

    def justAfterInit(self):

        if not noDBUS:
            from nwmanager import NetworkManager
            self.nw = NetworkManager(self.refresh_timeline)
        else:
            self.refresh_timeline

        self.notifications = KhweeteurNotification()

        self.connect(self.timer, SIGNAL('timeout()'),
                     self.timed_refresh)
        if int(self.settings.value('refreshInterval') > 0):
            self.timer.start(int(self.settings.value('refreshInterval'
                             )) * 60 * 1000)

        if not self.search_keyword:
            self.open_saved_search()

    def enterEvent(self, event):
        """
            Redefine the enter event to refresh timestamp
        """

        self.tweetsModel.refreshTimestamp()

    def timedUnserialize(self):
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
        self.tweetsModel.unSerialize()
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, False)

    def setupMain(self):

        self.tweetsView = KhweetsView(self)
        try:
            self.tweetsView.custom_delegate.show_screenname = \
                int(self.settings.value('displayUser')) == 2
            self.tweetsView.custom_delegate.show_timestamp = \
                int(self.settings.value('displayTimestamp')) == 2
            self.tweetsView.custom_delegate.show_avatar = \
                int(self.settings.value('displayAvatar')) == 2
            self.tweetsView.custom_delegate.show_replyto = \
                int(self.settings.value('displayReplyTo')) == 2
        except:
            pass

        self.connect(self.tweetsView,
                     SIGNAL('doubleClicked(const QModelIndex&)'),
                     self.tweet_do_ask_action)
        self.tweetsModel = KhweetsModel(self.search_keyword)
        try:  # If pref didn't exist
            self.tweetsModel.setLimit(int(self.settings.value('tweetHistory'
                    )))
        except:
            self.tweetsModel.setLimit(50)
        self.tweetsView.setModel(self.tweetsModel)
        self.setCentralWidget(self.tweetsView)

        self.toolbar = QToolBar('Toolbar')
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar)

        if isMAEMO:
            self.tb_update = QAction(QIcon.fromTheme('general_refresh'
                    ), 'Update', self)
        else:
            self.tb_update = \
                QAction(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'icons', 'refresh.png')), 'Update', self)

        self.tb_update.setShortcut('Ctrl+R')
        self.connect(self.tb_update, SIGNAL('triggered()'),
                     self.request_refresh)
        self.toolbar.addAction(self.tb_update)

        self.tb_text = QPlainTextEdit()
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.tb_text_replysource = ''
        self.tb_text.enabledChange(True)
        self.toolbar.addWidget(self.tb_text)

        self.tb_charCounter = QLabel('140')
        self.toolbar.addWidget(self.tb_charCounter)
        self.connect(self.tb_text, SIGNAL('textChanged()'),
                     self.countCharsAndResize)

        if isMAEMO:
            self.tb_tweet = QAction(QIcon.fromTheme('khweeteur'),
                                    'Tweet', self)
        else:
            self.tb_tweet = \
                QAction(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'icons', 'khweeteur.png')), 'Tweet', self)

        self.connect(self.tb_tweet, SIGNAL('triggered()'), self.tweet)
        self.toolbar.addAction(self.tb_tweet)

        if isMAEMO:
            self.tb_text.setFixedHeight(70)
        else:
            self.countCharsAndResize()

        # Actions not in toolbar

        self.tb_reply = QAction('Reply', self)
        self.tb_reply.setShortcut('Ctrl+M')
        self.connect(self.tb_reply, SIGNAL('triggered()'), self.reply)
        self.addAction(self.tb_reply)

        self.tb_scrolltop = QAction('Scroll to top', self)
        self.tb_scrolltop.setShortcut(Qt.CTRL + Qt.Key_Up)
        self.connect(self.tb_scrolltop, SIGNAL('triggered()'),
                     self.scrolltop)
        self.addAction(self.tb_scrolltop)

        self.tb_scrollbottom = QAction('Scroll to bottom', self)
        self.tb_scrollbottom.setShortcut(Qt.CTRL + Qt.Key_Down)
        self.connect(self.tb_scrollbottom, SIGNAL('triggered()'),
                     self.scrollbottom)
        self.addAction(self.tb_scrollbottom)

        QTimer.singleShot(200, self.timedUnserialize)

    def scrolltop(self):
        self.tweetsView.scrollToTop()

    def scrollbottom(self):
        self.tweetsView.scrollToBottom()

    def tweet_do_ask_action(self):
        user = None
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel.data(index, role=SCREENNAMEROLE)
        if user:
            self.tweetActionDialog = KhweetAction(self, user)
            self.connect(self.tweetActionDialog.reply,
                         SIGNAL('clicked()'), self.reply)
            self.connect(self.tweetActionDialog.openurl,
                         SIGNAL('clicked()'), self.open_url)
            self.connect(self.tweetActionDialog.retweet,
                         SIGNAL('clicked()'), self.retweet)
            self.connect(self.tweetActionDialog.follow,
                         SIGNAL('clicked()'), self.follow)
            self.connect(self.tweetActionDialog.unfollow,
                         SIGNAL('clicked()'), self.unfollow)
            self.connect(self.tweetActionDialog.destroy_tweet,
                         SIGNAL('clicked()'), self.destroy_tweet)
            self.tweetActionDialog.exec_()

    def countCharsAndResize(self):
        local_self = self.tb_text
        self.tb_charCounter.setText(unicode(140
                                    - len(local_self.toPlainText())))
        doc = local_self.document()
        cursor = local_self.cursorRect()
        s = doc.size()
        if isMAEMO:
            s.setHeight((s.height() + 1)
                        * (local_self.fontMetrics().lineSpacing() + 1)
                        - 21)
        else:
            s.setHeight((s.height() + 1)
                        * (local_self.fontMetrics().lineSpacing() + 1)
                        - 10)
        fr = local_self.frameRect()
        cr = local_self.contentsRect()
        local_self.setFixedHeight(min(370, s.height() + fr.height()
                                  - cr.height() - 1))

    def reply(self):
        if self.tweetActionDialog != None:
            self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel.data(index, role=SCREENNAMEROLE)
            self.tb_text_replyid = self.tweetsModel.data(index,
                    role=IDROLE)
            self.tb_text_replytext = '@' + user + ' '
            self.tb_text.setPlainText('@' + user + ' ')
            self.tb_text_replysource = self.tweetsModel.data(index,
                    role=ORIGINROLE)

#            print self.tb_text_replysource, self.tb_text_replyid, self.tweetsModel._items[index.row()][3]

    def open_url(self):
        import re
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            status = self.tweetsModel.data(index)
            try:
                urls = re.findall("(?P<url>https?://[^\s]+)", status)
                for url in urls:
                    QDesktopServices.openUrl(QUrl(url))
            except StandardError, e:
                print e

    def follow(self):
        self.tweetActionDialog.accept()
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.follow)
        else:
            for index in self.tweetsView.selectedIndexes():
                user_screenname = self.tweetsModel.data(index,
                        role=SCREENNAMEROLE)
                if QMessageBox.question(self, 'Khweeteur',
                        self.tr('Follow : %s ?') % user_screenname,
                        QMessageBox.Yes | QMessageBox.Close) \
                    == QMessageBox.Yes:
                    if 'twitter' in self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('twitter_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                        password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('twitter_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur/%s'
                                        % __version__)
                                api.CreateFriendship(user_screenname)
                                self.notifications.info(self.tr('You are now following %s on Twitter'
                                        ) % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname, str(e)))
                                print e

                    if 'http://identi.ca/api/' \
                        == self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('identica_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(base_url='http://identi.ca/api/'
                                        ,
                                        username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                        password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('identica_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('identica_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur/%s'
                                        % __version__)
                                api.CreateFriendship(user_screenname)
                                self.notifications.info(self.tr('You are now following %s on Identi.ca'
                                        ) % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname, str(e)))
                                print e

    def unfollow(self):
        self.tweetActionDialog.accept()
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.unfollow)
        else:
            for index in self.tweetsView.selectedIndexes():
                user_screenname = self.tweetsModel.data(index,
                        role=SCREENNAMEROLE)
                if QMessageBox.question(self, 'Khweeteur',
                        self.tr('Unfollow : %s ?') % user_screenname,
                        QMessageBox.Yes | QMessageBox.Close) \
                    == QMessageBox.Yes:

                    # print 'DEBUG Follow:', user_screenname

                    if 'twitter' in self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('twitter_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                        password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('twitter_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur/%s'
                                        % __version__)
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Twitter'
                                         % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname, str(e)))
                                print e

                    if 'http://identi.ca/api/' \
                        == self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('identica_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(base_url='http://identi.ca/api/'
                                        ,
                                        username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                        password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('identica_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('identica_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur/%s'
                                        % __version__)
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Identi.ca'
                                         % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname, str(e)))
                                print e

    def retweet(self):
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            if QMessageBox.question(self, 'Khweeteur',
                                    'Retweet this : %s ?'
                                    % self.tweetsModel.data(index),
                                    QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                tweetid = self.tweetsModel.data(index, role=IDROLE)
                if 'twitter' in self.tweetsModel.data(index,
                        role=ORIGINROLE):
                    try:
                        if self.settings.value('twitter_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.PostRetweet(tweetid)
                            self.notifications.info(self.tr('Retweet sent to Twitter'
                                    ))
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Retweet to twitter failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Retweet to twitter failed : '
                                    ) + str(e))
                            print e

                if 'http://identi.ca/api/' \
                    == self.tweetsModel.data(index, role=ORIGINROLE):
                    try:
                        if self.settings.value('identica_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(base_url='http://identi.ca/api/'
                                    ,
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.PostRetweet(tweetid)
                            self.notifications.info(self.tr('Retweet sent to Identi.ca'
                                    ))
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Retweet to identi.ca failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Retweet to identi.ca failed : '
                                    ) + str(e))
                            print e

    def destroy_tweet(self):
        self.tweetActionDialog.accept()
        for index in self.tweetsView.selectedIndexes():
            if QMessageBox.question(self, 'Khweeteur',
                                    self.tr('Destroy this : %s ?')
                                    % self.tweetsModel.data(index),
                                    QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                tweetid = self.tweetsModel.data(index, role=IDROLE)
                if 'twitter' in self.tweetsModel.data(index,
                        role=ORIGINROLE):
                    try:
                        if self.settings.value('twitter_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.DestroyStatus(tweetid)
                            self.tweetsModel.destroyStatus(index)
                            self.notifications.info('Status destroyed on Twitter'
                                    )
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn('Destroy status from twitter failed : '
                                     + e.message)
                            print e.message
                        else:
                            self.notifications.warn('Destroy status from twitter failed : '
                                     + str(e))
                            print e

                if 'http://identi.ca/api/' \
                    == self.tweetsModel.data(index, role=ORIGINROLE):
                    try:
                        if self.settings.value('identica_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(base_url='http://identi.ca/api/'
                                    ,
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.DestroyStatus(tweetid)
                            self.tweetsModel.destroyStatus(index)
                            self.notifications.info('Status destroyed on Identi.ca'
                                    )
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn('Destroy status from identi.ca failed : '
                                     + e.message)
                            print e.message
                        else:
                            self.notifications.warn('Destroy status from identi.ca failed : '
                                     + str(e))
                            print e

    def tweetSent(self):
        self.tb_text.setPlainText('')
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.request_refresh()  # Feature Request : 201

    def tweetSentFinished(self):
        self.tb_text.setEnabled(True)
        self.tb_tweet.setEnabled(True)

    def tweet(self):
        try:
            if not self.nw.device_has_networking:
                self.nw.request_connection_with_tmp_callback(self.tweet)
            else:
                raise StandardError('No network control')
        except:
            self.tb_text.setDisabled(True)
            self.tb_tweet.setDisabled(True)
            try:
                geoposition = self.parent.coordinates
            except:
                geoposition = None
            self.tweetAction = KhweeteurActionWorker(
                self,
                'tweet',
                unicode(self.tb_text.toPlainText()).encode('utf-8'),
                self.tb_text_replyid,
                self.tb_text_replytext,
                self.tb_text_replysource,
                geoposition,
                )
            self.connect(self.tweetAction, SIGNAL('tweetSent()'),
                         self.tweetSent)
            self.connect(self.tweetAction, SIGNAL('finished()'),
                         self.tweetSentFinished)
            self.notifications.connect(self.tweetAction,
                    SIGNAL('info(PyQt_PyObject)'),
                    self.notifications.info)
            self.notifications.connect(self.tweetAction,
                    SIGNAL('warn(PyQt_PyObject)'),
                    self.notifications.warn)
            self.tweetAction.start()

    def refreshEnded(self):
        counter = self.tweetsModel.getNew()
        if counter > 0 and int(self.settings.value('useNotification')) \
            == 2 and not self.isActiveWindow():
            if self.search_keyword == None:
                self.notifications.notify('Khweeteur', str(counter)
                        + ' new tweet(s)', count=counter)
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, False)

    def do_refresh_now(self):
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
        if self.search_keyword == 'GeOSearH':
            if self.parent.coordinates:
                geocode = (self.parent.coordinates[0],
                           self.parent.coordinates[1], '1km')  # FIXME
            else:
                geocode = None
        else:
            geocode = None
        if not self.worker:
            self.worker = KhweeteurWorker(self,
                    search_keyword=self.search_keyword, geocode=geocode)
            self.connect(self.worker,
                         SIGNAL('newStatuses(PyQt_PyObject)'),
                         self.tweetsModel.addStatuses)
            self.connect(self.worker, SIGNAL('finished()'),
                         self.refreshEnded)
            self.notifications.connect(self.worker,
                    SIGNAL('info(PyQt_PyObject)'),
                    self.notifications.info)
        else:
            self.worker.geocode = geocode
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
        if not self.worker:
            self.do_refresh_now()
        elif self.worker.isFinished() == True:
            self.do_refresh_now()

    def restartTimer(self):
        if isMAEMO:
            if int(self.settings.value('useAutoRotation')) == 2:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.tweetsView.refreshCustomDelegate()

        self.tweetsView.custom_delegate.show_screenname = \
            int(self.settings.value('displayUser')) == 2
        self.tweetsView.custom_delegate.show_timestamp = \
            int(self.settings.value('displayTimestamp')) == 2
        self.tweetsView.custom_delegate.show_avatar = \
            int(self.settings.value('displayAvatar')) == 2
        self.tweetsView.custom_delegate.show_replyto = \
            int(self.settings.value('displayReplyTo')) == 2
        QObject.emit(self.tweetsModel,
                     SIGNAL('dataChanged(const QModelIndex&, const QModelIndex &)'
                     ), self.tweetsModel.createIndex(0, 0),
                     self.tweetsModel.createIndex(0,
                     self.tweetsModel.rowCount()))
        if int(self.settings.value('refreshInterval')) > 0:
            self.timer.start(int(self.settings.value('refreshInterval'
                             )) * 60 * 1000)
        else:
            self.timer.stop()
        if self.parent != None:  # We are in a search so no need to start gps #Fix bug#399
            if int(self.settings.value('useGPS')) == 2:
                self.parent.positionStart()
            else:
                self.parent.positionStop()
        for search_win in self.search_win:
            search_win.restartTimer()

    def setupMenu(self):
        fileMenu = QMenu(self.tr('&Menu'), self)

        self.menuBar().addMenu(fileMenu)

        fileMenu.addAction(self.tr('&Preferences'), self.do_show_pref,
                           QKeySequence(self.tr('Ctrl+P', 'Preferences'
                           )))
        fileMenu.addAction(self.tr('&Near Tweets'), self.near_search,
                           QKeySequence(self.tr('Ctrl+N', 'Near Tweets'
                           )))
        fileMenu.addAction(self.tr('&Search'), self.open_search,
                           QKeySequence(self.tr('Ctrl+S', 'Search')))

        if self.search_keyword != None:
            keywords = self.settings.value('savedSearch')
            if keywords != None:
                if self.search_keyword in keywords:
                    fileMenu.addAction(self.tr('&Remove Search'),
                            self.del_search)
                else:
                    fileMenu.addAction(self.tr('&Save Search'),
                            self.save_search)
            else:
                fileMenu.addAction(self.tr('&Save Search'),
                                   self.save_search)

        fileMenu.addAction(self.tr('&About'), self.do_about)

    def del_search(self):
        keywords = self.settings.value('savedSearch')
        if not keywords:
            keywords = []
        elif type(keywords) == str:
            if self.search_keyword == keywords:
                keywords = []
        elif type(keywords) == list:
            try:
                keywords.remove(self.search_keyword)
            except:
                pass
        else:
            keywords.remove(self.search_keyword)
        self.settings.setValue('savedSearch', keywords)
        self.close()

    def save_search(self):
        keywords = self.settings.value('savedSearch')
        if not keywords:
            keywords = []
        elif type(keywords) == str:
            keywords = [keywords]
        keywords.append(self.search_keyword)
        self.settings.setValue('savedSearch', keywords)

    def open_saved_search(self):
        keywords = self.settings.value('savedSearch')
        if type(keywords) == str:
            keywords = [keywords]

        if keywords != None:
            for keyword in keywords:
                self.do_search(keyword)
        self.activateWindow()

    def open_search(self):
        (search_keyword, ok) = QInputDialog.getText(self,
                self.tr('Search'),
                self.tr('Enter the search keyword(s) :'))
        if ok == 1:
            self.do_search(search_keyword)

    def near_search(self):
        self.do_search('GeOSearH')

    def do_search(self, search_keyword):
        swin = KhweeteurWin(search_keyword=unicode(search_keyword),
                            parent=self.parent)
        self.search_win.append(swin)
        swin.show()

    def do_show_pref(self):
        self.pref_win = KhweeteurPref(self)
        self.connect(self.pref_win, SIGNAL('save()'), self.restartTimer)
        self.pref_win.show()

    def do_about(self):
        self.aboutWin = KhweeteurAbout(self)

#    @Slot()

    @pyqtSlot()
    def activated_by_dbus(self):
        self.tweetsModel.getNewAndReset()
        self.activateWindow()


class Khweeteur(QApplication):

    activated_by_dbus = pyqtSignal()

#    activated_by_dbus = Signal()

    def __init__(self):

        QApplication.__init__(self, sys.argv)
        self.setOrganizationName('Khertan Software')
        self.setOrganizationDomain('khertan.net')
        self.setApplicationName('Khweeteur')
        self.version = __version__

        if not noDBUS:
            try:
                self.dbus_loop = DBusQtMainLoop()
                dbus.set_default_main_loop(self.dbus_loop)
            except:
                pass

        install_excepthook(__version__)

        if not noDBUS:
            self.dbus_object = KhweeteurDBus()

        self.coordinates = None
        self.source = None

        self.run()

    def positionStart(self):
        '''Start the GPS with a 50000 refresh_rate'''

        if self.source is None:
            self.source = \
                QGeoPositionInfoSource.createDefaultSource(None)
            if self.source is not None:
                self.source.setUpdateInterval(50000)
                self.source.positionUpdated.connect(self.positionUpdated)
                self.source.startUpdates()

    def positionStop(self):
        '''Stop the GPS'''

        if self.source is not None:
            self.source.stopUpdates()
            self.source = None

    def positionUpdated(self, update):
        '''GPS Callback on update'''

        if update.isValid():
            self.coordinates = (update.coordinate().latitude(),
                                update.coordinate().longitude())

    def handle_signal(self, *args):
        pass  # print 'received signal:', args

    def crash_report(self):
        if os.path.isfile(os.path.join(CACHE_PATH, 'crash_report')):
            import urllib
            if QMessageBox.question(None,
                                    self.tr('Khweeteur Crash Report'),
                                    self.tr('An error occur on khweeteur in the previous launch. Report this bug on the bug tracker ?'
                                    ), QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                url = 'http://khertan.net/report.php'  # write ur URL here
                try:
                    filename = os.path.join(CACHE_PATH, 'crash_report')
                    output = open(filename, 'rb')
                    error = pickle.load(output)
                    output.close()

                    values = {'project': 'khweeteur',
                              'version': __version__,
                              'description': error}

                    data = urllib.urlencode(values)
                    req = urllib2.Request(url, data)
                    response = urllib2.urlopen(req)
                    the_page = response.read()
                except Exception, detail:
                    QMessageBox.question(None,
                            self.tr('Khweeteur Crash Report'),
                            self.tr('An error occur during the report : %s'
                            ) % detail, QMessageBox.Close)
                    return False

                if 'Your report have been successfully stored' \
                    in the_page:
                    QMessageBox.question(None,
                            self.tr('Khweeteur Crash Report'), '%s'
                            % the_page, QMessageBox.Close)
                    return True
                else:
                    QMessageBox.question(None,
                            self.tr('Khweeteur Crash Report'),
                            QMessageBox.Close)
                    return False
            try:
                os.remove(os.path.join(CACHE_PATH, 'crash_report'))
            except:
                import traceback
                traceback.print_exc()

    def run(self):
        self.win = KhweeteurWin(self)
        if not noDBUS:
            self.dbus_object.attach_app(self)
            self.activated_by_dbus.connect(self.win.activated_by_dbus)
        self.crash_report()
        self.win.show()


if __name__ == '__main__':
    sys.exit(Khweeteur().exec_())
