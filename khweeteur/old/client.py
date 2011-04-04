#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

import Pyro.core
import time
import objects

Pyro.core.initClient()

URI='PYROLOC://127.0.0.1:'+str(objects.PYRO_PORT)+'/Accounts'
accounts=Pyro.core.getProxyForURI(URI)

print accounts.load_settings()
