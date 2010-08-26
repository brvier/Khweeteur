import conic
import dbus
import dbus.glib
import gobject

from PySide.QtCore import QObject

""" DBus connection monitor. Monitors device internet connection and can requests one if needed.
    most code taken from PyMaemo conic examples http://pymaemo.garage.maemo.org/conic.html """

class NetworkManager(QObject):
    
    def __init__(self, callback_if_connected=None):
        QObject.__init__(self)
        self.device_has_networking = False
        self.connection = None
        self.bearer = None
        
        self.callback_if_connected = callback_if_connected

        # Note prints so I wont forget the hack on for releases
        if self.device_has_networking:
            print "\n" + 10 * " >> >> NOTE: Scratchbox networking enabled hack in use!\n"

        self.gmainloop = gobject.MainLoop()
        self.mainloop_context = self.gmainloop.get_context()
        self.bus = dbus.SystemBus(private=True)
        
        gobject.threads_init()
        self.start_monitoring() 
        self.startTimer(250)
        
    def timer_event(self, q_timer_event):
        self.iteration()
                
    def iteration(self):
        self.mainloop_context.iteration(True)
        
    def request_connection(self):
        if not self.device_has_networking:
            self.connection.request_connection(conic.CONNECT_FLAG_NONE)

    def start_monitoring(self):
        if self.device_has_networking:
            return
        self.connection = conic.Connection()
        self.connection.connect("connection-event", self.connection_callback, 0xAA55)
        self.connection.set_property("automatic-connection-events", True)
        return False
        
    def stop_monitoring(self):
        self.connection.set_property("automatic-connection-events", False)

    def connection_callback(self, connection, event, magic):
        message = None
        status = event.get_status()
        error = event.get_error()
        iap_id = event.get_iap_id()
        bearer = event.get_bearer_type()    
        
        if status == conic.STATUS_CONNECTED:
            if self.device_has_networking:
                return
            if bearer != None:
                message = "Device online: connected with " + bearer
            else:
                message = "Device online"
            self.device_has_networking = True
        elif status == conic.STATUS_DISCONNECTED:
            if self.device_has_networking == False:
                return
            if bearer != None:
                message = "Device offline: disconnected from " + bearer
            else:
                message = "Device offline"
            self.device_has_networking = False
        elif status == conic.STATUS_DISCONNECTING:
            return
        else:
            return
#        if message != None:
#            self.logger.network(message)
        
        self.bearer = bearer
        if (self.device_has_networking):
            self.callback_if_connected()

