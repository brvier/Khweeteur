#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3
'''A simple Twitter client made with pyqt4'''

import datetime
import httplib2
import re

#import sip
#sip.setapi('QString', 2)
#sip.setapi('QVariant', 2)

from PySide.QtGui import QMainWindow, \
    QSizePolicy, \
    QSpinBox, \
    QVBoxLayout, \
    QDesktopServices, \
    QAbstractItemView, \
    QScrollArea, \
    QListView, \
    QComboBox, \
    QCheckBox, \
    QDialog, \
    QGridLayout, \
    QWidget, \
    QToolBar, \
    QLabel, \
    QPushButton, \
    QInputDialog, \
    QKeySequence, \
    QMenu, \
    QAction, \
    QApplication, \
    QIcon, \
    QMessageBox, \
    QPlainTextEdit
                         
from PySide.QtCore import Qt, \
    QUrl, \
    QAbstractListModel, \
    QSettings, \
    QModelIndex, \
    Signal

#Signal = pyqtSignal
   
SUPPORTED_ACCOUNTS = [{'name':'Twitter',
                           'consumer_key':'uhgjkoA2lggG4Rh0ggUeQ',
                           'consumer_secret':'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU',
                           'base_url':'https://api.twitter.com/1',
                           'request_token_url':'https://api.twitter.com/oauth/request_token',
                           'access_token_url':'https://api.twitter.com/oauth/access_token',
                           'authorization_url':'https://api.twitter.com/oauth/authorize'},
                          {'name':'Identi.ca',
                           'consumer_key':'c7e86efd4cb951871200440ad1774413',
                           'consumer_secret':'236fa46bf3f65fabdb1fd34d63c26d28',
                           'base_url':'http://identi.ca/api',
                           'request_token_url':'http://identi.ca/api/oauth/request_token',
                           'access_token_url':'http://identi.ca/api/oauth/access_token',
                           'authorization_url':'http://identi.ca/api/oauth/authorize'},                          
                         ]

import oauth2 as oauth
from notifications import KhweeteurNotification

try:
    from urlparse import parse_qs
except:
    from cgi import parse_qs

from PyQt4.QtWebKit import *

class OAuthView(QWebView):
    gotpin = Signal(unicode)
    def __init__(self, parent=None, account_type={},use_for_tweet=False):  
        QWebView.__init__(self,parent)  
        self.loggedIn = False  
        self.account_type = account_type
        self.use_for_tweet = use_for_tweet
        self.pin = None
        
    def open(self, url):  
        """."""  
        self.url = QUrl(url)  
        self.loadFinished.connect(self._loadFinished)  
        self.load(self.url)
        self.show()

    def createWindow(self, windowType):  
        """Load links in the same web-view."""  
        return self  

    def _loadFinished(self):  

        regex = re.compile('.*<div.*oauth_pin.*>(.*)<')
        res = regex.findall(self.page().mainFrame().toHtml())
        if len(res)>0:
            self.pin = res[0]
            
        self.loggedIn = (self.pin not in (None,''))

        if self.loggedIn:  
            self.loadFinished.disconnect(self._loadFinished)
            self.gotpin.emit(self.pin)

class AccountDlg( QDialog):
    """ Find and replace dialog """
    add_account = Signal(dict,bool)
    
    def __init__(self, parent=None):
        QDialog.__init__(self,parent)
        self.setWindowTitle("Add account")

        self.accounts_type = QComboBox()
        for account_type in SUPPORTED_ACCOUNTS:
            self.accounts_type.addItem(account_type['name'])
            
        self.use_for_tweet =  QCheckBox("Use for posting")

        self.add =  QPushButton("&Add")
        
        gridLayout =  QGridLayout()
        gridLayout.addWidget(self.accounts_type, 0, 0)
        gridLayout.addWidget(self.use_for_tweet, 0, 1)
        gridLayout.addWidget(self.add, 1, 2)
        self.setLayout(gridLayout)
#        self.twitterAccount.clicked.connect(self.switchType)
#        self.identicaAccount.clicked.connect(self.switchType)
        self.add.clicked.connect(self.addit)        
        
