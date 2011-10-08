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
        
try:
    from PySide.QtMaemo5 import *
except ImportError:
    pass
    
from PySide.QtCore import Qt

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

    def require_update(self, optional=False):
        def success_handler(update_started):
            try:
                self.parent.setAttribute(
                    Qt.WA_Maemo5ShowProgressIndicator, update_started)
            except:
                pass

        def error_handler(exception):
            logging.error("Error starting update: %s" % (str(exception)))

            if hasattr(self, 'iface'):
                del self.iface

        if not isThisRunning('daemon.py'):
            Popen(['/usr/bin/python',
                  os.path.join(os.path.dirname(__file__),
                  'daemon.py'),
                  'start'])

        if not hasattr(self, 'iface'):
            bus = dbus.SessionBus()
            obj = bus.get_object('net.khertan.khweeteur.daemon',
                                 '/net/khertan/khweeteur/daemon')
            self.iface = dbus.Interface(obj, 'net.khertan.khweeteur.daemon')

        # Run ansynchronously to avoid blocking the user interface.
        self.iface.require_update(
            optional,
            reply_handler=success_handler,
            error_handler=error_handler)


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
        return post_tweet(shorten_url, serialize, text, latitude, longitude,
                          base_url, action, tweet_id)
