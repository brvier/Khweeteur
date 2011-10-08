# Copyright (c) 2011 Neal H. Walfield
#
# This software is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from PySide.QtCore import QTimer
from functools import wraps
import time
import threading
import traceback
import logging
from mainthread import mainthread
from settings import accounts, settings_db

# Don't fail if the Woodchuck modules are not available.  Just disable
# Woodchuck's functionality.

# Whether we imported the woodchuck modules successfully.
woodchuck_imported = True
try:
    import pywoodchuck
    from pywoodchuck import PyWoodchuck
    from pywoodchuck import woodchuck
except ImportError, e:
    import traceback
    logging.exception(
        "Unable to load Woodchuck modules: disabling Woodchuck support: %s"
        % str(e))
    print("Unable to load Woodchuck modules: disabling Woodchuck support: %s"
          % traceback.format_exc())

    woodchuck_imported = False

    # Users of this module do: from wc import woodchuck
    # Make sure that doesn't gratutiously fail.
    woodchuck = None

    class PyWoodchuck(object):
        def __init__(self, *args, **kwargs):
            pass

        def available(self):
            return False

def refresh_interval():
    """Return the refresh interval (in seconds)."""
    settings = settings_db()
    if not settings.contains('refresh_interval'):
        return 600
    else:
        return int(settings.value('refresh_interval')) * 60

def stream_id_build(account, feed):
    return account.uuid + '::' + feed

def stream_id_split(id):
    try:
        (account_id, feed) = (id.split('::', 1) + [None,])[:2]
    except (TypeError, ValueError):
        return (None, None)

    for account in accounts():
        if account.uuid == account_id:
            break
    else:
        return (None, None)

    return (account, feed)

def coroutine(func):
    def wrapper(*args, **kwargs):
        def doit(generator):
            def execute():
                try:
                    generator.next()
                    QTimer.singleShot(0, execute)
                except StopIteration:
                    return
            execute()

        generator = func(*args, **kwargs)
        doit(generator)
    return wrapper

class mywoodchuck(PyWoodchuck):
    """
    stream_update is a function that is called when a stream should be
    updated.  It is passed two arguments: the account (a
    settings.Account instance) and the feed (a string) to update.

    object_transfer is a function that is called when an object should
    be transferred.  It is passed three arguments: the account (a
    settings.Account instance), the feed (a string) and the tweet
    identifier (a string).

    If stream_update is None, then no callbacks will be requested.
    """
    def __init__(self, stream_update, object_transfer):
        if stream_update is None:
            # Disable upcalls.
            request_feedback = False
        else:
            request_feedback = True

        PyWoodchuck.__init__(self, "Khweeteur", "net.khertan.khweeteur.daemon",
                             request_feedback=request_feedback)

        self.stream_update = stream_update
        self.object_transfer = object_transfer

    def stream_unregister(self, stream):
        try:
            logging.debug(
                "Unregistering stream %s(%s)"
                % (stream.human_readable_name, stream.identifier))
            del self[stream.identifier]
        except (KeyError, woodchuck.Error), exception:
            logging.exception(
                "Unregistering stream %s(%s): %s"
                % (stream.human_readable_name, stream.identifier,
                   str(exception)))

    # Woodchuck upcalls.
    def stream_update_cb(self, stream, *args, **kwargs):
        logging.debug("stream update called on %s (%s)"
                    % (stream.human_readable_name, stream.identifier,))

        account, feed = stream_id_split(stream.identifier)
        if account is None:
            self.stream_unregister(stream)
            return

        self.stream_update(account, feed)

    def object_transfer_cb(self, stream, object,
                           version, filename, quality, *args, **kwargs):
        logging.debug("object transfer called on %s (%s) in stream %s (%s)"
                    % (object.human_readable_name, object.identifier,
                       stream.human_readable_name, stream.identifier))

        if stream.identifier == 'topost':
            account = None
            feed = 'topost'
        else:
            account, feed = stream_id_split(stream.identifier)
            if account is None:
                del self[stream.identifier]
                return

        if not (account is None and feed == 'topost'):
            # object_transfer should only be called on topost
            logging.debug(
                "object_transfer_cb called on feed other than topost (%s)!"
                % (stream.identifier))
            try:
                self[stream.identifier][object.identifier].dont_transfer = True
            except Exception:
                logger.exception(
                    "Setting DontTransfer on %s.%s: %s"
                    % (stream.identifier, object.identifier, str(e)))
            return

        self.object_transfer(account, feed, object.identifier)

    @coroutine
    def synchronize_config(self):
        # Called to synchronize Woodchuck's configuration with our
        # configuration.
    
        # The list of known streams.
        streams = self.streams_list()
        stream_ids = [s.identifier for s in streams]
    
        freshness = refresh_interval()
    
        # Register any unknown streams.  Remove known streams from
        # STREAMS_IDS.
        def check(stream_id, name, freshness):
            if stream_id not in stream_ids:
                logging.debug(
                    "Registering previously unknown feed: %s (%s)"
                    % (name, stream_id))
                self.stream_register(stream_identifier=stream_id,
                                     human_readable_name=name,
                                     freshness=freshness)
            else:
                logging.debug(
                    "%s (%s) already registered"
                    % (name, stream_id))

                # The account name can change: it's the user's stream
                # name.
                stream_ids.remove(stream_id)
                self[stream_id].human_readable_name = name
                self[stream_id].freshness = freshness
    
        for account in accounts():
            for feed in account.feeds():
                check(stream_id_build(account, feed),
                      account.name + ': ' + feed,
                      freshness=freshness)
            yield

        # The outbox.
        check('topost', 'outbox', woodchuck.never_updated)
    
        # Unregister any streams that are no longer subscribed to.
        for stream_id in stream_ids:
            logging.debug("%s no longer registered." % (stream_id,))
            self.stream_unregister(self[stream_id])
            yield

_w = None

def wc(stream_update=None, object_transfer=None):
    """
    Connect to the woodchuck server and initialize any state.

    stream_update is a function that is passed two arguments: an
    account identifier and the name of the stream to update (e.g.,
    'HomeTimeline').

    object_transfer is a function that is passed three arguments: an
    account identifier, a name of the stream and the post to transfer.

    If channel_update and episode_download are None, then Woodchuck
    upcalls will be disabled.
    """
    global _w
    if _w is not None:
        return _w

    _w = mywoodchuck(stream_update, object_transfer)

    if not _w.available():
        logging.info(
            "Woodchuck support disabled: unable to contact Woodchuck server.")
        print "Woodchuck support disabled: unable to contact Woodchuck server."
        return

    logging.info("Woodchuck appears to be available.")

    if stream_update is not None:
        QTimer.singleShot(0, _w.synchronize_config)

    return _w
