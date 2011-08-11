#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

from __future__ import with_statement

import sys
import twitter
import socket
socket.setdefaulttimeout(60)
from urllib import urlretrieve
import re

import cPickle as pickle
try:
    from PIL import Image
except ImportError:
    import Image

from PySide.QtCore import QSettings,QThread, Signal

#from threading import Thread

import logging
import os
import socket
import glob

class KhweeteurRefreshWorker(QThread):

    new_tweets = Signal(int, str)
    error = Signal(str)

    def __init__(
        self,
        api,
        call,
        #dbus_handler,
        me_user_id,
        ):
        """
        api: An instance of the twitter.Api class.

        call is one of

          'HomeTimeline': Fetch the home time line
          'Mentions': Fetch user mentions
          'DMs': Fetch direct messages
          'Search:*': Fetch search results where * is the terms to search for
          'RetrieveLists': Retrive lists
          'List:*:*': The first * should be replace with the user and
                      the second with the id
          'Near:*:*': Fetch tweets near (1km) a the specified
                      location.  The first start is the the first
                      geocode and the second * is the second geocode.

        me_user_id: The user's user id.
        """
        QThread.__init__(self)
        self.api = api

        self.me_user_id = me_user_id
        self.call = call
        #self.dbus_handler = dbus_handler
        socket.setdefaulttimeout(60)

