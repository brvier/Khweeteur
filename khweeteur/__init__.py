#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4'''

__version__ = '0.1.17'

#TODOS :
#* Fix Identi.ca oauth bug
#* Add separate notification for dm and mention
#* Add list features
#* Push 0.1.x line to extras
#* Add retry on network errors

from utils import *
from notifications import KhweeteurNotification
from post_worker import KhweeteurActionWorker
from refresh_worker import KhweeteurRefreshWorker, \
                           KhweeteurHomeTimelineWorker, \
                           KhweeteurRetweetedByMeWorker, \
                           KhweeteurRetweetsOfMeWorker, \
                           KhweeteurRepliesWorker, \
                           KhweeteurDMWorker, \
                           KhweeteurMentionWorker, \
                           KhweeteurSearchWorker, \
                           KhweeteurWorker
from list_model import KhweetsModel
from list_view import WhiteCustomDelegate, \
                      DefaultCustomDelegate, \
                      CoolWhiteCustomDelegate, \
                      CoolGrayCustomDelegate, \
                      KhweetsView
import sys
from settings import KhweeteurPref
import twitter
import urllib2
import socket

if not USE_PYSIDE:
    from PyQt4.QtGui import QMainWindow, \
                            QDialog, \
                            QApplication, \
                            QMenu, \
                            QKeySequence, \
                            QToolBar, \
                            QAction, \
                            QIcon, \
                            QPlainTextEdit, \
                            QLabel, \
                            QMessageBox, \
                            QGridLayout, \
                            QPushButton, \
                            QDesktopServices, \
                            QScrollArea, \
                            QWidget, \
                            QSizePolicy, \
                            QVBoxLayout, \
                            QHBoxLayout, \
                            QInputDialog, \
                            QFileDialog, \
                            QDirModel, \
                            QPixmap
                            
#    from PyQt4.QtGui import *                                                      
    from PyQt4.QtCore import QTimer, QSettings, \
                             QUrl, \
                             Qt, QObject

    try:
        from PyQt4.QtMobility.QtLocation import *
        noQtLocation = False
    except:
        noQtLocation = True
                            
else:
    from PySide.QtGui import QMainWindow, \
                             QDialog, \
                             QApplication, \
                             QMenu, \
                             QKeySequence, \
                             QToolBar, \
                             QAction, \
                             QIcon, \
                             QPlainTextEdit, \
                             QLabel, \
                             QMessageBox, \
                             QGridLayout, \
                             QPushButton, \
                             QDesktopServices, \
                             QScrollArea, \
                             QWidget, \
                             QSizePolicy, \
                             QVBoxLayout, \
                             QHBoxLayout, \
                             QInputDialog, \
                             QFileDialog, \
                             QDirModel, \
                             QPixmap
                             
    try:
        from QtMobility.Location import * #PySide
        noQtLocation = False
    except:
        noQtLocation = True
                                                     
    from PySide.QtCore import QTimer, QSettings, \
                              QUrl, \
                              Qt, QObject