#    def switchType(self):
#        if self.twitterAccount.isChecked():
#           self.identicaAccount.setChecked(0) 
#        elif self.identicaAccount.isChecked():
#           self.twitterAccount.setChecked(0) 

    def addit(self):
        index = self.accounts_type.currentIndex()
        self.add_account.emit(SUPPORTED_ACCOUNTS[index],
                              self.use_for_tweet.isChecked())
        self.hide()

        
class AccountsModel(QAbstractListModel):
    dataChanged = Signal(QModelIndex,QModelIndex)
    
    def __init__(self):
        QAbstractListModel.__init__(self)
        self._items = []

    def set(self,mlist):
        self._items =mlist
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(0,
                              len(self._items)))
        
    def rowCount(self, parent = QModelIndex()):
        return len(self._items)
        
    def data(self, index, role = Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self._items[index.row()].name
        else:
            return None

class AccountsView(QListView):
    def __init__(self, parent = None):
        QListView.__init__(self, parent)   
        self.setEditTriggers(QAbstractItemView.SelectedClicked)
            
class KhweeteurAccount():
    def __init__(self, name='Unknow', consumer_key='', consumer_secret='', token_key='', token_secret='', use_for_tweet=True, base_url='' ):
       self.consumer_key = consumer_key
       self.consumer_secret = consumer_secret
       self.token_key = token_key
       self.token_secret = token_secret
       self.use_for_tweet = use_for_tweet
       self.base_url = base_url
       self.name = name
        
class KhweeteurPref(QMainWindow):
    save = Signal()
    
    DEFAULTTHEME = 'Default'
    WHITETHEME = 'White'
    COOLWHITETHEME = 'CoolWhite'
    COOLGRAYTHEME = 'CoolGray'
    ALTERNATETHEME = 'Alternate'
    THEMES = [DEFAULTTHEME, WHITETHEME, COOLWHITETHEME, COOLGRAYTHEME, ALTERNATETHEME]

    def __init__(self, parent=None):
        ''' Init the GUI Win'''
        QMainWindow.__init__(self,parent)
        self.parent = parent

        self.settings = QSettings()

        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)            
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle("Khweeteur Prefs")

        self._setupGUI()
        self.loadPrefs()

    def loadPrefs(self):
        ''' Load and init default prefs to GUI'''
        #load account
        self.accounts = []
        nb_accounts = self.settings.beginReadArray('accounts')
        for index in range(nb_accounts):
            self.settings.setArrayIndex(index)
            self.accounts.append(KhweeteurAccount(name=self.settings.value('name'), \
                consumer_key=self.settings.value('consumer_key'), \
                consumer_secret=self.settings.value('consumer_secret'), \
                token_key=self.settings.value('token_key'), \
                token_secret=self.settings.value('token_secret'), \
                use_for_tweet=self.settings.value('use_for_tweet'), \
                base_url=self.settings.value('base_url')))
        self.settings.endArray()
        self.accounts_model.set(self.accounts)

        #load other prefs
        if self.settings.contains('refresh_interval'):
            self.refresh_value.setValue(int(self.settings.value("refreshInterval")))
        else:
            self.refresh_value.setValue(10)
            
        if self.settings.contains("useDaemon"):
            self.useNotification_value.setCheckState(Qt.CheckState(int(self.settings.value("useNotification"))))
        else:
            self.useNotification_value.setCheckState(Qt.CheckState(2))
            
        if self.settings.contains("useSerialization"):
            self.useSerialization_value.setCheckState(Qt.CheckState(int(self.settings.value("useSerialization"))))
        else:
            self.useSerialization_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains("useBitly"):
            self.useBitly_value.setCheckState(Qt.CheckState(int(self.settings.value("useBitly"))))
        else:
            self.useBitly_value.setCheckState(Qt.CheckState(2))
            
        if not self.settings.contains("theme"):
            if not self.settings.value("theme") in self.THEMES:
                self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
        else:
            self.settings.setValue("theme",KhweeteurPref.DEFAULTTHEME)
                        
        self.theme_value.setCurrentIndex(self.THEMES.index(self.settings.value("theme")))

        if self.settings.contains("tweetHistory"):
            self.history_value.setValue(int(self.settings.value("tweetHistory")))
        else:
            self.history_value.setValue(60)

        if self.settings.contains("useGPS"):
            self.useGPS_value.setCheckState(Qt.CheckState(int(self.settings.value("useGPS"))))
        else:
            self.useGPS_value.setCheckState(Qt.CheckState(2))

    def savePrefs(self):
        ''' Save the prefs from the GUI to QSettings''' 
        self.settings.beginWriteArray("accounts")
        for index,account in enumerate(self.accounts):
            self.settings.setArrayIndex(index)
            self.settings.setValue("name", account.name)
            self.settings.setValue("consumer_key", account.consumer_key)
            self.settings.setValue("consumer_secret", account.consumer_secret )
            self.settings.setValue("token_key", account.token_key )
            self.settings.setValue("token_secret",  account.token_secret )
            self.settings.setValue("use_for_tweet", account.use_for_tweet )
            self.settings.setValue("base_url", account.base_url )
        self.settings.endArray()
        
        self.settings.setValue('refreshInterval', self.refresh_value.value())
        self.settings.setValue('useDaemon', self.useNotification_value.checkState())
        self.settings.setValue('useSerialization', self.useSerialization_value.checkState())
        self.settings.setValue('useBitly', self.useBitly_value.checkState())
        self.settings.setValue('theme', self.theme_value.currentText())
        self.settings.setValue('useGPS', self.useGPS_value.checkState())
        self.settings.setValue('tweetHistory', self.history_value.value())
        self.settings.sync()
        self.save.emit()
        
    def add_account(self):
        self.dlg = AccountDlg()
        self.dlg.add_account.connect(self.do_ask_token)
        self.dlg.show()

    def do_verify_pin(self,pincode):
        token = oauth.Token(self.oauth_webview.request_token['oauth_token'][0], self.oauth_webview.request_token['oauth_token_secret'][0])
        token.set_verifier(unicode(pincode.strip()))

        signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
        oauth_consumer             = oauth.Consumer(key=self.oauth_webview.account_type['consumer_key'], secret=self.oauth_webview.account_type['consumer_secret'])
        oauth_client               = oauth.Client(oauth_consumer)                


        try:
            oauth_client  = oauth.Client(oauth_consumer, token)
            resp, content = oauth_client.request(self.oauth_webview.account_type['access_token_url'], method='POST', body='oauth_verifier=%s' % str(pincode.strip()))
            access_token  = (parse_qs(content))

            print access_token['oauth_token'][0]
            
            if resp['status'] == '200':
                #Create the account
                self.accounts.append(KhweeteurAccount(\
                        name=self.oauth_webview.account_type['name'],\
                        base_url=self.oauth_webview.account_type['base_url'],\
                        consumer_key=self.oauth_webview.account_type['consumer_key'],\
                        consumer_secret=self.oauth_webview.account_type['consumer_secret'],\
                        token_key=access_token['oauth_token'][0],\
                        token_secret=access_token['oauth_token_secret'][0],\
                        use_for_tweet=self.oauth_webview.use_for_tweet,\
                        ))
                self.accounts_model.set(self.accounts)
                self.savePrefs()
            else:
                KhweeteurNotification().warn(self.tr('Invalid respond from %s requesting access token: %s') % (self.oauth_webview.account_type['name'],resp['status']))
        except StandardError, err:
            KhweeteurNotification().warn(self.tr('A error occur while requesting temp token : %s' % (err,)))    
            import traceback
            traceback.print_exc()

        self.oauth_win.close()
        del self.oauth_win
        del self.oauth_webview
        
    def do_ask_token(self, account_type,use_for_tweet):
        print account_type,use_for_tweet

        signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
        oauth_consumer             = oauth.Consumer(key=account_type['consumer_key'], secret=account_type['consumer_secret'])
        oauth_client               = oauth.Client(oauth_consumer)                

        #Crappy hack for fixing oauth_callback not yet supported by the oauth2 lib but requested by identi.ca
        body = 'oauth_callback=oob'

        try:
            resp, content = oauth_client.request(account_type['request_token_url'], 'POST', body=body)
    
            if resp['status'] != '200':            
                KhweeteurNotification().warn(self.tr('Invalid respond from %s requesting temp token: %s') % (account_type['name'],resp['status']))
            else:
                request_token = (parse_qs(content))            
        
            self.oauth_webview=OAuthView(self,account_type,use_for_tweet)
            self.oauth_webview.open((QUrl('%s?oauth_token=%s' % (account_type['authorization_url'], request_token['oauth_token'][0]))))
            self.oauth_webview.request_token = request_token

            self.oauth_webview.show()
            self.oauth_webview.gotpin.connect(self.do_verify_pin)
            self.oauth_win = QMainWindow(self)
            self.oauth_win.setCentralWidget(self.oauth_webview)
            self.oauth_win.setAttribute(Qt.WA_Maemo5AutoOrientation, True)            
            self.oauth_win.setAttribute(Qt.WA_Maemo5StackedWindow, True)
            self.oauth_win.setWindowTitle("Khweeteur OAuth")
            self.oauth_win.show()
            
        except httplib2.ServerNotFoundError,err:
            KhweeteurNotification().warn(self.tr('Server not found : %s :') % unicode(err))
            
    def delete_account(self, index):
        if QMessageBox.question(self,'Delete account', 'Are you sure you want to delete this account ?', QMessageBox.Yes | QMessageBox.Close) ==  QMessageBox.Yes:
            for index in self.accounts_view.selectedIndexes():
                del self.accounts[index.row()]
            self.accounts_model.set(self.accounts)
        
