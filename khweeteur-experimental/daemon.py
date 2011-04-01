#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

#import sip
#sip.setapi('QString', 2)
#sip.setapi('QVariant', 2)

from __future__ import with_statement

import sys
import time
from PySide.QtCore import QSettings
import atexit
import os
from signal import SIGTERM

import logging

from retriever import KhweeteurRefreshWorker
from settings import SUPPORTED_ACCOUNTS
import gobject
gobject.threads_init()
import socket
import pickle
import re

__version__ = '0.5.0'

import dbus
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)
import threading

import twitter
from urllib import urlretrieve
import urllib2
import pickle
import glob

try:
    from PIL import Image
except:
    import Image

from PySide.QtCore import QSettings

from threading import Thread

import logging
import os
import os.path
import dbus
import dbus.service


#A hook to catch errors
def install_excepthook(version):
    '''Install an excepthook called at each unexcepted error'''
    __version__ = version

    def my_excepthook(exctype, value, tb):
        '''Method which replace the native excepthook'''
        #traceback give us all the errors information message like
        # the method, file line ... everything like
        # we have in the python interpreter
        import traceback
        trace_s = ''.join(traceback.format_exception(exctype, value, tb))
        print 'Except hook called : %s' % (trace_s)
        formatted_text = "%s Version %s\nTrace : %s" % ('Khweeteur', __version__, trace_s)
        logging.error(formatted_text)

    sys.excepthook = my_excepthook


class Daemon:
    """
    A generic daemon class.
    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit first parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)
    
        # decouple from parent environment
        os.chdir("/") 
        os.setsid() 
        os.umask(0) 
    
        # do second fork
        try: 
            pid = os.fork() 
            if pid > 0:
                # exit from second parent
                sys.exit(0) 
        except OSError, e: 
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1) 
    
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    
        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        file(self.pidfile, 'w+').write("%s\n" % pid)
    
    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
    
        if pid:
            try:
                os.kill(pid, 0)
                message = "pidfile %s already exist. Daemon already running?\n"
                sys.stderr.write(message % self.pidfile)
                sys.exit(1)

            except OSError, err:
                sys.stderr.write('pidfile %s already exist. But daemon is dead.\n' % self.pidfile)
        
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile, 'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None
    
        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process    
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """


class KhweeteurDBusHandler(dbus.service.Object):

    def __init__(self):
        dbus.service.Object.__init__(self, dbus.SessionBus(), '/net/khertan/Khweeteur')
        self.m_id = 0

    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur',
                         signature='')
    def refresh_ended(self):
        pass
                
    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur',
                         signature='us')
    def new_tweets(self, count, ttype):
        logging.debug('New tweet notification ttype : %s (%s)' % (ttype,str(type(ttype)),))
        if ttype in ('Mentions', 'DMs'):
            m_bus = dbus.SystemBus()
            m_notify = m_bus.get_object('org.freedesktop.Notifications',
                              '/org/freedesktop/Notifications')
            iface = dbus.Interface(m_notify, 'org.freedesktop.Notifications')
            m_id = 0
    
            if ttype == 'DMs':
                msg = 'New DMs'
            elif ttype == 'Mentions':
                msg = 'New mentions'            
            else:
                msg = 'New tweets'
            try:
                self.m_id = iface.Notify('Khweeteur',
                                  self.m_id,
                                  'khweeteur',
                                  msg,
                                  msg,
                                  ['default', 'call'],
                                  {'category': 'khweeteur-new-tweets',
                                  'desktop-entry': 'khweeteur',
                                  'dbus-callback-default': 'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show_now',
                                  'count': count,
                                  'amount': count},
                                  -1)
            except:
                pass


