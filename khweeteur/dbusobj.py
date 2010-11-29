#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3
#!/usr/bin/env python

import dbus
import dbus.service

class KhweeteurDBus(dbus.service.Object):
    '''DBus Object handle dbus callback'''
    def __init__(self):
        bus_name = dbus.service.BusName('net.khertan.khweeteur', bus=dbus.SessionBus())
#        dbus.service.Object.__init__(self, self.bus, '/net/khertan/khweeteur')
        dbus.service.Object.__init__(self, bus_name, '/net/khertan/khweeteur')
    #activated = pyqtSignal()

    @dbus.service.method(dbus_interface='net.khertan.khweeteur')
    def show_now(self):
        '''Callback called to active the window and reset counter'''
        print 'dbus ?'
        self.app.activated_by_dbus.emit()
        return True

    def attach_app(self, app):
        self.app = app