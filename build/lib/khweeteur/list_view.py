#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QListView'''

import sip
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)

SCREENNAMEROLE = 20
REPLYTOSCREENNAMEROLE = 21
REPLYTEXTROLE = 22
REPLYIDROLE = 25
IDROLE = 23
ORIGINROLE = 24
TIMESTAMPROLE = 26
RETWEETOFROLE = 27
ISMEROLE = 28


from PySide.QtGui import QStyledItemDelegate, \
                    QListView, \
                    QColor, \
                    QAbstractItemView, \
                    QFontMetrics, \
                    QFont, \
                    QStyle
from PySide.QtCore import Qt, \
                     QSize, \
                     QSettings

from settings import KhweeteurPref

class WhiteCustomDelegate(QStyledItemDelegate):

    '''Delegate to do custom draw of the items'''

    def __init__(self, parent):
        '''Initialization'''

        QStyledItemDelegate.__init__(self, parent)

        self.bg_color = QColor('#FFFFFF')
        self.bg_alternate_color = QColor('#dddddd')
        self.user_color = QColor('#7AB4F5')
        self.time_color = QColor('#7AB4F5')
        self.replyto_color = QColor('#7AB4F5')

        self.text_color = QColor('#000000')
        self.separator_color = QColor('#000000')


class DefaultCustomDelegate(QStyledItemDelegate):

    '''Delegate to do custom draw of the items'''

    memoized_size = {}
    memoized_width = {}

    def __init__(self, parent):
        '''Initialization'''

        QStyledItemDelegate.__init__(self, parent)
        self.show_avatar = True
        self.show_screenname = True
        self.show_timestamp = True
        self.show_replyto = True

        self.bg_color = QColor('#000000')
        self.bg_alternate_color = QColor('#333333')
        self.user_color = QColor('#7AB4F5')
        self.time_color = QColor('#7AB4F5')
        self.replyto_color = QColor('#7AB4F5')

        self.text_color = QColor('#FFFFFF')
        self.separator_color = QColor('#000000')

        self.fm = None
        self.minifm = None

        self.normFont = None
        self.miniFont = None

    def sizeHint(self, option, index):
        '''Custom size calculation of our items'''

        uid = str(index.data(role=IDROLE)) + 'x' + \
            str(option.rect.width())
        try:
            return self.memoized_size[uid]
        except:
            size = QStyledItemDelegate.sizeHint(self, option, index)
            tweet = index.data(Qt.DisplayRole)

            # One time is enought sizeHint need to be fast

            if not self.fm:
                self.fm = QFontMetrics(option.font)
            height = self.fm.boundingRect(
                0,
                0,
                option.rect.width() - 75,
                800,
                int(Qt.AlignTop) | int(Qt.AlignLeft)
                    | int(Qt.TextWordWrap),
                tweet,
                ).height() + 40

            if self.show_replyto:
                reply_name = index.data(role=REPLYTOSCREENNAMEROLE)
                reply_text = index.data(role=REPLYTEXTROLE)
                if reply_name and reply_text:

                    # One time is enought sizeHint need to be fast

                    reply = 'In reply to @' + reply_name + ' : ' \
                        + reply_text
                    if not self.minifm:
                        if not self.miniFont:
                            self.miniFont = QFont(option.font)
                            self.miniFont.setPointSizeF(option.font.pointSizeF()
                                    * 0.80)
                        self.minifm = QFontMetrics(self.miniFont)
                    height += self.minifm.boundingRect(
                        0,
                        0,
                        option.rect.width() - 75,
                        800,
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap),
                        reply,
                        ).height()
                elif reply_name:
                    reply = 'In reply to @' + reply_name
                    if not self.minifm:
                        if not self.miniFont:
                            self.miniFont = QFont(option.font)
                            self.miniFont.setPointSizeF(option.font.pointSizeF()
                                    * 0.80)
                        self.minifm = QFontMetrics(self.miniFont)
                    height += self.minifm.boundingRect(
                        0,
                        0,
                        option.rect.width() - 75,
                        800,
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap),
                        reply,
                        ).height()

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

