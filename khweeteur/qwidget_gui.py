#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with Python and Qt'''

from __future__ import with_statement

__version__ = '0.5.14'

# import sip
# sip.setapi('QString', 2)
# sip.setapi('QVariant', 2)

from PySide.QtGui import QMainWindow, QHBoxLayout, QSizePolicy, QToolButton, \
    QVBoxLayout, QFileDialog, QDesktopServices, QScrollArea, QPushButton, \
    QToolBar, QLabel, QWidget, QInputDialog, QMenu, QAction, QApplication, \
    QIcon, QMessageBox, QPlainTextEdit
from PySide.QtCore import Qt, QUrl, QSettings, Slot, Signal, QTimer
from PySide.QtMaemo5 import *
from qbadgebutton import QToolBadgeButton

import dbus
import dbus.service
import os
import sys
import pickle
import time
from list_view import KhweetsView
from list_model import KhweetsModel, ISMEROLE, IDROLE, ORIGINROLE, SCREENNAMEROLE, PROTECTEDROLE, USERIDROLE
from settings import KhweeteurPref
from dbusobj import KhweeteurDBus
import re

try:
    from QtMobility.Location import QGeoPositionInfoSource
except:
    print 'Pysode QtMobility not installed or broken'
    
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
        self.parent.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)

    def post_tweet(
        self,
        shorten_url=1,
        serialize=1,
        text='',
        lattitude='0',
        longitude='0',
        base_url='',
        action='',
        tweet_id='0',
        ):

        if not os.path.exists(self.post_path):
            os.makedirs(self.post_path)
        with open(os.path.join(self.post_path, str(time.time())), 'wb') as \
            fhandle:
            post = {
                'shorten_url': shorten_url,
                'serialize': serialize,
                'text': text,
                'lattitude': lattitude,
                'longitude': longitude,
                'base_url': base_url,
                'action': action,
                'tweet_id': tweet_id,
                }
            pickle.dump(post, fhandle, pickle.HIGHEST_PROTOCOL)


