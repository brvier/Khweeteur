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
    COOLWHITETHEME, COOLGRAYTHEME, XMASTHEME, \
    MINITHEME

SUPPORTED_ACCOUNTS = [{
    'name': 'Twitter',
    'consumer_key': 'uhgjkoA2lggG4Rh0ggUeQ',
    'consumer_secret': 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU',
    'base_url': 'https://api.twitter.com/1.1',
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

    def __init__(self, **dct):
        # Defaults
        self.name = 'Unknown'
        self.consumer_key = ''
        self.consumer_secret = ''
        self.token_key = ''
        self.token_secret = ''
        self.use_for_tweet = True
        self.base_url = ''

        self.deleted = False

        self.update_from_dict(dct)

    def update_from_dict(self, dct):
        for k, v in dct.items():
            self.__setattr__(k, v)
        self.dirty = False

    def __getitem__(self, key):
        # Turn dictionary accesses into attribute look ups.
        return self.__getattribute__(key)

    # Attributes to not track or save.
    meta_attributes = ('dirty', '_api', '_me_user', 'deleted')

    def __setattr__(self, name, value):
        """Track changes."""
        if name not in self.meta_attributes:
            try:
                old_value = getattr(self, name)
                have_old_value = True
            except AttributeError:
                old_value = None
                have_old_value = False

            if not have_old_value or old_value != value:
                # try:
                #     logging.debug("DIRTY %s(%s) %s: %s->%s",
                #                   self.name, self.uuid, name, old_value, value)
                # except AttributeError:
                #     pass
                self.dirty = True

        return super(Account, self).__setattr__(name, value)

    def items(self):
        return dict([(k, v) for k, v in self.__dict__.items()
                     if k not in self.meta_attributes]).items()

    def __repr__(self):
        return dict([(k,
                      v if k not in ('token_key', 'token_secret')
                      else '*' * len(v))
                     for k, v in self.items()]).__repr__()

    def feeds(self):
        """
        Return the list of feeds associated with an account as a list of
        strings.
        """
        feeds = ['HomeTimeline', 'Mentions', 'DMs', 'RetrieveLists']

        settings = settings_db()

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

    @property
    def api(self):
        """
        An authenticated twitter.Api object.
        """
        try:
            return self._api
        except AttributeError:
            pass

        api = twitter.Api(username=self.consumer_key,
                          password=self.consumer_secret,
                          access_token_key=self.token_key,
                          access_token_secret=self.token_secret,
                          base_url=self.base_url)
        api.SetUserAgent('Khweeteur')
        self._api = api

        try:
            id = api.VerifyCredentials().id
        except Exception, err:
            id = None
            logging.error(
                'Failed to verify the credentials for account %s: %s'
                % (self.name, str(err)))

        self._me_user = id

        return api

    @property
    def me_user(self):
        """The user's identifier."""
        try:
            return self._me_user
        except AttributeError:
            pass

        api = self.api
        return self._me_user

    @property
    def uuid(self):
        try:
            return self.base_url + ';' + self.token_key
        except AttributeError:
            return 'unconfigured'

    def screenname(self):
        """
        Given a Account, refresh the name attribute with the screen
        name.

        Returns True if self.name was updated.
        """
        try:
            creds = self.api.VerifyCredentials()
            account_type = [a['name'] for a in SUPPORTED_ACCOUNTS
                            if a['base_url'] == self.base_url][0]
            name = account_type + ': ' + creds.name
            if name == self.name:
                return False
            self.name = name
            return True
        except Exception:
            logging.exception("Unable to look up account's screen name (%s)",
                              str(self))
            return False

# Cached list of accounts.
_accounts = []
# The last time the accounts were reread from the setting's DB.
_accounts_read_at = None


def accounts(force_sync=False):
    """Returns a list of dictionaries where each dictionary describes
    an account."""
    global _accounts
    global _accounts_read_at

    settings = settings_db()

    if not force_sync and _accounts_read_at == settings_db_generation:
        # logging.debug("accounts(): Using cached version (%d accounts)."
        #               % (len(_accounts),))
        return _accounts
    logging.debug("accounts(force_sync=%s): Reloading accounts.",
                  str(force_sync))

    accounts_dirty = 0

    try:
        nb_accounts = settings.beginReadArray('accounts')
    except Exception:
        logging.exception("Loading accounts")
        nb_accounts = 0

    # The accounts that are in memory, but not on disk.
    not_on_disk_accounts = _accounts
    # The accounts that are in memory and on disk.  We assume that all
    # are only in memory and then check what is on disk.  If an
    # account is on disk, we move it to this list.
    _accounts = []

    for index in range(nb_accounts):
        settings.setArrayIndex(index)
        d = dict((key, settings.value(key)) for key in settings.allKeys())

        for account in not_on_disk_accounts:
            if (account.base_url == d['base_url']
                    and account.token_key == d['token_key']):
                # ACCOUNT is already on disk.

                not_on_disk_accounts.remove(account)

                if account.deleted:
                    # Don't update deleted accounts.
                    accounts_dirty += 1
                    break

                _accounts.append(account)

                if account.dirty:
                    # The account has been changed.  Don't update from
                    # disk.
                    logging.debug("Account %s(%s) is dirty, not reloading",
                                  account.name, account.uuid)
                    accounts_dirty += 1
                else:
                    # logging.debug("Refreshing account: %s", str(account))
                    account.update_from_dict(d)

                break
        else:
            logging.debug("Loading account from disk: %s", d)

            try:
                account = Account(**dict([(str(k), v) for k, v in d.items()]))
                _accounts.append(account)
            except Exception:
                account = "Error"
                logging.exception("Creating new account: %s", d)

    settings.endArray()

    # Conceivably, an account could be created and then deleted before
    # it is written to disk.
    not_on_disk_accounts = [account for account in not_on_disk_accounts
                            if not account.deleted]

    _accounts += not_on_disk_accounts

    _accounts_read_at = settings_db_generation

    if accounts_dirty or not_on_disk_accounts:
        # Save the current account configuration.
        logging.debug("Saving account configuration to backing store.")

        settings.remove('accounts')
        settings.beginWriteArray('accounts')
        for index, account in enumerate(_accounts):
            logging.debug("%d: %s", index, str(account))

            settings.setArrayIndex(index)
            for k, v in account.items():
                settings.setValue(k, v)

            account.dirty = False
        settings.endArray()

    return _accounts


def account_add(account):
    """Add a new account."""
    a = accounts(True)
    a.append(account)
    return accounts(True)


def account_remove(account):
    """Remove an account."""
    account.deleted = True
    return accounts(True)


def account_lookup_by_uuid(uuid):
    """Return the account with specified UUID.  If no such account
    exists, return None."""
    for account in accounts():
        if account.uuid == uuid:
            return account
    return None


class OAuthView(QWebView):

    gotpin = Signal(unicode, tuple)

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
            self.gotpin.emit(self.pin, self.request_token)


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


class KhweeteurPref(QMainWindow):

    save = Signal()

    THEMES = [DEFAULTTHEME, WHITETHEME, COOLWHITETHEME, COOLGRAYTHEME,
              XMASTHEME, MINITHEME]

    def __init__(self, parent=None):
        ''' Init the GUI Win'''

        QMainWindow.__init__(self, parent)
        self.parent = parent

        try:
            self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        except:
            pass
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle('Khweeteur Prefs')

        self._setupGUI()
        self.loadPrefs()

    @property
    def settings(self):
        return settings_db()

    def loadPrefs(self):
        ''' Load and init default prefs to GUI'''

        # load account

        self.accounts_model.set(accounts())

        # load other prefs

        self.refresh_value.valueChanged.connect(self.checkRefreshRate)
        if self.settings.contains('refresh_interval'):
            self.refresh_value.setValue(
                int(self.settings.value('refresh_interval')))
        else:
            self.refresh_value.setValue(10)

        if self.settings.contains('useDaemon'):
            self.useNotification_value.setCheckState(
                Qt.CheckState(int(self.settings.value('useDaemon'))))
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

        if self.settings.contains('showInfos'):
            self.showInfos_value.setCheckState(
                Qt.CheckState(int(self.settings.value('showInfos'))))
        else:
            self.showInfos_value.setCheckState(Qt.CheckState(0))

        if self.settings.contains('showDMNotifications'):
            self.showDMNotifications_value.setCheckState(
                Qt.CheckState(int(self.settings.value('showDMNotifications'))))
        else:
            self.showDMNotifications_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('showMentionNotifications'):
            self.showMentionNotifications_value.setCheckState(
                Qt.CheckState(int(self.settings.value('showMentionNotifications'))))
        else:
            self.showMentionNotifications_value.setCheckState(Qt.CheckState(2))

        if self.settings.contains('showHomeTimelineNotifications'):
            self.showHomeTimelineNotifications_value.setCheckState(
                Qt.CheckState(int(self.settings.value('showHomeTimelineNotifications'))))
        else:
            self.showHomeTimelineNotifications_value.setCheckState(
                Qt.CheckState(2))

    def checkRefreshRate(self):
        if self.refresh_value.value() < 10:
            self.refresh_warning.show()
        else:
            self.refresh_warning.hide()

    def savePrefs(self):
        ''' Save the prefs from the GUI to QSettings'''

        self.settings.setValue('refresh_interval', self.refresh_value.value())
        self.settings.setValue('useDaemon',
                               self.useNotification_value.checkState())
        self.settings.setValue('useSerialization',
                               self.useSerialization_value.checkState())
        self.settings.setValue('useBitly', self.useBitly_value.checkState())
        self.settings.setValue('theme', self.theme_value.currentText())
        self.settings.setValue('showInfos', self.showInfos_value.checkState())
        self.settings.setValue(
            'showDMNotifications', self.showDMNotifications_value.checkState())
        self.settings.setValue(
            'showMentionNotifications', self.showMentionNotifications_value.checkState())
        self.settings.setValue('showHomeTimelineNotifications',
                               self.showHomeTimelineNotifications_value.checkState())
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
                account = Account(
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
                account.screenname()
                self.accounts_model.set(account_add(account))
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

        # Crappy hack for fixing oauth_callback not yet supported by the oauth2
        # lib but requested by identi.ca

        body = 'oauth_callback=oob'

        try:
            (resp, content) = \
                oauth_client.request(account_type['request_token_url'], 'POST',
                                     body=body)

            if resp['status'] != '200':
                KhweeteurNotification().warn(self.tr('Unable to add account: Unexpected HTTP response from %s requesting oauth token: %s'
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
        account = account_lookup_by_uuid(
            self.accounts_model._items[index.row()].uuid)

        if QMessageBox.question(
            self, 'Delete %s' % (account.name or 'account'),
            'Are you sure you want to delete this account ?'                                , QMessageBox.Yes | QMessageBox.Close) \
                == QMessageBox.Yes:
            self.accounts_model.set(account_remove(account))

    def closeEvent(self, widget, *args):
        ''' close event called when closing window'''

        self.savePrefs()

        # Restart the daemon on prefs changes instead of loading data at every
        # loop of daemon.

        from subprocess import Popen
        Popen(['/usr/bin/python', os.path.join(os.path.dirname(__file__),
              'daemon.py'), 'restart'])

    def _setupGUI(self):
        ''' Create the gui content of the window'''

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.aWidget = QWidget(self.scrollArea)
        self.aWidget.setMinimumSize(480, 1200)
        self.aWidget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        self.aWidget.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._umain_layout.addWidget(QLabel(self.tr('Refresh Interval (Minutes) :'
                                                    )), 3, 0)
        self.refresh_value = QSpinBox()
        self._umain_layout.addWidget(self.refresh_value, 3, 1)
        self.refresh_warning = QLabel(
            '<font color=\'red\'>Setting low refresh rate can exceed<br>twitter limit rate</font>')

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

        self.showInfos_value = QCheckBox(self.tr('Show errors notifications'))
        self._umain_layout.addWidget(self.showInfos_value, 16, 1)

        self.showDMNotifications_value = QCheckBox(self.tr('DM Notifications'))
        self._umain_layout.addWidget(self.showDMNotifications_value, 17, 1)

        self.showMentionNotifications_value = QCheckBox(
            self.tr('Mention Notifications'))
        self._umain_layout.addWidget(
            self.showMentionNotifications_value, 18, 1)

        self.showHomeTimelineNotifications_value = QCheckBox(
            self.tr('Timeline Notifications'))
        self._umain_layout.addWidget(
            self.showHomeTimelineNotifications_value, 19, 1)

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
    print "Accounts:"
    for i, account in enumerate(accounts()):
        print "  %d: %s" % (i, str(account))

    print
    print"Settings:"
    settings = settings_db()
    for k in sorted(settings.allKeys()):
        print "  %s: %s" % (k, settings.value(k))

    import sys
    app = QApplication(sys.argv)
    app.setOrganizationName('Khertan Software')
    app.setOrganizationDomain('khertan.net')
    app.setApplicationName('Khweeteur')

    khtsettings = KhweeteurPref()
    khtsettings.show()
    sys.exit(app.exec_())
