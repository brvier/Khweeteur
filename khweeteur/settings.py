#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3
'''A simple Twitter client made with pyqt4'''
import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

from PyQt4.QtGui import *
from PyQt4.QtCore import *

from utils import *
from notifications import KhweeteurNotification

KHWEETEUR_TWITTER_CONSUMER_KEY = 'uhgjkoA2lggG4Rh0ggUeQ'
KHWEETEUR_TWITTER_CONSUMER_SECRET = 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU'
KHWEETEUR_IDENTICA_CONSUMER_KEY = 'c7e86efd4cb951871200440ad1774413'
KHWEETEUR_IDENTICA_CONSUMER_SECRET = '236fa46bf3f65fabdb1fd34d63c26d28'
KHWEETEUR_STATUSNET_CONSUMER_KEY = '84e768bba2b6625f459a9a19f5d57bd1'
KHWEETEUR_STATUSNET_CONSUMER_SECRET = 'fbc51241e2ab12e526f89c26c6ca5837'

try:
    from PyQt4.QtMobility.QtLocation import *
#    from PySide.QtMobility.QtLocation import *
    noQtLocation = False
except:
    noQtLocation = True

try:
    from PyQt4.QtMaemo5 import *
#    from PySide.QtMaemo5 import *
    isMAEMO = True
except:
    isMAEMO = False

import oauth2 as oauth

