#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QListView'''

from list_model import IDROLE, SCREENNAMEROLE, REPLYTEXTROLE, \
    RETWEETOFROLE, TIMESTAMPROLE, REPLYTOSCREENNAMEROLE

import os

from PySide.QtGui import QStyledItemDelegate, QListView, QColor, \
    QAbstractItemView, QFontMetrics, QFont, QStyle, QPixmap
from PySide.QtCore import Qt, QSize, QSettings

from theme import DEFAULTTHEME, WHITETHEME, \
                     COOLWHITETHEME, COOLGRAYTHEME, \
                     MINITHEME
              

class DefaultCustomDelegate(QStyledItemDelegate):

    '''Delegate to do custom draw of the items'''

    memoized_size = {}

    def __init__(self, parent):
        '''Initialization'''

        QStyledItemDelegate.__init__(self, parent)

        self.bg_color = QColor('#000000')
        self.bg_alternate_color = QColor('#333333')
        self.user_color = QColor('#7AB4F5')
        self.time_color = QColor('#7AB4F5')
        self.replyto_color = QColor('#7AB4F5')

        self.text_color = QColor('#FFFFFF')
        self.separator_color = QColor('#000000')
        self.fsize = 1.0
        self.fm = None
        self.minifm = None

        self.normFont = None
        self.miniFont = None

#        print os.path.join(os.path.dirname(__file__),
#                                  'icons', 'reply.png')
        self.reply_icon = QPixmap(os.path.join(os.path.dirname(__file__),
                                  'icons', 'reply.png'))
#        print dir(self.reply_icon)
        self.retweet_icon = QPixmap(os.path.join(os.path.dirname(__file__),
                                    'icons', 'retweet.png'))
        self.geoloc_icon = QPixmap(os.path.join(os.path.dirname(__file__),
                                   'icons', 'geoloc.png'))

    def doZoomRefresh(self):
        self.memoized_size.clear()
        self.fm = None
        self.minifm = None
        self.normFont = None
        self.miniFont = None

    def sizeHint(self, option, index):
        '''Custom size calculation of our items'''

        uid = str(index.data(role=IDROLE)) + 'x' + str(option.rect.width())
        try:
            return self.memoized_size[uid]
        except:
            size = QStyledItemDelegate.sizeHint(self, option, index)
            tweet = index.data(Qt.DisplayRole)

            # One time is enought sizeHint need to be fast

            if not self.fm:
                self.normFont = QFont(option.font)
                self.normFont.setPointSizeF(option.font.pointSizeF()
                        * self.fsize)
                self.fm = QFontMetrics(self.normFont)

            if not self.minifm:
                self.miniFont = QFont(option.font)
                self.miniFont.setPointSizeF(option.font.pointSizeF()
                        * 0.8 * self.fsize)
                self.minifm = QFontMetrics(self.miniFont)

            height = self.fm.boundingRect(
                0,
                0,
                option.rect.width() - 75,
                800,
                int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap),
                tweet,
                ).height()

            reply_text = index.data(role=REPLYTEXTROLE)
            if reply_text:
                height += self.minifm.boundingRect(
                    0,
                    0,
                    option.rect.width() - 75,
                    800,
                    int(Qt.AlignTop) | int(Qt.AlignLeft)
                        | int(Qt.TextWordWrap),
                    reply_text,
                    ).height() + 5

            height += self.minifm.boundingRect(
                0,
                0,
                option.rect.width() - 75,
                800,
                int(Qt.AlignTop) | int(Qt.AlignLeft) | int(Qt.TextWordWrap),
                'LpqAT',
                ).height()
            height += 10  # Spacer

            if height < 70:
                height = 70
            self.memoized_size[uid] = QSize(size.width(), height)
            return self.memoized_size[uid]

    def paint(
        self,
        painter,
        option,
        index,
        ):
        '''Paint our tweet'''

        (x1, y1, x2, y2) = option.rect.getCoords()

        # Ugly hack ?

        if y1 < 0 and y2 < 0:
            return

        # Init Font : One time is enough

        if not self.fm:
            self.normFont = QFont(option.font)
            self.normFont.setPointSizeF(option.font.pointSizeF() * self.fsize)

        if not self.minifm:
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF()
                                        * 0.8 * self.fsize)

        # Query data

        tweet = index.data(Qt.DisplayRole)
        screenname = index.data(SCREENNAMEROLE)
        retweet_of = index.data(RETWEETOFROLE)
        timestamp = index.data(role=TIMESTAMPROLE)
        reply_name = index.data(role=REPLYTOSCREENNAMEROLE)
        reply_text = index.data(role=REPLYTEXTROLE)

        painter.save()

        # Draw alternate ?

        if index.row() % 2 == 0:
            painter.fillRect(option.rect, self.bg_color)
        else:
            painter.fillRect(option.rect, self.bg_alternate_color)

        # highlight selected items

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        # Draw icon

        icon = index.data(Qt.DecorationRole)
        if icon != None:
            painter.drawPixmap(x1 + 10, y1 + 10, 50, 50, icon)

        # Draw screenname

        painter.setFont(self.miniFont)
        painter.setPen(self.user_color)
        nrect = painter.drawText(option.rect.adjusted(70, 5, -4, -9),
                                 int(Qt.AlignTop) | int(Qt.AlignLeft),
                                 screenname)

        # Reply icon

        if reply_name:
            painter.drawPixmap(x1 + 74 + nrect.width(), y1, 26, 26,
                               self.reply_icon)
            painter.setFont(self.miniFont)
            painter.setPen(self.replyto_color)
            painter.drawText(option.rect.adjusted(109 + nrect.width(), 5, -4,
                             -9), int(Qt.AlignTop) | int(Qt.AlignLeft),
                             reply_name)

        # Retweet icon

        if retweet_of:
            painter.drawPixmap(x1 + 74 + nrect.width(), y1, 32, 32,
                               self.retweet_icon)
            painter.setFont(self.miniFont)
            painter.setPen(self.replyto_color)
            painter.drawText(option.rect.adjusted(110 + nrect.width(), 5, -4,
                             -9), int(Qt.AlignTop) | int(Qt.AlignLeft),
                             retweet_of.user.screen_name)

        # Draw tweet

        painter.setFont(self.normFont)
        painter.setPen(self.text_color)
        new_rect = painter.drawText(option.rect.adjusted(70, nrect.height()
                                    + 5, -4, 0), int(Qt.AlignTop)
                                    | int(Qt.AlignLeft) | int(Qt.TextWordWrap),
                                    tweet)

        # Draw Timeline

        painter.setFont(self.miniFont)
        painter.setPen(self.time_color)
        painter.drawText(option.rect.adjusted(70, 5, -4, -9), int(Qt.AlignTop)
                         | int(Qt.AlignRight), timestamp)

        # Draw reply

        if reply_text:
            painter.setFont(self.miniFont)
            painter.setPen(self.replyto_color)
            painter.drawText(option.rect.adjusted(70, nrect.height()
                             + new_rect.height() + 5, -4, -9), int(Qt.AlignTop)
                             | int(Qt.AlignLeft) | int(Qt.TextWordWrap),
                             reply_text)

        # Draw line separator

        painter.setPen(self.separator_color)
        painter.drawLine(x1, y2, x2, y2)

        # restore painter

        painter.restore()


