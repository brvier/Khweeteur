#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with PySide and QML'''

from PySide.QtGui import *
from PySide.QtCore import *

import os
import sys
import glob
import pickle
import time
import twitter
import dbus
import dbus.service

AVATAR_CACHE_FOLDER = '/home/user/.khweeteur/avatars'

class KhweeteurDBusHandler(dbus.service.Object):
    def __init__(self):
        dbus.service.Object.__init__(self, dbus.SessionBus(), '/net/khertan/Khweeteur/RequireUpdate')

    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur',
                         signature='')
    def require_update(self):
        pass
        
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

    def __cmp__(obj1,obj2):
        if obj1._status.created_at == obj2._status.created_at:
            return 0
        if obj1._status.created_at > obj2._status.created_at:
            return -1
        else:
            return 1
        
    screen_name = Property(unicode, _screen_name, notify=changed)
    id = Property(unicode, _id, notify=changed)
    image_url = Property(unicode, _image_url, notify=changed)
    avatar = Property(unicode, _avatar, notify=changed)
    text = Property(unicode, _text, notify=changed)
    created_at = Property(unicode, _created_at, notify=changed)
    in_reply_to_screenname = Property(unicode, _in_reply_to_screenname, notify=changed)

class TweetsListModel(QAbstractListModel):
#    dataChanged = Signal(QModelIndex,QModelIndex)

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

    @Slot(unicode)
    def load_list(self,tweetlist):
        print 'load timeline tweets'
        start = time.time()
        TIMELINE_PATH = '/home/user/.khweeteur/cache/%s' % (tweetlist)
        cach_path = TIMELINE_PATH
        uids = glob.glob(cach_path + '/*')[:60]
        statuses = []
        for uid in uids:
            uid = os.path.basename(uid)
            try:
                pkl_file = open(os.path.join(cach_path, uid), 'rb')
                status = pickle.load(pkl_file)
                pkl_file.close()
                statuses.append(status)
            except:
                pass
        print time.time() - start
        print len(statuses) 
        self._statuses = [StatusWrapper(status) for status in statuses]
        self._statuses.sort()

        #FIXME
        #Wait pyside bug is resolved
#        self.dataChanged.emit(self.createIndex(0, 1),
#                              self.createIndex(0,
#                              len(self._statuses)))


class ButtonWrapper(QObject):
    def __init__(self,button):
        QObject.__init__(self)
        self._button = button
        
    def _label(self):
        return self._button['label']

    def _count(self): 
        return self._button['count']

    def _src(self): 
        return self._button['src']
        
    @Signal
    def changed(self):
        pass
        
    label = Property(unicode, _label, notify=changed)
    src = Property(unicode, _src, notify=changed)
    count = Property(int, _count, notify=changed)

class ToolbarListModel(QAbstractListModel):
    COLUMNS = ('button',)
    def __init__(self,):
        QAbstractListModel.__init__(self)
        self._buttons = []
        self._buttons.append(ButtonWrapper({'label':'','src':'refresh.png','count':0}))
        self._buttons.append(ButtonWrapper({'label':'Timeline','src':'','count':0}))
        self._buttons.append(ButtonWrapper({'label':'Mentions','src':'','count':0}))
        self._buttons.append(ButtonWrapper({'label':'DMs','src':'','count':0}))
        self.setRoleNames(dict(enumerate(ToolbarListModel.COLUMNS)))

    def rowCount(self,parent=QModelIndex):
        return len(self._buttons)

    def data(self,index,role):
        if index.isValid():
            return self._buttons[index.row()]
        else:
            return None

    def setCount(self,msg,count):
        for button in self._buttons:
            if button._button['label'] == msg:
                button._button['count'] = int(count)

        #FIXME
        #Wait pyside bug is resolved
#        self.dataChanged.emit(self.createIndex(0, 1),
#                              self.createIndex(0,
#                              len(self._statuses)))
   	
class Controller(QObject):
    switch_fullscreen = Signal()
    switch_list = Signal(unicode)

    def __init__(self):
        QObject.__init__(self,None)
        self.dbus_handler = KhweeteurDBusHandler()
        
    @Slot(QObject)
    def statusSelected(self, wrapper):
        print 'User clicked on:', wrapper._status.id

    @Slot(unicode)
    def toolbar_callback(self,name):
        print name
        if name.endswith('fullsize.png'):
            self.switch_fullscreen.emit()
        elif name.endswith('Timeline'):
            QApplication.processEvents()
            self.switch_list.emit('HomeTimeline')
        elif name.endswith('Mentions'):
            QApplication.processEvents()
            self.switch_list.emit('Mentions')
        elif name.endswith('refresh.png'):
            QApplication.processEvents()
            self.dbus_handler.require_update()