class KhweeteurAbout(QMainWindow):

    '''About Window'''

    def __init__(self, parent=None):
        QMainWindow.__init__(self, parent)
        self.parent = parent

        self.settings = QSettings()

        if isMAEMO:
            try:  # Preferences not set yet
                if int(self.settings.value('useAutoRotation')) == 2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)

            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setWindowTitle(self.tr('Khweeteur About'))

        if isMAEMO:
            aboutScrollArea = QScrollArea(self)
            aboutScrollArea.setWidgetResizable(True)
            awidget = QWidget(aboutScrollArea)
            awidget.setMinimumSize(480, 1400)
            awidget.setSizePolicy(QSizePolicy.Expanding,
                                  QSizePolicy.Expanding)
            aboutScrollArea.setSizePolicy(QSizePolicy.Expanding,
                    QSizePolicy.Expanding)

        # Kinetic scroller is available on Maemo and should be on meego

            try:
                scroller = aboutScrollArea.property('kineticScroller')
                scroller.setEnabled(True)
            except:
                pass

            aboutLayout = QVBoxLayout(awidget)
        else:
            awidget = QWidget(self)
            aboutLayout = QVBoxLayout(awidget)

        aboutIcon = QLabel()
        if isMAEMO:
            aboutIcon.setPixmap(QIcon.fromTheme('khweeteur'
                                ).pixmap(128, 128))
        else:
            aboutIcon.setPixmap(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'icons', 'khweeteur.png')).pixmap(128,
                                128))

        aboutIcon.setAlignment(Qt.AlignCenter or Qt.AlignHCenter)
        aboutIcon.resize(128, 128)
        aboutLayout.addWidget(aboutIcon)

        aboutLabel = \
            QLabel(self.tr('''<center><b>Khweeteur</b> %s
                                   <br><br>A Simple twitter client with follower status, reply,
                                   <br>and direct message in a unified view
                                   <br><br>Licenced under GPLv3
                                   <br>By Beno&icirc;t HERVIER (Khertan)
                                   <br><br><b>Khweeteur try to be simple and fast identi.ca and twitter client,</b>
                                   <br>your timeline, reply and direct message arer displayed in a unified view.
                                   <br><br><b>To reply, retweet, open a url, follow/unfollow an account :</b>
                                   <br>double click on a status and choose the action in the dialog which appear.
                                   <br><br>To activate automatic update set a refresh interval different of zero.
                                   <br><br>Use preferences from dialog to set your account with oauth,
                                   <br>and to display or not timestamp, username or avatar.
                                   <br><br><b>Shortcuts :</b>
                                   <br>Control-R : Refresh current view
                                   <br>Control-M : Reply to selected tweet
                                   <br>Control-Up : To scroll to top
                                   <br>Control-Bottom : To scroll to bottom
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
                                   </center>''')
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

        if isMAEMO:
            awidget.setLayout(aboutLayout)
            aboutScrollArea.setWidget(awidget)
            self.setCentralWidget(aboutScrollArea)
        else:
            self.setCentralWidget(awidget)

        self.show()

    def open_website(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur'))

    def open_bugtracker(self):
        QDesktopServices.openUrl(QUrl('http://khertan.net/khweeteur/bugs'
                                 ))

class KhweetAction(QMainWindow):

    def __init__(self, parent=None): 
        QMainWindow.__init__(self, parent)

        self.settings = QSettings()

        if isMAEMO:
            try:
                if int(self.settings.value('useAutoRotation')) == 2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:
                # No pref yet default is true
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        self.setupGUI()

    def setupGUI(self):
        self._main_widget = QWidget(self)
        self._layout = QVBoxLayout(self._main_widget)

        self._head_widget = QWidget(self._main_widget)
        self._screen_name = QLabel()
        self._screen_name.setWordWrap(True)
        self._head_layout = QHBoxLayout(self._head_widget)
        self._icon = QLabel()
        
        self._head_layout.addWidget(self._icon)
        self._head_layout.addWidget(self._screen_name)
        self._head_layout.setStretch(1,1)
        self._head_layout.setSpacing(6)
        self._head_layout.setMargin(0)
        self._layout.setMargin(11)
                        
        self._head_widget.setLayout(self._head_layout)
        self._layout.addWidget(self._head_widget)        

        self._text = QLabel()
        self._text.setWordWrap(True)
        self._layout.addWidget(self._text)
        self._layout.setStretch(1,10)
        self._layout.setStretch(0,1)

        self._text_reply = QLabel()
        self._text_reply.setWordWrap(True)
        self._layout.addWidget(self._text_reply)
        self._layout.setStretch(2,1)

        self._foot_widget = QWidget(self._main_widget)
        self._foot_layout = QGridLayout(self._foot_widget)        
        self._foot_layout.setSpacing(6)
        self._foot_layout.setMargin(0)
        
        self.reply = QPushButton('Reply')
        self.reply.setText(self.tr('&Reply'))
        self._foot_layout.addWidget(self.reply, 0, 0)

        self.retweet = QPushButton('Retweet')
        self.retweet.setText(self.tr('&Retweet'))
        self._foot_layout.addWidget(self.retweet, 1, 0)

        self.destroy_tweet = QPushButton('Destroy')
        self.destroy_tweet.setText(self.tr('&Destroy'))
        self._foot_layout.addWidget(self.destroy_tweet, 0, 1)

        self.openurl = QPushButton('Open URL')
        self.openurl.setText(self.tr('&Open URL'))
        self._foot_layout.addWidget(self.openurl, 0, 2)

        self.favorite = QPushButton('Favorite')
        self.favorite.setText(self.tr('&Favorite'))
        self.unfavorite = QPushButton('UnFavorite')
        self.unfavorite.setText(self.tr('&UnFavorite'))

        self._foot_layout.addWidget(self.favorite, 1, 1)
        self._foot_layout.addWidget(self.unfavorite, 1, 2)
        self._favorited = QLabel()
        favorited = QPixmap(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'icons', 'favorite.png'))
        self._favorited.setPixmap(favorited)
        self._head_layout.addWidget(self._favorited)

        self.follow = QPushButton('Follow')
        self.follow.setText(self.tr('&Follow'))
        self._head_layout.addWidget(self.follow)

        self.unfollow = QPushButton('Unfollow')
        self.unfollow.setText(self.tr('&Unfollow'))
        self._head_layout.addWidget(self.unfollow)

        self._foot_widget.setLayout(self._foot_layout)
        self._layout.addWidget(self._foot_widget)
        self._main_widget.setLayout(self._layout)
        self.setCentralWidget(self._main_widget)

    def closeEvent(self,event):
#        event.accept()
        event.ignore()
        self.hide()
#        self.close()
        print 'CloseEvent'
                               
    def set(self, parent=None, tweet_id='' ,folder=''):
#        self.setupGUI()
        self.tweet_id = tweet_id

        #Load Tweet
        try:
            pkl_file = open(os.path.join(folder, unicode(tweet_id)), 'rb')
            status = pickle.load(pkl_file)
            pkl_file.close()
        except:
            import traceback
            traceback.print_exc()
            self.close()

        if hasattr(status,'user'):
            if hasattr(status.user,'status.user.name'):            
                _screen_name = status.user.name + ' (' + status.user.screen_name+')'
            else:
                _screen_name = status.user.screen_name
            icon_path = os.path.basename(status.user.profile_image_url.replace('/' , '_'))
        else:
            _screen_name = status.sender_screen_name
            icon_path = None
        _text = status.text
        
        self.setWindowTitle('Khweeteur : ' + _screen_name)
        
        if icon_path:
            try:
                icon = QPixmap(os.path.join(AVATAR_CACHE_FOLDER,
                                        icon_path))
                self._icon.setPixmap(icon)
            except:
                import traceback
                traceback.print_exc()

        _text_reply = ''
        if hasattr(status,'in_reply_to_screen_name'):
            if status.in_reply_to_screen_name:
                if status.in_reply_to_status_text:
                    _text_reply = '<small><i>In reply to ' + status.in_reply_to_screen_name + ' : ' + status.in_reply_to_status_text+'</i></small>'
                else:
                    _text_reply = '<small><i>In reply to ' + status.in_reply_to_screen_name+'</i></small>'
                

        if hasattr(status, 'retweeted_status'):
            if status.retweeted_status != None: #Fix truncated RT
                _text = status.retweeted_status.text
                _text_reply = '<small><i>Retweet of ' + status.retweeted_status.user.screen_name+'<i></small>'
                
        self._screen_name.setText(_screen_name)
        self._text.setText(_text)
        if status.favorited:
            self._favorited.show()
            self.favorite.hide()
            self.unfavorite.show()
        else:
            self._favorited.hide()
            self.favorite.show()
            self.unfavorite.hide()
        if _text_reply:
            self._text_reply.setText(_text_reply)
            self._text_reply.show()
        else:
            self._text_reply.hide()

#        self._text_reply.resize(-1,-1)
#        self._text.resize(-1,-1)
#        self._text.update()
#        self._text.repaint()
        
#        self._head_layout.update()
#        self._layout.update()
#        self._main_widget.repaint()
#        self.repaint()
#        self._main_widget.setLayout(self._layout)
#        self.setCentralWidget(self._main_widget)
    def do_update(self):
        self._text.repaint()
        self._text_reply.repaint()
        self._screen_name.repaint()
        
class KhweeteurWin(QMainWindow):
    def __init__(self, parent=None, search_keyword=None):
        QMainWindow.__init__(self, None)
            
        self._parent = parent
        self.timer = QTimer()  # Fix bug #451

        self.search_keyword = search_keyword

        # crappy trick to avoid search win to be garbage collected
        self.search_win = []

        self.settings = KhweeteurSettings()

        #Crappy fix for old prefs due to change to QVariant
        #Api 2 and PySide
        if self.settings.value('twitter_access_token') in ('True','1',1):
            self.settings.setValue('twitter_access_token',1)
        else:
            print 'Should not happen error 448:',type(self.settings.value('twitter_access_token')),self.settings.value('twitter_access_token')
            self.settings.setValue('twitter_access_token',0)
            
        if self.settings.value('identica_access_token') in ('True','1',1):
            self.settings.setValue('identica_access_token',1)
        else:
            self.settings.setValue('identica_access_token',0)

        try:
            if int(self.settings.value('useGPS')) == 2:
                if self._parent != None:
                    self._parent.positionStart()
        except:
            pass

        if isMAEMO:
            try:  # Pref not set yet
                if int(self.settings.value('useAutoRotation')) == 2:
                    self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            except:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
        else:
            self.resize(300, 600)

        if self.search_keyword != None:
            if self.search_keyword != 'GeOSearH':
                self.setWindowTitle('Khweeteur:'
                                    + unicode(self.search_keyword))
            else:
                self.setWindowTitle('Khweeteur: Near Tweets')
        else:
            self.setWindowTitle('Khweeteur')

        self.setupMenu()
        self.setupMain()

        self.worker = None
        self.tweetsModel.display_screenname = \
            self.settings.value('displayUser') == '2'
        self.tweetsModel.display_timestamp = \
            self.settings.value('displayTimestamp') == '2'
        self.tweetsModel.display_avatar = \
            self.settings.value('displayAvatar') == '2'

        self.tweetActionDialog = None

        if self.search_keyword != None:
            if self.search_keyword == 'GeOSearH':
                if int(self.settings.value('useGPS')) != 2:  # FIX446
                    if QMessageBox.question(self, 'Khweeteur',
                            self.tr('This feature require activation of the gps, did you want to continue ?'
                            ), QMessageBox.Yes | QMessageBox.Close) \
                        == QMessageBox.Yes:
                        self.settings.setValue('useGPS', 2)
                        self._parent.positionStart()
                    else:
                        self.close()
                        return

        self.notifications = KhweeteurNotification()

        QTimer.singleShot(200, self.justAfterInit)

    def closeEvent(self, widget, *args):
#        if self._parent != None:            
#            self._parent.search_win.remove(self)
        for win in self.search_win:
            win.close()
#        if self._parent != None:            
#            self._parent.setAttribute(Qt.WA_Maemo5StackedWindow, True)


    def justAfterInit(self):
        try:
            from nwmanager import NetworkManager
            self.nw = NetworkManager(self.refresh_timeline)
        except:
            self.refresh_timeline()

#        self.connect(self.timer, SIGNAL('timeout()'),
#                     self.timed_refresh)
        self.timer.timeout.connect(self.timed_refresh)
        if int(self.settings.value('refreshInterval') > 0):
            self.timer.start(int(self.settings.value('refreshInterval'
                             )) * 60 * 1000)

        if not self.search_keyword:
            if not (bool(self.settings.value('twitter_access_token')) or \
                bool(self.settings.value('identica_access_token'))):
                self.notifications.warn('Khweeteur aren\'t authorized to connect to any service. Please authorize one in preferences.')
            self.open_saved_search()

    def enterEvent(self, event):
        """
            Redefine the enter event to refresh timestamp
        """

        self.tweetsModel.refreshTimestamp()

    def timedUnserialize(self):
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
        self.tweetsModel.unSerialize()
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, False)

    def setupMain(self):

        self.tweetsView = KhweetsView(self)
        try:
            self.tweetsView.custom_delegate.show_screenname = \
                int(self.settings.value('displayUser')) == 2
            self.tweetsView.custom_delegate.show_timestamp = \
                int(self.settings.value('displayTimestamp')) == 2
            self.tweetsView.custom_delegate.show_avatar = \
                int(self.settings.value('displayAvatar')) == 2
            self.tweetsView.custom_delegate.show_replyto = \
                int(self.settings.value('displayReplyTo')) == 2
        except:
            pass