class WhiteCustomDelegate(DefaultCustomDelegate):

    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''

        DefaultCustomDelegate.__init__(self, parent)

        self.bg_color = QColor('#FFFFFF')
        self.bg_alternate_color = QColor('#dddddd')
        self.user_color = QColor('#7AB4F5')
        self.time_color = QColor('#7AB4F5')
        self.replyto_color = QColor('#7AB4F5')

        self.text_color = QColor('#000000')
        self.separator_color = QColor('#000000')
        self.fsize = 1.0


class MiniDefaultCustomDelegate(DefaultCustomDelegate):

    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''

        DefaultCustomDelegate.__init__(self, parent)
        self.fsize = 0.80000000000000004


class CoolWhiteCustomDelegate(DefaultCustomDelegate):

    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''

        DefaultCustomDelegate.__init__(self, parent)

        self.user_color = QColor('#3399cc')
        self.replyto_color = QColor('#3399cc')
        self.time_color = QColor('#94a1a7')
        self.bg_color = QColor('#edf1f2')
        self.bg_alternate_color = QColor('#e6eaeb')
        self.text_color = QColor('#444444')
        self.separator_color = QColor('#c8cdcf')


class CoolGrayCustomDelegate(DefaultCustomDelegate):

    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''

        DefaultCustomDelegate.__init__(self, parent)

        self.user_color = QColor('#3399cc')
        self.time_color = QColor('#94a1a7')
        self.replyto_color = QColor('#94a1a7')
        self.bg_color = QColor('#4a5153')
        self.bg_alternate_color = QColor('#444b4d')
        self.text_color = QColor('#FFFFFF')
        self.separator_color = QColor('#333536')


class KhweetsView(QListView):

    ''' Model View '''

    def __init__(self, parent=None):
        QListView.__init__(self, parent)
        self.setWordWrap(True)
        self.refreshCustomDelegate()
        self.setEditTriggers(QAbstractItemView.SelectedClicked)
        self.setSpacing(0)
        self.setUniformItemSizes(False)
        self.setResizeMode(QListView.Adjust)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Up, Qt.Key_Down, Qt.Key_Control):
            QListView.keyPressEvent(self, event)
        else:
            self.parent().switch_tb_edit()
            self.parent().tb_text.setFocus()
            self.parent().tb_text.keyPressEvent(event)

    def do_zoom_in(self):
        print 'do zoom in called'
        self.custom_delegate.fsize = self.custom_delegate.fsize + 0.1
        self.custom_delegate.doZoomRefresh()
        self.parent().resize(-1, -1)

    def do_zoom_out(self):
        print 'do zoom out called'
        self.custom_delegate.fsize = self.custom_delegate.fsize - 0.1
        self.custom_delegate.doZoomRefresh()
        self.parent().resize(-1, -1)

    def refreshCustomDelegate(self):
        settings = QSettings('Khertan Software', 'Khweeteur')
        theme = settings.value('theme')
        if theme == WHITETHEME:
            self.custom_delegate = WhiteCustomDelegate(self)
        elif theme == DEFAULTTHEME:
            self.custom_delegate = DefaultCustomDelegate(self)
        elif theme == COOLWHITETHEME:
            self.custom_delegate = CoolWhiteCustomDelegate(self)
        elif theme == COOLGRAYTHEME:
            self.custom_delegate = CoolGrayCustomDelegate(self)
        elif theme == MINITHEME:
            self.custom_delegate = MiniDefaultCustomDelegate(self)
        else:
            self.custom_delegate = DefaultCustomDelegate(self)
        self.setItemDelegate(self.custom_delegate)


