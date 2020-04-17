# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Check travis tag"""

import os
import sys
import json

a = os.getenv("TRAVIS_TAG")
with open("setup.json") as fhandle:
    b = "v{version}".format(**json.load(fhandle))

if not a:
    print("TRAVIS_TAG not set")

elif a != b:
    print("ERROR: TRAVIS_TAG and version are inconsistent: '%s' vs '%s'" % (a, b))
    sys.exit(3)
