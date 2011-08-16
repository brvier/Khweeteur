#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4'''

import httplib2
import os
import time
import logging

from PySide.QtGui import QMainWindow, QSizePolicy, QSpinBox, QVBoxLayout, \
    QAbstractItemView, QScrollArea, QListView, QComboBox, QCheckBox, QDialog, \
    QGridLayout, QWidget, QLabel, QPushButton, QApplication, QMessageBox

from PySide.QtCore import Qt, QUrl, QAbstractListModel, QSettings, QModelIndex, \
    Signal

from theme import DEFAULTTHEME, WHITETHEME, \
                     COOLWHITETHEME, COOLGRAYTHEME, \
                     MINITHEME

SUPPORTED_ACCOUNTS = [{
    'name': 'Twitter',
    'consumer_key': 'uhgjkoA2lggG4Rh0ggUeQ',
    'consumer_secret': 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU',
    'base_url': 'https://api.twitter.com/1',
    'request_token_url': 'https://api.twitter.com/oauth/request_token',
    'access_token_url': 'https://api.twitter.com/oauth/access_token',
    'authorization_url': 'https://api.twitter.com/oauth/authorize',
    }, {
    'name': 'Identi.ca',
    'consumer_key': 'c7e86efd4cb951871200440ad1774413',
    'consumer_secret': '236fa46bf3f65fabdb1fd34d63c26d28',
    'base_url': 'http://identi.ca/api',
    'request_token_url': 'http://identi.ca/api/oauth/request_token',
    'access_token_url': 'http://identi.ca/api/oauth/access_token',
    'authorization_url': 'http://identi.ca/api/oauth/authorize',
    }]

import oauth2 as oauth
from notifications import KhweeteurNotification

try:
    from urlparse import parse_qs
except:
    from cgi import parse_qs

from PySide.QtWebKit import QWebView

import twitter

_settings = None
_settings_synced = None
# Each time the DB changes, this is incremented.  Our current
# implementation just rereads the DB periodically.  A better approach
# would be to use the last modification time of the underlying file
# (determined using QSettings.fileName).
settings_db_generation = 0
def settings_db():
    """
    Return the setting's database, a QSettings instance, ensuring that
    it is sufficiently up to date.
    """
    global _settings
    global _settings_synced
    global settings_db_generation

    if _settings is None:
        # First time through.
        _settings = QSettings('Khertan Software', 'Khweeteur')
        _settings_synced = time.time()
        return _settings

    # Ensure that the in-memory settings database is synchronized
    # with the values on disk.
    now = time.time()
    if now - _settings_synced > 10:
        # Last synchronized more than 10 seconds ago.
        _settings.sync()
        _settings_synced = now
        settings_db_generation += 1

    return _settings

class Account(object):
    def __init__(self, dct):
        self.update_from_dict(dct)

    def update_from_dict(self, dct):
        for k, v in dct.items():
            self.__setattr__(k, v)

    def __getitem__(self, key):
        # Turn dictionary accesses into attribute look ups.
        return self.__getattribute__(key)

    def __repr__(self):
        return dict([(k, v) for k, v in self.__dict__.items()]).__repr__()

    def feeds(self):
        """
        Return the list of feeds associated with an account as a list of
        strings.
        """
        feeds = ['HomeTimeline', 'Mentions', 'DMs', 'RetrieveLists']
    
        settings = settings_db()
        if settings.value('useGPS') == '2':
            feeds.append['Near']
    
        nb_searches = settings.beginReadArray('searches')
        for index in range(nb_searches):
            settings.setArrayIndex(index)
            feeds.append('Search:' + settings.value('terms'))
        settings.endArray()
    
        nb_lists = settings.beginReadArray('lists')
        for index in range(nb_lists):
            settings.setArrayIndex(index)
            feeds.append(
                'List:' + settings.value('user') + ':' + settings.value('id'))
        settings.endArray()
    
        return feeds

