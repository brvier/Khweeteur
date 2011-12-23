#!/usr/bin/python
# -*- coding: utf-8 -*-

#
# Copyright (c) 2010 Benoît HERVIER
# Copyright (c) 2011 Neal H. Walfield
# Licenced under GPLv3

'''A simple Twitter client made with pyqt4 : QModel'''

from __future__ import with_statement

import time
import cPickle as pickle
#import glob
import os
import logging
import weakref
import atexit

SCREENNAMEROLE = 20
REPLYTOSCREENNAMEROLE = 21
REPLYTEXTROLE = 22
REPLYIDROLE = 25
IDROLE = 23
ORIGINROLE = 24
TIMESTAMPROLE = 26
RETWEETOFROLE = 27
ISMEROLE = 28
PROTECTEDROLE = 28
USERIDROLE = 29
ISNEWROLE = 30
TIMESTAMPABSROLE = 31

from PySide.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, \
    QSettings, QTimer
from PySide.QtGui import QPixmap
import twitter #Not really unused. Avoid pickle to do it each time

# Data that we may cache.  The most important data for caching is the
# data needed for sizing rows.  See list_view for the required
# columns.
DATA_CACHE = (IDROLE, Qt.DisplayRole, REPLYTEXTROLE, TIMESTAMPABSROLE)

pyqtSignal = Signal

