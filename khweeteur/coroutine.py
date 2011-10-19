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