#        if not USE_PYSIDE:
        (x1, y1, x2, y2) = option.rect.getCoords()
#        else:
            #Work arround Pyside bug #544
#            y1 = option.rect.y()
#            y2 = y1 + option.rect.height()
#            x1 = option.rect.x()
#            x2 = x1 + option.rect.width()
#
        # Ugly hack ?
        if y1 < 0 and y2 < 0:
            return

        if not self.fm:
            self.fm = QFontMetrics(option.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole)
        is_me = index.data(ISMEROLE)

        # Instantiate font only one time !

        if not self.normFont:
            self.normFont = QFont(option.font)
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.80)

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

        if self.show_avatar:
            icon = index.data(Qt.DecorationRole)
            if icon != None:
                if is_me:
                    painter.drawPixmap(x2 -60, y1 + 10, 50, 50, icon)
                else:
                    painter.drawPixmap(x1 + 10, y1 + 10, 50, 50, icon)

        # Draw tweet

        painter.setPen(self.text_color)
        if is_me:
            new_rect = \
                painter.drawText(option.rect.adjusted(4, 5, -70, 0), int(Qt.AlignTop)
                                 | int(Qt.AlignRight)
                                 | int(Qt.TextWordWrap), tweet)
        else:
            new_rect = \
                painter.drawText(option.rect.adjusted(int(self.show_avatar)
                                 * 70, 5, -4, 0), int(Qt.AlignTop)
                                 | int(Qt.AlignLeft)
                                 | int(Qt.TextWordWrap), tweet)

        # Draw Timeline

        if self.show_timestamp:
            time = index.data(role=TIMESTAMPROLE)
            painter.setFont(self.miniFont)
            painter.setPen(self.time_color)
            if is_me:
                painter.drawText(option.rect.adjusted(4, 10, -80, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignRight),
                                 time)
            else:
                painter.drawText(option.rect.adjusted(70, 10, -10, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignRight),
                                 time)

        # Draw screenname

        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE)
            retweet_of = index.data(RETWEETOFROLE)
            if retweet_of:
                screenname = '%s : Retweet of %s' % (screenname, retweet_of.user.screen_name)
            painter.setFont(self.miniFont)
            painter.setPen(self.user_color)
            if is_me:
                painter.drawText(option.rect.adjusted(4, 10, -70, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignLeft),
                                 screenname)
            else:
                painter.drawText(option.rect.adjusted(70, 10, -10, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignLeft),
                                 screenname)

        # Draw reply

        if self.show_replyto:
            reply_name = index.data(role=REPLYTOSCREENNAMEROLE)
            reply_text = index.data(role=REPLYTEXTROLE)
            if reply_name and reply_text:
                reply = 'In reply to ' + reply_name + ' : ' \
                    + reply_text
                painter.setFont(self.miniFont)
                painter.setPen(self.replyto_color)
                if is_me:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(4, new_rect.height() + 5, -70, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)
                else:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(int(self.show_avatar)
                            * 70, new_rect.height() + 5, -4, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)
            elif reply_name:
                reply = 'In reply to ' + reply_name
                painter.setFont(self.miniFont)
                painter.setPen(self.replyto_color)
                if is_me:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(4, new_rect.height() + 5, -70, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)
                else:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(int(self.show_avatar)
                            * 70, new_rect.height() + 5, -4, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)

        # Draw line

        painter.setPen(self.separator_color)
        painter.drawLine(x1, y2, x2, y2)

        painter.restore()


