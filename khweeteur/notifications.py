#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

from PySide.QtCore import QObject
    
try:   
    import dbus
    import dbus.service
    from dbus.mainloop.qt import DBusQtMainLoop
#    from dbusobj import KhweeteurDBus
    noDBUS = False
except:
    noDBUS = True
    print 'No dbus try with pynotify'
    import pynotify
    
class KhweeteurNotification(QObject):
    '''Notification class interface'''
    def __init__(self):
        global noDBUS
        QObject.__init__(self)
        if not noDBUS:
            try:
                self.m_bus = dbus.SystemBus()
                self.m_notify = self.m_bus.get_object('org.freedesktop.Notifications',
                                  '/org/freedesktop/Notifications')
                self.iface = dbus.Interface(self.m_notify, 'org.freedesktop.Notifications')
                self.m_id = 0
            except:
                 noDBUS = True

    def warn(self, message):
        '''Display an Hildon banner'''
        if not noDBUS:
            try:
                self.iface.SystemNoteDialog(message,0, 'Nothing')
            except:
                pass
        else:
            if pynotify.init("Khweeteur"):
                n = pynotify.Notification(message, message)
                n.show()
                
    def info(self, message):
        '''Display an information banner'''
        if not noDBUS:
            try:
                self.iface.SystemNoteInfoprint('Khweeteur : '+message)
            except:
                pass
        else:
            if pynotify.init("Khweeteur"):
                n = pynotify.Notification(message, message)
                n.show()
                
    def notify(self,title, message,category='khweeteur-new-tweets', icon='khweeteur',count=1):
        '''Create a notification in the style of email one'''
        if not noDBUS:
            try:
                self.m_id = self.iface.Notify('Khweeteur',
                                  self.m_id,
                                  icon,
                                  title,
                                  message,
                                  ['default','call'],
                                  {'category':category,
                                  'desktop-entry':'khweeteur',
                                  'dbus-callback-default':'net.khertan.khweeteur /net/khertan/khweeteur net.khertan.khweeteur show_now',
                                  'count':count,
                                  'amount':count},
                                  -1
                                  )
            except:
                pass
                
        else:
            if pynotify.init("Khweeteur"):
                n = pynotify.Notification(title, message)
                n.show()