#    def send_notification(self, msg, count):
#        try:
#            #self.dbus_handler.new_tweets(count, msg)
#            self.new_tweets.emit(count, msg)
#        except Exception, err:
#            logging.debug('Retriever : %s' % str(err))

    def getCacheFolder(self):
        if not hasattr(self, 'folder_path'):
            self.folder_path = os.path.join(os.path.expanduser('~'),
                    '.khweeteur', 'cache',
                    os.path.normcase(unicode(self.call.replace('/', '_'
                    ))).encode('UTF-8'))

            if not os.path.isdir(self.folder_path):
                try:
                    os.makedirs(self.folder_path)
                except IOError, e:
                    logging.debug('getCacheFolder:' + e)

        return self.folder_path

    def statusIdFilename(self, status_id):
        if not hasattr(self, 'filename_prefix'):
            self.filename_prefix = re.sub(
                '^https?://', '', self.api.base_url).replace('/', '_') + '-'

        return os.path.join(self.getCacheFolder(),
                            self.filename_prefix + str(status_id))

    def statusFilename(self, status):
        # Place each service in its own name space.
        return self.statusIdFilename(status.id)

    def downloadProfilesImage(self, statuses):
        avatar_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                   'avatars')
        if not os.path.exists(avatar_path):
            os.makedirs(avatar_path)

        for status in statuses:
            if type(status) != twitter.DirectMessage:
                filename = os.path.join(
                    avatar_path,
                    os.path.basename(
                        status.user.profile_image_url.replace('/', '_')))
                filename = os.path.splitext(filename)[0] + '.png'

                # Try to open the file.  If it already exists, another
                # thread is downloading it.
                try:
                    with open(filename, "wbx") as fhandle:
                        pass
                except IOError, exception:
                    if 'File exists' in exception:
                        continue
                    raise

                try:
                    urlretrieve(status.user.profile_image_url, filename)
                    im = Image.open(filename)
                    im = im.resize((50, 50))
                    im.save(filename, 'PNG')
                except StandardError, err:
                    os.remove(filename)
                    logging.debug('DownloadProfileImage: %s -> %s: %s'
                                  % (status.user.profile_image_url, filename,
                                     str(err)))
                except:
                    os.remove(filename)
                    raise

    def removeAlreadyInCache(self, statuses):
        """
        If a status was already downloaded, remove it from statuses.

        statuses is a list of status updates (twitter.Status objects).
        """
        statuses = [status for status in statuses
                    if os.path.exists(self.statusFilename(status))]

    def applyOrigin(self, statuses):
        """
        Set the statuses origin (the account from which the status was
        fetch).

        statuses is a list of status updates (twitter.Status objects).
        """
        for status in statuses:
            status.base_url = (
                self.api.base_url + ';' + self.api._access_token_key)

    def isMe(self, statuses):
        """
        statuses is a list of status updates (twitter.Status objects).
        For each status update, sets status.is_me according to whether
        the status's user id is the user's id.
        """
        for status in statuses:
            if status.user.id == self.me_user_id:
                status.is_me = True
            else:
                status.is_me = False

    def getRepliesContent(self, statuses):
        """
        If a status update is a reply, ensure that the message to
        which it is a reply is downloaded and include its text in the
        reply's data structure.
        """
        # If a reply to status is not available, we download it.  If
        # that's a reply to something, we *don't* fetch the third
        # thing.
        new_statuses = []
        for status in statuses:
            try:
                # If the status update is a reply, create include the
                # text of the origin message in the reply.
                if not hasattr(status, 'in_reply_to_status_id'):
                    # It is not a reply.
                    status.in_reply_to_status_text = None
                    continue
                if not (not status.in_reply_to_status_text
                        and status.in_reply_to_status_id):
                    # We have the text or we don't know the original's
                    # id.
                    continue

                # We don't have the text and we know the original
                # message's id.
                logging.debug("%s:%s: Looking for reply to %s"
                              % (self.call, str(status.id), str(status)))

                reply_to_id = status.in_reply_to_status_id
                reply_to = None

                # First check whether we just downloaded the
                # message to which this is a reply.
                reply_tos = [s for s in statuses if s.id == reply_to_id]
                if reply_tos:
                    # It is.
                    reply_to = reply_tos[0]
                    logging.debug("%s:%s: Reply found in update (%s)"
                                  % (self.call, str(status.id), str(reply_to)))
                else:
                    # Nope.  See if it is in the message cache.
                    reply_tos = glob.glob(os.path.join(
                            os.path.expanduser('~'),
                            '.khweeteur', 'cache', '*',
                            self.statusIdFilename(
                                status.in_reply_to_status_id)))
                    if reply_tos:
                        # It is.
                        with open(reply_tos[0], 'rb') as fhandle:
                            reply_to = pickle.load(fhandle)
                            logging.debug(
                                "%s:%s: Reply found in cache (%s)"
                                % (self.call, str(status.id), str(reply_to)))
                    else:
                        # Try downloading it.
                        logging.debug("%s:%s: Downloading %s"
                                      % (self.call, status.id, reply_to_id))
                        try:
                            reply_to = self.api.GetStatus(
                                status.in_reply_to_status_id)
                        except twitter.TwitterError, exception:
                            logging.debug(
                                "%s:%s: Download failed: %s"
                                % (self.call, str(status.id), str(exception)))
                        else:
                            new_statuses.append(reply_to)
                            logging.debug(
                                "%s:%s: Reply to %s downloaded (%s)"
                                % (self.call, str(status.id), str(reply_to)))

                if reply_to:
                    status.in_reply_to_status_text = reply_to.text
                else:
                    logging.debug(
                        "%s:%s: No reply to %s found."
                        % (self.call, str(status.id),
                           status.in_reply_to_status_id))
            except StandardError, err:
                import traceback
                (exc_type, exc_value, exc_traceback) = sys.exc_info()
                logging.debug('%s: getRepliesContent(%s): %s: %s'
                              % (self.call, str(status), str(err),
                                 repr(traceback.format_exception(
                                          exc_type, exc_value, exc_traceback))))

        statuses += new_statuses

    def serialize(self, statuses):
        """
        statuses is a list of status updates (twitter.Status objects).
        For each status update, writes the status update to disk.

        If the status was already written to disk, removes it from the
        statuses list.
        """
        # Don't modify a list over which we are iterating.  Consider:
        #   a=[1,2,3,4,5]
        #   for i in a:
        #     a.remove(i)
        #   print a
        #   [2, 4]
        keep = []
        for status in statuses:
            filename = self.statusFilename(status)
            try:
                # Open the file exclusively.
                with open(filename, 'wbx') as fhandle:
                    pickle.dump(status, fhandle, pickle.HIGHEST_PROTOCOL)
            except IOError, exception:
                if 'File exists' in str(exception):
                    # Another thread downloaded this status update.
                    pass
                else:
                    raise
            except pickle.PickleError, exception:
                logging.debug('Serialization of %s failed: %s'
                              % (status.id, str (exception)))
                # Remove the empty file.
                os.remove(filename)
            else:
                keep.append(status)

        statuses[:] = keep

    def run(self):
        settings = QSettings('Khertan Software', 'Khweeteur')
        statuses = []

        logging.debug("Thread for '%s' running" % self.call)
        try:
            since = settings.value(self.api._access_token_key + '_' + self.call)

            logging.debug('%s running' % self.call)
            if self.call == 'HomeTimeline':
                statuses = self.api.GetHomeTimeline(since_id=since)
            elif self.call == 'Mentions':
                statuses = self.api.GetMentions(since_id=since)
            elif self.call == 'DMs':
                statuses = self.api.GetDirectMessages(since_id=since)
            elif self.call.startswith('Search:'):
                statuses = self.api.GetSearch(since_id=since,
                        term=self.call.split(':', 1)[1])
            elif self.call == 'RetrieveLists':
                # Get the list subscriptions

                lists = \
                    self.api.GetSubscriptions(user=self.api.VerifyCredentials().id)
                settings.beginWriteArray('lists')
                for (index, list_instance) in enumerate(lists):
                    settings.setArrayIndex(index)
                    settings.setValue('id', list_instance.id)
                    settings.setValue('user', list_instance.user.screen_name)
                    settings.setValue('name', list_instance.name)
                settings.endArray()

                # Get the status of list

                settings.sync()
            elif self.call.startswith('List:'):
                user, id = self.call.split(':', 2)[1:]
                statuses = self.api.GetListStatuses(user=user, id=id,
                                                    since_id=since)

            #Near GPS
            elif self.call.startswith('Near:'):
                geocode = self.call.split(':', 2)[1:] + ['1km']
                logging.debug('geocode=(%s)', str(geocode))
                statuses = self.api.GetSearch(since_id=since,
                        term='', geocode=geocode)
            else:
                logging.error('Unknown call: %s' % (self.call, ))
        except Exception, err:
            logging.debug('Retriever %s: %s' % (self.call, str(err)))
            if settings.value('ShowInfos') == '2':
                self.error.emit('Khweeteur Error : %s' % str(err))
                #self.dbus_handler.info('Khweeteur Error : ' + str(err))

        downloaded_statuses = len(statuses)

        self.removeAlreadyInCache(statuses)

        logging.debug('%s: %d statuses downloaded; %d new statuses'
                      % (self.call, downloaded_statuses, len(statuses)))

        if len(statuses) > 0:
            self.getRepliesContent(statuses)
            self.downloadProfilesImage(statuses)
            self.applyOrigin(statuses)
            if self.call != 'DMs':
                self.isMe(statuses)
            self.serialize(statuses)

            if len(statuses) > 0:
                settings.setValue(self.api._access_token_key + '_' + self.call,
                                  max(statuses).id)
                self.new_tweets.emit(len(statuses), self.call)
        settings.sync()
        logging.debug('%s finished' % self.call)


