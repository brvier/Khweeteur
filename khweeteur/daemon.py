#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

from __future__ import with_statement

import sys
import time
from PySide.QtCore import QSettings, Slot, QTimer, QCoreApplication
import atexit
import os
from signal import SIGTERM
import random

import logging

from retriever import KhweeteurRefreshWorker
from settings import SUPPORTED_ACCOUNTS

import cPickle as pickle
import re

from qwidget_gui import __version__

import dbus

import dbus.mainloop.glib

#from dbus.mainloop.qt import DBusQtMainLoop
#DBusQtMainLoop(set_as_default=True)

import twitter
import glob

try:
    from PIL import Image
except:
    import Image

import os.path
import dbus.service

from pydaemon.runner import DaemonRunner
from lockfile import LockTimeout

try:
    from QtMobility.Location import QGeoPositionInfoSource
except:
    print 'Pyside QtMobility not installed or broken'

# A hook to catch errors

def install_excepthook(version):
    '''Install an excepthook called at each unexcepted error'''

    __version__ = version

    def my_excepthook(exctype, value, tb):
        '''Method which replace the native excepthook'''

        # traceback give us all the errors information message like
        # the method, file line ... everything like
        # we have in the python interpreter

        import traceback
        trace_s = ''.join(traceback.format_exception(exctype, value, tb))
        print 'Except hook called : %s' % trace_s
        formatted_text = '%s Version %s\nTrace : %s' % ('Khweeteur',
                __version__, trace_s)
        logging.error(formatted_text)

    sys.excepthook = my_excepthook

_settings = None
_settings_synced = None
# Each time the DB changes, this is incremented.  Our current
# implementation just rereads the DB periodically.  A better approach
# would be to use the last modification time of the underlying file
# (determined using QSettings.fileName).
settings_db_generation = 0
def settings_db():
    """
    Return the setting's database, a QSettings instance, ensuring that
    it is sufficiently up to date.
    """
    global _settings
    global _settings_synced
    global settings_db_generation

    if _settings is None:
        # First time through.
        _settings = QSettings('Khertan Software', 'Khweeteur')
        _settings_synced = time.time()
        return _settings

    # Ensure that the in-memory settings database is synchronized
    # with the values on disk.
    now = time.time()
    if now - _settings_synced > 10:
        # Last synchronized more than 10 seconds ago.
        _settings.sync()
        _settings_synced = now
        settings_db_generation += 1

    return _settings

class KhweeteurDBusHandler(dbus.service.Object):

    def __init__(self):
        dbus.service.Object.__init__(self, dbus.SessionBus(),
                                     '/net/khertan/Khweeteur')
        self.m_id = 0

    def info(self, message):
        '''Display an information banner'''

        logging.debug('Dbus.info(%s)' % message)

        message = message.replace('\'', '')
        message = message.replace('<', '')
        message = message.replace('>', '')

        if message == '':
            import traceback
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            logging.error('Null info message : %s'
                          % repr(traceback.format_exception(exc_type,
                          exc_value, exc_traceback)))

        try:
            m_bus = dbus.SystemBus()
            m_notify = m_bus.get_object('org.freedesktop.Notifications',
                                        '/org/freedesktop/Notifications')
            iface = dbus.Interface(m_notify, 'org.freedesktop.Notifications')
            if not message.startswith('Khweeteur'):
                message = 'Khweeteur : ' + message
            iface.SystemNoteInfoprint(message)
        except:
            import traceback
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            logging.error('Error info message : %s'
                          % repr(traceback.format_exception(exc_type,
                          exc_value, exc_traceback)))

    @dbus.service.method(dbus_interface='net.khertan.Khweeteur',
                         in_signature='', out_signature='b')
    def isRunning(self):
        return True
        
    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur', signature='')
    def refresh_ended(self):
        pass

    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur', signature='us')
    def new_tweets(self, count, ttype):
        logging.debug('New tweet notification ttype : %s (%s)' % (ttype,
                      str(type(ttype))))
        settings = settings_db()
        #.value('showNotifications') == '2':                      

        if ((ttype == 'Mentions') and
            (settings.value('showDMNotifications') == '2')) \
            or ((ttype == 'DMs') and
                (settings.value('showDMNotifications') == '2')):
            m_bus = dbus.SystemBus()
            m_notify = m_bus.get_object('org.freedesktop.Notifications',
                                        '/org/freedesktop/Notifications')
            iface = dbus.Interface(m_notify, 'org.freedesktop.Notifications')

            if ttype == 'DMs' :
                msg = 'New DMs'
            elif ttype == 'Mentions':
                msg = 'New mentions'
            else:
                msg = 'New tweets'
            try:
                self.m_id = iface.Notify(
                    'Khweeteur',
                    self.m_id,
                    'khweeteur',
                    msg,
                    msg,
                    ['default', 'call'],
                    {
                        'category': 'khweeteur-new-tweets',
                        'desktop-entry': 'khweeteur',
                        'dbus-callback-default'
                            : 'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show_now'
                            ,
                        'count': count,
                        'amount': count,
                        },
                    -1,
                    )
            except:
                pass


