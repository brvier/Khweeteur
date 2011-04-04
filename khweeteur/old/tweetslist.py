#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with PySide and QML'''

__version__ = '0.2.0'

from PySide.QtGui import *
from PySide.QtCore import *

import os
import sys

AVATAR_CACHE_FOLDER = '/home/user/.khweeteur/cache'

class StatusWrapper(QObject):
    def __init__(self,status):
        QObject.__init__(self)
        self._status = status
        
    def _screen_name(self):
        return self._status.user.screen_name

    def _id(self):
        return self._status.id
        
    def _image_url(self):
        return self._status.user.profile_image_url

    def _avatar(self):
        return os.path.join(AVATAR_CACHE_FOLDER, \
            os.path.basename(self._status.user.profile_image_url.replace('/' , '_')))

    def _text(self):
        return self._status.text

    def _created_at(self):
        return self._status.created_at

    def _in_reply_to_screenname(self):        
        return self._status.in_reply_to_screenname

    @Signal
    def changed(self):
        pass
        
    screen_name = Property(unicode, _screen_name, notify=changed)
    id = Property(unicode, _id, notify=changed)
    image_url = Property(unicode, _image_url, notify=changed)
    avatar = Property(unicode, _avatar, notify=changed)
    text = Property(unicode, _text, notify=changed)
    created_at = Property(unicode, _created_at, notify=changed)
    in_reply_to_screenname = Property(unicode, _in_reply_to_screenname, notify=changed)

class TweetsListModel(QAbstractListModel):
    COLUMNS = ('status',)

    def __init__(self, statuses = []):
        QAbstractListModel.__init__(self)
        self._statuses = statuses
        self.setRoleNames(dict(enumerate(TweetsListModel.COLUMNS)))

    def rowCount(self,parent=QModelIndex):
        return len(self._statuses)

    def data(self,index,role):
        if index.isValid():
            return self._statuses[index.row()]
        else:
            return None
	
class Controller(QObject):
    @Slot(QObject)
    def statusSelected(self, wrapper):
        print 'User clicked on:', wrapper._status.id

