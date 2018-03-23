#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/cp2k/aiida-cp2k      #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################
from __future__ import print_function

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
