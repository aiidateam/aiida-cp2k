#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
from __future__ import print_function

import sys

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

from aiida.orm import Dict  # noqa
from aiida.common import NotExistent
from aiida.engine import run
from aiida_cp2k.calculations import Cp2kCalculation
from aiida.common.exceptions import OutputParsingError

# ==============================================================================
if len(sys.argv) != 2:
    print("Usage: test_failure.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]

try:
    code = Code.get_from_string(codename)
except NotExistent:
    print ("The code '{}' does not exist".format(codename))
    sys.exit(1)

print("Testing CP2K failure...")

# a broken CP2K input
parameters = Dict(dict= {'GLOBAL': {'FOO_BAR_QUUX': 42}})
options = {
    "resources": {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    },
    "max_wallclock_seconds": 1 * 2 * 60,
}

print("Submitted calculation...")
inputs = {
        'parameters':parameters,
        'code': code,
        'metadata': {
            'options': options,
        }
}
try:
    run(Cp2kCalculation, **inputs)
    print("ERROR!")
    print("CP2K failure was not recognized")
    sys.exit(3)
except OutputParsingError:
    print("CP2K failure correctly recognized")

sys.exit(0)
# EOF
