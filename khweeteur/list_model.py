#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

import time
import pickle
import glob
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

from PySide.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide.QtGui import QPixmap
import twitter

pyqtSignal = Signal

        
class KhweetsModel(QAbstractListModel):

    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    dataChanged = pyqtSignal(QModelIndex, QModelIndex)

    def __init__(self):
        QAbstractListModel.__init__(self)

        # Cache the passed data list as a class member.

        self._items = []
        self._uids = []

        self._avatars = {}
        self.now = time.time()
        self.call = None

    def setLimit(self, limit):
        self.khweets_limit = limit

    def getCacheFolder(self):
        return os.path.join(os.path.expanduser('~'), '.khweeteur', 'cache',
                            os.path.normcase(unicode(self.call.replace('/', '_'
                            ))).encode('UTF-8'))

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def refreshTimestamp(self):
        self.now = time.time()
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0,
                              len(self._items)))

    def destroyStatus(self, index):
        self._items.pop(index.row())
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0,
                              len(self._items)))

    def load(self, call):

        self.now = time.time()

        if self.call != call:
            self._items = []
            self._uids = []
        self.call = call

        self.avatar_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                       'avatars')

        try:
            folder = self.getCacheFolder()
            uids = glob.glob(folder + u'/*')
#            pickleload = pickle.load
            for uid in uids:
#                if uid not in [status.id for status in self._items]:
                if uid not in self._uids:
                    pkl_file = open(os.path.join(folder, str(uid)), 'rb')
                    status = pickle.load(pkl_file)
                    pkl_file.close()

                    self._uids.append(status.id)
                    self._items.append(status)
                    if hasattr(status, 'user'):
                        if status.user.profile_image_url not in self._avatars:
                            profile_image = os.path.join(self.avatar_path,
                                 os.path.basename(status.user.profile_image_url.replace('/', '_'))) 
                            try:
                                 self._avatars[status.user.profile_image_url] = \
                                 QPixmap(os.path.splitext(profile_image)[0] + '.png', 'PNG')
                            except:
                                 self._avatars[status.user.profile_image_url] = QPixmap('/opt/usr/share/icons/hicolor/48x48/hildon/general_default_avatar.png')
                    else:
                        self._avatars['default'] = QPixmap('/opt/usr/share/icons/hicolor/48x48/hildon/general_default_avatar.png')                        

                    
            self._items.sort(key=lambda status: status.created_at_in_seconds,
                             reverse=True)
            self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0,
                                  len(self._items)))
        except StandardError, e:

            print 'unSerialize : ', e
        
    def data(self, index, role=Qt.DisplayRole):

        if role == Qt.DisplayRole:
            status = self._items[index.row()]
            try:
                if status.truncated:
                    return status.retweeted_status.text
                else:
                    return status.text
            except:
                return status.text
        elif role == SCREENNAMEROLE:
            try:
                return self._items[index.row()].user.screen_name
            except:
                return self._items[index.row()].sender_screen_name
        elif role == IDROLE:
            return self._items[index.row()].id
        elif role == REPLYIDROLE:
            try:
                return self._items[index.row()].in_reply_to_status_id
            except:
                return None
        elif role == REPLYTOSCREENNAMEROLE:
            try:
                return self._items[index.row()].in_reply_to_screen_name
            except:
                return None
        elif role == REPLYTEXTROLE:
            return self._items[index.row()].in_reply_to_status_text
        elif role == ORIGINROLE:
            return self._items[index.row()].base_url
        elif role == RETWEETOFROLE:
            try:
                return self._items[index.row()].retweeted_status
            except:
                return None
        elif role == ISMEROLE:
            try:
                return self._items[index.row()].is_me
            except:
                return False
        elif role == TIMESTAMPROLE:

            return self._items[index.row()].GetRelativeCreatedAt(self.now)
        elif role == PROTECTEDROLE:
            return self._items[index.row()].user.protected
        elif role == USERIDROLE:

            return self._items[index.row()].user.id
        elif role == Qt.DecorationRole:
            try:
                return self._avatars[self._items[index.row()].user.profile_image_url]
            except:
                return self._avatars['default']
        else:
            return None

    def wantsUpdate(self):
        self.layoutChanged.emit()


