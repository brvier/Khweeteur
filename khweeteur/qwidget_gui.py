#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

'''A Twitter client made with Python and Qt'''

from __future__ import with_statement

__version__ = '0.6.0'

# import sip
# sip.setapi('QString', 2)
# sip.setapi('QVariant', 2)

from PySide.QtGui import QMainWindow, QHBoxLayout, QSizePolicy, QToolButton, \
    QVBoxLayout, QFileDialog, QDesktopServices, QScrollArea, QPushButton, \
    QToolBar, QLabel, QWidget, QInputDialog, QMenu, QAction, QApplication, \
    QIcon, QMessageBox, QPlainTextEdit, QTextCursor, QDialog, QCheckBox, \
    QDialogButtonBox
from PySide.QtCore import Qt, QUrl, QSettings, Slot, Signal, QTimer

try:
    from PySide.QtMaemo5 import *
except:
    pass

try:
    import osso
except:
    pass

from qbadgebutton import QToolBadgeButton

import os
import sys
import logging
from list_view import KhweetsView
from list_model import KhweetsModel, ISMEROLE, IDROLE, ORIGINROLE, SCREENNAMEROLE, PROTECTEDROLE, USERIDROLE, ISNEWROLE
from posttweet import post_tweet
from settings import settings_db, accounts

import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
from dbushandler import KhweeteurDBusHandler

class KhweeteurAbout(QMainWindow):

    '''About Window'''

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.parent = parent

        self.settings = QSettings()

        try:  # Preferences not set yet
            self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        except:
            pass

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
                "Khweeteur Crash Report",
                "An error occured during your last execution of Khweeteur. Send relevant information to the bug tracker?",
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
                    "An error occurred sending the report: %s" % detail,
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
                    "Khweeteur Crash Report",
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

class KhweeteurWin(QMainWindow):

    activated_by_dbus = Signal()

    def __init__(self, parent=None):
        # Ensure that we are able to get our DBus name before we
        # create the window.
        self.dbus_handler = KhweeteurDBusHandler(self)
        self.dbus_handler.attach_win(self)

        QMainWindow.__init__(self, parent)

        try:
            self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        except:
            pass

        self.setWindowTitle('Khweeteur')

        settings = QSettings()

        self.view = KhweetsView()
        self.setCentralWidget(self.view)

        self.model = KhweetsModel()
        self.view.setModel(self.model)
        self.view.clicked.connect(self.switch_tb_action)

        self.toolbar = QToolBar('Toolbar')
