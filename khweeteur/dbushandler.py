#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

from __future__ import with_statement
import dbus.service
import os.path
from subprocess import Popen, PIPE
        
try:
    from PySide.QtMaemo5 import *
except ImportError:
    pass
    
from PySide.QtCore import Qt

def isThisRunning( process_name ):
  ps = Popen("ps -eaf | grep %s" % process_name, shell=True, stdout=PIPE)
  output = ps.stdout.read()
  ps.stdout.close()
  ps.wait()
  return False if process_name not in output else True


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
        if not isThisRunning('daemon.py'):
            Popen(['/usr/bin/python',
                  os.path.join(os.path.dirname(__file__),
                  'daemon.py'),
                  'start'])

    @dbus.service.method(dbus_interface='net.khertan.khweeteur')
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
        latitude='0',
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
                'latitude': latitude,
                'longitude': longitude,
                'base_url': base_url,
                'action': action,
                'tweet_id': tweet_id,
                }
            pickle.dump(post, fhandle, pickle.HIGHEST_PROTOCOL)
