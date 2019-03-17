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

a = json.load(open("../setup.json"))['version']
b = aiida_cp2k.__version__

if a != b:
    print("ERROR!")
    print("Versions are not consistent: '%s' vs '%s'" % (a, b))
    sys.exit(3)

sys.exit(0)

# EOF
