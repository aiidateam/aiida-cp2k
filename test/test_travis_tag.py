#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from __future__ import print_function

from __future__ import absolute_import
import os
import sys
import json

a = os.getenv("TRAVIS_TAG")
b = "v" + json.load(open("setup.json"))['version']

if not a:
    print("TRAVIS_TAG not set")

elif a != b:
    print("ERROR!")
    print("TRAVIS_TAG and version are not consistend: '%s' vs '%s'" % (a, b))
    sys.exit(3)

sys.exit(0)

# EOF
