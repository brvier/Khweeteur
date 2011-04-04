#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

PYRO_PORT=9123

import Pyro.core
import time
import uuid
from PySide.QtCore import QSettings
import twitter

class Accounts(Pyro.core.ObjBase):
    def __init__(self):
        Pyro.core.ObjBase.__init__(self)
        self.accounts = {}
        
        self.daemon_refresh_interval = 10 #Min != Refresh interval GUI

    def load_settings(self):
	settings = QSettings()
	uids = settings.value('accounts')
	if type(uids) in (str,unicode):
	    uids = [uids,]
	elif type(uids) != dict:
	    uids = {}
	for uid in uids:
	    acc = Account(uid)
	    acc.load_settings()
	    self.accounts[uid]=acc
	return self.accounts

        value = settings.value('daemon_refresh_interval')
        if not value:
            self.daemon_refresh_interval = 10        
        else:
            self.daemon_refresh_interval = int(value)

    def create_account(self,base_url, token_key, token_secret):
        account = Account(uid=uuid.uuid4())
        account.base_url = base_url
        account.token_key= token_key
        account.token_secret = token_secret
        account.save_settings()
	settings = QSettings()
	self.load_settings()
	self.accounts[account.uid]=account
	settings.setValue('accounts',[acc.uid for acc in self.accounts])	         

    def del_account(self,uid):
        if uid in self.accounts:
            self.accounts[uid].del_account_()
            del account[uid]
         
class Account(Pyro.core.ObjBase):
    def __init__(self, uid=None):
        Pyro.core.ObjBase.__init__(self)
        self.api = None
        self.base_url = None
        self.token_key = None
        self.token_secret = None
        self.uid = uid

    def connect(self):
        if 'twitter' in self.base_url:
            consumer_key = 'uhgjkoA2lggG4Rh0ggUeQ'
            consumer_secret = 'lbKAvvBiyTlFsJfb755t3y1LVwB0RaoMoDwLD14VvU'
        else:
            consumer_key = 'c7e86efd4cb951871200440ad1774413'
            consumer_secret = '236fa46bf3f65fabdb1fd34d63c26d28'
            
        self.api = twitter.Api(username=consumer_key,
                        password=consumer_secret,
                        access_token_key=self.token_key,
                        access_token_secret=self.token_secret)       
        self.api.SetUserAgent('Khweeteur')
        
    def load_settings(self):
	if self.uid:
	    settings = QSettings()
	    self.base_url = settings.value('%s_base_url' % self.uid)
	    self.token_key = settings.value('%s_token_key' % self.uid)
	    self.token_secret = settings.value('%s_token_secret' % self.uid)

    def save_settings(self):
	if self.uid:
	    settings = QSettings()
	    settings.setValue('%s_base_url' % self.uid, self.base_url)
	    settings.setValue('%s_token_key' % self.uid, self.token_key)
	    settings.setValue('%s_token_secret' % self.uid, self.token_secret)

    def del_account(self):
        if self.uid:
            settings = QSettings()
            settings.remove('%s_base_url' % self.uid)
            settings.remove('%s_token_key' % self.uid)
            settings.remove('%s_token_secret' % self.uid)


class Timeline(Pyro.core.ObjBase):
    def __init__(self):
	Pyro.core.ObjBase.__init__(self)
	self.tids = []
    def update(self):
	return []
	
class HomeTimeline(Timeline):
    def __init__(self):
	Timeline.__init__(self)
    def update(self):
	return []
	
class DMTimeline(Timeline):
    def __init__(self):
	Timeline.__init__(self)
    def update(self):
	return []
	
class MentionTimeline(Timeline):
    def __init__(self):
	Timeline.__init__(self)
    def update(self):
	return []
	
class SearchTimeline(Timeline):
    def __init__(self, search_terms):
	Timeline.__init__(self)
	self.search_terms = search_terms
    def update(self):
	return []