#        self.connect(self.tweetsView,
#                     SIGNAL('doubleClicked(const QModelIndex&)'),
#                     self.tweet_do_ask_action)
        self.tweetsView.clicked.connect(self.tweet_do_ask_action)
        self.tweetsModel = KhweetsModel(self.search_keyword)
        try:  # If pref didn't exist
            self.tweetsModel.setLimit(int(self.settings.value('tweetHistory'
                    )))
        except:
            self.tweetsModel.setLimit(50)
        self.tweetsView.setModel(self.tweetsModel)
        self.setCentralWidget(self.tweetsView)

        self.toolbar = QToolBar('Toolbar')
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar)

        if isMAEMO:
            self.tb_update = QAction(QIcon.fromTheme('general_refresh'
                    ), 'Update', self)
        else:
            self.tb_update = \
                QAction(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'icons', 'refresh.png')), 'Update', self)

        self.tb_update.setShortcut('Ctrl+R')
        self.tb_update.triggered.connect(self.request_refresh)
#        self.connect(self.tb_update, SIGNAL('triggered()'),
#                     self.request_refresh)
        self.toolbar.addAction(self.tb_update)

        self.tb_text = QPlainTextEdit()
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.tb_text_replysource = ''
        if not USE_PYSIDE:
            self.tb_text.enabledChange(True)
        self.toolbar.addWidget(self.tb_text)

        self.tb_charCounter = QLabel('140')
        self.toolbar.addWidget(self.tb_charCounter)
        self.tb_text.textChanged.connect(self.countCharsAndResize)