class KhweetsModel(QAbstractListModel):

    """ListModel : A simple list : Start_At,TweetId, Users Screen_name, Tweet Text, Profile Image"""

    dataChanged = pyqtSignal(QModelIndex, QModelIndex)

    _model_instances = None

    def __init__(self):
        if self._model_instances is None:
            # This is the first time an instance of this class is
            # being instantiated.  Register the atexit handler to
            # ensure the state get saved on exit.
            self.__class__._model_instances = []
            atexit.register(KhweetsModel.save_all_config, lazily=False)

        self._model_instances.append(weakref.ref(self))

        QAbstractListModel.__init__(self)

        # Cache the passed data list as a class member.

        # Status is a dict mapping uids to status
        self.statuses = {}
        # UIDs is an array of the UIDs in the current data set.
        self.uids = []

        self.avatars = {}
        self.now = time.time()
        self.nothing_really_loaded = True
        self.call = None
        self.max_created_at = None
        self.new_message_horizon = self.now

        self.khweets_limit = 10000

        try:
            self.default_avatar = QPixmap('/opt/usr/share/icons/hicolor/48x48/hildon/general_default_avatar.png')
        except:
            self.default_avatar = None

        self.data_cache = {}

    def __del__(self):
        self.save_config(lazily=False)

        # Remove our weak reference from self._model_instance (and any
        # others that might be dead...).
        model_instances = []
        for ref in self._model_instances:
            instance = ref()
            if instance == self or instance is None:
                pass
            else:
                model_instances.append(ref)

        # Don't create a new object: _model_instances should remain a
        # class attribute; it should not become an instance attribute.
        self._model_instances[:] = model_instances

    @classmethod
    def save_all_config(cls, lazily=True):
        logging.debug("%s.save_all_config(lazily=%s) called",
                      cls.__name__, str(lazily))
        for ref in cls._model_instances:
            instance = ref()
            if instance is not None:
                instance.save_config(lazily)

    def save_config(self, lazily=True):
        logging.debug("%s.save_config(%s) (nothing really loaded: %s)",
                      self.call, lazily, self.nothing_really_loaded)

        if not self.nothing_really_loaded:
            settings = QSettings('Khertan Software', 'Khweeteur')
            settings.setValue(
                self.call + '-new-message-horizon', self.max_created_at)

            self.save_data_cache(lazily)

    def reset_new_message_horizon(self):
        self.new_message_horizon = time.time()
        # Tell all views to reload data.
        self.reset()

    def setLimit(self, limit):
        self.khweets_limit = limit

    def getCacheFolder(self):
        return os.path.join(os.path.expanduser('~'), '.khweeteur', 'cache',
                            os.path.normcase(unicode(self.call.replace('/', '_'
                            ))).encode('UTF-8'))

    def rowCount(self, parent=QModelIndex()):
        return min(len(self.uids), self.khweets_limit)

    def refreshTimestamp(self):
        self.now = time.time()
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(self.rowCount(), 0))

    def destroyStatus(self, index):
        index = index.row()
        self.uids.pop(index)
        self.dataChanged.emit(self.createIndex(index, 0),
                              self.createIndex(self.rowCount(), 0))


    def save_data_cache(self, lazily=True):
        filename = self.getCacheFolder() + '-data-cache'

        def closure(data_cache):
            def doit():
                with open(filename, 'wb') as fhandle:
                    pickle.dump(data_cache, fhandle,
                                pickle.HIGHEST_PROTOCOL)
            return doit

        func = closure(self.data_cache)
        if lazily:
            QTimer.singleShot(0, func)
        else:
            func()

    def load(self, call, limit=None):
        """
        Load a stream.

        call is the stream to load (see
        retriever.py:KhweeteurRefreshWorker for a description of the
        possible values).

        limit is the maximum number of messages to show.  If the
        number of messages exceeds limit, then selects the newest
        messages (in terms of creation time, not download time).

        Returns whether the load loaded a new data set (True) or was
        just a reload (False).
        """
        self.now = time.time()

        # print "model.load(%s -> %s)" % (self.call, call)

        # new_message_horizon is the point in time that separates read
        # messages from new messages.  The messages' creation time is
        # used.
        settings = QSettings('Khertan Software', 'Khweeteur')
        if self.call != call:
            # It's not a reload.  Save the setting for the old stream
            # and load the setting for the new one.
            reloading = True

            self.save_config()

            try:
                self.new_message_horizon = int(
                    settings.value(call + '-new-message-horizon', 0))
            except (ValueError, TypeError) :
                self.new_message_horizon = self.now
                
            # There might be some useful avatars, but figuring out
            # which they are requires loading all of the status
            # updates.
            self.avatars = {}
        else:
            reloading = False

        self.nothing_really_loaded = False

        self.call = call

        self.avatar_path = os.path.join(os.path.expanduser('~'), '.khweeteur',
                                       'avatars')

        folder = self.getCacheFolder()
        try:
            self.uids = os.listdir(folder)
        except (OSError, IOError), e: #Trap only OSError
            if e.errno != errno.ENOENT:
	            logging.exception('listdir(%s): %s' % (folder, str(e)))
            self.uids = []

        # Drop any statuses from the cache that we no longer need.
        self.statuses = dict([(k, v) for k, v in self.statuses.items()
                              if k in self.uids])

        if reloading:
            try:
                filename = self.getCacheFolder() + '-data-cache'
                with open(filename, 'rb') as fhandle:
                    self.data_cache = pickle.load(fhandle)
            except IOError, e:
                if e.errno != errno.ENOENT:
                    logging.exception('pickle.load(%s): %s' % (filename, str(e)))
                self.data_cache = {}


        # Sort AFTER we load the cache (otherwise, what's the point of
        # the cache).
        self.uids.sort(
            key=lambda uid: [self.data_by_uid(uid, TIMESTAMPABSROLE),
                             uid],
            reverse=True)
        if limit:
            self.uids = self.uids[:limit]

        # Tell all views to reload all data.
        self.reset()

        return reloading

    def get_status(self, uid):
        # Look up the status update.
        try:
            return self.statuses[uid]
        except KeyError:
            filename = os.path.join(self.getCacheFolder(), str(uid))
            try:
                pkl_file = open(filename, 'rb')
            except (OSError, IOError) : #Python syntax error a list of type of error are a tuple ;) else it s name the exception. #Fix Bug #976
                # Error accessing the file.  Likely, the back end
                # purged the file.  Just return None.
                # self.data_by_uid does the right thing.
                return None
            with pkl_file:
                try:
                    status = pickle.load(pkl_file)
                except EOFError:
                    # The file disappeared.  This can happen if the
                    # daemon cleans old files, but has not yet
                    # informed us that an update occured.
                    return None
                self.statuses[uid] = status
            # print "Loaded %s: %s" % (uid, status.text[0:30])
            return status

    def data(self, index, role=Qt.DisplayRole):
        if not isinstance(index, int):
            index = index.row()

        uid = self.uids[index]

        return self.data_by_uid(uid, role)

    def data_by_uid(self, uid, role):
        if role in DATA_CACHE:
            # Check if the value is in our cache.
            cache_entry = self.data_cache.get(uid, None)
            if cache_entry is not None and role in cache_entry:
                ok = False
                # Make sure that the cached entry is reasonably
                # consistent.
                if (# Status entries that can change: last_update.
                    # Everything else, once created, is static.
                    not uid.endswith('last_update')
                    or ('validated' in cache_entry
                        and cache_entry['validated'] >= time.time() - 10)):
                    # The file is immutable or we validated the
                    # contents recently.
                    ok = True
                else:
                    filename = os.path.join(self.getCacheFolder(), str(uid))
                    try:
                        mtime = os.stat(filename).st_mtime
                    except OSError:
                        # The file likely doesn't exist any more.
                        # Note that we don't use None because:
                        #
                        #   None == None => True
                        #
                        # If the cache entry doesn't have an mtime
                        # attribute, we would return this.
                        mtime = -1

                    if mtime == cache_entry.get('mtime', None):
                        ok = True
                        cache_entry['validated'] = time.time()
                    else:
                        # The file changed!
                        del self.data_cache[uid]
                        try:
                            del self.statuses[uid]
                        except KeyError:
                            pass
                if ok:
                    return cache_entry[role]

        status = None
        value = None
        if role == Qt.DisplayRole:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                if status.truncated:
                    value = status.retweeted_status.text
                else:
                    value = status.text
            except:
                value = status.text

            # Make sure that the text is either None or some sort of
            # string.
            if value is not None and not isinstance(value, basestring):
                value = unicode(value, errors='replace')

        elif role == SCREENNAMEROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                value = status.user.screen_name
            except:
                value = status.sender_screen_name
        elif role == IDROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            value = status.id
        elif role == REPLYIDROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                value = status.in_reply_to_status_id
            except:
                value = None
        elif role == REPLYTOSCREENNAMEROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                value = status.in_reply_to_screen_name
            except AttributeError:
                value = None
        elif role == REPLYTEXTROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            value = status.in_reply_to_status_text
        elif role == ORIGINROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                value = status.base_url
            except AttributeError: #Fix for #973
                value = None
        elif role == RETWEETOFROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                value = status.retweeted_status
            except AttributeError:
                value = None
        elif role == ISMEROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                value = status.is_me
            except AttributeError:
                value = False
        elif role == TIMESTAMPROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            value = status.GetRelativeCreatedAt(self.now)
        elif role == TIMESTAMPABSROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            value = status.GetCreatedAtInSeconds()
        elif role == ISNEWROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                created_at = int(status.GetCreatedAtInSeconds())
            except ValueError:
                created_at = 0
            self.max_created_at = max(self.max_created_at, created_at)

            value = created_at > self.new_message_horizon
        elif role == PROTECTEDROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            value = status.user.protected
        elif role == USERIDROLE:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                value = status.user.id
            except AttributeError:
                try: #Fix Bug #970
                    value = status.sender_id
                except AttributeError:
                    value = None
        elif role == Qt.DecorationRole:
            status = self.get_status(uid)
            if status is None:
                return None
            try:
                profile_image_url = status.user.profile_image_url
            except AttributeError:
                value = self.default_avatar
            else:
                try:
                    value = self.avatars[profile_image_url]
                except KeyError:
                    profile_image = os.path.join(
                        self.avatar_path,
                        os.path.basename(profile_image_url.replace('/', '_')))
                    try:
                        value = QPixmap(
                            os.path.splitext(profile_image)[0] + '.png', 'PNG')
                    except:
                        value = self.default_avatar
                    else:
                        self.avatars[profile_image_url] = value
        else:
            return None

        # If the data is cachable, cache it.
        if role in DATA_CACHE:
            cache_entry = self.data_cache.get(uid, None)
            if cache_entry is None:
                cache_entry = {}
                self.data_cache[uid] = cache_entry

                filename = os.path.join(self.getCacheFolder(), str(uid))
                cache_entry['mtime'] = os.stat(filename).st_mtime
                cache_entry['validated'] = int(time.time())
                
            cache_entry[role] = value

        return value

    def wantsUpdate(self):
        self.layoutChanged.emit()


