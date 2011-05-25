#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

from __future__ import with_statement
import dbus.service
import os.path
try:
    from PySide.QtMaemo5 import *
except:
    pass
    
from PySide.QtCore import Qt

class KhweeteurDBusHandler(dbus.service.Object):

    def __init__(self, parent):
        dbus.service.Object.__init__(self, dbus.SessionBus(),
                                     '/net/khertan/Khweeteur')
        self.parent = parent

        # Post Folder

        self.post_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                      'topost')

    @dbus.service.signal(dbus_interface='net.khertan.Khweeteur')
    def require_update(self, optional=None):
        try:
            self.parent.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
        except:
            pass

    @dbus.service.method(dbus_interface='net.khertan.Khweeteur')
    def show_now(self):
        '''Callback called to active the window and reset counter'''
        self.win.activated_by_dbus.emit()
        return True

    def attach_win(self, win):
        self.win = win
        
    def post_tweet(
        self,
        shorten_url=1,
        serialize=1,
        text='',
        lattitude='0',
        longitude='0',
        base_url='',
        action='',
        tweet_id='0',
        ):
        import time
        import pickle
        if not os.path.exists(self.post_path):
            os.makedirs(self.post_path)
        with open(os.path.join(self.post_path, str(time.time())), 'wb') as \
            fhandle:
            post = {
                'shorten_url': shorten_url,
                'serialize': serialize,
                'text': text,
                'lattitude': lattitude,
                'longitude': longitude,
                'base_url': base_url,
                'action': action,
                'tweet_id': tweet_id,
                }
            pickle.dump(post, fhandle, pickle.HIGHEST_PROTOCOL)