#        self.connect(self.tb_text, SIGNAL('textChanged()'),
#                     self.countCharsAndResize)

        if isMAEMO:
            self.tb_tweet = QAction(QIcon.fromTheme('khweeteur'),
                                    'Tweet', self)
        else:
            self.tb_tweet = \
                QAction(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'icons', 'khweeteur.png')), 'Tweet', self)

        self.tb_tweet.triggered.connect(self.tweet)
        self.toolbar.addAction(self.tb_tweet)

        if isMAEMO:
            self.tb_text.setFixedHeight(70)
        else:
            self.countCharsAndResize()

        # Actions not in toolbar

        self.tb_reply = QAction('Reply', self)
        self.tb_reply.setShortcut('Ctrl+M')
        self.tb_reply.triggered.connect(self.reply)
        self.addAction(self.tb_reply)

        self.tb_scrolltop = QAction('Scroll to top', self)
        self.tb_scrolltop.setShortcut(Qt.CTRL + Qt.Key_Up)
        self.tb_scrolltop.triggered.connect(self.scrolltop)
        self.addAction(self.tb_scrolltop)

        self.tb_scrollbottom = QAction('Scroll to bottom', self)
        self.tb_scrollbottom.setShortcut(Qt.CTRL + Qt.Key_Down)
        self.tb_scrollbottom.triggered.connect(self.scrollbottom)
        self.addAction(self.tb_scrollbottom)

        QTimer.singleShot(200, self.timedUnserialize)

    @pyqtSlot()
    def scrolltop(self):
        self.tweetsView.scrollToTop()

    @pyqtSlot()
    def scrollbottom(self):
        self.tweetsView.scrollToBottom()

    @pyqtSlot()
    def tweet_do_ask_action(self):
        for index in self.tweetsView.selectedIndexes():
            tweet_id = self.tweetsModel.data(index, role=IDROLE)
                        
        if tweet_id:
            if self.tweetActionDialog == None:
                self.tweetActionDialog = KhweetAction(self)
                self.tweetActionDialog.reply.clicked.connect(self.reply)
                self.tweetActionDialog.openurl.clicked.connect(self.open_url)
                self.tweetActionDialog.retweet.clicked.connect(self.retweet)
                self.tweetActionDialog.follow.clicked.connect(self.follow)
                self.tweetActionDialog.unfollow.clicked.connect(self.unfollow)
                self.tweetActionDialog.destroy_tweet.clicked.connect(self.destroy_tweet)
                self.tweetActionDialog.favorite.clicked.connect(self.favorite)
                self.tweetActionDialog.unfavorite.clicked.connect(self.unfavorite)