class KhweeteurDaemon(QCoreApplication):
    def __init__(self):
        pass

    def run(self):
        QCoreApplication.__init__(self,sys.argv)
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        try:
            from PySide import __version_info__ as __pyside_version__
        except:
            __pyside_version__ = None
        try:
            from PySide.QtCore import __version_info__ as __qt_version__
        except:
            __qt_version__ = None

#        app = QCoreApplication(sys.argv)

        logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s %(levelname)-8s %(message)s',
                            datefmt='%a, %d %b %Y %H:%M:%S',
                            filename=os.path.expanduser('~/.khweeteur.log'), filemode='w')
        logging.info('Starting daemon %s' % __version__)
        logging.info('PySide version %s' % repr(__pyside_version__))
        logging.info('Qt Version %s' % repr(__qt_version__))

        try:
            os.nice(10)
        except:
            pass
            
        self.bus = dbus.SessionBus()
        self.bus.add_signal_receiver(self.update, path='/net/khertan/Khweeteur'
                                     , dbus_interface='net.khertan.Khweeteur',
                                     signal_name='require_update')
        self.bus.add_signal_receiver(self.post_tweet,
                                     path='/net/khertan/Khweeteur',
                                     dbus_interface='net.khertan.Khweeteur',
                                     signal_name='post_tweet')
        # We maintain the list of currently running jobs so that we
        # know when all jbos complete, to improve debugging output,
        # and because we have to: if the QThread object goes out of
        # scope and is gced while the thread is still running, Bad
        # Things Happen.
        self.threads = {}
        # Hash from an account's token_key to an authenticated twitter.Api.
        self.apis = {}
        # Hash from an account's token_key to the user's identifier.
        # If the value is None, the account was not successfully
        # authenticated.
        self.me_users = {}
        self.idtag = None

        # The last time the accounts were reread from the setting's
        # DB.
        self._accounts_read_at = None

        #On demand geoloc
        self.geoloc_source = None
        self.geoloc_coordinates = None

        # Cache Folder

        self.cache_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                       'cache')
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)

        # Post Folder

        self.post_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                      'topost')
        if not os.path.exists(self.post_path):
            os.makedirs(self.post_path)

        self.dbus_handler = KhweeteurDBusHandler()
                
        # mainloop = DBusQtMainLoop(set_as_default=True)

        settings = settings_db()
        if not settings.contains('refresh_interval'):
            refresh_interval = 600
        else:
            refresh_interval = int(settings.value('refresh_interval')) * 60

        self.utimer = QTimer()
        self.utimer.timeout.connect(self.update)
        self.utimer.start(refresh_interval * 1000)
                
        QTimer.singleShot(200, self.update)

        # gobject.timeout_add_seconds(refresh_interval, self.update, priority=gobject.PRIORITY_LOW)

        logging.debug('Timer added')
        self.exec_()
        logging.debug('Daemon stop')

    def post_tweet(
        self,
        shorten_url=True,
        serialize=True,
        text='',
        latitude='',
        longitude='',
        base_url='',
        action='',
        tweet_id='',
        ):
        """
        Queue a status update.

        shorten_url: A boolean indicating whether to shorten any URLs
            embedded in text.  If true, text is searched for any URLs
            and they are shortened using the configured URL shortener.

        serialize: A boolean indicating whether to send the tweet as
            multiple status updates if the length of text exceeds the
            single tweet limit.

        text: The body of the tweet.

        latitude, longitude: The latitude and longitude of where the
           status update was made

        base_url: Meaning depends on the value of 'action':

           If 'twitpic': the filename of the picture to tweet.

           If 'tweet': ''.

           If 'reply': the base url of the tweet to which this tweet
               is a reply.

           If 'retweet', 'delete', 'favorite', 'follow' or 'unfollow':
               the base url of the account.

        action: 'twitpic', 'tweet', 'reply', 'retweet', 'delete',
          'favorite', 'follow'

        tweet_id: If action is 'retweet', 'delete' or 'favorite', the
           tweet id of the tweet in question.

           If action is 'follow' or 'unfollow': the user id or the
               screen name of the user to follow.

           Otherwise, ''.

        The status update will actually be sent when do_posts is
        called.
        """

        post = {'shorten_url':shorten_url,
                'serialize':serialize,
                'text': text, 
                'latitude':latitude,
                'longitude':longitude,
                'base_url':base_url,
                'action':action,
                'tweet_id':tweet_id,
                }
        logging.debug('post_tweet %s' % (repr(post),))

        if not os.path.isdir(self.post_path):
            try:
                os.makedirs(self.post_path)
            except IOError, e:
                logging.error('post_tweet %s: creating directory %s: %s'
                              % (repr(post), self.post_path, e))

        filename = os.path.join(self.post_path,
                                str(time.time()) + '-' + str (random.random()))
        logging.debug('Saving status update %s to %s'
                      % (post.__repr__(), filename))
        with open(filename, 'wb') as fhandle:
            pickle.dump(post, fhandle, pickle.HIGHEST_PROTOCOL)

