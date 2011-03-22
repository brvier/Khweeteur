#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

import time
import pickle
import datetime
import glob
from notifications import KhweeteurNotification 
import os

SCREENNAMEROLE = 20
REPLYTOSCREENNAMEROLE = 21
REPLYTEXTROLE = 22
REPLYIDROLE = 25
IDROLE = 23
ORIGINROLE = 24
TIMESTAMPROLE = 26
RETWEETOFROLE = 27


from PyQt4.QtCore import QAbstractListModel,QModelIndex, \
                         QThread, \
                         Qt, \
                         QSettings, \
                         QObject, \
                         pyqtSignal
                         
from PyQt4.QtGui import QPixmap

    
class KhweetsModel(QAbstractListModel):

    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    dataChanged = pyqtSignal(QModelIndex,QModelIndex)

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
        return os.path.join(os.path.expanduser("~"), \
                                 '.khweeteur','cache', \
                                 os.path.normcase(unicode(self.call.replace('/', \
                                 '_'))).encode('UTF-8'))

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
        return len(self._items)

    def refreshTimestamp(self):
        self.now = time.time()
        for status in self._items:
            try:
                status.relative_created_at = self.GetRelativeCreatedAt(status.created_at)
            except StandardError, e:
                print e

        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(0,
                              len(self._items)))
                              
    def addStatuses(self, uids):
        #Optimization
        folder_path = self.getCacheFolder()
        pickleload = pickle.load
        try:
            keys = []
            for uid in uids:
                try:
                    pkl_file = open(os.path.join(folder_path,
                                    str(uid)), 'rb')
                    status = pickleload(pkl_file)
                    pkl_file.close()

                    #Test if status already exists
                    if status.id not in self._uids:
                        self._uids.append(status.id)
                        self._items.append(status)

                except StandardError, e:
                    print e

        except StandardError, e:
            print "We shouldn't got this error here :", e
            import traceback
            traceback.print_exc()
            
        self._items.sort()
        self._uids.sort()        
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(0,
                              len(self._items)))

    def destroyStatus(self, index):
        self._items.pop(index.row())
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(0,
                              len(self._items)))


    def load(self,call):
        self.call = call
        self._items=[]
        try:
            folder = self.getCacheFolder()
            uids = glob.glob(folder + u'/*')
            pickleload = pickle.load
            avatar_path = os.path.join(os.path.expanduser("~"),
                        '.khweeteur','avatars')
            for uid in uids:
                pkl_file = open(os.path.join(folder,
                                str(uid)), 'rb')
                status = pickleload(pkl_file)
                pkl_file.close()
    
                #Test if status already exists
                if status not in self._items:
                    self._uids.append(status.id)
                    self._items.append(status)
                    if hasattr(status, 'user'):                                       
                        profile_image = os.path.basename(status.user.profile_image_url.replace('/'                        
                                             , '_'))                                                          
                    else:                                                                                     
                        profile_image = '/opt/usr/share/icons/hicolor/64x64/hildon/general_default_avatar.png'
   
                    if profile_image not in self._avatars:                                                
                        try:
                            self._avatars[status.user.profile_image_url] = QPixmap(os.path.join(avatar_path,
                                        profile_image))                  
                        except:
                            pass

#            self._items.sort()
            self._items.sort(key=lambda status:status.created_at_in_seconds, reverse=True)
#            for status in self._items:
#                print status.created_at_in_seconds
                
            self.dataChanged.emit(self.createIndex(0, 0),
                                  self.createIndex(0,
                                  len(self._items)))
    
        except StandardError, e:
            print 'unSerialize : ', e

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
        # 10 -> Retweet of

        if role == Qt.DisplayRole:
            return self._items[index.row()].text
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
            return self._items[index.row()].source
        elif role == RETWEETOFROLE:
#            return False
            try:
                return self._items[index.row()].retweeted_status
            except:
                return None
        elif role == TIMESTAMPROLE:
            return self._items[index.row()].relative_created_at
        elif role == Qt.DecorationRole:
            try:
                return self._avatars[self._items[index.row()].user.profile_image_url]
            except KeyError, keye:
                pass
        else:
            return None

    def wantsUpdate(self):
        #QObject.emit(self, SIGNAL('layoutChanged()'))
        self.layoutChanged.emit()
