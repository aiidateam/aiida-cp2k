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
import os
import ase.build
from utils import wait_for_calc

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

from aiida.orm import load_node  # noqa
from aiida.orm.data.remote import RemoteData  # noqa
from aiida.common.example_helpers import test_and_get_code  # noqa
from aiida.orm.data.structure import StructureData  # noqa
from aiida.orm.data.parameter import ParameterData  # noqa
from aiida.orm.data.singlefile import SinglefileData  # noqa

# ==============================================================================
if len(sys.argv) != 2:
    print("Usage: test_restart.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
code = test_and_get_code(codename, expected_code_type='cp2k')

print("Testing CP2K restart...")

# structure
atoms = ase.build.molecule('H2O')
atoms.center(vacuum=2.0)
structure = StructureData(ase=atoms)

# Input file
force_eval = {
    'METHOD': 'Quickstep',
    'DFT': {
        'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
        'POTENTIAL_FILE_NAME': 'POTENTIAL',
        'RESTART_FILE_NAME': './parent_calc/aiida-RESTART.wfn',
        'QS': {
            'METHOD': 'GPW',
            'EXTRAPOLATION': 'ASPC',
            'EXTRAPOLATION_ORDER': '3',
            'EPS_DEFAULT': '1.0E-14',
        },
        'MGRID': {
            'CUTOFF': '%d' % (200),
            'NGRIDS': '5',
        },
        'SCF': {
            'MAX_SCF': '20',
            'SCF_GUESS': 'RESTART',
            'EPS_SCF': '1.0E-7',
            'OT': {
                'PRECONDITIONER': 'FULL_SINGLE_INVERSE',
                'MINIMIZER': 'CG',
            },
            'OUTER_SCF': {
                'MAX_SCF': '15',
                'EPS_SCF': '1.0E-7',
            },
            'PRINT': {
                'RESTART': {
                    'EACH': {
                        'QS_SCF': '0',
                        'GEO_OPT': '1',
                    },
                    'ADD_LAST': 'NUMERIC',
                    'FILENAME': 'RESTART'
                },
                'RESTART_HISTORY': {'_': 'OFF'}
            }
        },
        'XC': {
            'XC_FUNCTIONAL': {'_': 'PBE'},
        },
    },
    'SUBSYS': {
        'KIND': [
            {'_': 'O', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                'POTENTIAL': 'GTH-LDA-q6'},
            {'_': 'H', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                'POTENTIAL': 'GTH-LDA-q1'},
        ],
    }
}

# parameters
parameters = ParameterData(dict={
    'GLOBAL': {
        'RUN_TYPE': 'GEO_OPT',
        'WALLTIME': '00:01:00',
    },
    'MOTION': {
        'GEO_OPT': {
            'MAX_FORCE': 1e-20,  # impossible to reach
            'MAX_ITER': 100000,  # run forever
        }
    },
    'FORCE_EVAL': force_eval
})

# Set up the first calculation
calc = code.new_calc()
calc.use_structure(structure)
calc.use_parameters(parameters)
calc.set_max_wallclock_seconds(2*60)
calc.set_resources({"num_machines": 1})

# And go.
calc.store_all()
calc.submit()
print("submitted calculation: PK=%s" % calc.pk)
wait_for_calc(calc)

# Set up and start the second calculation
calc2 = calc.create_restart()
calc2.store_all()
calc2.submit()

print("submitted calc2ulation: PK=%s" % calc2.pk)
print("calc2ulation-label: {}".format(calc2.label))
wait_for_calc(calc2)

calc2_remote_workdir = calc2.get_outputs(type=RemoteData)[0]
calc2_workdir_path = calc2_remote_workdir.get_attr('remote_path')
assert 'parent_calc' in os.listdir(calc2_workdir_path)
assert os.path.islink(os.path.join(calc2_workdir_path, 'parent_calc'))
print('OK! parent_calc exists and is a symlink')

sys.exit(0)
# EOF
