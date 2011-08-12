#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

from __future__ import with_statement

import time
import cPickle as pickle
#import glob
import os

SCREENNAMEROLE = 20
REPLYTOSCREENNAMEROLE = 21
REPLYTEXTROLE = 22
REPLYIDROLE = 25
IDROLE = 23
ORIGINROLE = 24
TIMESTAMPROLE = 26
RETWEETOFROLE = 27
ISMEROLE = 28
PROTECTEDROLE = 28
USERIDROLE = 29
ISNEWROLE = 30

from PySide.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, QSettings
from PySide.QtGui import QPixmap
import twitter #Not really unused. Avoid pickle to do it each time

pyqtSignal = Signal

class KhweetsModel(QAbstractListModel):

    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    dataChanged = pyqtSignal(QModelIndex, QModelIndex)

    def __init__(self):
        QAbstractListModel.__init__(self)

        # Cache the passed data list as a class member.

        # Status is a dict mapping uids to status
        self.statuses = {}
        # UIDs is an array of the UIDs in the current data set.
        self.uids = []

        self.avatars = {}
        self.now = time.time()
        self.nothing_really_loaded = True
        self.call = 'HomeTimeLine'
        self.max_created_at = None
        self.new_message_horizon = self.now

        self.khweets_limit = 10000

        try:
            self.default_avatar = QPixmap('/opt/usr/share/icons/hicolor/48x48/hildon/general_default_avatar.png')
        except:
            self.default_avatar = None

    def __del__(self):
        if not self.nothing_really_loaded:
            settings = QSettings('Khertan Software', 'Khweeteur')
            settings.setValue(
                self.call + '-new-message-horizon', self.max_created_at)

    def setLimit(self, limit):
        self.khweets_limit = limit

    def getCacheFolder(self):
        return os.path.join(os.path.expanduser('~'), '.khweeteur', 'cache',
                            os.path.normcase(unicode(self.call.replace('/', '_'
                            ))).encode('UTF-8'))

    def rowCount(self, parent=QModelIndex()):
        return min(len(self.uids), self.khweets_limit)

    def refreshTimestamp(self):
        self.now = time.time()
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(self.rowCount(), 0))

    def destroyStatus(self, index):
        index = index.row()
        self.uids.pop(index)
        self.dataChanged.emit(self.createIndex(index, 0),
                              self.createIndex(self.rowCount(), 0))

    def load(self, call, limit=None):
        """
        Load a stream.

        call is the stream to load (see
        retriever.py:KhweeteurRefreshWorker for a description of the
        possible values).

        limit is the maximum number of messages to show.  If the
        number of messages exceeds limit, then selects the newest
        messages (in terms of creation time, not download time).

        Returns whether the load loaded a new data set (True) or was
        just a reload (False).
        """
        self.now = time.time()

        # new_message_horizon is the points in time that separates read
        # messages from new messages.  The messages creation time is
        # used.
        settings = QSettings('Khertan Software', 'Khweeteur')
        if self.call != call:
            # It's not a reload.  Save the setting for the old stream
            # and load the setting for the new one.
            ret = True

            if not self.nothing_really_loaded:
                settings.setValue(
                    self.call + '-new-message-horizon', self.max_created_at)

            try:
                self.new_message_horizon = int(
                    settings.value(call + '-new-message-horizon', 0))
            except ValueError:
                self.new_message_horizon = self.now

            # There might be some useful avatars, but figuring out
            # which they are requires loading all of the status
            # updates.
            self.avatars = {}
        else:
            ret = False

        self.nothing_really_loaded = False

        self.call = call

        self.avatar_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                       'avatars')

        folder = self.getCacheFolder()
        try:
            self.uids = os.listdir(folder)
        except Exception, e:
            import traceback
            traceback.print_exc()
            print 'listdir(%s): %s' % (folder, str(e))
            self.uids = []

        self.uids.sort(reverse=True)
        if limit:
            self.uids = self.uids[:limit]

        # Drop any statuses from the cache that we no longer need.
        self.statuses = dict([(k, v) for k, v in self.statuses.items()
                              if k in self.uids])

        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(self.rowCount(), 0))

        return ret

    def data(self, index, role=Qt.DisplayRole):
        if not isinstance(index, int):
            index = index.row()

        uid = self.uids[index]
        try:
            status = self.statuses[uid]
        except KeyError:
            filename = os.path.join(self.getCacheFolder(), str(uid))
            with open(filename, 'rb') as pkl_file:
                status = pickle.load(pkl_file)
                self.statuses[uid] = status

        if role == Qt.DisplayRole:
            try:
                if status.truncated:
                    return status.retweeted_status.text
                else:
                    return status.text
            except:
                return status.text
        elif role == SCREENNAMEROLE:
            try:
                return status.user.screen_name
            except:
                return status.sender_screen_name
        elif role == IDROLE:
            return status.id
        elif role == REPLYIDROLE:
            try:
                return status.in_reply_to_status_id
            except:
                return None
        elif role == REPLYTOSCREENNAMEROLE:
            try:
                return status.in_reply_to_screen_name
            except:
                return None
        elif role == REPLYTEXTROLE:
            return status.in_reply_to_status_text
        elif role == ORIGINROLE:
            return status.base_url
        elif role == RETWEETOFROLE:
            try:
                return status.retweeted_status
            except:
                return None
        elif role == ISMEROLE:
            try:
                return status.is_me
            except:
                return False
        elif role == TIMESTAMPROLE:

            return status.GetRelativeCreatedAt(self.now)
        elif role == ISNEWROLE:
            try:
                created_at = int(status.GetCreatedAtInSeconds())
            except ValueError:
                created_at = 0
            self.max_created_at = max(self.max_created_at, created_at)

            return created_at > self.new_message_horizon
        elif role == PROTECTEDROLE:
            return status.user.protected
        elif role == USERIDROLE:
            try:
                return status.user.id
            except AttributeError:
                return status.sender_id
        elif role == Qt.DecorationRole:
            try:
                profile_image_url = status.user.profile_image_url
            except AttributeError:
                value = self.default_avatar
            else:
                try:
                    value = self.avatars[profile_image_url]
                except KeyError:
                    profile_image = os.path.join(
                        self.avatar_path,
                        os.path.basename(profile_image_url.replace('/', '_')))
                    try:
                        value = QPixmap(
                            os.path.splitext(profile_image)[0] + '.png', 'PNG')
                    except:
                        value = self.default_avatar
                    else:
                        self.avatars[profile_image_url] = value
            return value
        else:
            return None

    def wantsUpdate(self):
        self.layoutChanged.emit()


