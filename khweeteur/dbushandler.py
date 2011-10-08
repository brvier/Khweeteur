#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

import dbus.service
import os.path
from subprocess import Popen, PIPE
from posttweet import post_tweet
import logging
from functools import wraps
import sys
import time

try:
    from PySide.QtMaemo5 import *
except ImportError:
    pass
    
from PySide.QtCore import Qt, QTimer

def isThisRunning( process_name ):
  ps = Popen("ps -eaf", shell=True, stdout=PIPE)
  output = ""
  try:
      output = ps.stdout.read()
  except Exception, e:
      logging.exception("read(): %s" % str(e))
  ps.stdout.close()
  ps.wait()
  return process_name in output

class KhweeteurDBusHandler(dbus.service.Object):
    """
    Class responsible for sending messages to Khweeteur daemon and
    managing callbacks.
    """
    def __init__(self, parent):
        dbus.service.Object.__init__(self, dbus.SessionBus(),
                                     '/net/khertan/khweeteur')

        self.parent = parent

        # Post Folder
        self.post_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                      'topost')

    def start_daemon(self):
        if not isThisRunning('daemon.py'):
            logging.error("starting daemon")
            Popen(['/usr/bin/python',
                  os.path.join(os.path.dirname(__file__),
                  'daemon.py'),
                  'start'])

    def retry(self, f, *args, **kwargs):
        """Start daemon and call the function after a short delay."""
        self.start_daemon()
        if hasattr(self, '_iface'):
            del self._iface

        def cb(self, args, kwargs):
            def doit():
                return f(*args, **kwargs)
            return doit
        logging.debug("Started daemon.  Retrying call in 5 seconds.")
        QTimer.singleShot(5 * 1000, cb(self, args, kwargs))

    @property
    def iface(self):
        if not hasattr(self, '_iface'):
            bus = dbus.SessionBus()
            obj = bus.get_object('net.khertan.khweeteur.daemon',
                                 '/net/khertan/khweeteur/daemon')
            self._iface = dbus.Interface(obj, 'net.khertan.khweeteur.daemon')

        return self._iface

    def require_update(self, optional=True, only_uploads=False, first_try=True):
        def success_handler(update_started):
            if not update_started:
                try:
                    self.parent.setAttribute(
                        Qt.WA_Maemo5ShowProgressIndicator, update_started)
                except:
                    pass

        def error_handler(exception):
            if first_try:
                logging.error("Error starting update, retrying: %s"
                              % (str(exception)))
                self.retry(self.require_update,
                           optional, only_uploads, first_try=False)
            else:
                # We've tried twice.  Give up.
                logging.error("Error starting update: %s" % (str(exception)))
                self.parent.setAttribute(
                    Qt.WA_Maemo5ShowProgressIndicator, False)

        try:
            self.parent.setAttribute(
                Qt.WA_Maemo5ShowProgressIndicator, True)
        except:
            pass

        # Run ansynchronously to avoid blocking the user interface.
        self.iface.require_update(
            optional, only_uploads,
            reply_handler=success_handler,
            error_handler=error_handler)

    @dbus.service.method(dbus_interface='net.khertan.khweeteur')
    def show_now(self):
        '''Callback called to active the window and reset counter.

        See notifications.py.'''
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
        return post_tweet(shorten_url, serialize, text, latitude, longitude,
                          base_url, action, tweet_id)
