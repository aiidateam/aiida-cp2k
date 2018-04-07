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
from aiida.orm.data.structure import StructureData  # noqa
from aiida.orm.data.parameter import ParameterData  # noqa
from aiida.orm.data.singlefile import SinglefileData  # noqa


# ==============================================================================
if len(sys.argv) != 2:
    print("Usage: test_no_struct.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
code = test_and_get_code(codename, expected_code_type='cp2k')

print("Testing CP2K ENERGY on H2 (DFT) without StructureData...")

# calc object
calc = code.new_calc()

# parameters
parameters = ParameterData(dict={
    'FORCE_EVAL': {
        'METHOD': 'Quickstep',
        'DFT': {
            'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
            'QS': {
                'EPS_DEFAULT': 1.0e-12,
                'WF_INTERPOLATION': 'ps',
                'EXTRAPOLATION_ORDER': 3,
            },
            'MGRID': {
                'NGRIDS': 4,
                'CUTOFF': 280,
                'REL_CUTOFF': 30,
            },
            'XC': {
                'XC_FUNCTIONAL': {
                    '_': 'LDA',
                },
            },
            'POISSON': {
                'PERIODIC': 'none',
                'PSOLVER': 'MT',
            },
        },
        'SUBSYS': {
            # structure directly included in parameters
            'CELL': {'ABC': '4.0   4.0   4.75'},
            'COORD': {' ': ['H    2.0   2.0   2.737166',
                            'H    2.0   2.0   2.000000']},
            'KIND': [
                {'_': 'O', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                    'POTENTIAL': 'GTH-LDA-q6'},
                {'_': 'H', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                    'POTENTIAL': 'GTH-LDA-q1'},
            ],
        },
    }
})
calc.use_parameters(parameters)

# resources
calc.set_max_wallclock_seconds(3*60)  # 3 min
calc.set_resources({"num_machines": 1})

# store and submit
calc.store_all()
calc.submit()
print("submitted calculation: PK=%s" % calc.pk)

wait_for_calc(calc)

# check energy
expected_energy = -1.14005678487
if abs(calc.res.energy - expected_energy) < 1e-10:
    print("OK, energy has the expected value")
else:
    print("ERROR!")
    print("Expected energy value: {}".format(expected_energy))
    print("Actual energy value: {}".format(calc.res.energy))
    sys.exit(3)

sys.exit(0)

# EOF