#        self.toolbar.setMovable(False)
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar)

        self.toolbar_mode = 0  # 0 - Default , 1 - Edit, 2 - Action

        self.list_tb_action = []
        self.edit_tb_action = []
        self.action_tb_action = []

        # Switch to edit mode (default)

        self.tb_new = QAction(QIcon.fromTheme('khweeteur'), 'New', self)
        #Move the tb_new connection after the tb_edit toolbar creation #848
        self.toolbar.addAction(self.tb_new)
        self.list_tb_action.append(self.tb_new)

        # Refresh (Default)

        self.tb_update = QAction(QIcon.fromTheme('general_refresh'), 'Update',
                                 self)
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

        # Lists (Default)

        self.tb_list_button = QToolBadgeButton(self)
        self.tb_list_button.setText('')
        self.tb_list_button.setIcon(QIcon.fromTheme('general_notes'))
        self.tb_list_button.setMenu(self.tb_list_menu)
        self.tb_list_button.setPopupMode(QToolButton.InstantPopup)
        self.tb_list_button.setCheckable(True)
        self.tb_list_button.clicked.connect(self.show_list)
        self.list_tb_action.append(self.toolbar.addWidget(self.tb_list_button))

        # Near (Default)
        self.near_button = QToolBadgeButton(self)
        self.near_button.setText('Nears')
        self.near_button.setIcon(QIcon.fromTheme('general_web'))
        self.near_button.setCheckable(True)
        self.near_button.clicked.connect(self.show_nears)
        self.list_tb_action.append(self.toolbar.addWidget(self.near_button))

        # Fullscreen

        self.tb_fullscreen = QAction(QIcon.fromTheme('general_fullsize'),
                                     'Fullscreen', self)
        self.tb_fullscreen.triggered.connect(self.do_tb_fullscreen)
        self.toolbar.addAction(self.tb_fullscreen)
        self.list_tb_action.append(self.tb_fullscreen)

        self.setWindowTitle('Khweeteur: Home')

        self.show()

        QTimer.singleShot(0,self.post_init_2)
        QTimer.singleShot(0,self.post_init_3)
        QApplication.processEvents()

    @Slot()
    def post_init_3(self):
        self.do_model_load('HomeTimeline')
        #Check if there is at least one account
        if not accounts():
            if (( QMessageBox.question(None,
                "Khweeteur",
                'No microblogging account configured, do you want to add one now?',
                QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
                    self.showPrefs()

    @Slot()
    def post_init_2(self):
        self.listen_dbus()

        QTimer.singleShot(3 * 1000, self.dbus_handler.require_update)

        # When the user requests an update, mark it as mandatory (=
        # not optional).
        self.tb_update.triggered.connect(
            lambda: self.dbus_handler.require_update(optional=False))

        self.geolocDoStart()

        self.loadSearchMenu()
        self.loadListMenu()

        #Toolbar to set after startup
        # Back button (Edit + Action)

        self.tb_back = QAction(QIcon.fromTheme('general_back'), 'Back', self)
        self.tb_back.triggered.connect(self.switch_tb_default)
        self.toolbar.addAction(self.tb_back)
        self.tb_back.setVisible(False)
        self.edit_tb_action.append(self.tb_back)
        self.action_tb_action.append(self.tb_back)

        self.setupMenu()

        # Twitpic button

        self.tb_twitpic = QAction(QIcon.fromTheme('tasklaunch_images'),
                                  'Twitpic', self)
        self.tb_twitpic.triggered.connect(self.do_tb_twitpic)
        self.tb_twitpic.setVisible(False)
        self.toolbar.addAction(self.tb_twitpic)
        self.edit_tb_action.append(self.tb_twitpic)

        # Text field (edit)

        self.tb_text = QPlainTextEdit()
        self.tb_text_reply_id = 0
        self.tb_text_reply_base_url = ''
        self.tb_text.setFixedHeight(66)
        action = self.toolbar.addWidget(self.tb_text)
        action.setVisible(False)
        self.edit_tb_action.append(action)

        # Char count (Edit)

        self.tb_charCounter = QLabel('140')
        action = self.toolbar.addWidget(self.tb_charCounter)
        action.setVisible(False)
        self.edit_tb_action.append(action)
        self.tb_text.textChanged.connect(self.countCharsAndResize)

        # Send tweet (Edit)

        self.tb_send = QAction(QIcon.fromTheme('khweeteur'), 'Tweet', self)
        self.tb_send.triggered.connect(self.do_tb_send)
        self.tb_send.setVisible(False)
        self.toolbar.addAction(self.tb_send)
        self.edit_tb_action.append(self.tb_send)

        # Reply button (Action)

        self.tb_reply = QAction('Reply', self)
        self.tb_reply.setShortcut('Ctrl+M')
        self.tb_reply.setVisible(False)
        self.toolbar.addAction(self.tb_reply)
        self.tb_reply.triggered.connect(self.do_tb_reply)
        self.action_tb_action.append(self.tb_reply)

        # Retweet (Action)
        self.tb_retweet = QAction('Retweet', self)
        self.tb_retweet.setShortcut('Ctrl+P')
        self.tb_retweet.setVisible(False)
        self.toolbar.addAction(self.tb_retweet)
        self.tb_retweet.triggered.connect(self.do_tb_retweet)
        self.action_tb_action.append(self.tb_retweet)

        # RT (Action)
        self.tb_rt = QAction('RT', self)
        self.tb_rt.setVisible(False)
        self.toolbar.addAction(self.tb_rt)
        self.tb_rt.triggered.connect(self.do_tb_rt)
        self.action_tb_action.append(self.tb_rt)

        # Follow (Action)
        self.tb_follow = QAction('Follow', self)
        self.tb_follow.triggered.connect(self.do_tb_follow)
        self.tb_follow.setVisible(False)
        self.toolbar.addAction(self.tb_follow)
        self.action_tb_action.append(self.tb_follow)

        # UnFollow (Action)
        self.tb_unfollow = QAction('Unfollow', self)
        self.tb_unfollow.triggered.connect(self.do_tb_unfollow)
        self.tb_unfollow.setVisible(False)
        self.toolbar.addAction(self.tb_unfollow)
        self.action_tb_action.append(self.tb_unfollow)

        # Favorite (Action)

        self.tb_favorite = QAction('Favorite', self)
        self.tb_favorite.triggered.connect(self.do_tb_favorite)
        self.tb_favorite.setVisible(False)
        self.toolbar.addAction(self.tb_favorite)
        self.action_tb_action.append(self.tb_favorite)

        # Open URLs (Action)

        self.tb_urls = QAction('URLs', self)
        self.tb_urls.setShortcut('Ctrl+O')
        self.tb_urls.setVisible(False)
        self.toolbar.addAction(self.tb_urls)
        self.tb_urls.triggered.connect(self.do_tb_openurl)
        self.action_tb_action.append(self.tb_urls)

        # Delete (Action)

        self.tb_delete = QAction('Delete', self)
        self.tb_delete.setVisible(False)
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
        
        #Bug #848
        self.tb_new.triggered.connect(self.switch_tb_edit)


    def do_model_load(self, *args, **kwargs):
        if not self.model.load(*args, **kwargs):
            # It was a reload.  Don't scroll.
            return

        def test(i):
            try:
                return not self.model.data(i, ISNEWROLE)
            except IndexError:
                return False

        def bisect_right(test, x):
            lo = 0
            hi = self.model.rowCount()
            while lo < hi:
                mid = (lo+hi)//2
                if x < test(mid): hi = mid
                else: lo = mid+1 
            return lo

        # We want to scroll to the last new message (i - 1),
        # not the first old message (i)
        first_old = bisect_right(test, False)
        # print "Scrolling to %d" % (first_old,)
        self.view.scrollTo(self.model.index(max (0,  first_old - 1), 0))

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
        self.bus = dbus.SessionBus()

        # Connect the new tweet signal

        self.bus.add_signal_receiver(
            self.new_tweets,
            path='/net/khertan/khweeteur/daemon',
            dbus_interface='net.khertan.khweeteur.daemon',
            signal_name='new_tweets')
        self.bus.add_signal_receiver(self.stop_spinning,
                                     path='/net/khertan/khweeteur',
                                     dbus_interface='net.khertan.khweeteur',
                                     signal_name='refresh_ended')
        self.activated_by_dbus.connect(self.bring_to_front)

    def bring_to_front(self):
        try:
            self.activateWindow()
            self.raise_()
        except Exception:
            logging.exception("bring to front")

    def stop_spinning(self):
        try:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, False)
        except AttributeError:
            pass

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
        elif msg == 'Nears':
            self.near_button.setCounter(self.near_button.getCounter() + count)
            self.near_button.update()
        elif msg.startswith('Search:'):
            self.tb_search_button.setCounter(self.tb_search_button.getCounter()
                    + count)
            self.tb_search_button.update()
        elif msg.startswith('List:'):
            self.tb_list_button.setCounter(self.tb_list_button.getCounter()
                    + count)
            self.tb_list_button.update()

        if self.model.call == msg:
            self.do_model_load(msg)

    @Slot()
    def show_search(self):
        terms = self.sender().text()
        self.tb_search_button.setCounter(0)
        self.home_button.setChecked(False)
        self.msg_button.setChecked(False)
        self.tb_search_button.setChecked(True)
        self.mention_button.setChecked(False)
        self.tb_list_button.setChecked(False)
        self.near_button.setChecked(False)
        self.do_model_load('Search:' + terms)
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
        self.near_button.setChecked(False)
        self.do_model_load('List:' + user + ':' + tid)
        self.delete_search_action.setVisible(True)
        self.setWindowTitle('Khweeteur List : ' + name)

    @Slot()
    def show_hometimeline(self):
        self.home_button.setCounter(0)
        self.home_button.setChecked(True)
        self.msg_button.setChecked(False)
        self.tb_search_button.setChecked(False)
        self.near_button.setChecked(False)
        self.tb_list_button.setChecked(False)
        self.mention_button.setChecked(False)
        self.do_model_load('HomeTimeline')
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
            post_tweet(  # shorten_url=\
                         # serialize=\
                         # text=\
                         # latitude =
                         # longitude =
                         # base_url =
                         # tweet_id =
                0,
                1,
                text,
                ('' if self.geoloc_source == None else self.geoloc_coordinates[0]),
                ('' if self.geoloc_source == None else self.geoloc_coordinates[1]),
                filename,
                'twitpic',
                '',
                )
            self.switch_tb_default()
            self.dbus_handler.require_update(only_uploads=True)

    @Slot()
    def do_tb_openurl(self):
        import re
        for index in self.view.selectedIndexes():
            status = self.model.data(index)
            try:
                urls = re.findall("(?P<url>https?://[^\s]+)", status)
                for url in urls:
                    QDesktopServices.openUrl(QUrl(url))
                self.switch_tb_default()
            except:
                raise

    def select_accounts(self, message='Select Accounts',
                        default_accounts=None, service=None):
        """
        Ask the user what accounts should be used for some action,
        which is described by message.

        If default_accounts is not None, it must be a list of account
        identifiers that should be selected by default.  Otherwise,
        the default is those accounts with 'use_for_tweet' set to
        'true'.

        If service is not None, only asks about those accounts for the
        specified service.

        The make default button is only shown if default_accoutns and
        service is None.

        Returns account identifiers (use as the base_url).
        """
        print("Default accounts: %s; service: %s"
              % (str (default_accounts), str(service)))

        def make_default():
            for account_widget in account_widgets:
                checkbox = account_widget['box']
                account = account_widget['account']

                if checkbox.checkState() == Qt.Checked:
                    account.use_for_tweet = 'true'
                else:
                    account.use_for_tweet = 'false'

            accounts(True)

        accounts_to_consider = []
        for account in accounts():
            if service is None or service == account['base_url']:
                accounts_to_consider.append(account)

        if len(accounts_to_consider) == 1:
            # We have exactly one account that is marked as
            # appropriate for sending tweets.  Use it.
            pass
        else:
            d = QDialog()
            d.setWindowTitle(message)

            layout = QVBoxLayout()
            account_widgets = []
            for account in accounts_to_consider:
                checkbox = QCheckBox(account['name'])
                account_widget = {'box': checkbox, 'account': account}
                account_widgets.append(account_widget)

                checked = False
                if default_accounts is not None:
                    if account.uuid in default_accounts:
                        checked = True
                else:
                    if account.use_for_tweet == 'true':
                        checked = True

                checkbox.setCheckState(Qt.Checked if checked else Qt.Unchecked)

                layout.addWidget(checkbox)

            buttonbox = QDialogButtonBox(
                QDialogButtonBox.Ok|QDialogButtonBox.Cancel,
                parent=d)
            buttonbox.accepted.connect(d.accept)
            buttonbox.rejected.connect(d.reject)

            if default_accounts is None and service is None:
                make_default_button = QPushButton("Make &Default")
                buttonbox.addButton(make_default_button,
                                    QDialogButtonBox.ApplyRole)
                make_default_button.clicked.connect(make_default)

            layout.addWidget(buttonbox)

            d.setLayout(layout)
            if d.exec_() == QDialog.Accepted:
                target_accounts \
                    = [account_widget['account']
                       for account_widget in account_widgets
                       if account_widget['box'].checkState() == Qt.Checked]
            else:
                target_accounts = []

        base_urls = [account['base_url'] + ';' + account['token_key']
                     for account in target_accounts]

        return base_urls

    @Slot()
    def do_tb_send(self):
        is_not_reply = self.tb_text_reply_id == 0

        default_accounts = None
        if not is_not_reply:
            default_accounts = [self.tb_text_reply_base_url]

        base_urls = self.select_accounts(default_accounts=default_accounts)
        if not base_urls:
            # Nothing selected => cancelled.
            return

        for base_url in base_urls:
            post_tweet(  # shorten_url=\
                         # serialize=\
                         # text=\
                         # latitude =
                         # longitude =
                         # base_url
                         # action
                1,
                1,
                self.tb_text.toPlainText(),
                ('' if self.geoloc_source == None else self.geoloc_coordinates[0]),
                ('' if self.geoloc_source == None else self.geoloc_coordinates[1]),
                base_url,
                ('tweet' if is_not_reply else 'reply'),
                ('' if is_not_reply else str(self.tb_text_reply_id)),
                )
        self.switch_tb_default()
        self.dbus_handler.require_update(only_uploads=True)

    @Slot()
    def do_tb_reply(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_screenname = self.model.data(index, role=SCREENNAMEROLE)
        if tweet_id:
            self.tb_text.setPlainText('@%s ' % tweet_screenname)
            cur = self.tb_text.textCursor()
            cur.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
            self.tb_text.setTextCursor(cur)
            self.tb_text_reply_id = tweet_id
            self.tb_text_reply_base_url = tweet_source
            self.switch_tb_edit()

    @Slot()
    def do_tb_rt(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_screenname = self.model.data(index, role=SCREENNAMEROLE)
            tweet_text = self.model.data(index, role=Qt.DisplayRole)
        if tweet_id:
            self.tb_text.setPlainText('RT @%s: %s' % (tweet_screenname, tweet_text))
            cur = self.tb_text.textCursor()
            cur.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
            self.tb_text.setTextCursor(cur)
            self.switch_tb_edit()
            self.tb_text.show()
            self.tb_text.updateGeometry()
            self.tb_text.textChanged.emit()

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
                                    "%s's tweets are protected: you can't retweet them."
                                     % screenname, QMessageBox.Close)

        if not (( QMessageBox.question(None,
            "Khweeteur Retweet",
            "Do you want to retweet '%s'?" % tweet_text,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            return

        for base_url in self.select_accounts(default_accounts=[tweet_source]):
            post_tweet(  # shorten_url=\
                         # serialize=\
                         # text=\
                         # latitude =
                         # longitude =
                         # base_url =
                         # action =
                         # tweet_id =
                0,
                0,
                '',
                '',
                '',
                base_url,
                'retweet',
                str(tweet_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update(only_uploads=True)

    @Slot()
    def do_tb_delete(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_text = self.model.data(index, role=Qt.DisplayRole)

        if not (( QMessageBox.question(None,
            "Khweeteur Delete",
            "Do you really want to delete '%s'?" % tweet_text,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            tweet_id = None

        if tweet_id:
            post_tweet(  # shorten_url=\
                         # serialize=\
                         # text=\
                         # latitude =
                         # longitude =
                         # base_url =
                         # action =
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
            self.dbus_handler.require_update(only_uploads=True)

    @Slot()
    def do_tb_favorite(self):
        tweet_id = None
        for index in self.view.selectedIndexes():
            tweet_id = self.model.data(index, role=IDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            tweet_text = self.model.data(index, role=Qt.DisplayRole)

        if not (( QMessageBox.question(None,
            "Khweeteur Favorite",
            "Do you really want to favorite '%s'?" % tweet_text,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            return

        for base_url in self.select_accounts(default_accounts=[tweet_source]):
            post_tweet(  # shorten_url=\
                         # serialize=\
                         # text=\
                         # latitude =
                         # longitude =
                         # base_url =
                         # action =
                         # tweet_id =
                0,
                0,
                '',
                '',
                '',
                base_url,
                'favorite',
                str(tweet_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update(only_uploads=True)

    @Slot()
    def do_tb_follow(self):
        user_id = None
        for index in self.view.selectedIndexes():
            user_id = self.model.data(index, role=USERIDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            screenname = self.model.data(index, role=SCREENNAMEROLE)

        if user_id is None:
            user_id = screenname

        if not (( QMessageBox.question(None,
            "Khweeteur Follow",
            "Do you really want to follow '%s'?" % screenname,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            return

        for base_url in self.select_accounts(default_accounts=[tweet_source]):
            post_tweet(  # shorten_url=\
                         # serialize=\
                         # text=\
                         # latitude =
                         # longitude =
                         # base_url =
                         # action =
                         # tweet_id =
                0,
                0,
                '',
                '',
                '',
                base_url,
                'follow',
                str(user_id),
                )
            self.switch_tb_default()
            self.dbus_handler.require_update(only_uploads=True)

    @Slot()
    def do_tb_unfollow(self):
        user_id = None
        for index in self.view.selectedIndexes():
            user_id = self.model.data(index, role=USERIDROLE)
            tweet_source = self.model.data(index, role=ORIGINROLE)
            screenname = self.model.data(index, role=SCREENNAMEROLE)

        if not (( QMessageBox.question(None,
            "Khweeteur Unfollow",
            "Do you really want to unfollow '%s'?" % screenname,
            QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
            user_id = None

        if user_id:
            post_tweet(  # shorten_url=\
                         # serialize=\
                         # text=\
                         # latitude =
                         # longitude =
                         # base_url =
                         # action =
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
            self.dbus_handler.require_update(only_uploads=True)

    @Slot()
    def show_mentions(self):
        self.mention_button.setCounter(0)
        self.mention_button.setChecked(True)
        self.msg_button.setChecked(False)
        self.tb_list_button.setChecked(False)
        self.tb_search_button.setChecked(False)
        self.home_button.setChecked(False)
        self.near_button.setChecked(False)
        self.do_model_load('Mentions')
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
        self.near_button.setChecked(False)
        self.do_model_load('DMs')
        self.setWindowTitle('Khweeteur : DMs')
        self.delete_search_action.setVisible(False)

    @Slot()
    def show_nears(self):
        settings = QSettings()
        if settings.value('useGPS') != '2':
            if (( QMessageBox.question(None,
                "Khweeteur",
                'This feature requires the GPS, do you want to activate it now?',
                QMessageBox.Yes| QMessageBox.Close)) ==  QMessageBox.Yes):
                    settings.setValue('useGPS','2')
                    settings.sync()
                    self.geolocDoStart()
                    self.dbus_handler.require_update(only_uploads=True)

        self.near_button.setCounter(0)
        self.near_button.setChecked(True)
        self.msg_button.setChecked(False)
        self.tb_list_button.setChecked(False)
        self.home_button.setChecked(False)
        self.tb_search_button.setChecked(False)
        self.mention_button.setChecked(False)
        self.do_model_load('Nears')
        self.setWindowTitle('Khweeteur: Nearby Tweets')
        self.delete_search_action.setVisible(False)

    @Slot()
    def countCharsAndResize(self):
        local_self = self.tb_text
        self.tb_charCounter.setText(unicode(140
                                    - len(local_self.toPlainText())))
        doc = local_self.document()
        fm = local_self.fontMetrics()

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
        from settings import KhweeteurPref
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
            if (settings.value('useGPS') == '2') and (settings.value('useGPSOnDemand')!='2'):
                self.geolocStart()
            else:
                self.geolocStop()

    def geolocStart(self):
        '''Start the GPS with a 50000 refresh_rate'''
        self.geoloc_coordinates = None
        if self.geoloc_source is None:
            try:
                from QtMobility.Location import QGeoPositionInfoSource
                self.geoloc_source = \
                    QGeoPositionInfoSource.createDefaultSource(None)
            except:
                self.geoloc_source = None
                logging.exception(
                    'PySide QtMobility not installed or package broken')
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
    app = Khweeteur()
    app.exec_()
