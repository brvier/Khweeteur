#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

import twitter
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

class KhweeteurRefreshWorker(Thread):
    
    # Signal
#    errors = Signal(Exception)
#    newStatuses = Signal(list)

    def __init__(self,base_url, consumer_key, consumer_secret, access_token, access_secret, call):
        Thread.__init__(self, None)
        self.api = twitter.Api(username=consumer_key,
                               password=consumer_secret,
                               access_token_key=access_token,
                               access_token_secret=access_secret,
                               base_url=base_url)
        self.api.SetUserAgent('Khweeteur')
        self.call = call
        self.consumer_key = consumer_key

    def send_notification(self,msg,count):
        m_bus = dbus.SystemBus()
        m_notify = m_bus.get_object('org.freedesktop.Notifications',
                          '/org/freedesktop/Notifications')
        iface = dbus.Interface(m_notify, 'org.freedesktop.Notifications')
        m_id = 0

        try:
            m_id = iface.Notify('Khweeteur',
                              m_id,
                              'khweeteur',
                              'New Tweets',
                              msg,
                              ['default','call'],
                              {'category':'khweeteur-new-tweets',
                              'desktop-entry':'khweeteur',
                              'dbus-callback-default':'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show_now',
                              'count':count,
                              'amount':count},
                              -1
                              )
        except:
            pass
    
    def getCacheFolder(self):
        if not hasattr(self,'folder_path'):
            self.folder_path = os.path.join(os.path.expanduser("~"),
                                 '.khweeteur',
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
        for root,dirs,files in os.walk(os.path.join(os.path.expanduser("~"),'.khweeteur')):
            for afile in files:                
                if unicode(tid)==afile:
                    fhandle = open(os.path.join(root,afile), 'rb')
                    status = pickle.load(fhandle)
                    fhandle.close()
                    return status.text

        try:
            rpath = os.path.join(os.path.expanduser("~"),'.khweeteur','Replies')
            if not os.path.exists(rpath):
                os.makedirs(rpath)
    
            status = self.api.GetStatus(tid)
            fhandle = open(os.path.join(os.path.join(rpath,
                        unicode(status.id)), 'wb'))
            pickle.dump(status, fhandle, pickle.HIGHEST_PROTOCOL)
            fhandle.close()
            return status.text
        except StandardError, er:
            logging.debug('getOneReplyContent:'+err)
            print err

            
    def getRepliesContent(self, statuses):
        for status in statuses:
            if not hasattr(status, 'in_reply_to_status_id'):
                status.in_reply_to_status_text = None
            elif not status.in_reply_to_status_text \
                and status.in_reply_to_status_id:
                status.in_reply_to_status_text = \
                    self.getOneReplyContent(status.in_reply_to_status_id)

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
        
        try:
            since = settings.value(self.consumer_key + '_' + self.call)
                        
            if self.call == 'HomeTimeline':
                statuses = self.api.GetHomeTimeline(since_id=since)
            elif self.call == 'Mentions':
                statuses = self.api.GetMentions(since_id=since)
            elif self.call == 'DMs':
                statuses = self.api.GetDirectMessages(since_id=since)
            else:
                #Its a search ....
                pass
        except StandardError, err:
            logging.debug(err)
            print err
        
        self.removeAlreadyInCache(statuses)
        self.downloadProfilesImage(statuses)
        self.applyOrigin(statuses)
        self.getRepliesContent(statuses)
        self.serialize(statuses)
        statuses.sort()
        statuses.reverse()
        if len(statuses) > 0:
            settings.setValue(self.consumer_key + \
                       '_' + self.call, statuses[0].id)
            self.send_notification('New %s' % (self.call,),len(statuses))
        settings.sync()

if __name__ == "__main__":
    worker = KhweeteurRefreshWorker(\
                 'https://api.twitter.com/1',
                 'uhgjkoA2lggG4Rh0ggUeQ',
                 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU',
                 '15847937-z6jfvVmzrTVRUwoYjuKo6wKv2zyp4EIByjc7bWSs',
                 '1OklngYcx3Hg8SFC2D9m2NjN0EAIpQjuO3kuxFGkpi8',
                 'HomeTimeline')
    worker.start()
    worker = KhweeteurRefreshWorker(\
                 'https://api.twitter.com/1',
                 'uhgjkoA2lggG4Rh0ggUeQ',
                 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU',
                 '15847937-z6jfvVmzrTVRUwoYjuKo6wKv2zyp4EIByjc7bWSs',
                 '1OklngYcx3Hg8SFC2D9m2NjN0EAIpQjuO3kuxFGkpi8',
                 'DMs')
    worker.start()
    worker = KhweeteurRefreshWorker(\
                 'https://api.twitter.com/1',
                 'uhgjkoA2lggG4Rh0ggUeQ',
                 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU',
                 '15847937-z6jfvVmzrTVRUwoYjuKo6wKv2zyp4EIByjc7bWSs',
                 '1OklngYcx3Hg8SFC2D9m2NjN0EAIpQjuO3kuxFGkpi8',
                 'Mentions')
    worker.start()