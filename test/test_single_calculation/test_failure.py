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
from utils import wait_for_calc

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

from aiida.common.example_helpers import test_and_get_code  # noqa
from aiida.orm.data.parameter import ParameterData  # noqa


# ==============================================================================
if len(sys.argv) != 2:
    print("Usage: test_failure.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
code = test_and_get_code(codename, expected_code_type='cp2k')

print("Testing CP2K failure...")

# a broken CP2K input
params = {'GLOBAL': {'FOO_BAR_QUUX': 42}}

calc = code.new_calc()
calc.use_parameters(ParameterData(dict=params))
calc.set_max_wallclock_seconds(2*60)
calc.set_resources({"num_machines": 1})
calc.store_all()
calc.submit()
print("submitted calculation: PK=%s" % calc.pk)

wait_for_calc(calc, ensure_finished_ok=False)

if calc.has_failed():
    print("CP2K failure correctly recognized")
else:
    print("ERROR!")
    print("CP2K failure was not recognized")
    sys.exit(3)

sys.exit(0)
# EOF