#        self.do_posts() #Else we loop when action create a post

    def get_api(self, account):
        """
        Return an unauthenticated twitter.Api object cor
        """
        token_key = account['token_key']
        api = self.apis.get(token_key, None)
        if api is None:
            api = twitter.Api(username=account['consumer_key'],
                              password=account['consumer_secret'],
                              access_token_key=token_key,
                              access_token_secret=account['token_secret'],
                              base_url=account['base_url'])
            api.SetUserAgent('Khweeteur')
            self.apis[token_key] = api

            try:
                id = api.VerifyCredentials().id
            except Exception, err:
                id = None
                logging.error(
                    'Failed to verify the credentials for account %s: %s'
                    % (account, str(err)))

            self.me_users[token_key] = id

        return api

    @property
    def accounts(self):
        """A list of dictionaries where each dictionary
        describes an account."""
        settings = settings_db()

        if self._accounts_read_at == settings_db_generation:
            logging.debug("accounts(): Using cached version (%d accounts)."
                          % (len(self._accounts),))
            return self._accounts
        logging.debug("accounts(): Reloading accounts from settings file.")

        nb_accounts = settings.beginReadArray('accounts')
        accounts = []
        for index in range(nb_accounts):
            settings.setArrayIndex(index)
            account = dict((key, settings.value(key))
                           for key in settings.allKeys())
            accounts.append(account)

            logging.debug("accounts(): Account %d: %s"
                          % (index + 1, repr(account)))
        settings.endArray()
        logging.debug("accounts(): Loaded %d accounts" % (len(accounts),))

        self._accounts = accounts
        self._accounts_read_at = settings_db_generation

        return accounts

    def geolocStart(self):
        '''Start the GPS with a 50000 refresh_rate'''
        self.geoloc_coordinates = None
        if self.geoloc_source is None:
            try:
                self.geoloc_source = \
                    QGeoPositionInfoSource.createDefaultSource(None)
            except:
                self.geoloc_source = None
                self.geoloc_coordinates = (0,0)
                print 'PySide QtMobility not installed or package broken'
            if self.geoloc_source is not None:
                self.geoloc_source.setUpdateInterval(50000)
                self.geoloc_source.positionUpdated.connect(self.geolocUpdated)
                self.geoloc_source.startUpdates()

    def geolocStop(self):
        '''Stop the GPS'''

        self.geoloc_coordinates = None
        if self.geoloc_source is not None:
            self.geoloc_source.stopUpdates()
            self.geoloc_source = None

    def geolocUpdated(self, update):
        '''GPS Callback on update'''

        if update.isValid():
            self.geoloc_coordinates = (update.coordinate().latitude(),
                                       update.coordinate().longitude())
            self.update()
            self.geolocStop()
        else:
            print 'GPS Update not valid'

    def do_posts(self):
        """
        Post any queued posts.
        """
        settings = settings_db()

        items = glob.glob(os.path.join(self.post_path, '*'))

        if len(items)>0:
            if (settings.value('useGPS')=='2') and (settings.value('useGPSOnDemand')=='2'):
                if self.geoloc_source == None:
                    self.geolocStart()
                if self.geoloc_coordinates == None:
                    return

        for item in items:
            self.do_post(item, settings)

    def do_post(self, item, settings=None):
        """
        Post a status update.  item is the name of a file containing a
        pickled status update.
        """
        if settings is None:
            settings = settings_db()

        try:
            with open(item, 'rb') as fhandle:
                post = pickle.load(fhandle)

            logging.debug('Posting %s: %s' % (item, repr(post)))

            text = post['text']
            if post['shorten_url'] == 1:
                urls = re.findall("(?:^|\s)(?P<url>https?://[^\s]+)", text)
                if len(urls) > 0:
                    import bitly
                    a = bitly.Api(login='pythonbitly',
                            apikey='R_06871db6b7fd31a4242709acaf1b6648')

                    for url in urls:
                        try:
                            short_url = a.shorten(url)
                            text = text.replace(url, short_url)
                        except:
                            pass

            if (settings.value('useGPS')=='2') and (settings.value('useGPSOnDemand')=='2'):
                post['latitude'], post['longitude'] = \
                    self.geoloc_coordinates

            if not post['latitude']:
                post['latitude'] = None
            else:
                post['latitude'] = int(post['latitude'])
            if not post['longitude']:
                post['longitude'] = None
            else:
                post['longitude'] = int(post['longitude'])

            # Loop on accounts
            did_something = False
            for account in self.accounts:
                aid = account['base_url'] + ';' + account['token_key']

                # Reply

                acted = True
                if post['action'] == 'reply':  # Reply tweet
                    if aid == post['base_url']:
                        api = self.get_api(account)
                        if post['serialize'] == 1:
                            api.PostSerializedUpdates(text,
                                    in_reply_to_status_id=int(post['tweet_id'
                                    ]), latitude=post['latitude'],
                                    longitude=post['longitude'])
                        else:
                            api.PostUpdate(text,
                                    in_reply_to_status_id=int(post['tweet_id'
                                    ]), latitude=post['latitude'],
                                    longitude=post['longitude'])
                        logging.debug('Posted reply %s : %s' % (text,
                                post['tweet_id']))
                        if settings.contains('ShowInfos'):
                            if settings.value('ShowInfos') == '2':
                                self.dbus_handler.info('Khweeteur: Reply posted to '
                                 + account['name'])
                elif post['action'] == 'retweet':

                    # Retweet

                    if aid == post['base_url']:
                        api = self.get_api(account)
                        api.PostRetweet(tweet_id=int(post['tweet_id']))
                        logging.debug('Posted retweet %s'
                                % (post['tweet_id'], ))
                        if settings.contains('ShowInfos'):
                            if settings.value('ShowInfos') == '2':
                                self.dbus_handler.info('Khweeteur: Retweet posted to '
                                     + account['name'])
                elif post['action'] == 'tweet':

                    # Else "simple" tweet

                    if aid == post['base_url']:
                        api = self.get_api(account)
                        if post['serialize'] == 1:
                            api.PostSerializedUpdates(text,
                                    latitude=post['latitude'],
                                    longitude=post['longitude'])
                        else:
                            api.PostUpdate(text,
                                    latitude=post['latitude'],
                                    longitude=post['longitude'])
                        logging.debug('Posted %s' % (text, ))
                        if settings.contains('ShowInfos'):
                            if settings.value('ShowInfos') == '2':
                                self.dbus_handler.info('Khweeteur: Status posted to '
 + account['name'])
                elif post['action'] == 'delete':
                    if aid == post['base_url']:
                        api = self.get_api(account)
                        api.DestroyStatus(int(post['tweet_id']))
                        path = os.path.join(os.path.expanduser('~'),
                                '.khweeteur', 'cache', 'HomeTimeline',
                                post['tweet_id'])
                        os.remove(path)
                        logging.debug('Deleted %s' % (post['tweet_id'],
                                ))
                        if settings.contains('ShowInfos'):
                            if settings.value('ShowInfos') == '2':
                                self.dbus_handler.info('Khweeteur: Status deleted on '
 + account['name'])
                elif post['action'] == 'favorite':
                    if aid == post['base_url']:
                        api = self.get_api(account)
                        api.CreateFavorite(int(post['tweet_id']))
                        logging.debug('Favorited %s' % (post['tweet_id'
                                ], ))
                elif post['action'] == 'follow':
                    if aid == post['base_url']:
                        api = self.get_api(account)
                        friend = api.CreateFriendship(post['tweet_id'])
                        logging.debug('Follow %s (account: %s) -> %s'
                                      % (repr(post), repr(account), friend))
                elif post['action'] == 'unfollow':
                    if aid == post['base_url']:
                        api = self.get_api(account)
                        friend = api.DestroyFriendship(post['tweet_id'])
                        logging.debug('Unfollow %s (account: %s) -> %s'
                                      % (repr(post), repr(account), friend))
                elif post['action'] == 'twitpic':
                    if account['base_url'] \
                            == SUPPORTED_ACCOUNTS[0]['base_url']:
                        api = self.get_api(account)
                        import twitpic
                        twitpic_client = \
                            twitpic.TwitPicOAuthClient(consumer_key=api._username,
                                consumer_secret=api._password,
                                access_token=api._oauth_token.to_string(),
                                service_key='f9b7357e0dc5473df5f141145e4dceb0'
                                )
                        params = {}
                        params['media'] = 'file://' + post['base_url']
                        params['message'] = unicode(post['text'])
                        response = twitpic_client.create('upload',
                                params)
                        if 'url' in response:
                            self.post_tweet(
                                post['shorten_url'],
                                post['serialize'],
                                unicode(response['url']) + u' : '
                                    + post['text'],
                                post['latitude'],
                                post['longitude'],
                                '',
                                'tweet',
                                '',
                                )
                        else:

                            raise StandardError('No twitpic url')
                else:
                    acted = False
                    logging.error('Processing post %s: unknown action: %s'
                                  % (str(post), post['action']))
                if acted:
                    did_something = True

            if not did_something:
                logging.error('Post %s not handled by any accounts!'
                              % (str(post)))
                if settings.value('ShowInfos', None) == '2':
                    self.dbus_handler.info(
                        'Khweeteur: Post %s not handled by any accounts!'
                        % (str(post)))

            logging.debug("post processed, deleting %s" % item)
            try:
                os.remove(item)
            except OSError, exception:
                logging.error("remove (processed) file %s: %s"
                              % (item, str(exception)))
        except twitter.TwitterError, err:

            if err.message == 'Status is a duplicate.':
                logging.error('Do_posts (remove): %s' % (err.message, ))
                os.remove(item)
            elif 'ID' in err.message:
                logging.error('Do_posts (remove): %s' % (err.message, ))
                os.remove(item)
            else:
                logging.error('Do_posts : %s' % (err.message, ))
            if settings.contains('ShowInfos'):
                if settings.value('ShowInfos') == '2':
                    self.dbus_handler.info('Khweeteur: Error occured while posting: '
                             + err.message)
        except StandardError, err:
            logging.error('Do_posts : %s' % (str(err), ))
            if settings.contains('ShowInfos'):
                if settings.value('ShowInfos') == '2':
                    self.dbus_handler.info('Khweeteur: Error occured while posting: '
                             + str(err))
            import traceback
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            logging.error('%s' % repr(traceback.format_exception(exc_type,
                          exc_value, exc_traceback)))
        except Exception, err:

            # Emitting the error will block the other tweet post
            # raise #can t post, we will keep the file to do it later

            logging.error('Do_posts : %s' % str(err))
            if settings.contains('ShowInfos'):
                if settings.value('ShowInfos') == '2':
                    self.dbus_handler.info('Khweeteur: Error occured while posting: '
                             + str(err))
        except:
            logging.error('Do_posts : Unknown error')

    @Slot()
    def update(self):
        try:
            self.do_posts()
            self.retrieve()
        except Exception:
            import traceback
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            logging.error('%s' % repr(traceback.format_exception(exc_type,
                          exc_value, exc_traceback)))

    def retrieve(self, options=None):
        logging.debug('Start update')
        settings = settings_db()

        showInfos = False
        if settings.contains('ShowInfos'):
            if settings.value('ShowInfos') == '2':
                showInfos = True

        useGPS = False
        if settings.contains('useGPS'):
            if settings.value('useGPS') == '2':
                useGPS = True

        if len(self.threads)>0:
            for t, job in self.threads.items():
                # Check whether the threads are really running.  the
                # finished and terminate signals appear rather
                # unreliable.
                logging.debug("%s: %s: isRunning: %d; isFinished: %d"
                              % (str(t), job, t.isRunning(), t.isFinished()))
                if t.isFinished():
                    self.thread_exited(t)

            if len(self.threads)>0:
                # Update in progress.
                logging.info('Update in progress (%s jobs still running: %s)'
                             % (len (self.threads), str(self.threads.values())))
                return            

        # Remove old tweets in cache according to history prefs

        try:
            keep = int(settings.value('tweetHistory'))
        except:
            keep = 60

        for (root, folders, files) in os.walk(self.cache_path):
            for folder in folders:
                statuses = []
                filenames = {}
                uids = glob.glob(os.path.join(root, folder, '*'))
                for uid in uids:
                    uid = os.path.basename(uid)
                    try:
                        filename = os.path.join(root, folder, uid)
                        with open(filename, 'rb') as pkl_file:
                            status = pickle.load(pkl_file)
                        filenames[status] = filename
                        statuses.append(status)
                    except StandardError, err:
                        logging.debug('Error in cache cleaning: %s,%s'
                                % (err, os.path.join(root, uid)))
                statuses.sort(key=lambda status: \
                              status.created_at_in_seconds, reverse=True)
                for status in statuses[keep:]:
                    try:
                        os.remove(filenames[status])
                    except StandardError, err:
                        logging.debug('Cannot remove: %s : %s'
                                      % (str(status.id), str(err)))

        nb_searches = settings.beginReadArray('searches')
        searches = []
        for index in range(nb_searches):
            settings.setArrayIndex(index)
            searches.append(settings.value('terms'))
        settings.endArray()

        nb_lists = settings.beginReadArray('lists')
        lists = []
        for index in range(nb_lists):
            settings.setArrayIndex(index)
            lists.append((settings.value('id'), settings.value('user')))
        settings.endArray()

        for account in self.accounts:
            api = self.get_api(account)
            me_user_id = self.me_users[account['token_key']]

            # If have an authorized user:
            if me_user_id:

                def spawn(thing):
                    # Worker
                    try:
                        t = KhweeteurRefreshWorker(api, thing, me_user_id)
                        t.error.connect(self.dbus_handler.info)
                        t.finished.connect(self.athread_end)
                        t.terminated.connect(self.athread_end)
                        t.new_tweets.connect(self.dbus_handler.new_tweets)
                        t.start()
                        self.threads[t] = (thing + ' on ' + account['base_url']
                                           + ';' + account['token_key'])
                    except Exception, err:
                        logging.error(
                            'Creating worker for account %s, job %s: %s'
                            % (str(account), thing, str(err)))

                spawn('HomeTimeline')
                spawn('Mentions')
                spawn('DMs')

                # Start searches thread
                for terms in searches:
                    spawn('Search:' + terms)

                # Start retrieving the list
                spawn('RetrieveLists')

                # Near retrieving
                if useGPS:
                    if not self.geoloc_source:
                        self.geolocStart()
                    if self.geoloc_coordinates:
                        spawn('Near:%s:%s'
                              % (str(self.geoloc_coordinates[0]),
                                 str(self.geoloc_coordinates[1])))

                # Start lists thread
                for (list_id, user) in lists:
                    spawn('List:' + user + ':' + list_id)

    @Slot()
    def kill_thread(self):
        for thread, tid in self.threads.items():
            if not thread.isFinished():
                logging.debug("Terminating thread %s: %s"
                              % (str(thread), tid))
                thread.terminate()

    def thread_exited(self, thread):
        logging.debug("Job %s finished; Jobs still running: %s"
                      % (self.threads[thread],
                         str ([v for k, v in self.threads.items()
                               if k != thread])))
        try:
            del self.threads[thread]
        except ValueError, exception:
            logging.debug("Unregistered thread %s called athread_end (%s)!"
                          % (str(thread), str (exception)))

        if len(self.threads) == 0:
            self.dbus_handler.refresh_ended()
            logging.debug('Finished update')

    @Slot()
    def athread_end(self):
        if self.sender() not in self.threads:
            logging.debug("athread_end called by %s, but not in self.threads"
                          % (self.sender()))
            return

        return self.thread_exited(self.sender())

