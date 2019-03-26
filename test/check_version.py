# -*- coding: utf-8 -*-
# pylint: disable=C0103
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Check versions"""
from __future__ import print_function
from __future__ import absolute_import

import sys
import json
import aiida_cp2k

a = aiida_cp2k.__version__
with open("../setup.json") as fhandle:
    b = json.load(fhandle)['version']

if a != b:
    print("ERROR: Versions in aiida_cp2k/__init__.py and setup.json are inconsistent: '%s' vs '%s'" % (a, b))
    sys.exit(3)