# Cached list of accounts.
_accounts = []
# The last time the accounts were reread from the setting's DB.
_accounts_read_at = None
def accounts():
    """Returns a list of dictionaries where each dictionary describes
    an account."""
    global _accounts
    global _accounts_read_at

    settings = settings_db()

    if _accounts_read_at == settings_db_generation:
        # logging.debug("accounts(): Using cached version (%d accounts)."
        #               % (len(_accounts),))
        return _accounts
    logging.debug("accounts(): Reloading accounts from settings file.")

    nb_accounts = settings.beginReadArray('accounts')
    accounts = []
    for index in range(nb_accounts):
        settings.setArrayIndex(index)

        d = dict((key, settings.value(key)) for key in settings.allKeys())
        for account in _accounts:
            if (account.base_url == d['base_url']
                and account.token_key == d['token_key']):
                account.update_from_dict(d)
                break
        else:
            account = Account(d)

        accounts.append(account)

        logging.debug("accounts(): Account %d: %s"
                      % (index + 1, repr(account)))

    settings.endArray()
    logging.debug("accounts(): Loaded %d accounts" % (len(accounts),))

    _accounts = accounts
    _accounts_read_at = settings_db_generation

    return accounts

def screenname(account):
    """
    Given a KhweeteurAccount, refresh the name attribute with the
    screen name.

    Returns True if account.name was updated.
    """
    api = twitter.Api(username=account.consumer_key,
                      password=account.consumer_secret,
                      access_token_key=account.token_key,
                      access_token_secret=account.token_secret,
                      base_url=account.base_url)
    creds = api.VerifyCredentials()
    account_type = [a['name'] for a in SUPPORTED_ACCOUNTS
                    if a['base_url'] == account.base_url][0]
    name = account_type + ': ' + creds.name
    if name == account.name:
        return False
    account.name = name
    return True

class OAuthView(QWebView):

    gotpin = Signal(unicode,tuple)

    def __init__(
        self,
        parent=None,
        account_type={},
        use_for_tweet=False,
        ):
        QWebView.__init__(self, parent)
        self.loggedIn = False
        self.account_type = account_type
        self.use_for_tweet = use_for_tweet
        self.pin = None
        self.request_token = None

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
        import re

        regex = re.compile('.*<div.*oauth_pin.*>(.*)<')
        res = regex.findall(self.page().mainFrame().toHtml())
        if len(res) > 0:
            self.pin = res[0]
        else:
            regex = re.compile('.*<code>(.*)</code>')
            res = regex.findall(self.page().mainFrame().toHtml())
            if len(res) > 0:
                self.pin = res[0]

        self.loggedIn = self.pin not in (None, '')

        if self.loggedIn:
            self.loadFinished.disconnect(self._loadFinished)
            self.gotpin.emit(self.pin,self.request_token)


class AccountDlg(QDialog):

    """ Find and replace dialog """

    add_account = Signal(dict, bool)

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle('Add account')

        self.accounts_type = QComboBox()
        for account_type in SUPPORTED_ACCOUNTS:
            self.accounts_type.addItem(account_type['name'])

        self.use_for_tweet = QCheckBox('Use for posting')
        self.use_for_tweet.setCheckState(Qt.CheckState(2))
        self.add = QPushButton('&Add')

        gridLayout = QGridLayout()
        gridLayout.addWidget(self.accounts_type, 0, 0)
        gridLayout.addWidget(self.use_for_tweet, 0, 1)
        gridLayout.addWidget(self.add, 1, 2)
        self.setLayout(gridLayout)
        self.add.clicked.connect(self.addit)

    def addit(self):
        index = self.accounts_type.currentIndex()
        self.add_account.emit(SUPPORTED_ACCOUNTS[index],
                              self.use_for_tweet.isChecked())
        self.hide()


class AccountsModel(QAbstractListModel):

    dataChanged = Signal(QModelIndex, QModelIndex)

    def __init__(self):
        QAbstractListModel.__init__(self)
        self._items = []

    def set(self, mlist):
        self._items = mlist
        self.dataChanged.emit(self.createIndex(0, 0), self.createIndex(0,
                              len(self._items)))

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            try:
                return self._items[index.row()].name
            except IndexError:
                return None
        else:
            return None


class AccountsView(QListView):

    def __init__(self, parent=None):
        QListView.__init__(self, parent)
        self.setEditTriggers(QAbstractItemView.SelectedClicked)


class KhweeteurAccount:

    def __init__(
        self,
        name='Unknow',
        consumer_key='',
        consumer_secret='',
        token_key='',
        token_secret='',
        use_for_tweet=True,
        base_url='',
        ):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.token_key = token_key
        self.token_secret = token_secret
        self.use_for_tweet = use_for_tweet
        self.base_url = base_url
        self.name = name