class KhweeteurPref(QMainWindow):
    DEFAULTTHEME = 'Default'
    WHITETHEME = 'White'
    COOLWHITETHEME = 'CoolWhite'
    COOLGRAYTHEME = 'CoolGray'
    THEMES = [DEFAULTTHEME, WHITETHEME, COOLWHITETHEME, COOLGRAYTHEME]

    def __init__(self, parent=None):
        QMainWindow.__init__(self,parent)
        self.parent = parent

        self.settings = QSettings()

        if isMAEMO:
            try: #Preferences not set yet
                if int(self.settings.value('useAutoRotation'))==2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)

            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur Prefs")

        self.setupGUI()
        self.loadPrefs()

    def loadPrefs(self):
        if self.settings.value("refreshInterval"):
            self.refresh_value.setValue(int(self.settings.value("refreshInterval")))
        else:
            self.refresh_value.setValue(10)
        if self.settings.value("displayUser"):
            self.displayUser_value.setCheckState(int(self.settings.value("displayUser")))
        else:
            self.displayUser_value.setCheckState(2)
        if self.settings.value("displayAvatar"):
            self.displayAvatar_value.setCheckState(int(self.settings.value("displayAvatar")))
        if self.settings.value("displayTimestamp"):
            self.displayTimestamp_value.setCheckState(int(self.settings.value("displayTimestamp")))
        if self.settings.value("displayReplyTo"):
            self.displayReplyTo_value.setCheckState(int(self.settings.value("displayReplyTo")))
        if self.settings.value("useNotification"):
            self.useNotification_value.setCheckState(int(self.settings.value("useNotification")))
        if self.settings.value("useSerialization"):
            self.useSerialization_value.setCheckState(int(self.settings.value("useSerialization")))
        if self.settings.value("useBitly"):
            self.useBitly_value.setCheckState(int(self.settings.value("useBitly")))
        if not self.settings.value("theme"):
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        if not self.settings.value("theme") in self.THEMES:
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        if not self.settings.value("theme"):
            self.settings.setValue("useAutoRotation",True)
        self.theme_value.setCurrentIndex(self.THEMES.index(self.settings.value("theme")))
        if self.settings.value("useAutoRotation"):
            self.useAutoRotation_value.setCheckState(int(self.settings.value("useAutoRotation")))
        if self.settings.value("useGPS"):
            self.useGPS_value.setCheckState(int(self.settings.value("useGPS")))
        if self.settings.value("tweetHistory"):
            self.history_value.setValue(int(self.settings.value("tweetHistory")))
        else:
            self.history_value.setValue(30)

    def savePrefs(self):
        self.settings.setValue('refreshInterval', self.refresh_value.value())
        self.settings.setValue('displayUser', self.displayUser_value.checkState())
        self.settings.setValue('useNotification', self.useNotification_value.checkState())
        self.settings.setValue('useSerialization', self.useSerialization_value.checkState())
        self.settings.setValue('displayAvatar', self.displayAvatar_value.checkState())
        self.settings.setValue('displayTimestamp', self.displayTimestamp_value.checkState())
        self.settings.setValue('displayReplyTo', self.displayReplyTo_value.checkState())
        self.settings.setValue('useBitly', self.useBitly_value.checkState())
        self.settings.setValue('theme', self.theme_value.currentText())
        self.settings.setValue('useAutoRotation', self.useAutoRotation_value.checkState())
        self.settings.setValue('useGPS', self.useGPS_value.checkState())
        self.settings.setValue('tweetHistory', self.history_value.value())
        self.emit(SIGNAL("save()"))

    def closeEvent(self,widget,*args):
        self.savePrefs()

    def request_twitter_access_or_clear(self):
        if self.settings.value('twitter_access_token'):
            self.settings.setValue('twitter_access_token_key','')
            self.settings.setValue('twitter_access_token_secret','')
            self.settings.setValue('twitter_access_token',False)
            self.twitter_value.setText(self.tr('Auth on Twitter'))
        else:

            try:
                if not self.parent.nw.device_has_networking:
                    self.parent.nw.request_connection_with_tmp_callback(self.request_twitter_access_or_clear)
                else:
                    raise StandardError(self.tr('No network control'))
            except:
                import os
                import sys
                try:
                    from urlparse import parse_qsl
                except:
                    from cgi import parse_qsl

                REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
                ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
                AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'

                signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
                oauth_consumer             = oauth.Consumer(key=KHWEETEUR_TWITTER_CONSUMER_KEY, secret=KHWEETEUR_TWITTER_CONSUMER_SECRET)
                oauth_client               = oauth.Client(oauth_consumer)

                resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')

                if resp['status'] != '200':
                    KhweeteurNotification().warn(self.tr('Invalid respond from Twitter requesting temp token: %s') % resp['status'])
                else:
                    request_token = dict(parse_qsl(content))

                    QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))

                    pincode, ok = QInputDialog.getText(self, self.tr('Twitter Authentification'), self.tr('Enter the pincode :'))

                    if ok:
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                        token.set_verifier(str(pincode))

                        oauth_client  = oauth.Client(oauth_consumer, token)
                        resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                        access_token  = dict(parse_qsl(content))

                        if resp['status'] != '200':
                            KhweeteurNotification().warn(self.tr('The request for a Token did not succeed: %s') % resp['status'])
                            self.settings.setValue('twitter_access_token_key','')
                            self.settings.setValue('twitter_access_token_secret','')
                            self.settings.setValue('twitter_access_token',False)
                        else:
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('twitter_access_token_key',access_token['oauth_token'])
                            self.settings.setValue('twitter_access_token_secret',access_token['oauth_token_secret'])
                            self.settings.setValue('twitter_access_token',True)
                            self.twitter_value.setText(self.tr('Clear Twitter Auth'))
                            KhweeteurNotification().info(self.tr('Khweeteur is now authorized to connect'))
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def request_identica_access_or_clear(self):
        import urllib
        if self.settings.value('identica_access_token'):
            self.settings.setValue('identica_access_token_key','')
            self.settings.setValue('identica_access_token_secret','')
            self.settings.setValue('identica_access_token',False)
            self.identica_value.setText(self.tr('Auth on Identi.ca'))
        else:
            try:
                if not self.parent.nw.device_has_networking:
                    self.parent.nw.request_connection_with_tmp_callback(self.request_identica_access_or_clear)
                else:
                    raise StandardError(self.tr('No network control'))
            except:
                import os
                import sys
                try:
                    from urlparse import parse_qsl
                except:
                    from cgi import parse_qsl

                REQUEST_TOKEN_URL = 'http://identi.ca/api/oauth/request_token'
                ACCESS_TOKEN_URL  = 'http://identi.ca/api/oauth/access_token'
                AUTHORIZATION_URL = 'http://identi.ca/api/oauth/authorize'

                signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
                oauth_consumer             = oauth.Consumer(key=KHWEETEUR_IDENTICA_CONSUMER_KEY, secret=KHWEETEUR_IDENTICA_CONSUMER_SECRET)
                oauth_client               = oauth.Client(oauth_consumer)
                oauth_callback_uri = 'oob'
                #Crappy hack for fixing oauth_callback not yet supported by the oauth2 lib but requested by identi.ca
                resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'POST', body=urllib.urlencode(dict(oauth_callback=oauth_callback_uri)))
                write_log(resp)
                write_log(content)
                if resp['status'] != '200':
                    KhweeteurNotification().warn(self.tr('Invalid respond from Identi.ca requesting temp token: %s') % resp['status'])
                else:
                    request_token = dict(parse_qsl(content))

                    QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))

                    pincode, ok = QInputDialog.getText(self, self.tr('Identi.ca Authentification'), self.tr('Enter the token :'))

                    if ok:
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                        token.set_verifier(str(pincode))

                        oauth_client  = oauth.Client(oauth_consumer, token)
                        resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                        write_log(resp)
                        write_log(content)
                        access_token  = dict(parse_qsl(content))

                        if resp['status'] != '200':
                            KhweeteurNotification().warn(self.tr('The request for a Token did not succeed: %s') % resp['status'])
                            self.settings.setValue('identica_access_token_key','')
                            self.settings.setValue('identica_access_token_secret','')
                            self.settings.setValue('identica_access_token',False)
                        else:
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('identica_access_token_key',access_token['oauth_token'])
                            self.settings.setValue('identica_access_token_secret',access_token['oauth_token_secret'])
                            self.settings.setValue('identica_access_token',True)
                            self.identica_value.setText(self.tr('Clear Identi.ca Auth'))
                            KhweeteurNotification().info(self.tr('Khweeteur is now authorized to connect'))
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def request_statusnet_access_or_clear(self):
        QMessageBox.question(self,
           "Khweeteur",
           "Status.net isn't yet fully implemented",
           QMessageBox.Close)
        return

        if self.settings.value('statusnet_access_token'):
            self.settings.setValue('statusnet_access_token_key','')
            self.settings.setValue('statusnet_access_token_secret','')
            self.settings.setValue('statusnet_access_token',False)
            self.status_value.setText(self.tr('Auth on Status.net'))
        else:
            try:
                if not self.parent.nw.device_has_networking:
                    self.parent.nw.request_connection_with_tmp_callback(self.request_identica_access_or_clear)
                else:
                    raise StandardError(self.tr('No network control'))
            except:
                import os
                import sys
                try:
                    from urlparse import parse_qsl
                except:
                    from cgi import parse_qsl

                REQUEST_TOKEN_URL = 'http://khertan.status.net/api/oauth/request_token'
                ACCESS_TOKEN_URL  = 'http://khertan.status.net/api/oauth/access_token'
                AUTHORIZATION_URL = 'http://khertan.status.net/api/oauth/authorize'

                signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
                oauth_consumer             = oauth.Consumer(key=KHWEETEUR_STATUSNET_CONSUMER_KEY, secret=KHWEETEUR_STATUSNET_CONSUMER_SECRET)
                oauth_client               = oauth.Client(oauth_consumer)

                resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')

                if resp['status'] != '200':
                    KhweeteurNotification().warn(self.tr('Invalid respond from Status.net requesting temp token: %s') % resp['status'])
                else:
                    request_token = dict(parse_qsl(content))

                    QDesktopServices.openUrl(QUrl('%s?oauth_token=%s' % (AUTHORIZATION_URL, request_token['oauth_token'])))

                    pincode, ok = QInputDialog.getText(self, self.tr('Status.net Authentification'), self.tr('Enter the token :'))

                    if ok:
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,True)
                        token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
                        token.set_verifier(str(pincode))

                        oauth_client  = oauth.Client(oauth_consumer, token)
                        resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % str(pincode))
                        access_token  = dict(parse_qsl(content))

                        if resp['status'] != '200':
                            KhweeteurNotification().warn(self.tr('The request for a Token did not succeed: %s') % resp['status'])
                            self.settings.setValue('statusnet_access_token_key','')
                            self.settings.setValue('statusnet_access_token_secret','')
                            self.settings.setValue('statusnet_access_token',False)
                        else:
                            #print access_token['oauth_token']
                            #print access_token['oauth_token_secret']
                            self.settings.setValue('statusnet_access_token_key',access_token['oauth_token'])
                            self.settings.setValue('statusnet_access_token_secret',access_token['oauth_token_secret'])
                            self.settings.setValue('statusnet_access_token',True)
                            self.statusnet_value.setText(self.tr('Clear Status.net Auth'))
                            KhweeteurNotification().info(self.tr('Khweeteur is now authorized to connect'))
                        if isMAEMO:
                            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator,False)

    def setupGUI(self):
