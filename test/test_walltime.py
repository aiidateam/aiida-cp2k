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

import sys
import ase.build
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
    print("Usage: test_walltime.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
code = test_and_get_code(codename, expected_code_type='cp2k')

print("Testing CP2K walltime exceeded...")

# calc object
calc = code.new_calc()

# structure
atoms = ase.build.molecule('H2')
atoms.center(vacuum=2.0)
structure = StructureData(ase=atoms)
calc.use_structure(structure)

# parameters
parameters = ParameterData(dict={
    'GLOBAL': {
        'RUN_TYPE': 'GEO_OPT',
        'WALLTIME': '00:00:03',  # 3 seconds
    },
    'MOTION': {
        'GEO_OPT': {
            'MAX_FORCE': 1e-20,  # impossible to reach
            'MAX_ITER': 100000,  # run forever
        },
    },
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

# check walltime exceeded
assert calc.res.exceeded_walltime is True
assert calc.res.energy is not None
assert calc.out.output_structure is not None
print("OK, walltime exceeded as expected")

sys.exit(0)
# EOF
