#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

'''A Twitter client made with Python and Qt'''

from qwidget_gui import Khweeteur

if __name__ == '__main__':
    from subprocess import Popen
    Popen(['/usr/bin/python',os.path.join(os.path.dirname(__file__),'daemon.py'),'start'])
    app = Khweeteur()    
    app.exec_()