class KhweeteurAbout(QMainWindow):

    '''About Window'''

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.parent = parent

        self.settings = QSettings()

        try:  # Preferences not set yet
            if int(self.settings.value('useAutoRotation')) == 2:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        except:
            self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)

        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle(self.tr('Khweeteur About'))

        try:
            aboutScrollArea = QScrollArea(self)
            aboutScrollArea.setWidgetResizable(True)
            awidget = QWidget(aboutScrollArea)
            awidget.setMinimumSize(480, 1400)
            awidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            aboutScrollArea.setSizePolicy(QSizePolicy.Expanding,
                    QSizePolicy.Expanding)

        # Kinetic scroller is available on Maemo and should be on meego

            try:
                scroller = aboutScrollArea.property('kineticScroller')
                scroller.setEnabled(True)
            except:
                pass

            aboutLayout = QVBoxLayout(awidget)
        except:
            awidget = QWidget(self)
            aboutLayout = QVBoxLayout(awidget)

        aboutIcon = QLabel()
        try:
            aboutIcon.setPixmap(QIcon.fromTheme('khweeteur').pixmap(128, 128))
        except:
            aboutIcon.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'icons', 'khweeteur.png')).pixmap(128, 128))

        aboutIcon.setAlignment(Qt.AlignCenter or Qt.AlignHCenter)
        aboutIcon.resize(128, 128)
        aboutLayout.addWidget(aboutIcon)

        aboutLabel = \
            QLabel(self.tr('''<center><b>Khweeteur</b> %s
                                   <br><br>An easy to use twitter client
                                   <br><br>Licenced under GPLv3
                                   <br>By Beno&icirc;t HERVIER (Khertan)
                                   <br><br><b>Try to be simple and fast
                                   <br>identi.ca and twitter client</b></center>
                                   <br><br><b>Features</b>
                                   <br>* Support multiple account
                                   <br>* Notify DMs and Mentions In Background
                                   <br>* Reply, Retweet,
                                   <br>* Follow/Unfollow user,
                                   <br>* Favorite, Delete your tweet
                                   <br>* Disconnected mode
                                   <br>  Action will be done
                                   <br>  when you recover network
                                   <br>* Twitpic upload
                                   <br>* Automated OAuth authentification
                                   <br><br><b>Shortcuts :</b>
                                   <br>* Control-R : Refresh current view
                                   <br>* Control-M : Reply to selected tweet
                                   <br>* Control-Up : To scroll to top
                                   <br>* Control-Bottom : To scroll to bottom
                                   <br>* Control-Left : Zoom out
                                   <br>* Control-Right : Zoom in
                                   <br>* Control-C : Copy text of the selected tweet
                                   <br><br><b>Thanks to :</b>
                                   <br>ddoodie on #pyqt
                                   <br>xnt14 on #maemo
                                   <br>trebormints on twitter
                                   <br>moubaildotcom on twitter
                                   <br>teotwaki on twitter
                                   <br>Jaffa on maemo.org
                                   <br>creip on Twitter
                                   <br>zcopley on #statusnet
                                   <br>jordan_c on #statusnet
                                   <br>ZogG on twitter
                                   ''')
                   % __version__)
        aboutLayout.addWidget(aboutLabel)
        self.bugtracker_button = QPushButton(self.tr('BugTracker'))
        self.bugtracker_button.clicked.connect(self.open_bugtracker)
        self.website_button = QPushButton(self.tr('Website'))
        self.website_button.clicked.connect(self.open_website)
        awidget2 = QWidget()
        buttonLayout = QHBoxLayout(awidget2)
        buttonLayout.addWidget(self.bugtracker_button)
        buttonLayout.addWidget(self.website_button)
        aboutLayout.addWidget(awidget2)

        try:
            awidget.setLayout(aboutLayout)
            aboutScrollArea.setWidget(awidget)
            self.setCentralWidget(aboutScrollArea)
        except:
            self.setCentralWidget(awidget)

        self.show()

    def open_website(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur'))

    def open_bugtracker(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur/bugs'))


class Khweeteur(QApplication):

    def __init__(self):
        QApplication.__init__(self, sys.argv)
        self.setOrganizationName('Khertan Software')
        self.setOrganizationDomain('khertan.net')
        self.setApplicationName('Khweeteur')
        self.run()

    def check_crash_report(self):
        if os.path.isfile(os.path.join(os.path.join(os.path.expanduser("~"),'.khweeteur_crash_report'))):
            import urllib2
            import urllib
            import pickle
            if (( QMessageBox.question(None,
                "Kheeteur Crash Report",
                "An error occur on Khweeteur in the previous launch. Report this bug on the bug tracker ?",
                QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
                url = 'http://khertan.net/report.php' # write ur URL here
                try:
                    filename = os.path.join(os.path.join(os.path.expanduser("~"),'.khweeteur_crash_report'))
                    output = open(filename, 'rb')
                    error = pickle.load(output)
                    output.close()

                    values = {
                          'project' : 'khweeteur',
                          'version': __version__,
                          'description':error,
                      }

                    data = urllib.urlencode(values)
                    req = urllib2.Request(url, data)
                    response = urllib2.urlopen(req)
                    the_page = response.read()
                except Exception, detail:
                    print detail
                    QMessageBox.question(None,
                    "Khweeteur Crash Report",
                    "An error occur during the report : %s" % detail,
                    QMessageBox.Close)
                    return False

                if 'Your report have been successfully stored' in the_page:
                    QMessageBox.question(None,
                    "Khweeteur Crash Report",
                    "%s" % the_page,
                    QMessageBox.Close)
                    return True
                else:
                    print 'page:',the_page
                    QMessageBox.question(None,
                    "KhtEditor Crash Report",
                    "%s" % the_page,
                    QMessageBox.Close)
                    return False
            try:
                os.remove(os.path.join(os.path.join(os.path.expanduser("~"),'.khweeteur_crash_report')))
            except:
                pass

    def run(self):
        self.check_crash_report()
        self.win = KhweeteurWin()
        self.win.show()


class KhweeteurWin(QMainWindow):

    activated_by_dbus = Signal()

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)

        self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle('Khweeteur')

        self.listen_dbus()

        settings = QSettings()

        self.view = KhweetsView()
        self.model = KhweetsModel()
        try:
            self.model.setLimit(int(settings.value('tweetHistory')))
        except:
            self.model.setLimit(60)
        self.view.setModel(self.model)
        self.view.clicked.connect(self.switch_tb_action)

        self.dbus_handler.require_update()

        self.toolbar = QToolBar('Toolbar')
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar)

        self.toolbar_mode = 0  # 0 - Default , 1 - Edit, 2 - Action

        self.list_tb_action = []
        self.edit_tb_action = []
        self.action_tb_action = []

        # Switch to edit mode (default)

        self.tb_new = QAction(QIcon.fromTheme('khweeteur'), 'New', self)
        self.tb_new.triggered.connect(self.switch_tb_edit)
        self.toolbar.addAction(self.tb_new)
        self.list_tb_action.append(self.tb_new)

        # Back button (Edit + Action)

        self.tb_back = QAction(QIcon.fromTheme('general_back'), 'Back', self)
        self.tb_back.triggered.connect(self.switch_tb_default)
        self.toolbar.addAction(self.tb_back)
        self.edit_tb_action.append(self.tb_back)
        self.action_tb_action.append(self.tb_back)

        self.setupMenu()

        # Twitpic button

        self.tb_twitpic = QAction(QIcon.fromTheme('tasklaunch_images'),
                                  'Twitpic', self)
        self.tb_twitpic.triggered.connect(self.do_tb_twitpic)
        self.toolbar.addAction(self.tb_twitpic)
        self.edit_tb_action.append(self.tb_twitpic)

        # Text field (edit)

        self.tb_text = QPlainTextEdit()
        self.tb_text_reply_id = 0
        self.tb_text_reply_base_url = ''
        self.tb_text.setFixedHeight(66)
        self.edit_tb_action.append(self.toolbar.addWidget(self.tb_text))

        # Char count (Edit)

        self.tb_charCounter = QLabel('140')
        self.edit_tb_action.append(self.toolbar.addWidget(self.tb_charCounter))
        self.tb_text.textChanged.connect(self.countCharsAndResize)

        # Send tweet (Edit)

        self.tb_send = QAction(QIcon.fromTheme('khweeteur'), 'Tweet', self)
        self.tb_send.triggered.connect(self.do_tb_send)
        self.tb_send.setVisible(False)
        self.toolbar.addAction(self.tb_send)
        self.edit_tb_action.append(self.tb_send)

        # Refresh (Default)

        self.tb_update = QAction(QIcon.fromTheme('general_refresh'), 'Update',
                                 self)
        self.tb_update.triggered.connect(self.dbus_handler.require_update)
        self.toolbar.addAction(self.tb_update)
        self.list_tb_action.append(self.tb_update)

        # Home (Default)

        self.home_button = QToolBadgeButton(self)
        self.home_button.setText('Home')
        self.home_button.setCheckable(True)
        self.home_button.setChecked(True)
        self.home_button.clicked.connect(self.show_hometimeline)
        self.list_tb_action.append(self.toolbar.addWidget(self.home_button))

        # Mentions (Default)

        self.mention_button = QToolBadgeButton(self)
        self.mention_button.setText('Mentions')
        self.mention_button.setCheckable(True)
        self.mention_button.clicked.connect(self.show_mentions)
        self.list_tb_action.append(self.toolbar.addWidget(self.mention_button))

        # DM (Default)

        self.msg_button = QToolBadgeButton(self)
        self.msg_button.setText('DMs')
        self.msg_button.setCheckable(True)
        self.msg_button.clicked.connect(self.show_dms)
        self.list_tb_action.append(self.toolbar.addWidget(self.msg_button))

        # Search Button

        self.tb_search_menu = QMenu()
        self.loadSearchMenu()

        # Search (Default)

        self.tb_search_button = QToolBadgeButton(self)
        self.tb_search_button.setText('')
        self.tb_search_button.setIcon(QIcon.fromTheme('general_search'))
        self.tb_search_button.setMenu(self.tb_search_menu)
        self.tb_search_button.setPopupMode(QToolButton.InstantPopup)
        self.tb_search_button.setCheckable(True)
        self.tb_search_button.clicked.connect(self.show_search)
        self.list_tb_action.append(self.toolbar.addWidget(self.tb_search_button))

        # Lists Button

        self.tb_list_menu = QMenu()
        self.loadListMenu()

        # Lists (Default)

        self.tb_list_button = QToolBadgeButton(self)
        self.tb_list_button.setText('')
        self.tb_list_button.setIcon(QIcon.fromTheme('general_notes'))
        self.tb_list_button.setMenu(self.tb_list_menu)
        self.tb_list_button.setPopupMode(QToolButton.InstantPopup)
        self.tb_list_button.setCheckable(True)
        self.tb_list_button.clicked.connect(self.show_list)
        self.list_tb_action.append(self.toolbar.addWidget(self.tb_list_button))

        # Fullscreen

        self.tb_fullscreen = QAction(QIcon.fromTheme('general_fullsize'),
                                     'Fullscreen', self)
        self.tb_fullscreen.triggered.connect(self.do_tb_fullscreen)
        self.toolbar.addAction(self.tb_fullscreen)
        self.list_tb_action.append(self.tb_fullscreen)

        # Reply button (Action)

        self.tb_reply = QAction('Reply', self)
        self.tb_reply.setShortcut('Ctrl+M')
        self.toolbar.addAction(self.tb_reply)
        self.tb_reply.triggered.connect(self.do_tb_reply)
        self.action_tb_action.append(self.tb_reply)

        # Retweet (Action)

        self.tb_retweet = QAction('Retweet', self)
        self.tb_retweet.setShortcut('Ctrl+P')
        self.toolbar.addAction(self.tb_retweet)
        self.tb_retweet.triggered.connect(self.do_tb_retweet)
        self.action_tb_action.append(self.tb_retweet)

        # Follow (Action)

        self.tb_follow = QAction('Follow', self)
        self.tb_follow.triggered.connect(self.do_tb_follow)
        self.toolbar.addAction(self.tb_follow)
        self.action_tb_action.append(self.tb_follow)

        # UnFollow (Action)

        self.tb_unfollow = QAction('Unfollow', self)
        self.tb_unfollow.triggered.connect(self.do_tb_unfollow)
        self.toolbar.addAction(self.tb_unfollow)
        self.action_tb_action.append(self.tb_unfollow)

        # Favorite (Action)

        self.tb_favorite = QAction('Favorite', self)
        self.tb_favorite.triggered.connect(self.do_tb_favorite)
        self.toolbar.addAction(self.tb_favorite)
        self.action_tb_action.append(self.tb_favorite)

        # Open URLs (Action)

        self.tb_urls = QAction('Open URLs', self)
        self.tb_urls.setShortcut('Ctrl+O')
        self.toolbar.addAction(self.tb_urls)
        self.tb_urls.triggered.connect(self.do_tb_openurl)
        self.action_tb_action.append(self.tb_urls)

        # Delete (Action)

        self.tb_delete = QAction('Delete', self)
        self.toolbar.addAction(self.tb_delete)
        self.tb_delete.triggered.connect(self.do_tb_delete)
        self.action_tb_action.append(self.tb_delete)

        # Actions not in toolbar

        self.tb_scrolltop = QAction('Scroll to top', self)
        self.tb_scrolltop.setShortcut(Qt.CTRL + Qt.Key_Up)
        self.tb_scrolltop.triggered.connect(self.view.scrollToTop)
        self.addAction(self.tb_scrolltop)

        self.tb_scrollbottom = QAction('Scroll to bottom', self)
        self.tb_scrollbottom.setShortcut(Qt.CTRL + Qt.Key_Down)
        self.tb_scrollbottom.triggered.connect(self.view.scrollToBottom)
        self.addAction(self.tb_scrollbottom)

        self.tb_zoomin = QAction('ZoomIn', self)
        self.tb_zoomin.setShortcut(Qt.CTRL + Qt.Key_Left)
        self.tb_zoomin.triggered.connect(self.view.do_zoom_in)
        self.addAction(self.tb_zoomin)

        self.tb_zoomout = QAction('ZoomOut', self)
        self.tb_zoomout.setShortcut(Qt.CTRL + Qt.Key_Right)
        self.tb_zoomout.triggered.connect(self.view.do_zoom_out)
        self.addAction(self.tb_zoomout)

        self.tb_copy = QAction('Copy', self)
        self.tb_copy.setShortcut(Qt.CTRL + Qt.Key_C)
        self.tb_copy.triggered.connect(self.do_tb_copy)
        self.addAction(self.tb_copy)

        self.switch_tb_default()

        self.setWindowTitle('Khweeteur : Home')
        self.setCentralWidget(self.view)
        QTimer.singleShot(100,self.post_init)

    @Slot()
    def post_init(self):
        self.model.load('HomeTimeline')
        self.geolocDoStart()

    @Slot()
    def do_tb_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    @Slot()
    def do_tb_copy(self):
        text = None
        for index in self.view.selectedIndexes():
            text = self.model.data(index, role=Qt.DisplayRole)

        if text:
            cb = QApplication.clipboard()
            cb.setText(text)

    def enterEvent(self, event):
        """
            Redefine the enter event to refresh recent file list
        """

        self.model.refreshTimestamp()

    def listen_dbus(self):
        from dbus.mainloop.qt import DBusQtMainLoop
        self.dbus_loop = DBusQtMainLoop()
        dbus.set_default_main_loop(self.dbus_loop)
        self.bus = dbus.SessionBus()

        # Connect the new tweet signal

        self.bus.add_signal_receiver(self.new_tweets,
                                     path='/net/khertan/Khweeteur',
                                     dbus_interface='net.khertan.Khweeteur',
                                     signal_name='new_tweets')
        self.bus.add_signal_receiver(self.stop_spinning,
                                     path='/net/khertan/Khweeteur',
                                     dbus_interface='net.khertan.Khweeteur',
                                     signal_name='refresh_ended')
        self.dbus_handler = KhweeteurDBusHandler(self)
        self.activated_by_dbus.connect(self.activateWindow)
        dbusobj = KhweeteurDBus()
        dbusobj.attach_win(self)

    def stop_spinning(self):
        self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, False)

    def new_tweets(self, count, msg):
        if msg == 'HomeTimeline':
            self.home_button.setCounter(self.home_button.getCounter() + count)
            self.home_button.update()
        elif msg == 'Mentions':
            self.mention_button.setCounter(self.mention_button.getCounter()
                    + count)
            self.mention_button.update()
        elif msg == 'DMs':
            self.msg_button.setCounter(self.msg_button.getCounter() + count)
            self.msg_button.update()
        elif msg.startswith('Search:'):
            self.tb_search_button.setCounter(self.tb_search_button.getCounter()
                    + count)
            self.tb_search_button.update()
        elif msg.startswith('List:'):
            self.tb_list_button.setCounter(self.tb_list_button.getCounter()
                    + count)
            self.tb_list_button.update()

        if self.model.call == msg:
            self.model.load(msg)

    @Slot()
    def show_search(self):
        terms = self.sender().text()
        self.tb_search_button.setCounter(0)
        self.home_button.setChecked(False)
        self.msg_button.setChecked(False)
        self.tb_search_button.setChecked(True)
        self.mention_button.setChecked(False)
        self.tb_list_button.setChecked(False)
        self.view.scrollToTop()
        self.model.load('Search:' + terms)
        self.delete_search_action.setVisible(True)
        self.setWindowTitle('Khweeteur : ' + terms)

    def show_list(
        self,
        name='',
        user='',
        tid='',
        ):
        self.tb_list_button.setCounter(0)
        self.home_button.setChecked(False)
        self.msg_button.setChecked(False)
        self.tb_search_button.setChecked(False)
        self.tb_list_button.setChecked(True)
        self.mention_button.setChecked(False)
        self.view.scrollToTop()
        self.model.load('List:' + user + ':' + tid)
        self.delete_search_action.setVisible(True)
        self.setWindowTitle('Khweeteur List : ' + name)

    @Slot()
    def show_hometimeline(self):
        self.home_button.setCounter(0)
        self.home_button.setChecked(True)
        self.msg_button.setChecked(False)
        self.tb_search_button.setChecked(False)
        self.tb_list_button.setChecked(False)
        self.mention_button.setChecked(False)
        self.view.scrollToTop()
        self.model.load('HomeTimeline')
        self.setWindowTitle('Khweeteur : Home')
        self.delete_search_action.setVisible(False)

    @Slot()
    def switch_tb_default(self):
        self.tb_text.setPlainText('')
        self.tb_text_reply_id = 0
        self.tb_text_reply_base_url = ''
        self.toolbar_mode = 0
        self.switch_tb()

    @Slot()
    def switch_tb_edit(self):
        self.toolbar_mode = 1
        self.switch_tb()

    @Slot()
    def switch_tb_action(self):
        if self.toolbar_mode != 2:
            self.toolbar_mode = 2
            self.switch_tb()
        for index in self.view.selectedIndexes():
            isme = self.model.data(index, role=ISMEROLE)
        if isme:
            self.tb_follow.setVisible(False)
            self.tb_unfollow.setVisible(False)
            self.tb_delete.setVisible(True)
        else:
            self.tb_delete.setVisible(False)
            self.tb_follow.setVisible(True)
            self.tb_unfollow.setVisible(True)

    def switch_tb(self):
        mode = self.toolbar_mode
        for item in self.list_tb_action:
            item.setVisible(mode == 0)
            self.view.setFocus()
        for item in self.edit_tb_action:
            item.setVisible(mode == 1)
            if mode == 1:
                self.tb_text.setFocus()
        for item in self.action_tb_action:
            item.setVisible(mode == 2)
        if mode in (1, 2):
            self.tb_back.setVisible(True)

    @Slot()
    def do_tb_twitpic(self):
        text = self.tb_text.toPlainText()

        if not text:
            QMessageBox.warning(self, 'Khweeteur - Twitpic',
                                'Please enter a text before posting a picture.'
                                , QMessageBox.Close)
            return

        filename = QFileDialog.getOpenFileName(self, 'Khweeteur',
                '/home/user/MyDocs')

        # PySide work arround bug #625

        if type(filename) == tuple:
            filename = filename[0]

        if filename:
            self.dbus_handler.post_tweet(  # shorten_url=\
                                           # serialize=\
                                           # text=\
                                           # lattitude =
                                           # longitude =
                                           # base_url =
                                           # tweet_id =
                0,
                1,
                text,
                ('' if self.geoloc_source == None else self.geoloc_source[0]),
                ('' if self.geoloc_source == None else self.geoloc_source[1]),
                filename,
                'twitpic',
                '',
                )
            self.switch_tb_default()
            self.dbus_handler.require_update()

    @Slot()
    def do_tb_openurl(self):
        for index in self.view.selectedIndexes():
            status = self.model.data(index)
            try:
                urls = re.findall("(?P<url>https?://[^\s]+)", status)
                for url in urls:
                    QDesktopServices.openUrl(QUrl(url))
                self.switch_tb_default()
            except:
                raise

    @Slot()
    def do_tb_send(self):
        is_not_reply = self.tb_text_reply_id == 0
        self.dbus_handler.post_tweet(  # shorten_url=\
                                       # serialize=\
                                       # text=\
                                       # lattitude =
                                       # longitude =
                                       # base_url
                                       # action
            1,
            1,
            self.tb_text.toPlainText(),
            ('' if self.geoloc_source == None else self.geoloc_source[0]),
            ('' if self.geoloc_source == None else self.geoloc_source[1]),
            ('' if is_not_reply else self.tb_text_reply_base_url),
            ('tweet' if is_not_reply else 'reply'),
            ('' if is_not_reply else str(self.tb_text_reply_id)),
            )
        self.switch_tb_default()
        self.dbus_handler.require_update()

    @Slot()
    def do_tb_reply(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_screenname = self.model.data(index, role=SCREENNAMEROLE)
        if tweet_id:
            self.tb_text.setPlainText('@' + tweet_screenname
                                      + self.tb_text.toPlainText())
            self.tb_text_reply_id = tweet_id
            self.tb_text_reply_base_url = tweet_source
            self.switch_tb_edit()

    @Slot()
    def do_tb_retweet(self):

        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_text = self.model.data(index, role=Qt.DisplayRole)
            if self.model.data(index, role=PROTECTEDROLE):
                screenname = self.model.data(index, role=SCREENNAMEROLE)
                QMessageBox.warning(self, 'Khweeteur - Retweet',
                                    "%s protect his tweets you can't retweet them"
                                     % screenname, QMessageBox.Close)

        if not (( QMessageBox.question(None,
            "Kheeteur Retweet",
            "Did you want to retweet '%s'?" % tweet_text,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            tweet_id = None

        if tweet_id:
            self.dbus_handler.post_tweet(  # shorten_url=\
                                           # serialize=\
                                           # text=\
                                           # lattitude =
                                           # longitude =
                                           # base_url =
                                           # tweet_id =
                0,
                0,
                '',
                '',
                '',
                tweet_source,
                'retweet',
                str(tweet_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update()

    @Slot()
    def do_tb_delete(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_text = self.model.data(index, role=Qt.DisplayRole)

        if not (( QMessageBox.question(None,
            "Kheeteur Delete",
            "Did you really want to delete '%s'?" % tweet_text,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            tweet_id = None

        if tweet_id:
            self.dbus_handler.post_tweet(  # shorten_url=\
                                           # serialize=\
                                           # text=\
                                           # lattitude =
                                           # longitude =
                                           # base_url =
                                           # tweet_id =
                0,
                0,
                '',
                '',
                '',
                tweet_source,
                'delete',
                str(tweet_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update()

    @Slot()
    def do_tb_favorite(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_text = self.model.data(index, role=Qt.DisplayRole)

        if not (( QMessageBox.question(None,
            "Kheeteur Favorite",
            "Did you really want to favorite '%s'?" % tweet_text,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            tweet_id = None

        if tweet_id:
            self.dbus_handler.post_tweet(  # shorten_url=\
                                           # serialize=\
                                           # text=\
                                           # lattitude =
                                           # longitude =
                                           # base_url =
                                           # tweet_id =
                0,
                0,
                '',
                '',
                '',
                tweet_source,
                'favorite',
                str(tweet_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update()

    @Slot()
    def do_tb_follow(self):
        user_id = None
        for index in self.view.selectedIndexes():
            user_id = self.model.data(index, role=USERIDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            screenname = self.model.data(index, role=SCREENNAMEROLE)

        if not (( QMessageBox.question(None,
            "Kheeteur Follow",
            "Did you really want to follow '%s'?" % screenname,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            user_id = None

        if user_id:
            self.dbus_handler.post_tweet(  # shorten_url=\
                                           # serialize=\
                                           # text=\
                                           # lattitude =
                                           # longitude =
                                           # base_url =
                                           # tweet_id =
                0,
                0,
                '',
                '',
                '',
                tweet_source,
                'follow',
                str(user_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update()

    @Slot()
    def do_tb_unfollow(self):
        user_id = None
        for index in self.view.selectedIndexes():
            user_id = self.model.data(index, role=USERIDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            screenname = self.model.data(index, role=SCREENNAMEROLE)

        if not (( QMessageBox.question(None,
            "Kheeteur Unfollow",
            "Did you really want to unfollow '%s'?" % screenname,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            user_id = None

        if user_id:
            self.dbus_handler.post_tweet(  # shorten_url=\
                                           # serialize=\
                                           # text=\
                                           # lattitude =
                                           # longitude =
                                           # base_url =
                                           # tweet_id =
                0,
                0,
                '',
                '',
                '',
                tweet_source,
                'unfollow',
                str(user_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update()

    @Slot()
    def show_mentions(self):
        self.mention_button.setCounter(0)
        self.mention_button.setChecked(True)
        self.msg_button.setChecked(False)
        self.tb_list_button.setChecked(False)
        self.tb_search_button.setChecked(False)
        self.home_button.setChecked(False)
        self.view.scrollToTop()
        self.model.load('Mentions')
        self.setWindowTitle('Khweeteur : Mentions')
        self.delete_search_action.setVisible(False)

    @Slot()
    def show_dms(self):
        self.msg_button.setCounter(0)
        self.msg_button.setChecked(True)
        self.tb_list_button.setChecked(False)
        self.home_button.setChecked(False)
        self.tb_search_button.setChecked(False)
        self.mention_button.setChecked(False)
        self.view.scrollToTop()
        self.model.load('DMs')
        self.setWindowTitle('Khweeteur : DMs')
        self.delete_search_action.setVisible(False)

    @Slot()
    def countCharsAndResize(self):
        local_self = self.tb_text
        self.tb_charCounter.setText(unicode(140
                                    - len(local_self.toPlainText())))
        doc = local_self.document()
        fm = local_self.fontMetrics()
#        line_height = fm.boundingRect(local_self.toPlainText()).height()

#        height = (line_height ) * doc.documentLayout().documentSize().height() + fm.lineSpacing()
#        s = doc.documentLayout().documentSize()

#        print 'Doc size', doc.size().height()

#        doc.setHeight(s.height())
#        s.setHeight((s.height() + 2) + (local_self.fontMetrics().lineSpacing()*2 + 2))
#        s.setHeight(s.height())
#        print 'Doc size', s.height()
#        fr = local_self.frameRect()
#        print 'frame size', fr.size().height()
#        cr = local_self.contentsRect()
#        print 'content size', cr.size().height()
#        print 'page size', doc.pageSize().height()
#        print 'page count', doc.pageCount()
#        local_self.setFixedHeight(min(370, s.height() + fr.height()
#                                  - cr.height() - 1))
#        text_height = fm.boundingRect(0,0,local_self.size().width(),370, \
#                    int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap), \
#                    local_self.toPlainText()).height()
#        print 'text height',text_height
#        if height > 5 :
#        local_self.setFixedHeight(min(370, text_height + (fr.height() - cr.height()) + 6))
#        local_self.updateGeometry()
#Resize
#        doc = self.document()            
        s = doc.size().toSize()
        s.setHeight((s.height() + 1) * (fm.lineSpacing()+1))
        fr = local_self.frameRect()
        cr = local_self.contentsRect()
        local_self.setFixedHeight(min(s.height() +  (fr.height() - cr.height() - 1) - 15,370))
        local_self.updateGeometry()
        
    def loadSearchMenu(self):
        settings = QSettings()
        self.tb_search_menu.clear()
        self.tb_search_menu.addAction(QIcon.fromTheme('general_add'), 'New',
                                      self.newSearchAsk)

        nb_searches = settings.beginReadArray('searches')
        for index in range(nb_searches):
            settings.setArrayIndex(index)
            self.tb_search_menu.addAction(settings.value('terms'),
                    self.show_search)
        settings.endArray()

    def loadListMenu(self):
        settings = QSettings()
        self.tb_list_menu.clear()
        nb_lists = settings.beginReadArray('lists')
        for index in range(nb_lists):
            settings.setArrayIndex(index)
            self.tb_list_menu.addAction(settings.value('name'),
                                        lambda user=settings.value('user'), \
                                        id=settings.value('id'), \
                                        name=settings.value('name'): \
                                        self.show_list(name, user, id))
        settings.endArray()

    @Slot()
    def do_delete_search_action(self):
        try:
            terms = self.model.call.split(':')[1]
            for (index, action) in enumerate(self.tb_search_menu.actions()):
                if action.text() == terms:
                    self.tb_search_menu.removeAction(action)
            self.saveSearchMenuInPrefs()
            self.loadSearchMenu()
            self.show_hometimeline()
        except Exception, err:

            print err  # not a search

    def saveSearchMenuInPrefs(self):
        settings = QSettings()
        settings.beginWriteArray('searches')
        for (index, action) in enumerate(self.tb_search_menu.actions()):

            # pass the first which are the new option

            if index == 0:
                continue
            settings.setArrayIndex(index - 1)
            settings.setValue('terms', action.text())
        settings.endArray()
        settings.sync()

    @Slot()
    def newSearchAsk(self):
        (search_terms, ok) = QInputDialog.getText(self, self.tr('Search'),
                self.tr('Enter the search keyword(s) :'))
        if ok == 1:

            # FIXME : Create the search

            self.tb_search_menu.addAction(search_terms, self.show_search)
            self.saveSearchMenuInPrefs()
            self.dbus_handler.require_update()

    def setupMenu(self):
        """
            Initialization of the maemo menu
        """

        fileMenu = QMenu(self.tr('&Menu'), self)
        self.menuBar().addMenu(fileMenu)
        self.delete_search_action = QAction(self.tr('&Delete Search'), self)
        self.delete_search_action.triggered.connect(self.do_delete_search_action)
        fileMenu.addAction(self.tr('&Preferences...'), self.showPrefs)
        fileMenu.addAction(self.tr('&About'), self.showAbout)
        fileMenu.addAction(self.delete_search_action)
        self.delete_search_action.setVisible(False)

    @Slot()
    def showPrefs(self):
        khtsettings = KhweeteurPref(parent=self)
        khtsettings.save.connect(self.refreshPrefs)
        khtsettings.show()

    @Slot()
    def refreshPrefs(self):
        self.view.refreshCustomDelegate()
        self.geolocDoStart()

    @Slot()
    def showAbout(self):
        if not hasattr(self, 'aboutWin'):
            self.aboutWin = KhweeteurAbout(self)
        self.aboutWin.show()

    def geolocDoStart(self):
        settings = QSettings()
        self.geoloc_source = None
        if settings.contains('useGPS'):
            if settings.value('useGPS') == '2':
                self.geolocStart()
            else:
                self.geolocStop()

    def geolocStart(self):
        '''Start the GPS with a 50000 refresh_rate'''
        self.geoloc_coordinates = None
        if self.geoloc_source is None:
            try:
                self.geoloc_source = \
                    QGeoPositionInfoSource.createDefaultSource(None)
            except:
                self.geoloc_source = None
                print 'PySide QtMobility not installed or package broken'
            if self.geoloc_source is not None:
                self.geoloc_source.setUpdateInterval(50000)
                self.geoloc_source.positionUpdated.connect(self.geolocUpdated)
                self.geoloc_source.startUpdates()

    def geolocStop(self):
        '''Stop the GPS'''

        self.geoloc_coordinates = None
        if self.geoloc_source is not None:
            self.geoloc_source.stopUpdates()
            self.geoloc_source = None

    def geolocUpdated(self, update):
        '''GPS Callback on update'''

        if update.isValid():
            self.geoloc_coordinates = (update.coordinate().latitude(),
                                       update.coordinate().longitude())
        else:
            print 'GPS Update not valid'


if __name__ == '__main__':
    from subprocess import Popen
    Popen(['/usr/bin/python', os.path.join(os.path.dirname(__file__),
          'daemon.py'), 'start'])
    app = Khweeteur()
    app.exec_()
    settings = QSettings('Khertan Software', 'Khweeteur')
    if settings.contains('useDaemon'):
        print settings.value('useDaemon')
        if settings.value('useDaemon') != '2':
            print 'Stop daemon'

            # use system to wait the exec

            os.system('/usr/bin/python '
                      + os.path.join(os.path.dirname(__file__), 'daemon.py')
                      + ' stop')
