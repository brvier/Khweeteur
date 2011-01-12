#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4'''

from utils import *
import twitter
from urllib import urlretrieve
import urllib2
try:
    from PIL import Image
except:
    import Image

if not USE_PYSIDE:
    from PyQt4.QtCore import QThread, QSettings
else:
    from PySide.QtCore import QThread, QSettings
    
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
        if not hasattr(self,'folder_path'):
            if not hasattr(self, 'keywords'):
                self.folder_path = TIMELINE_PATH
            else:
                self.folder_path = os.path.join(CACHE_PATH,
                        os.path.normcase(unicode(self.keywords.replace('/',
                        '_'))).encode('UTF-8'))
    
            if not os.path.isdir(self.folder_path):
                try:
                    os.makedirs(self.folder_path)
                except IOError, e:
                    print 'getCacheFolder:', e
    
        return self.folder_path

    def setFavoriteInCache(self,tweetid,favorite):
        folder_path = self.getCacheFolder()
        try:
            path=os.path.join(folder_path, str(tweetid))
            
            fhandle = open(path, 'rb')
            status = pickle.load(fhandle)
            fhandle.close()            
            status.SetFavorited(favorite)
            pkl_file = open(path,'wb')
            pickle.dump(status, pkl_file, pickle.HIGHEST_PROTOCOL)
            pkl_file.close()
        except:
            print 'Serialization error : refresh_worker : setFavoriteInCache'

    def serialize(self, statuses):
        folder_path = self.getCacheFolder()

        for status in statuses:
            try:
                pkl_file = open(os.path.join(folder_path, str(status.id)),
                                'wb')
                pickle.dump(status, pkl_file, pickle.HIGHEST_PROTOCOL)
                pkl_file.close()
            except:
                print 'Serialization error : refresh_worker : serialize'

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
                    #print 'Debug : Already in cache',status.id
                    #import traceback
                    #traceback.print_stack()

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
            elif os.path.exists(rpath_reply):
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
                print 'Cannot write to reply path:',REPLY_PATH

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


class KhweeteurUserTimelineWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):

        # Get Home TimeLine
        try:
            statuses = \
                self.api.GetUserTimeline(since_id=self.settings.value('last_id/'
                     + self.api.base_url + '_GetUserTimeline'),
                    include_rts=True)
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
                        + '_GetUserTimeline', statuses[0].id)
        except twitter.TwitterError, e:
            self.errors.emit(e)
            print e
        except:
            self.errors.emit(StandardError('A network error occurs'))
            import traceback
            traceback.print_exc()


class KhweeteurHomeTimelineWorker(KhweeteurRefreshWorker):

    def __init__(self, parent=None, api=None):
        KhweeteurRefreshWorker.__init__(self, None, api)

    def run(self):

        # Get Home TimeLine
        try:
            statuses = \
                self.api.GetHomeTimeline(since_id=self.settings.value('last_id/'
                     + self.api.base_url + '_GetHomeTimeline'))
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
                        + '_GetHomeTimeline', statuses[0].id)
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
                     + self.api.base_url + '_GetRetweetedByMe'))
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
            print 'DEBUG Last Know Retweeted of me id:',self.settings.value('last_id/' + self.api.base_url + '_GetRetweetsOfMe'),':',self.api.base_url
            statuses = []
#FIXME
#            mystatuses = \
#                self.api.GetRetweetsOfMe(since_id=self.settings.value('last_id/'
#                     + self.api.base_url + '_GetRetweetsOfMe'))
            mystatuses = \
                self.api.GetRetweetsOfMe()
            for mystatus in mystatuses:
                statuses.extend(self.api.GetRetweetsForStatus(mystatus.id))
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_GetRetweetsOfMe', statuses[0].id)
                print 'DEBUG Last Know Retweeted of me id we register:',statuses[0].id
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.serialize(statuses)
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
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
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_DirectMessages', statuses[0].id)
            self.removeAlreadyInCache(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(self.api, statuses)
            self.serialize(statuses)
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])
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
                     + self.api.base_url + '_GetMentions'), \
                     include_rts = True)
            self.downloadProfilesImage(statuses)
            statuses.sort()
            statuses.reverse()
            if len(statuses) > 0:
                self.settings.setValue('last_id/' + self.api.base_url
                        + '_GetMentions', statuses[0].id)
            self.removeAlreadyInCache(statuses)
            self.applyOrigin(self.api, statuses)
            self.getRepliesContent(self.api, statuses)
            self.serialize(statuses)
            if len(statuses) > 0:
                self.newStatuses.emit([status.id for status in
                        statuses])

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

    newStatuses = pyqtSignal(list)
    info = pyqtSignal(unicode)

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
            api.SetUserAgent('Khweeteur')
            self.refresh_search_worker1 = KhweeteurSearchWorker(self,
                    api, self.search_keyword, self.geocode)
            self.refresh_search_worker1.errors.connect(self.errors)
            self.refresh_search_worker1.newStatuses.connect(self.transmitNewStatuses)
            self.refresh_search_worker1.start()

        if self.settings.value('identica_access_token_key') != None:
            api2 = twitter.Api(base_url='http://identi.ca/api',
                               username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                               password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                               access_token_key=str(self.settings.value('identica_access_token_key'
                               )),
                               access_token_secret=str(self.settings.value('identica_access_token_secret'
                               )))
            api2.SetUserAgent('Khweeteur')
            self.refresh_search_worker2 = KhweeteurSearchWorker(self,
                    api2, self.search_keyword, self.geocode)
            self.refresh_search_worker2.errors.connect(self.errors)
            self.refresh_search_worker2.newStatuses.connect(self.transmitNewStatuses)
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
                self.info.emit(self.error.message)  # fix bug#404
            else:
                self.info.emit(self.tr('A network error occur'))

    def errors(self, error):
        self.error = error
        print 'errors : ', error

    def transmitNewStatuses(self, alist):