class MiniDefaultCustomDelegate(QStyledItemDelegate):

    '''Delegate to do custom draw of the items'''

    memoized_size = {}
    memoized_width = {}

    def __init__(self, parent):
        '''Initialization'''

        QStyledItemDelegate.__init__(self, parent)
        self.show_avatar = True
        self.show_screenname = True
        self.show_timestamp = True
        self.show_replyto = True

        self.bg_color = QColor('#000000')
        self.bg_alternate_color = QColor('#333333')
        self.user_color = QColor('#7AB4F5')
        self.time_color = QColor('#7AB4F5')
        self.replyto_color = QColor('#7AB4F5')

        self.text_color = QColor('#FFFFFF')
        self.separator_color = QColor('#000000')

        self.fm = None
        self.minifm = None

        self.normFont = None
        self.miniFont = None

    def sizeHint(self, option, index):
        '''Custom size calculation of our items'''

        uid = str(index.data(role=IDROLE)) + 'x' + \
            str(option.rect.width())
        try:
            return self.memoized_size[uid]
        except:
            size = QStyledItemDelegate.sizeHint(self, option, index)
            tweet = index.data(Qt.DisplayRole)

            # One time is enought sizeHint need to be fast

            if not self.fm:
                self.font = QFont(option.font)
                self.font.setPointSizeF(option.font.pointSizeF()
                                    * 0.80)
                self.fm = QFontMetrics(self.font)
                                    
            height = self.fm.boundingRect(
                0,
                0,
                option.rect.width() - 75,
                800,
                int(Qt.AlignTop) | int(Qt.AlignLeft)
                    | int(Qt.TextWordWrap),
                tweet,
                ).height() + 40

            if self.show_replyto:
                reply_name = index.data(role=REPLYTOSCREENNAMEROLE)
                reply_text = index.data(role=REPLYTEXTROLE)
                if reply_name and reply_text:

                    # One time is enought sizeHint need to be fast

                    reply = 'In reply to @' + reply_name + ' : ' \
                        + reply_text
                    if not self.minifm:
                        if not self.miniFont:
                            self.miniFont = QFont(option.font)
                            self.miniFont.setPointSizeF(option.font.pointSizeF()
                                    * 0.60)
                        self.minifm = QFontMetrics(self.miniFont)
                    height += self.minifm.boundingRect(
                        0,
                        0,
                        option.rect.width() - 75,
                        800,
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap),
                        reply,
                        ).height()
                elif reply_name:
                    reply = 'In reply to @' + reply_name
                    if not self.minifm:
                        if not self.miniFont:
                            self.miniFont = QFont(option.font)
                            self.miniFont.setPointSizeF(option.font.pointSizeF()
                                    * 0.60)
                        self.minifm = QFontMetrics(self.miniFont)
                    height += self.minifm.boundingRect(
                        0,
                        0,
                        option.rect.width() - 75,
                        800,
                        int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap),
                        reply,
                        ).height()

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

#        if not USE_PYSIDE:
        (x1, y1, x2, y2) = option.rect.getCoords()
#        else:
            #Work arround Pyside bug #544