#            self.setAttribute(Qt.WA_Maemo5StackedWindow, True)
#            self.tweetActionDialog.setAttribute(Qt.WA_Maemo5StackedWindow, True)
            self.tweetActionDialog.set(tweet_id=tweet_id, folder=self.tweetsModel.getCacheFolder())
            self.tweetActionDialog.show()
            self.tweetActionDialog.do_update()

    @pyqtSlot()
    def countCharsAndResize(self):
        local_self = self.tb_text
        self.tb_charCounter.setText(unicode(140
                                    - len(local_self.toPlainText())))
        doc = local_self.document()
        cursor = local_self.cursorRect()
        s = doc.size()
        if isMAEMO:
            s.setHeight((s.height() + 1)
                        * (local_self.fontMetrics().lineSpacing() + 1)
                        - 21)
        else:
            s.setHeight((s.height() + 1)
                        * (local_self.fontMetrics().lineSpacing() + 1)
                        - 10)
        fr = local_self.frameRect()
        cr = local_self.contentsRect()
        local_self.setFixedHeight(min(370, s.height() + fr.height()
                                  - cr.height() - 1))

    @pyqtSlot()
    def reply(self):
        if self.tweetActionDialog != None:
            self.tweetActionDialog.close()
        for index in self.tweetsView.selectedIndexes():
            user = self.tweetsModel.data(index, role=SCREENNAMEROLE)
            self.tb_text_replyid = self.tweetsModel.data(index,
                    role=IDROLE)
            self.tb_text_replytext = '@' + user + ' '
            self.tb_text.setPlainText('@' + user + ' ')
            self.tb_text_replysource = self.tweetsModel.data(index,
                    role=ORIGINROLE)

    @pyqtSlot()
    def open_url(self):
        import re
        self.tweetActionDialog.close()
        for index in self.tweetsView.selectedIndexes():
            status = self.tweetsModel.data(index)
            try:
                urls = re.findall("(?P<url>https?://[^\s]+)", status)
                for url in urls:
                    QDesktopServices.openUrl(QUrl(url))
            except StandardError, e:
                print e

    @pyqtSlot()
    def follow(self):
        self.tweetActionDialog.close()
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.follow)
        else:
            for index in self.tweetsView.selectedIndexes():
                user_screenname = self.tweetsModel.data(index,
                        role=SCREENNAMEROLE)
                if QMessageBox.question(self, 'Khweeteur',
                        self.tr('Follow : %s ?') % user_screenname,
                        QMessageBox.Yes | QMessageBox.Close) \
                    == QMessageBox.Yes:
                    if 'twitter' in self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('twitter_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                        password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('twitter_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur')
                                api.CreateFriendship(user_screenname)
                                self.notifications.info(self.tr('You are now following %s on Twitter'
                                        ) % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname, str(e)))
                                print e

                    if 'http://identi.ca/api' \
                        == self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('identica_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(base_url='http://identi.ca/api'
                                        ,
                                        username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                        password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('identica_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('identica_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur/%s'
                                        % __version__)
                                api.CreateFriendship(user_screenname)
                                self.notifications.info(self.tr('You are now following %s on Identi.ca'
                                        ) % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Add %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname, str(e)))
                                print e

    @pyqtSlot()
    def unfollow(self):
        self.tweetActionDialog.close()
        
        if not self.nw.device_has_networking:
            self.parent().nw.request_connection_with_tmp_callback(self.unfollow)
        else:
            for index in self.tweetsView.selectedIndexes():
                user_screenname = self.tweetsModel.data(index,
                        role=SCREENNAMEROLE)
                if QMessageBox.question(self, 'Khweeteur',
                        self.tr('Unfollow : %s ?') % user_screenname,
                        QMessageBox.Yes | QMessageBox.Close) \
                    == QMessageBox.Yes:

                    if 'twitter' in self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('twitter_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                        password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('twitter_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur')
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Twitter'
                                         % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Twitter : %s'
                                        ) % (user_screenname, str(e)))
                                print e

                    if 'http://identi.ca/api' \
                        == self.tweetsModel.data(index,
                            role=ORIGINROLE):
                        try:
                            if self.settings.value('identica_access_token_key'
                                    ) != None:
                                api = \
                                    twitter.Api(base_url='http://identi.ca/api'
                                        ,
                                        username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                        password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                        access_token_key=str(self.settings.value('identica_access_token_key'
                                        )),
                                        access_token_secret=str(self.settings.value('identica_access_token_secret'
                                        )))
                                api.SetUserAgent('Khweeteur/%s'
                                        % __version__)
                                api.DestroyFriendship(user_screenname)
                                self.notifications.info('You didn\'t follow %s anymore on Identi.ca'
                                         % user_screenname)
                        except (
                            twitter.TwitterError,
                            StandardError,
                            urllib2.HTTPError,
                            urllib2.httplib.BadStatusLine,
                            socket.timeout,
                            socket.sslerror,
                            ), e:
                            if type(e) == twitter.TwitterError:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname,
                                        e.message))
                                print e.message
                            else:
                                self.notifications.warn(self.tr('Remove %s to friendship failed on Identi.ca : %s'
                                        ) % (user_screenname, str(e)))
                                print e
            
    @pyqtSlot()
    def favorite(self):
        self.tweetActionDialog.close()
        for index in self.tweetsView.selectedIndexes():
            if QMessageBox.question(self, 'Khweeteur',
                                    'Mark as Favorited : %s ?'
                                    % self.tweetsModel.data(index),
                                    QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                tweetid = self.tweetsModel.data(index, role=IDROLE)
                if 'twitter' in self.tweetsModel.data(index,
                        role=ORIGINROLE):
                    try:
                        if self.settings.value('twitter_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur')
                            api.CreateFavorite(tweetid)
                            KhweeteurRefreshWorker().setFavoriteInCache(tweetid,True)
                            self.notifications.info(self.tr('Favorite sent to Twitter'))
                                                     
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Favorite to twitter failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Favorite to twitter failed : '
                                    ) + str(e))
                            print e

                if 'http://identi.ca/api' \
                    == self.tweetsModel.data(index, role=ORIGINROLE):
                    try:
                        if self.settings.value('identica_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(base_url='http://identi.ca/api'
                                    ,
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.CreateFavorite(tweetid)
                            KhweeteurRefreshWorker().setFavoriteInCache(tweetid,True)
                            self.notifications.info(self.tr('Favorite sent to Identi.ca'
                                    ))
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Favorite to identi.ca failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Favorite to identi.ca failed : '
                                    ) + str(e))
                            print e

    @pyqtSlot()
    def unfavorite(self):
        self.tweetActionDialog.close()
        for index in self.tweetsView.selectedIndexes():
            if QMessageBox.question(self, 'Khweeteur',
                                    'Mark as UnFavorited : %s ?'
                                    % self.tweetsModel.data(index),
                                    QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                tweetid = self.tweetsModel.data(index, role=IDROLE)
                if 'twitter' in self.tweetsModel.data(index,
                        role=ORIGINROLE):
                    try:
                        if self.settings.value('twitter_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur')
                            api.DestroyFavorite(tweetid)
                            KhweeteurRefreshWorker().setFavoriteInCache(tweetid,False)
                            self.notifications.info(self.tr('Remove favorite to Twitter'
                                    ))
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Remove favorite to twitter failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Remove favorite to twitter failed : '
                                    ) + str(e))
                            print e

                if 'http://identi.ca/api' \
                    == self.tweetsModel.data(index, role=ORIGINROLE):
                    try:
                        if self.settings.value('identica_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(base_url='http://identi.ca/api'
                                    ,
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.DestroyFavorite(tweetid)
                            KhweeteurRefreshWorker().setFavoriteInCache(tweetid,False)
                            self.notifications.info(self.tr('Remove favorite sent to Identi.ca'
                                    ))
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Remove favorite to identi.ca failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Remove favorite to identi.ca failed : '
                                    ) + str(e))
                            print e
                            
    @pyqtSlot()
    def retweet(self):
        self.tweetActionDialog.close()
        
        for index in self.tweetsView.selectedIndexes():
            if QMessageBox.question(self, 'Khweeteur',
                                    'Retweet this : %s ?'
                                    % self.tweetsModel.data(index),
                                    QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                tweetid = self.tweetsModel.data(index, role=IDROLE)
                if 'twitter' in self.tweetsModel.data(index,
                        role=ORIGINROLE):
                    try:
                        if self.settings.value('twitter_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur')
                            api.PostRetweet(tweetid)
                            self.notifications.info(self.tr('Retweet sent to Twitter'
                                    ))
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Retweet to twitter failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Retweet to twitter failed : '
                                    ) + str(e))
                            print e

                if 'http://identi.ca/api' \
                    == self.tweetsModel.data(index, role=ORIGINROLE):
                    try:
                        if self.settings.value('identica_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(base_url='http://identi.ca/api'
                                    ,
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.PostRetweet(tweetid)
                            self.notifications.info(self.tr('Retweet sent to Identi.ca'
                                    ))
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn(self.tr('Retweet to identi.ca failed : '
                                    ) + e.message)
                            print e.message
                        else:
                            self.notifications.warn(self.tr('Retweet to identi.ca failed : '
                                    ) + str(e))
                            print e

    @pyqtSlot()
    def destroy_tweet(self):
        self.tweetActionDialog.close()
        
        for index in self.tweetsView.selectedIndexes():
            if QMessageBox.question(self, 'Khweeteur',
                                    self.tr('Destroy this : %s ?')
                                    % self.tweetsModel.data(index),
                                    QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                tweetid = self.tweetsModel.data(index, role=IDROLE)
                if 'twitter' in self.tweetsModel.data(index,
                        role=ORIGINROLE):
                    try:
                        if self.settings.value('twitter_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(username=KHWEETEUR_TWITTER_CONSUMER_KEY,
                                    password=KHWEETEUR_TWITTER_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('twitter_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('twitter_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur')
                            api.DestroyStatus(tweetid)
                            self.tweetsModel.destroyStatus(index)
                            self.notifications.info('Status destroyed on Twitter'
                                    )
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn('Destroy status from twitter failed : '
                                     + e.message)
                            print e.message
                        else:
                            self.notifications.warn('Destroy status from twitter failed : '
                                     + str(e))
                            print e

                if 'http://identi.ca/api' \
                    == self.tweetsModel.data(index, role=ORIGINROLE):
                    try:
                        if self.settings.value('identica_access_token_key'
                                ) != None:
                            api = \
                                twitter.Api(base_url='http://identi.ca/api'
                                    ,
                                    username=KHWEETEUR_IDENTICA_CONSUMER_KEY,
                                    password=KHWEETEUR_IDENTICA_CONSUMER_SECRET,
                                    access_token_key=str(self.settings.value('identica_access_token_key'
                                    )),
                                    access_token_secret=str(self.settings.value('identica_access_token_secret'
                                    )))
                            api.SetUserAgent('Khweeteur/%s'
                                    % __version__)
                            api.DestroyStatus(tweetid)
                            self.tweetsModel.destroyStatus(index)
                            self.notifications.info('Status destroyed on Identi.ca'
                                    )
                    except (
                        twitter.TwitterError,
                        StandardError,
                        urllib2.HTTPError,
                        urllib2.httplib.BadStatusLine,
                        socket.timeout,
                        socket.sslerror,
                        ), e:
                        if type(e) == twitter.TwitterError:
                            self.notifications.warn('Destroy status from identi.ca failed : '
                                     + e.message)
                            print e.message
                        else:
                            self.notifications.warn('Destroy status from identi.ca failed : '
                                     + str(e))
                            print e

    @pyqtSlot()
    def tweetSent(self):
        self.tb_text.setPlainText('')
        self.tb_text_replyid = 0
        self.tb_text_replytext = ''
        self.request_refresh()  # Feature Request : 201

    @pyqtSlot()
    def tweetSentFinished(self):
        self.tb_text.setEnabled(True)
        self.tb_tweet.setEnabled(True)

    @pyqtSlot()
    def tweet(self):
        try:
            if not self.nw.device_has_networking:
                self.nw.request_connection_with_tmp_callback(self.tweet)
            else:
                raise StandardError('No network control')
        except:
            self.tb_text.setDisabled(True)
            self.tb_tweet.setDisabled(True)
            try:
                geoposition = self.parent.coordinates
            except:
                geoposition = None
            self.tweetAction = KhweeteurActionWorker(
                self,
                'tweet',
                (unicode(self.tb_text.toPlainText()).encode('utf-8'),
                self.tb_text_replyid,
                self.tb_text_replytext,
                self.tb_text_replysource,
                geoposition),
                )
            self.tweetAction.tweetSent.connect(self.tweetSent)
            self.tweetAction.finished.connect(self.tweetSentFinished)
            self.tweetAction.info.connect(self.notifications.info)
            self.tweetAction.warn.connect(self.notifications.warn)
            self.tweetAction.tweetSent.connect(self.tweetSent)
            self.tweetAction.finished.connect(self.tweetSentFinished)
            self.tweetAction.start()

    def refreshEnded(self):
        counter = self.tweetsModel.getNew()
        if counter > 0 and int(self.settings.value('useNotification')) \
            == 2 and not self.isActiveWindow():
            if self.search_keyword == None:
                self.notifications.notify('Khweeteur', str(counter)
                        + ' new tweet(s)', count=counter)
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, False)

    def do_refresh_now(self):
        if isMAEMO:
            self.setAttribute(Qt.WA_Maemo5ShowProgressIndicator, True)
        if self.search_keyword == 'GeOSearH':
            if self.parent.coordinates:
                geocode = (self.parent.coordinates[0],
                           self.parent.coordinates[1], '1km')
            else:
                geocode = None
        else:
            geocode = None
        if not self.worker:
            self.worker = KhweeteurWorker(self,
                    search_keyword=self.search_keyword, geocode=geocode)
#            self.connect(self.worker,
#                         SIGNAL('newStatuses(tuple)'),
#                         self.tweetsModel.addStatuses)
            self.worker.newStatuses.connect(self.tweetsModel.addStatuses)
#            self.connect(self.worker, SIGNAL('finished()'),
#                         self.refreshEnded)
            self.worker.finished.connect(self.refreshEnded)
            self.worker.info.connect(self.notifications.info)
        else:
            self.worker.geocode = geocode
        self.worker.start()

    def request_refresh(self):
        try:
            if not self.nw.device_has_networking:
                self.nw.request_connection()
            else:
                raise StandardError('No network control')
        except:
            self.refresh_timeline()

    def timed_refresh(self):
        self.request_refresh()

    def refresh_timeline(self):
        if not self.worker:
            self.do_refresh_now()
        elif self.worker.isFinished() == True:
            self.do_refresh_now()

    def restartTimer(self):
        if isMAEMO:
            if int(self.settings.value('useAutoRotation')) == 2:
                self.setAttribute(Qt.WA_Maemo5AutoOrientation, True)
        self.tweetsView.refreshCustomDelegate()

        self.tweetsView.custom_delegate.show_screenname = \
            int(self.settings.value('displayUser')) == 2
        self.tweetsView.custom_delegate.show_timestamp = \
            int(self.settings.value('displayTimestamp')) == 2
        self.tweetsView.custom_delegate.show_avatar = \
            int(self.settings.value('displayAvatar')) == 2
        self.tweetsView.custom_delegate.show_replyto = \
            int(self.settings.value('displayReplyTo')) == 2
        #QObject.emit(self.tweetsModel,
        #             SIGNAL('dataChanged(const QModelIndex&, const QModelIndex &)'
        #             ), self.tweetsModel.createIndex(0, 0),
        #             self.tweetsModel.createIndex(0,
        #             self.tweetsModel.rowCount()))
        self.tweetsModel.dataChanged.emit(self.tweetsModel.createIndex(0, 0),
                     self.tweetsModel.createIndex(0,
                     self.tweetsModel.rowCount()))
        if int(self.settings.value('refreshInterval')) > 0:
            self.timer.start(int(self.settings.value('refreshInterval'
                             )) * 60 * 1000)
        else:
            self.timer.stop()
        if self._parent != None:  # We are in a search so no need to start gps #Fix bug#399
            if int(self.settings.value('useGPS')) == 2:
                self._parent.positionStart()
            else:
                self.parent._positionStop()
        for search_win in self.search_win:
            search_win.restartTimer()

    def setupMenu(self):
        fileMenu = QMenu(self.tr('&Menu'), self)

        self.menuBar().addMenu(fileMenu)

        fileMenu.addAction(self.tr('&Preferences'), self.do_show_pref,
                           QKeySequence(self.tr('Ctrl+P', 'Preferences'
                           )))
        fileMenu.addAction(self.tr('&Near Tweets'), self.near_search,
                           QKeySequence(self.tr('Ctrl+N', 'Near Tweets'
                           )))
        fileMenu.addAction(self.tr('&Search'), self.open_search,
                           QKeySequence(self.tr('Ctrl+S', 'Search')))

        fileMenu.addAction(self.tr('&TwitPic Upload'), self.twitpic_pre_upload,
                           QKeySequence(self.tr('Ctrl+T', 'Twitpic Upload')))

        if self.search_keyword != None:
            keywords = self.settings.value('savedSearch')
            if keywords != None:
                if self.search_keyword in keywords:
                    fileMenu.addAction(self.tr('&Remove Search'),
                            self.del_search)
                else:
                    fileMenu.addAction(self.tr('&Save Search'),
                            self.save_search)
            else:
                fileMenu.addAction(self.tr('&Save Search'),
                                   self.save_search)

        fileMenu.addAction(self.tr('&About'), self.do_about)

    @pyqtSlot()
    def twitpic_pre_upload(self):
        filename =  QFileDialog.getOpenFileName(self,
                            "Khweeteur",'/home/user/MyDocs')

        #PySide work arround bug #625
        if type(filename) == tuple:
            filename = filename[0
            ]
        twitpic_message, ok = QInputDialog.getText(self, self.tr('Twitpic Message'), self.tr('Enter the twitpic message :'))

        if ((not (filename == '')) and ok) :
            try:
                if not self.nw.device_has_networking:
                    self.nw.request_connection_with_tmp_callback(lambda data=((filename,twitpic_message),None,None,None,None):self.twitpic_upload(data))
                else:
                    raise StandardError('No network control')
            except:
                self.twitpic_upload(((filename,twitpic_message),None,None,None,None))

    @pyqtSlot(unicode)
    def twitpic_post_upload(self,url):
        self.tb_text.insertPlainText(url)
        
    @pyqtSlot(tuple)
    def twitpic_upload(self,data):
        self.tb_text.setDisabled(True)
        self.tb_tweet.setDisabled(True)
        self.tweetAction = KhweeteurActionWorker(
            self,
            'twitpic',
            data,
            )
        self.tweetAction.info.connect(self.notifications.info)
        self.tweetAction.warn.connect(self.notifications.warn)
        self.tweetAction.pictUploaded.connect(self.twitpic_post_upload)
        self.tweetAction.finished.connect(self.tweetSentFinished)
        self.tweetAction.start()


    @pyqtSlot()
    def del_search(self):
        keywords = self.settings.value('savedSearch')
        if not keywords:
            keywords = []
        elif type(keywords) == unicode:
            keywords = []
        elif type(keywords) == list:
            try:
                keywords.remove(self.search_keyword)
            except:
                pass
        else:
            keywords.remove(self.search_keyword)
        self.settings.setValue('savedSearch', keywords)
        self.close()

    @pyqtSlot()
    def save_search(self):
        keywords = self.settings.value('savedSearch')
        if not keywords:
            keywords = []
        elif type(keywords) == unicode:
            keywords = [keywords,]
        keywords.append(self.search_keyword)
        self.settings.setValue('savedSearch', keywords)

    def open_saved_search(self):
        keywords = self.settings.value('savedSearch')
        if type(keywords) == unicode:
            keywords = [keywords,]

        if keywords != None:
            if type(keywords)==list:
                for keyword in keywords:
                    self.do_search(keyword)
            else:
                self.settings.setValue('savedSearch',[])

        self.activateWindow()

    def open_search(self):
        (search_keyword, ok) = QInputDialog.getText(self,
                self.tr('Search'),
                self.tr('Enter the search keyword(s) :'))
        if ok == 1:
            self.do_search(search_keyword)

    def near_search(self):
        self.do_search('GeOSearH')

    def do_search(self, search_keyword):
        swin = KhweeteurWin(search_keyword=unicode(search_keyword),
                            parent=self)
        self.search_win.append(swin)
        swin.show()

    def do_show_pref(self):
        self.pref_win = KhweeteurPref(self)
        self.pref_win.save.connect(self.restartTimer)
        self.pref_win.show()

    def do_about(self):
        self.aboutWin = KhweeteurAbout(self)

#    @pyqtSlot()
    @pyqtSlot()
    def activated_by_dbus(self):
        self.tweetsModel.getNewAndReset()
        self.activateWindow()


class Khweeteur(QApplication):

    activated_by_dbus = pyqtSignal()

#    activated_by_dbus = Signal()

    def __init__(self):
        QApplication.__init__(self, sys.argv)
        self.setOrganizationName('Khertan Software')
        self.setOrganizationDomain('khertan.net')
        self.setApplicationName('Khweeteur')
        self.version = __version__

        try:
            import dbus
            import dbus.service
            from dbus.mainloop.qt import DBusQtMainLoop
            from dbusobj import KhweeteurDBus
            self.dbus_loop = DBusQtMainLoop()
            dbus.set_default_main_loop(self.dbus_loop)
            self.dbus_object = KhweeteurDBus()
        except:
            self.dbus_object = None

        install_excepthook(__version__)
        
        self.coordinates = None
        self.source = None

        self.run()

    def positionStart(self):
        '''Start the GPS with a 50000 refresh_rate'''

        if self.source is None:
            self.source = \
                QGeoPositionInfoSource.createDefaultSource(None)
            if self.source is not None:
                self.source.setUpdateInterval(50000)
                self.source.positionUpdated.connect(self.positionUpdated)
                self.source.startUpdates()

    def positionStop(self):
        '''Stop the GPS'''

        if self.source is not None:
            self.source.stopUpdates()
            self.source = None

    def positionUpdated(self, update):
        '''GPS Callback on update'''

        if update.isValid():
            self.coordinates = (update.coordinate().latitude(),
                                update.coordinate().longitude())

    def handle_signal(self, *args):
        pass  # print 'received signal:', args

    def crash_report(self):
        if os.path.isfile(os.path.join(CACHE_PATH, 'crash_report')):
            import urllib
            if QMessageBox.question(None,
                                    self.tr('Khweeteur Crash Report'),
                                    self.tr('An error occur on khweeteur in the previous launch. Report this bug on the bug tracker ?'
                                    ), QMessageBox.Yes
                                    | QMessageBox.Close) \
                == QMessageBox.Yes:
                url = 'http://khertan.net/report.php'  # write ur URL here
                try:
                    filename = os.path.join(CACHE_PATH, 'crash_report')
                    output = open(filename, 'rb')
                    error = pickle.load(output)
                    output.close()

                    values = {'project': 'khweeteur',
                              'version': __version__,
                              'description': error}

                    data = urllib.urlencode(values)
                    req = urllib2.Request(url, data)
                    response = urllib2.urlopen(req)
                    the_page = response.read()
                except Exception, detail:
                    QMessageBox.question(None,
                            self.tr('Khweeteur Crash Report'),
                            self.tr('An error occur during the report : %s'
                            ) % detail, QMessageBox.Close)
                    return False

                if 'Your report have been successfully stored' \
                    in the_page:
                    QMessageBox.question(None,
                            self.tr('Khweeteur Crash Report'), '%s'
                            % the_page, QMessageBox.Close)
                    return True
                else:
                    QMessageBox.question(None,
                            self.tr('Khweeteur Crash Report'),
                            QMessageBox.Close)
                    return False
            try:
                os.remove(os.path.join(CACHE_PATH, 'crash_report'))
            except:
                import traceback
                traceback.print_exc()

    def run(self):
        self.win = KhweeteurWin(self)
        if self.dbus_object !=None:
            self.dbus_object.attach_app(self)
        self.activated_by_dbus.connect(self.win.activated_by_dbus)
        self.crash_report()
        self.win.show()


if __name__ == '__main__':
    sys.exit(Khweeteur().exec_())
