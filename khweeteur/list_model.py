#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

from utils import *
import time
import datetime
import glob
from notifications import KhweeteurNotification 

if not USE_PYSIDE:
    from PyQt4.QtCore import QAbstractListModel,QModelIndex, \
                             QThread, \
                             Qt, \
                             QSettings, \
                             QObject
                             
    from PyQt4.QtGui import QPixmap

else:
    from PySide.QtCore import QAbstractListModel,QModelIndex, \
                              QThread, \
                              Qt, \
                              QSettings, \
                              QObject
                              
    from PySide.QtGui import QPixmap
    
class KhweetsModel(QAbstractListModel):

    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    dataChanged = pyqtSignal(QModelIndex,QModelIndex)

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


    def orderLimitAndCacheUids(self):
        self._items.sort()
        self._items.reverse()
        self._items = self._items[:self.khweets_limit]
        self._uids = [item[1] for item in self._items]

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

        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(0,
                              len(self._items)))
                              
    def addStatuses(self, uids):
        #Optimization
        _appendStatusInList = self._appendStatusInList
        pickleload = pickle.load
        try:
            keys = []
            for uid in uids:
                try:
                    pkl_file = open(os.path.join(TIMELINE_PATH,
                                    str(uid)), 'rb')
                    status = pickleload(pkl_file)
                    pkl_file.close()

                    #Test if status already exists
                    if _appendStatusInList(status):
                        keys.append(status.id)

                except IOError, e:
                    print e
        except StandardError, e:

            print "We shouldn't got this error here :", e
            import traceback
            traceback.print_exc()

        if len(keys) > 0:
            self.orderLimitAndCacheUids()

            for key in keys:
                if key in self._uids:
                    self._new_counter += 1

            print 'DEBUG 1'
            self.dataChanged.emit(self.createIndex(0, 0),
                                  self.createIndex(0,
                                  len(self._items)))
            print 'DEBUG 2'

    def destroyStatus(self, index):
        self._items.pop(index.row())
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(0,
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
            return False

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
        return True

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

            if len(uids) != 0:
                self._createCacheList(cach_path, uids)

            if len(self._uids) == 0:
                print 'Cache cleared'
                self.settings = QSettings()
                if not self.keyword:
                    self.settings.remove('last_id')
                else:
                    self.settings.remove(self.keyword + '/last_id')
            else:
                self.orderLimitAndCacheUids()

        except StandardError, e:
            print 'unSerialize : ', e
            self.dataChanged.emit(self.createIndex(0, 0),
                                  self.createIndex(0,
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
        #QObject.emit(self, SIGNAL('layoutChanged()'))
        self.layoutChanged.emit()

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
                    '_'))).encode('UTF-8')) + '/*'):
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