class KhweeteurDaemon(Daemon):

    def run(self):        
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(message)s',
                    datefmt='%a, %d %b %Y %H:%M:%S',
                    filename='/home/user/.khweeteur.log',
                    filemode='w')

        self.bus = dbus.SessionBus()
        self.bus.add_signal_receiver(self.update, path='/net/khertan/Khweeteur', dbus_interface='net.khertan.Khweeteur', signal_name='require_update')
        self.bus.add_signal_receiver(self.post_tweet, path='/net/khertan/Khweeteur', dbus_interface='net.khertan.Khweeteur', signal_name='post_tweet')
        self.threads = [] #Here to avoid gc 

        #Cache Folder
        self.cache_path = os.path.join(os.path.expanduser("~"),\
                                 '.khweeteur', 'cache')
        if not os.path.exists(self.cache_path):
            os.makedirs(self.cache_path)
        #Post Folder
        self.post_path = os.path.join(os.path.expanduser("~"),\
                                 '.khweeteur', 'topost')
        if not os.path.exists(self.post_path):
            os.makedirs(self.post_path)

        self.dbus_handler = KhweeteurDBusHandler()

        loop = gobject.MainLoop()
        gobject.timeout_add_seconds(1, self.update)
        logging.debug('Timer added')        
        loop.run()

    def post_tweet(self, \
            shorten_url=True,\
            serialize=True,\
            text='',\
            lattitude='',
            longitude='',
            base_url='',
            action='',
            tweet_id='',
            ):
        with open(os.path.join(self.post_path, str(time.time())), 'wb') as fhandle:
            post = {'shorten_url': shorten_url,
                    'serialize': serialize,
                    'text': text,
                    'lattitude': lattitude,
                    'longitude': longitude,
                    'base_url': base_url,
                    'action': action,
                    'tweet_id': tweet_id,}
            logging.debug('%s' % (post.__repr__(),))
            pickle.dump(post, fhandle, pickle.HIGHEST_PROTOCOL)
        self.do_posts()

    def get_api(self,account):
        api = \
            twitter.Api(username=account['consumer_key'],
                        password=account['consumer_secret'],
                        access_token_key=account['token_key'],
                        access_token_secret=account['token_secret'],
                        base_url=account['base_url'],)
        api.SetUserAgent('Khweeteur')

        return api

    def do_posts(self):
        settings = QSettings("Khertan Software", "Khweeteur")
        accounts = []
        nb_accounts = settings.beginReadArray('accounts')
        for index in range(nb_accounts):
            settings.setArrayIndex(index)
            accounts.append(dict((key, settings.value(key)) for key in settings.allKeys()))            
        settings.endArray()                        

        logging.debug('Number of account : %s' % len(accounts))

        for item in glob.glob(os.path.join(self.post_path, '*')):
            logging.debug('Try to post %s' % (item,))
            try:
                with open(item, 'rb') as fhandle:
                    post = pickle.load(fhandle)
                    text = post['text']
                    if post['shorten_url'] == 1:
                        urls = re.findall("(?P<url>https?://[^\s]+)", text)
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
                    if post['lattitude'] == '':
                        post['lattitude'] = None
                    else:
                        post['lattitude'] = int(post['lattitude'])
                    if post['longitude'] == '':
                        post['longitude'] = None                        
                    else:
                        post['longitude'] = int(post['longitude'])

                    #Loop on accounts
                    for account in accounts:
                        #Reply
                        if post['action'] == 'reply': #Reply tweet
                            if account['base_url'] == post['base_url'] \
                              and account['use_for_tweet'] == 'true':
                                api = self.get_api(account)
                                if post['serialize'] == 1:
                                    api.PostSerializedUpdates(text,
                                            in_reply_to_status_id=int(post['tweet_id']),
                                            latitude=post['lattitude'], longitude=post['longitude'])
                                else:
                                    api.PostUpdate(text,
                                            in_reply_to_status_id=int(post['tweet_id']),
                                            latitude=post['lattitude'], longitude=post['longitude'])
                                logging.debug('Posted reply %s' % (text,))
                        elif post['action'] == 'retweet':
                            #Retweet
                                if account['base_url'] == post['base_url'] \
                                  and account['use_for_tweet'] == 'true':
                                    api = self.get_api(account)
                                    api.PostRetweet(tweet_id=int(post['tweet_id']))
                                    logging.debug('Posted retweet %s' % (post['tweet_id'],))
                        elif post['action'] == 'tweet':
                            #Else "simple" tweet
                            if account['use_for_tweet'] == 'true':
                                api = self.get_api(account)
                                if post['serialize'] == 1:
                                    api.PostSerializedUpdates(text,
                                        latitude=post['lattitude'], longitude=post['longitude'])
                                else:
                                    api.PostUpdate(text,
                                        latitude=post['lattitude'], longitude=post['longitude'])
                                logging.debug('Posted %s' % (text,))
                        elif post['action'] == 'delete':
                            if account['base_url'] == post['base_url']:
                                api = self.get_api(account)
                                api.DestroyStatus(int(post['tweet_id']))
                                path = os.path.join(os.path.expanduser('~'), \
                                    '.khweeteur', \
                                    'cache', \
                                    'HomeTimeline', \
                                    post['tweet_id'])
                                os.remove(path)
                                logging.debug('Deleted %s' % (post['tweet_id'],))                                
                        elif post['action'] == 'favorite':
                            if account['base_url'] == post['base_url']:
                                api = self.get_api(account)
                                api.CreateFavorite(int(post['tweet_id']))
                                logging.debug('Favorited %s' % (post['tweet_id'],))                                
                        elif post['action'] == 'follow':
                            if account['base_url'] == post['base_url']:
                                api = self.get_api(account)
                                api.CreateFriendship(int(post['tweet_id']))
                                logging.debug('Follow %s' % (post['tweet_id'],))                                
                        elif post['action'] == 'unfollow':
                            if account['base_url'] == post['base_url']:
                                api = self.get_api(account)
                                api.DestroyFriendship(int(post['tweet_id']))
                                logging.debug('Follow %s' % (post['tweet_id'],))                                
                        else:
                            logging.error('Unknow action : %s' % post['action'])

                    os.remove(item)

            except twitter.TwitterError, err:
                if err.message == 'Status is a duplicate':
                    os.remove(item)
                else:
                    logging.error('Do_posts : %s' % (err.message,))                           
            except StandardError, err:
                logging.error('Do_posts : %s' % (str(err),))
                #Emitting the error will block the other tweet post
                #raise #can t post, we will keep the file to do it later                                   
            except:
                logging.error('Do_posts : Unknow error')
                
    def post_twitpic(self, file_path, text):
        settings = QSettings("Khertan Software", "Khweeteur")

        import twitpic
        import oauth2 as oauth
        import simplejson

        nb_accounts = settings.beginReadArray('accounts')
        for index in range(nb_accounts):
            settings.setArrayIndex(index)
            if (settings.value('base_url') == SUPPORTED_ACCOUNTS[0]['base_url']) \
              and (settings.value('use_for_tweet') == Qt.CheckState):
                api = twitter.Api(username=settings.value('consumer_key'),
                           password=settings.value('consumer_secret'),
                           access_token_key=settings.value('token_key'),
                           access_token_secret=settings.value('token_secret'),
                           base_url=SUPPORTED_ACCOUNTS[0]['base_url'])
                twitpic_client = twitpic.TwitPicOAuthClient(
                    consumer_key=settings.value('consumer_key'),
                    consumer_secret=settings.value('consumer_secret'),
                    access_token=api._oauth_token.to_string(),
                    service_key='f9b7357e0dc5473df5f141145e4dceb0')

                params = {}
                params['media'] = 'file://' + file_path
                params['message'] = text
                response = twitpic_client.create('upload', params)

                if 'url' in response:
                    self.post(text=url)                

        settings.endArray()                                    

    def update(self, option=None):
        settings = QSettings("Khertan Software", "Khweeteur")
        logging.debug('Setting loaded')
        settings.sync()

        #Verify the default interval
        if not settings.contains('refresh_interval'):
            refresh_interval = 600
        else:
            refresh_interval = int(settings.value('refresh_interval')) * 60
            if refresh_interval < 600:
                refresh_interval = 600
        logging.debug('refresh interval loaded')

        self.do_posts()
        self.retrieve()
        gobject.timeout_add_seconds(refresh_interval, self.update)
        return False
        
    def retrieve(self, options=None):
        settings = QSettings("Khertan Software", "Khweeteur")
        logging.debug('Setting loaded')
        try:
            #Re read the settings
            settings.sync()
            logging.debug('Setting synced')
            
            #Cleaning old thread reference for keep for gc
            for thread in self.threads:
                if not thread.isAlive():
                    self.threads.remove(thread)
                    logging.debug('Removed a thread')
                        
            #Remove old tweets in cache according to history prefs
            try:
                keep = int(settings.value('tweetHistory'))
            except:
                keep = 60
           
            for root, folders, files in os.walk(self.cache_path):
                for folder in folders:
                    statuses = []
                    uids = glob.glob(os.path.join(root, folder, '*'))
                    for uid in uids:
                        uid = os.path.basename(uid)
                        try:
                            pkl_file = open(os.path.join(root, folder, uid), 'rb')
                            status = pickle.load(pkl_file)
                            pkl_file.close()
                            statuses.append(status)
                        except StandardError, err:
                            logging.debug('Error in cache cleaning: %s,%s' % (err, os.path.join(root, uid)))
                    statuses.sort(key=lambda status: status.created_at_in_seconds, reverse=True)
                    for status in statuses[keep:]:
                        try:
                            os.remove(os.path.join(root, folder, str(status.id)))
                        except StandardError, err:
                            logging.debug('Cannot remove : %s : %s' % (str(status.id), str(err)))

            nb_searches = settings.beginReadArray('searches')
            searches = []
            for index in range(nb_searches):
                settings.setArrayIndex(index)
                searches.append(settings.value('terms'))
            settings.endArray()
            
            nb_accounts = settings.beginReadArray('accounts')
            logging.info('Found %s account' % (str(nb_accounts),))
            for index in range(nb_accounts):
                settings.setArrayIndex(index)
                #Worker
                try:                               
                    self.threads.append(KhweeteurRefreshWorker(\
                                settings.value('base_url'),
                                settings.value('consumer_key'),
                                settings.value('consumer_secret'),
                                settings.value('token_key'),
                                settings.value('token_secret'),
                                'HomeTimeline', self.dbus_handler))
                except Exception, err:
                    logging.error('Timeline : %s' % str(err))

                try:                                                   
                    self.threads.append(KhweeteurRefreshWorker(\
                                settings.value('base_url'),
                                settings.value('consumer_key'),
                                settings.value('consumer_secret'),
                                settings.value('token_key'),
                                settings.value('token_secret'),
                                'Mentions', self.dbus_handler))
                except Exception, err:
                    logging.error('Mentions : %s' % str(err))

                try:                               
                    self.threads.append(KhweeteurRefreshWorker(\
                                settings.value('base_url'),
                                settings.value('consumer_key'),
                                settings.value('consumer_secret'),
                                settings.value('token_key'),
                                settings.value('token_secret'),
                                'DMs', self.dbus_handler))
                except Exception, err:
                    logging.error('DMs : %s' % str(err))

                #Start searches thread
                for terms in searches:
                    try:                               
                        self.threads.append(KhweeteurRefreshWorker(\
                                    settings.value('base_url'),
                                    settings.value('consumer_key'),
                                    settings.value('consumer_secret'),
                                    settings.value('token_key'),
                                    settings.value('token_secret'),
                                    'Search:'+terms, self.dbus_handler))
                    except Exception, err:
                        logging.error('Search %s: %s' % (terms,str(err)))

                try:                               
                    for idx, thread in enumerate(self.threads):
                        logging.debug('Try to run Thread : %s' % str(thread))
                        try:
                            self.threads[idx].start()
                        except RuntimeError, err:
                            logging.debug('Attempt to start a thread already running : %s' % (str(err),))
                except:
                    logging.error('Running Thread error')

            settings.endArray()

            while any([thread.isAlive() for thread in self.threads]):
                time.sleep(1)
                
            self.dbus_handler.refresh_ended()

            logging.debug('Finished loop')          
                            
        except StandardError, err:
            logging.exception(str(err))
            logging.debug(str(err))

                         
if __name__ == "__main__":
    install_excepthook(__version__)
    daemon = KhweeteurDaemon('/tmp/khweeteur.pid')
    if len(sys.argv) == 2:
            if 'start' == sys.argv[1]:
                    daemon.start()
            elif 'stop' == sys.argv[1]:
                    daemon.stop()
            elif 'restart' == sys.argv[1]:
                    daemon.restart()
            else:
                    print "Unknown command"
                    sys.exit(2)
            sys.exit(0)
    else:
            print "usage: %s start|stop|restart" % sys.argv[0]
            sys.exit(2)
