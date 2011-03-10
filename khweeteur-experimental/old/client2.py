#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2010 Benoît HERVIER
# Licenced under GPLv3

import Pyro.core
import time

Pyro.core.initClient()

URI='PYROLOC://127.0.0.1:7768/home_timeline'
home_timeline=Pyro.core.getProxyForURI(URI)

print home_timeline.update2()