class KhweeteurPref(QMainWindow):

    save = Signal()

    THEMES = [DEFAULTTHEME, WHITETHEME, COOLWHITETHEME, COOLGRAYTHEME,
              MINITHEME]

    def __init__(self, parent=None):
        ''' Init the GUI Win'''

        QMainWindow.__init__(self, parent)
        self.parent = parent

        self.settings = QSettings()

        try:
            self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        except:
            pass
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle('Khweeteur Prefs')

        self._setupGUI()
        self.loadPrefs()

    def loadPrefs(self):
        ''' Load and init default prefs to GUI'''

        # load account

        self.accounts = []
        nb_accounts = self.settings.beginReadArray('accounts')
        have_update = False
        for index in range(nb_accounts):
            self.settings.setArrayIndex(index)
            account = KhweeteurAccount(
                name=self.settings.value('name'),
                consumer_key=self.settings.value('consumer_key'),
                consumer_secret=self.settings.value('consumer_secret'),
                token_key=self.settings.value('token_key'),
                token_secret=self.settings.value('token_secret'),
                use_for_tweet=self.settings.value('use_for_tweet'),
                base_url=self.settings.value('base_url'),
                )
            if screenname(account):
                have_update = True
            self.accounts.append(account)
        self.settings.endArray()
        self.accounts_model.set(self.accounts)

        # load other prefs

        self.refresh_value.valueChanged.connect(self.checkRefreshRate)
        if self.settings.contains('refresh_interval'):
            self.refresh_value.setValue(int(self.settings.value('refresh_interval')))
        else:
            self.refresh_value.setValue(10)

        if self.settings.contains('useDaemon'):
            self.useNotification_value.setCheckState(Qt.CheckState(int(self.settings.value('useDaemon'))))
        else:
            self.useNotification_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('useSerialization'):
            self.useSerialization_value.setCheckState(Qt.CheckState(int(self.settings.value('useSerialization'
                    ))))
        else:
            self.useSerialization_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('useBitly'):
            self.useBitly_value.setCheckState(Qt.CheckState(int(self.settings.value('useBitly'
                    ))))
        else:
            self.useBitly_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('theme'):
            if not self.settings.value('theme') in self.THEMES:
                self.settings.setValue('theme', DEFAULTTHEME)
        else:
            self.settings.setValue('theme', DEFAULTTHEME)

        self.theme_value.setCurrentIndex(self.THEMES.index(self.settings.value('theme'
                )))

        if self.settings.contains('tweetHistory'):
            self.history_value.setValue(int(self.settings.value('tweetHistory'
                                        )))
        else:
            self.history_value.setValue(60)

        self.useGPS_value.stateChanged.connect(self.checkGPS)
        if self.settings.contains('useGPS'):
            self.useGPS_value.setCheckState(Qt.CheckState(int(self.settings.value('useGPS'))))
        else:
            self.useGPS_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('useGPSOnDemand'):
            self.useGPSOnDemand_value.setCheckState(Qt.CheckState(int(self.settings.value('useGPSOnDemand'))))
        else:
            self.useGPSOnDemand_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('showInfos'):
            self.showInfos_value.setCheckState(Qt.CheckState(int(self.settings.value('showInfos'))))
        else:
            self.showInfos_value.setCheckState(Qt.CheckState(0))

        if self.settings.contains('showDMNotifications'):
            self.showDMNotifications_value.setCheckState(Qt.CheckState(int(self.settings.value('showDMNotifications'))))
        else:
            self.showDMNotifications_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('showMentionNotifications'):
            self.showMentionNotifications_value.setCheckState(Qt.CheckState(int(self.settings.value('showMentionNotifications'))))
        else:
            self.showMentionNotifications_value.setCheckState(Qt.CheckState(2))

        if have_update:
            self.savePrefs()

    def checkRefreshRate(self):
        if self.refresh_value.value() < 10:
            self.refresh_warning.show()
        else:
            self.refresh_warning.hide()

    def checkGPS(self):
        if self.useGPS_value.checkState() == Qt.CheckState(2):
            self.usegps_warning.show()
        else:
            self.usegps_warning.hide()

    def savePrefs(self):
        ''' Save the prefs from the GUI to QSettings'''

        self.settings.beginWriteArray('accounts')
        for (index, account) in enumerate(self.accounts):
            self.settings.setArrayIndex(index)
            self.settings.setValue('name', account.name)
            self.settings.setValue('consumer_key', account.consumer_key)
            self.settings.setValue('consumer_secret', account.consumer_secret)
            self.settings.setValue('token_key', account.token_key)
            self.settings.setValue('token_secret', account.token_secret)
            self.settings.setValue('use_for_tweet', account.use_for_tweet)
            self.settings.setValue('base_url', account.base_url)
        self.settings.endArray()

        self.settings.setValue('refresh_interval', self.refresh_value.value())
        self.settings.setValue('useDaemon',
                               self.useNotification_value.checkState())
        self.settings.setValue('useSerialization',
                               self.useSerialization_value.checkState())
        self.settings.setValue('useBitly', self.useBitly_value.checkState())
        self.settings.setValue('theme', self.theme_value.currentText())
        self.settings.setValue('useGPS', self.useGPS_value.checkState())
        self.settings.setValue('useGPSOnDemand', self.useGPSOnDemand_value.checkState())
        self.settings.setValue('showInfos', self.showInfos_value.checkState())
        self.settings.setValue('showDMNotifications', self.showDMNotifications_value.checkState())
        self.settings.setValue('showMentionNotifications', self.showMentionNotifications_value.checkState())
        self.settings.setValue('tweetHistory', self.history_value.value())
        self.settings.sync()
        self.save.emit()

    def add_account(self):
        self.dlg = AccountDlg()
        self.dlg.add_account.connect(self.do_ask_token)
        self.dlg.show()

    def do_verify_pin(self, pincode):
        token = oauth.Token(self.oauth_webview.request_token['oauth_token'][0],
                            self.oauth_webview.request_token['oauth_token_secret'
                            ][0])
        token.set_verifier(unicode(pincode.strip()))

        oauth_consumer = \
            oauth.Consumer(key=self.oauth_webview.account_type['consumer_key'],
                           secret=self.oauth_webview.account_type['consumer_secret'
                           ])
        oauth_client = oauth.Client(oauth_consumer)

        try:
            oauth_client = oauth.Client(oauth_consumer, token)
            (resp, content) = \
                oauth_client.request(self.oauth_webview.account_type['access_token_url'
                                     ], method='POST', body='oauth_verifier=%s'
                                     % str(pincode.strip()))
            access_token = parse_qs(content)

            print access_token['oauth_token'][0]

            if resp['status'] == '200':

                # Create the account
                account = KhweeteurAccount(
                    name=self.oauth_webview.account_type['name'],
                    base_url=self.oauth_webview.account_type['base_url'],
                    consumer_key=self.oauth_webview.account_type['consumer_key'
                            ],
                    consumer_secret=self.oauth_webview.account_type['consumer_secret'
                            ],
                    token_key=access_token['oauth_token'][0],
                    token_secret=access_token['oauth_token_secret'][0],
                    use_for_tweet=self.oauth_webview.use_for_tweet,
                    )
                screenname(account)
                self.accounts.append(account)
                self.accounts_model.set(self.accounts)
                self.savePrefs()
            else:
                KhweeteurNotification().warn(self.tr('Invalid respond from %s requesting access token: %s'
                        ) % (self.oauth_webview.account_type['name'],
                        resp['status']))
        except StandardError, err:
            KhweeteurNotification().warn(self.tr('A error occur while requesting temp token : %s'
                     % (err, )))
            import traceback
            traceback.print_exc()

        self.oauth_win.close()
        del self.oauth_win
        del self.oauth_webview

    def do_ask_token(self, account_type, use_for_tweet):
        print ("Ask for token for: %s (use for tweet: %s)"
               % (account_type, str(use_for_tweet)))

        oauth_consumer = oauth.Consumer(key=account_type['consumer_key'],
                                        secret=account_type['consumer_secret'])
        oauth_client = oauth.Client(oauth_consumer)

        # Crappy hack for fixing oauth_callback not yet supported by the oauth2 lib but requested by identi.ca

        body = 'oauth_callback=oob'

        try:
            (resp, content) = \
                oauth_client.request(account_type['request_token_url'], 'POST',
                                     body=body)

            if resp['status'] != '200':
                KhweeteurNotification().warn(self.tr('Invalid respond from %s requesting temp token: %s'
                        ) % (account_type['name'], resp['status']))
                return
            else:
                request_token = parse_qs(content)

            self.oauth_webview = OAuthView(self, account_type, use_for_tweet)
            self.oauth_webview.open(QUrl('%s?oauth_token=%s'
                                    % (account_type['authorization_url'],
                                    request_token['oauth_token'][0])))
            self.oauth_webview.request_token = request_token

            self.oauth_webview.show()
            self.oauth_webview.gotpin.connect(self.do_verify_pin)
            self.oauth_win = QMainWindow(self)
            self.oauth_win.setCentralWidget(self.oauth_webview)
            try:
                self.oauth_win.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
                self.oauth_win.setAttribute(Qt.WA_Maemo5StackedWindow, True)
            except:
                pass
            self.oauth_win.setWindowTitle('Khweeteur OAuth')
            self.oauth_win.show()
        except httplib2.ServerNotFoundError, err:

            KhweeteurNotification().warn(self.tr('Server not found : %s :')
                    % unicode(err))

    def delete_account(self, index):
        if QMessageBox.question(self, 'Delete account',
                                'Are you sure you want to delete this account ?'
                                , QMessageBox.Yes | QMessageBox.Close) \
            == QMessageBox.Yes:
            for index in self.accounts_view.selectedIndexes():
                del self.accounts[index.row()]
            self.accounts_model.set(self.accounts)

    def closeEvent(self, widget, *args):
        ''' close event called when closing window'''

        self.savePrefs()

        # Restart the daemon on prefs changes instead of loading data at every loop of daemon.

        from subprocess import Popen
        Popen(['/usr/bin/python', os.path.join(os.path.dirname(__file__),
              'daemon.py'), 'restart'])

    def _setupGUI(self):
        ''' Create the gui content of the window'''

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.aWidget = QWidget(self.scrollArea)
        self.aWidget.setMinimumSize(480, 1200)
        self.aWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scrollArea.setSizePolicy(QSizePolicy.Expanding,
                                      QSizePolicy.Expanding)
        self.scrollArea.setWidget(self.aWidget)

        # Available on maemo but should be too on Meego

        try:
            scroller = self.scrollArea.property('kineticScroller')
            scroller.setEnabled(True)
        except:
            pass

        self._main_layout = QVBoxLayout(self.aWidget)
        self._umain_layout = QGridLayout()
        self.aWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._umain_layout.addWidget(QLabel(self.tr('Refresh Interval (Minutes) :'
                                     )), 3, 0)
        self.refresh_value = QSpinBox()
        self._umain_layout.addWidget(self.refresh_value, 3, 1)
        self.refresh_warning = QLabel('<font color=\'red\'>Setting low refresh rate can exceed<br>twitter limit rate</font>')

        self._umain_layout.addWidget(self.refresh_warning, 4, 1)

        self._umain_layout.addWidget(QLabel(self.tr('Number of tweet to keep in the view :'
                                     )), 5, 0)
        self.history_value = QSpinBox()
        self._umain_layout.addWidget(self.history_value, 5, 1)

        self._umain_layout.addWidget(QLabel(self.tr('Theme :')), 6, 0)

        self.theme_value = QComboBox()
        self._umain_layout.addWidget(self.theme_value, 6, 1)
        for theme in self.THEMES:
            self.theme_value.addItem(theme)

        self._umain_layout.addWidget(QLabel(self.tr('Other preferences :')), 9,
                                     0)
        self.useNotification_value = QCheckBox(self.tr('Use Daemon'))
        self._umain_layout.addWidget(self.useNotification_value, 10, 1)

        self.useSerialization_value = QCheckBox(self.tr('Use Serialization'))
        self._umain_layout.addWidget(self.useSerialization_value, 11, 1)

        self.useBitly_value = QCheckBox(self.tr('Use Bit.ly'))
        self._umain_layout.addWidget(self.useBitly_value, 12, 1)

        self.useGPS_value = QCheckBox(self.tr('Use GPS Geopositionning'))
        self._umain_layout.addWidget(self.useGPS_value, 13, 1)

        self.useGPSOnDemand_value = QCheckBox(self.tr('Use GPS On Demand'))
        self._umain_layout.addWidget(self.useGPSOnDemand_value, 15, 1)
        self.usegps_warning = QLabel('<font color=\'red\'>Use gps delay status posting<br>until a gps fix is caught</font>')
        self._umain_layout.addWidget(self.usegps_warning, 14, 1)
        self.checkGPS()

        self.showInfos_value = QCheckBox(self.tr('Show errors notifications'))
        self._umain_layout.addWidget(self.showInfos_value, 16, 1)

        self.showDMNotifications_value = QCheckBox(self.tr('Use DMs notifications'))
        self._umain_layout.addWidget(self.showDMNotifications_value, 17, 1)

        self.showMentionNotifications_value = QCheckBox(self.tr('Use Mentions notifications'))
        self._umain_layout.addWidget(self.showMentionNotifications_value, 18, 1)

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
    app.setOrganizationName('Khertan Software')
    app.setOrganizationDomain('khertan.net')
    app.setApplicationName('Khweeteur')

    khtsettings = KhweeteurPref()
    khtsettings.show()
    sys.exit(app.exec_())