#        self.aWidget = QWidget()
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.aWidget = QWidget(self.scrollArea)
        self.aWidget.setMinimumSize(480,1000)
        self.aWidget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollArea.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollArea.setWidget(self.aWidget)
        #Available on maemo but should be too on Meego
        try:
            scroller = self.scrollArea.property("kineticScroller")
            scroller.setEnabled(True)
        except:
            pass
        self._main_layout = QGridLayout(self.aWidget)

        self._main_layout.addWidget(QLabel(self.tr('Authorizations :')),0,0)
        if self.settings.value(self.tr('twitter_access_token')):
            self.twitter_value = QPushButton(self.tr('Clear Twitter Auth'))
        else:
            self.twitter_value = QPushButton(self.tr('Auth on Twitter'))
        self._main_layout.addWidget(self.twitter_value,0,1)
        self.connect(self.twitter_value, SIGNAL('clicked()'), self.request_twitter_access_or_clear)

        if self.settings.value('identica_access_token'):
            self.identica_value = QPushButton(self.tr('Clear Identi.ca Auth'))
        else:
            self.identica_value = QPushButton(self.tr('Auth on Identi.ca'))
        self._main_layout.addWidget(self.identica_value,1,1)
        self.connect(self.identica_value, SIGNAL('clicked()'), self.request_identica_access_or_clear)

        #Remove statusnet oauth as it didn't support subdomain
        #and require app keys for each subdomain

        self._main_layout.addWidget(QLabel(self.tr('Refresh Interval (Minutes) :')),3,0)
        self.refresh_value = QSpinBox()
        self._main_layout.addWidget(self.refresh_value,3,1)

        self._main_layout.addWidget(QLabel(self.tr('Number of tweet to keep in the view (History) :')),4,0)
        self.history_value = QSpinBox()
        self._main_layout.addWidget(self.history_value,4,1)

        self._main_layout.addWidget(QLabel(self.tr('Display preferences :')),5,0)
        self.displayUser_value = QCheckBox(self.tr('Display username'))
        self._main_layout.addWidget(self.displayUser_value,5,1)

        self.displayAvatar_value = QCheckBox(self.tr('Display avatar'))
        self._main_layout.addWidget(self.displayAvatar_value,6,1)

        self.displayTimestamp_value = QCheckBox(self.tr('Display timestamp'))
        self._main_layout.addWidget(self.displayTimestamp_value,7,1)

        self.displayReplyTo_value = QCheckBox(self.tr('Display reply to'))
        self._main_layout.addWidget(self.displayReplyTo_value,8,1)

        self.useAutoRotation_value = QCheckBox(self.tr('Use AutoRotation'))
        self._main_layout.addWidget(self.useAutoRotation_value,9,1)

        self._main_layout.addWidget(QLabel(self.tr('Other preferences :')),9,0)
        self.useNotification_value = QCheckBox(self.tr('Use Notification'))
        self._main_layout.addWidget(self.useNotification_value,10,1)

        self.useSerialization_value = QCheckBox(self.tr('Use Serialization'))
        self._main_layout.addWidget(self.useSerialization_value,11,1)

        self.useBitly_value = QCheckBox(self.tr('Use Bit.ly'))
        self._main_layout.addWidget(self.useBitly_value,12,1)

        self.useGPS_value = QCheckBox(self.tr('Use GPS Geopositionning'))
        self._main_layout.addWidget(self.useGPS_value,13,1)

        self._main_layout.addWidget(QLabel(self.tr('Theme :')),14,0)

        self.theme_value = QComboBox()
        self._main_layout.addWidget(self.theme_value,14,1)
        for theme in self.THEMES:
            self.theme_value.addItem(theme)

        self.aWidget.setLayout(self._main_layout)
        self.setCentralWidget(self.scrollArea)