#    def save_account(self, index, name, consumer_key, consumer_secret, token_key, token_secret, use_for_tweet, base_url):
#        self.accounts[index].name = name
#        self.accounts[index].consumer_key = consumer_key
#        self.accounts[index].consumer_secret = consumer_secret
#        self.accounts[index].token_key = token_key
#        self.accounts[index].token_secret = token_secret
#        self.accounts[index].use_for_tweet = use_for_tweet
#        self.accounts[index].base_url = base_url
#        self.accounts_model.set(self.accounts)
#        self.savePrefs()
        
    def closeEvent(self,widget,*args):
        ''' close event called when closing window'''
        self.savePrefs()

    def _setupGUI(self):
        ''' Create the gui content of the window'''
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

        self._main_layout = QVBoxLayout(self.aWidget)
        self._umain_layout = QGridLayout()
        self.aWidget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._umain_layout.addWidget(QLabel(self.tr('Refresh Interval (Minutes) :')),3,0)
        self.refresh_value = QSpinBox()
        self._umain_layout.addWidget(self.refresh_value,3,1)

        self._umain_layout.addWidget(QLabel(self.tr('Number of tweet to keep in the view :')),4,0)
        self.history_value = QSpinBox()
        self._umain_layout.addWidget(self.history_value,4,1)

        self._umain_layout.addWidget(QLabel(self.tr('Theme :')),5,0)

        self.theme_value = QComboBox()
        self._umain_layout.addWidget(self.theme_value,5,1)
        for theme in self.THEMES:
            self.theme_value.addItem(theme)

        self._umain_layout.addWidget(QLabel(self.tr('Other preferences :')),9,0)
        self.useNotification_value = QCheckBox(self.tr('Use Daemon'))
        self._umain_layout.addWidget(self.useNotification_value,10,1)

        self.useSerialization_value = QCheckBox(self.tr('Use Serialization'))
        self._umain_layout.addWidget(self.useSerialization_value,11,1)

        self.useBitly_value = QCheckBox(self.tr('Use Bit.ly'))
        self._umain_layout.addWidget(self.useBitly_value,12,1)

        self.useGPS_value = QCheckBox(self.tr('Use GPS Geopositionning'))
        self._umain_layout.addWidget(self.useGPS_value,13,1)

        self._main_layout.addLayout(self._umain_layout)

        self.accounts_model = AccountsModel()
        self.accounts_view = AccountsView()
        self.accounts_view.clicked.connect(self.delete_account)
        self.accounts_view.setModel(self.accounts_model)
        self.add_acc_button = QPushButton('Add account')
        self.add_acc_button.clicked.connect(self.add_account)
        self._main_layout.addWidget(self.add_acc_button)
        self._main_layout.addWidget(self.accounts_view)

        self.aWidget.setLayout(self._main_layout)
        self.setCentralWidget(self.scrollArea)

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    app.setOrganizationName("Khertan Software")
    app.setOrganizationDomain("khertan.net")
    app.setApplicationName("Khweeteur")
    
    khtsettings = KhweeteurPref()
    khtsettings.show()
    sys.exit(app.exec_())