#        self.emit(SIGNAL('newStatuses(list)'), list)
        print 'transmitNewStatuses',len(alist)
        self.newStatuses.emit(alist)

    def refresh_unified(self, api):
        refresh_timeline_worker = KhweeteurHomeTimelineWorker(self, api)
        refresh_timeline_worker.errors.connect(self.errors)
        refresh_timeline_worker.newStatuses.connect(self.transmitNewStatuses)
        refresh_timeline_worker.start()

        refresh_retweetsofme_worker = KhweeteurRetweetsOfMeWorker(self,
                api)
        refresh_retweetsofme_worker.errors.connect(self.errors)
        refresh_retweetsofme_worker.newStatuses.connect(self.transmitNewStatuses)
        refresh_retweetsofme_worker.start() #FIXME

        refresh_retweetedbyme_worker = \
            KhweeteurRetweetedByMeWorker(self, api)
        if 'twitter' in api.base_url:
            refresh_retweetedbyme_worker.errors.connect(self.errors)
            refresh_retweetedbyme_worker.newStatuses.connect(self.transmitNewStatuses)
            #refresh_retweetedbyme_worker.start() #FIXME

        refresh_replies_worker = KhweeteurRepliesWorker(self, api)
        refresh_replies_worker.errors.connect(self.errors)
        refresh_replies_worker.newStatuses.connect(self.transmitNewStatuses)
        #refresh_replies_worker.start() #FIXME

        refresh_dm_worker = KhweeteurDMWorker(self, api)
        refresh_dm_worker.errors.connect(self.errors)
        refresh_dm_worker.newStatuses.connect(self.transmitNewStatuses)
        refresh_dm_worker.start()

        refresh_mention_worker = KhweeteurMentionWorker(self, api)
        refresh_mention_worker.errors.connect(self.errors)
        refresh_mention_worker.newStatuses.connect(self.transmitNewStatuses)
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
            if bool(int(self.settings.value('twitter_access_token'))):

                # Login to twitter

                if not hasattr(self, 'twitter_api'):
                    self.twitter_api = \
                        twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                    self.twitter_api.SetUserAgent('Khweeteur')
                threads.extend(self.refresh_unified(self.twitter_api))
        except twitter.TwitterError, e:

            print 'Error during twitter refresh : ', e.message
            self.info.emit(e.message)
        except StandardError, e:
            self.info.emit('A network error occur')
            print e

        try:
            identica_mlist = []
            if bool(int(self.settings.value('identica_access_token'))):
                if not hasattr(self, 'identica_api'):
                    self.identica_api = \
                        twitter.Api(base_url='http://identi.ca/api',
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                    self.identica_api.SetUserAgent('Khweeteur')
                threads.extend(self.refresh_unified(self.identica_api))
        except twitter.TwitterError, e:
            print 'Error during identi.ca refresh: ', e.message
            self.info.emit(e.message)
        except:
            self.info.emit('A network error occur')

        while any(thread.isRunning() == True for thread in threads):
            self.sleep(2)

        del threads

        if self.error != None:
            if type(self.error) == twitter.TwitterError:
                print 'Error during twitter refresh : ', \
                    self.error.message
                self.info.emit(self.error.message)  # fix bug#404
            elif type(self.error) == urllib2.httplib.BadStatusLine:
                print 'Bad status line : ', self.error.line
            else:
                self.info.emit('A network error occur')