#            y1 = option.rect.y()
#            y2 = y1 + option.rect.height()
#            x1 = option.rect.x()
#            x2 = x1 + option.rect.width()
#
        # Ugly hack ?
        if y1 < 0 and y2 < 0:
            return

        if not self.fm:
            self.font = QFont(option.font)
            self.font.setPointSizeF(option.font.pointSizeF()
                                * 0.80)
            self.fm = QFontMetrics(self.font)

        model = index.model()
        tweet = index.data(Qt.DisplayRole)
        is_me = index.data(ISMEROLE)

        # Instantiate font only one time !

        if not self.normFont:
            self.normFont = QFont(self.font)
            self.miniFont = QFont(option.font)
            self.miniFont.setPointSizeF(option.font.pointSizeF() * 0.60)

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

        if self.show_avatar:
            icon = index.data(Qt.DecorationRole)
            if icon != None:
                if is_me:
                    painter.drawPixmap(x2 -60, y1 + 10, 50, 50, icon)
                else:
                    painter.drawPixmap(x1 + 10, y1 + 10, 50, 50, icon)

        # Draw tweet
        painter.setFont(self.normFont)
        painter.setPen(self.text_color)
        if is_me:
            new_rect = \
                painter.drawText(option.rect.adjusted(4, 5, -70, 0), int(Qt.AlignTop)
                                 | int(Qt.AlignRight)
                                 | int(Qt.TextWordWrap), tweet)
        else:
            new_rect = \
                painter.drawText(option.rect.adjusted(int(self.show_avatar)
                                 * 70, 5, -4, 0), int(Qt.AlignTop)
                                 | int(Qt.AlignLeft)
                                 | int(Qt.TextWordWrap), tweet)

        # Draw Timeline

        if self.show_timestamp:
            time = index.data(role=TIMESTAMPROLE)
            painter.setFont(self.miniFont)
            painter.setPen(self.time_color)
            if is_me:
                painter.drawText(option.rect.adjusted(4, 10, -80, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignRight),
                                 time)
            else:
                painter.drawText(option.rect.adjusted(70, 10, -10, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignRight),
                                 time)

        # Draw screenname

        if self.show_screenname:
            screenname = index.data(SCREENNAMEROLE)
            retweet_of = index.data(RETWEETOFROLE)
            if retweet_of:
                screenname = '%s : Retweet of %s' % (screenname, retweet_of.user.screen_name)
            painter.setFont(self.miniFont)
            painter.setPen(self.user_color)
            if is_me:
                painter.drawText(option.rect.adjusted(4, 10, -70, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignLeft),
                                 screenname)
            else:
                painter.drawText(option.rect.adjusted(70, 10, -10, -9),
                                 int(Qt.AlignBottom) | int(Qt.AlignLeft),
                                 screenname)

        # Draw reply

        if self.show_replyto:
            reply_name = index.data(role=REPLYTOSCREENNAMEROLE)
            reply_text = index.data(role=REPLYTEXTROLE)
            if reply_name and reply_text:
                reply = 'In reply to ' + reply_name + ' : ' \
                    + reply_text
                painter.setFont(self.miniFont)
                painter.setPen(self.replyto_color)
                if is_me:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(4, new_rect.height() + 5, -70, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)
                else:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(int(self.show_avatar)
                            * 70, new_rect.height() + 5, -4, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)
            elif reply_name:
                reply = 'In reply to ' + reply_name
                painter.setFont(self.miniFont)
                painter.setPen(self.replyto_color)
                if is_me:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(4, new_rect.height() + 5, -70, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)
                else:
                    new_rect = \
                        painter.drawText(option.rect.adjusted(int(self.show_avatar)
                            * 70, new_rect.height() + 5, -4, 0),
                            int(Qt.AlignTop) | int(Qt.AlignLeft)
                            | int(Qt.TextWordWrap), reply)

        # Draw line

        painter.setPen(self.separator_color)
        painter.drawLine(x1, y2, x2, y2)

        painter.restore()


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
        if event.key() not in (Qt.Key_Up, Qt.Key_Down):
            self.parent().switch_tb_edit()
            self.parent().tb_text.setFocus()
            self.parent().tb_text.keyPressEvent(event)
        else:
            QListView.keyPressEvent(self, event)

    def refreshCustomDelegate(self):
        settings = QSettings("Khertan Software", "Khweeteur")
        theme = settings.value('theme')
        if theme == KhweeteurPref.WHITETHEME:
            self.custom_delegate = WhiteCustomDelegate(self)
        elif theme == KhweeteurPref.DEFAULTTHEME:
            self.custom_delegate = DefaultCustomDelegate(self)
        elif theme == KhweeteurPref.COOLWHITETHEME:
            self.custom_delegate = CoolWhiteCustomDelegate(self)
        elif theme == KhweeteurPref.COOLGRAYTHEME:
            self.custom_delegate = CoolGrayCustomDelegate(self)
        elif theme == KhweeteurPref.MINITHEME:
            self.custom_delegate = MiniDefaultCustomDelegate(self)
        else:
            self.custom_delegate = DefaultCustomDelegate(self)
        self.setItemDelegate(self.custom_delegate)
