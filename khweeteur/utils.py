#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Beno�t HERVIER
# Licenced under GPLv3

import pickle
import os.path
import shutil
import sys
import datetime

AVATAR_CACHE_FOLDER = os.path.join(os.path.expanduser("~"),  '.khweeteur', 'cache')
CACHE_PATH = os.path.join(os.path.expanduser("~"), '.khweeteur')
REPLY_PATH = os.path.join(CACHE_PATH,'replies')

#Close your eyes ... it s a secret !
KHWEETEUR_TWITTER_CONSUMER_KEY = 'uhgjkoA2lggG4Rh0ggUeQ'
KHWEETEUR_TWITTER_CONSUMER_SECRET = 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU'
KHWEETEUR_IDENTICA_CONSUMER_KEY = 'c7e86efd4cb951871200440ad1774413'
KHWEETEUR_IDENTICA_CONSUMER_SECRET = '236fa46bf3f65fabdb1fd34d63c26d28'
KHWEETEUR_STATUSNET_CONSUMER_KEY = '84e768bba2b6625f459a9a19f5d57bd1'
KHWEETEUR_STATUSNET_CONSUMER_SECRET = 'fbc51241e2ab12e526f89c26c6ca5837'
#....

SCREENNAMEROLE = 20
REPLYTOSCREENNAMEROLE = 21
REPLYTEXTROLE = 22
IDROLE = 23

def write_report(error):
    '''Function to write error to a report file'''
    try:
        shutil.makedirs(CACHE_PATH)
    except:
        pass
        
    filename = os.path.join(CACHE_PATH, 'crash_report')
    output = open(filename, 'wb')
    pickle.dump(error, output)
    output.close()

def write_log(log):
    filename = os.path.join('/tmp/khweeteur_log')
    output = open(filename, 'a')
    output.write(str(datetime.datetime.now())+':'+str(log)+'\n')
    output.close()

#Here is the installation of the hook. Each time a untrapped/unmanaged exception will
#happen my_excepthook will be called.
def install_excepthook(version):
    '''Install an excepthook called at each unexcepted error'''
    __version__ = version
    
    def my_excepthook(exctype, value, tb):
        '''Method which replace the native excepthook'''
        #traceback give us all the errors information message like the method, file line ... everything like
        #we have in the python interpreter
        import traceback
        trace_s = ''.join(traceback.format_exception(exctype, value, tb))
        print 'Except hook called : %s' % (trace_s)
        formatted_text = "%s Version %s\nTrace : %s" % ('Khweeteur', __version__, trace_s)
        write_report(formatted_text)

    sys.excepthook = my_excepthook