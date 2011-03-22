#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

import twitter
import socket
socket.setdefaulttimeout(60)
from urllib import urlretrieve

import urllib2
import pickle
try:
    from PIL import Image
except:
    import Image

from PySide.QtCore import QSettings

from threading import Thread

import logging
import os
import dbus
import dbus.service
import socket
       
class KhweeteurRefreshWorker(Thread):    
    def __init__(self,base_url, consumer_key, consumer_secret, access_token, access_secret, call, dbus_handler):
        Thread.__init__(self, None)
        self.api = twitter.Api(username=consumer_key,
                               password=consumer_secret,
                               access_token_key=access_token,
                               access_token_secret=access_secret,
                               base_url=base_url)
        self.api.SetUserAgent('Khweeteur')
        self.call = call
        self.consumer_key = consumer_key
        self.dbus_handler = dbus_handler
        socket.setdefaulttimeout(60)

    def send_notification(self,msg,count):
        self.dbus_handler.new_tweets(count,msg)
    
    def getCacheFolder(self):
        if not hasattr(self,'folder_path'):
            self.folder_path = os.path.join(os.path.expanduser("~"),
                                 '.khweeteur','cache',
                                 os.path.normcase(unicode(self.call.replace('/',
                                 '_'))).encode('UTF-8'))
                            
            if not os.path.isdir(self.folder_path):
                try:
                    os.makedirs(self.folder_path)
                except IOError, e:
                    logging.debug('getCacheFolder:' + e)
    
        return self.folder_path

    def downloadProfilesImage(self, statuses):
        avatar_path = os.path.join(os.path.expanduser("~"),
                        '.khweeteur','avatars')
        if not os.path.exists(avatar_path):
            os.makedirs(avatar_path)
            
        for status in statuses:
            if type(status) != twitter.DirectMessage:
                cache = os.path.join(avatar_path,
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
#                        status.user.profile_image_url = cache
                    except StandardError, err:
                        logging.debug('DownloadProfilImage:'+str(err))
                        print err

    def removeAlreadyInCache(self, statuses):
        # Load cached statuses
        try:
            folder_path = self.getCacheFolder()
            for status in statuses:
                if os.path.exists(os.path.join(folder_path,
                                  str(status.id))):
                    statuses.remove(status)
        except StandardError, err:
            logging.debug(err)

    def applyOrigin(self, statuses):
        for status in statuses:
            status.origin = self.api.base_url

    def getOneReplyContent(self, tid):
        #Got from cache        
        status = None
        for root,dirs,files in os.walk(os.path.join(os.path.expanduser("~"),'.khweeteur','cache')):
            for folder in dirs:
                logging.debug('getOneReplyContent Folder: %s' % (folder,))
            for afile in files:
                logging.debug('getOneReplyContent aFile: %s' % (os.path.join(root,afile),))
                if unicode(tid)==afile:
                    try:
                        fhandle = open(os.path.join(root,afile), 'rb')
                        status = pickle.load(fhandle)
                        fhandle.close()
                        return status.text
                    except StandardError,err:
                        logging.debug('getOneReplyContent:'+err)

        try:
            rpath = os.path.join(os.path.expanduser("~"),'.khweeteur','cache','Replies')
            if not os.path.exists(rpath):
                os.makedirs(rpath)
    
            status = self.api.GetStatus(tid)
            fhandle = open(os.path.join(os.path.join(rpath,
                        unicode(status.id)), 'wb'))
            pickle.dump(status, fhandle, pickle.HIGHEST_PROTOCOL)
            fhandle.close()
            return status.text
        except StandardError, err:
            logging.debug('getOneReplyContent:'+str(err))
            print err

            
    def getRepliesContent(self, statuses):
        for status in statuses:
            try:
                if not hasattr(status, 'in_reply_to_status_id'):
                    status.in_reply_to_status_text = None
                elif not status.in_reply_to_status_text \
                    and status.in_reply_to_status_id:
                    status.in_reply_to_status_text = \
                        self.getOneReplyContent(status.in_reply_to_status_id)
            except StandardError, err:
                logging.debug('getOneReplyContent:'+err)
                print err

    def serialize(self, statuses):
        folder_path = self.getCacheFolder()

        for status in statuses:
            try:
                fhandle = open(os.path.join(folder_path, unicode(status.id)),'wb')
                pickle.dump(status, fhandle, pickle.HIGHEST_PROTOCOL)
                fhandle.close()
            except:
                logging.debug('Serialization of %s failed' % (status.id,))                                    

    def run(self):
        settings = QSettings("Khertan Software", "Khweeteur")
        statuses = []
        
        logging.debug('Thread Runned')
        try:
            since = settings.value(self.consumer_key + '_' + self.call)
                        
            if self.call == 'HomeTimeline':
                logging.debug('%s running' % self.call)                            
                statuses = self.api.GetHomeTimeline(since_id=since)
                logging.debug('%s finished' % self.call)                            
            elif self.call == 'Mentions':
                logging.debug('%s running' % self.call)                            
                statuses = self.api.GetMentions(since_id=since)
                logging.debug('%s finished' % self.call)                            
            elif self.call == 'DMs':
                logging.debug('%s running' % self.call)                            
                statuses = self.api.GetDirectMessages(since_id=since)
                logging.debug('%s finished' % self.call)                            
            else:
                #Its a search ....
                pass
        except StandardError, err:
            logging.debug(err)
            raise err
        
        self.removeAlreadyInCache(statuses)
        if len(statuses) > 0:
            logging.debug('%s start download avatars' % self.call)                            
            self.downloadProfilesImage(statuses)
            logging.debug('%s start applying origin' % self.call)                            
            self.applyOrigin(statuses)
            logging.debug('%s start getreply' % self.call)                            
            self.getRepliesContent(statuses)
            logging.debug('%s start serialize' % self.call)                            
            self.serialize(statuses)
            statuses.sort()
            statuses.reverse()
            settings.setValue(self.consumer_key + \
                       '_' + self.call, statuses[0].id)
            self.send_notification(self.call,len(statuses))
        settings.sync()
        logging.debug('%s refreshed' % self.call)                            