if __name__ == '__main__':
    install_excepthook(__version__)

    def usage(exit_status=2):
        print ('usage: %s start|stop|restart|startfromprefs|debug'
               % sys.argv[0])
        sys.exit(2)

    if len(sys.argv) != 2:
        usage()

    detach_process = None
    if sys.argv[1] == 'debug':
        detach_process = False
        sys.argv[1] = 'start' 

    if 'startfromprefs' == sys.argv[1]:
        if settings_db().value('useDaemon') == '2':
            sys.argv[1] = 'start'
        else:
            sys.exit(0)

    if sys.argv[1] in ['start', 'stop', 'restart']:
        khweeteurdaemon = KhweeteurDaemon()

        if detach_process is None:
            khweeteurdaemon.stdin_path = "/dev/null"
            khweeteurdaemon.stdout_path = os.path.expanduser(
                '~/.khweeteur.log.out')
            khweeteurdaemon.stderr_path = os.path.expanduser(
                '~/.khweeteur.log.err')

        khweeteurdaemon.pidfile_path = os.path.expanduser('~/.khweeteur.pid')
        khweeteurdaemon.pidfile_timeout = 3

        khweeteurdaemon.detach_process = detach_process

        runner = DaemonRunner(khweeteurdaemon)
        try:
            runner.do_action()
        except LockTimeout:
            print "Failed to acquire lock."
            sys.exit(1)
    else:
        logging.error('Unknown command')
        print "Unknown command: '%s'" % (sys.argv[1],)
        usage(2)
