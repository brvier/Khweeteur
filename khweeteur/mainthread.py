# Copyright (c) 2011 Neal H. Walfield <neal@walfield.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import threading
import traceback
import logging
from functools import wraps

_run_in_main_thread = None
_main_thread = None

def init(run_in_main_thread=None):
    """
    run_in_main_thread is a function that takes a single argument, a
    callable and returns False.  run_in_main_thread should run the
    function in the main thread.

    If you are using glib, gobject.idle_add (the default) is
    sufficient.  (gobject.idle_add is thread-safe.)
    """
    if run_in_main_thread is None:
        import gobject
        run_in_main_thread = gobject.idle_add

    global _run_in_main_thread
    assert _run_in_main_thread is None
    _run_in_main_thread = run_in_main_thread

    global _main_thread
    _main_thread = threading.currentThread ()

def execute(func, *args, **kwargs):
    """
    Execute FUNC in the main thread.

    If kwargs['async'] exists and is True, the function is executed
    asynchronously (i.e., the thread does not wait for the function to
    return in which case the function's return value is discarded).
    Otherwise, this function waits until the function is executed and
    returns its return value.
    """
    async = False
    try:
        async = kwargs['async']
        del kwargs['async']
    except KeyError:
        pass

    if threading.currentThread() == _main_thread:
        if async:
            try:
                func (*args, **kwargs)
            except:
                logging.debug("mainthread.execute: Executing %s: %s"
                              % (func, traceback.format_exc ()))
            return
        else:
            return func (*args, **kwargs)

    assert _run_in_main_thread is not None, \
        "You can't call this function from a non-main thread until you've called init()"

    if not async:
        cond = threading.Condition()

    result = {}
    result['done'] = False

    def doit():
        @wraps(func)
        def it():
            # Execute the function.
            assert threading.currentThread() == _main_thread, \
                ("function executed in %s, not %s"
                 % (threading.currentThread(), _main_thread))


            try:
                result['result'] = func(*args, **kwargs)
            except:
                logging.debug("mainthread.execute: Executing %s: %s"
                              % (func, traceback.format_exc ()))

            if not async:
                cond.acquire ()
            result['done'] = True
            if not async:
                cond.notify ()
                cond.release ()

            return False
        return it

    if not async:
        cond.acquire ()
    _run_in_main_thread (doit())

    if async:
        # Don't wait for the method to complete execution.
        return

    # Wait for the result to become available.
    while not result['done']:
        cond.wait ()

    return result.get ('result', None)

def mainthread(async=None):
    """
    A decorator for ensuring that the function runs in the main
    thread.
    """
    def real_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if async is not None:
                kwargs['async'] = async
            return execute (f, *args, **kwargs)
        return wrapper
    return real_decorator

if __name__ == "__main__":
    import sys
    import gobject

    init()

    def in_main_thread(test_num):
        assert threading.currentThread() == _main_thread, \
            "Test %d failed" % (test_num,)
        return test_num

    mainloop = gobject.MainLoop()
    gobject.threads_init()

    assert execute (in_main_thread, 1) == 1
    assert (execute (in_main_thread, 2, async=False) == 2)
    execute (in_main_thread, 3, async=True)

    class T(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)

        def run(self):
            assert threading.currentThread() != _main_thread

            assert execute (in_main_thread, 4) == 4
            assert (execute (in_main_thread, 5, async=False) == 5)
            execute (in_main_thread, 6, async=True)
            execute (mainloop.quit, async=False)

    def start_thread():
        t = T()
        t.start()
        return False

    gobject.idle_add (start_thread)
    mainloop.run()
