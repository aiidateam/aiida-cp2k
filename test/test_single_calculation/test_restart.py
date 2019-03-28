#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from __future__ import print_function

import re
import sys
import ase.build
from copy import deepcopy
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
atoms1 = ase.build.molecule('H2O')
atoms1.center(vacuum=2.0)
structure1 = StructureData(ase=atoms1)

# CP2K input
params1 = {
    'GLOBAL': {
        'RUN_TYPE': 'GEO_OPT',
        'WALLTIME': '00:00:10',  # too short
    },
    'MOTION': {
        'GEO_OPT': {
            'MAX_FORCE': 1e-20,  # impossible to reach
            'MAX_ITER': 100000  # run forever
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
            'SCF': {
                'PRINT': {'RESTART': {'_': 'ON'}}
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
}

# ------------------------------------------------------------------------------
# Set up the first calculation

calc1 = code.new_calc()
calc1.use_structure(structure1)
calc1.use_parameters(ParameterData(dict=params1))
calc1.set_max_wallclock_seconds(2*60)
calc1.set_resources({"num_machines": 1})
calc1.store_all()
calc1.submit()
print("submitted calculation 1: PK=%s" % calc1.pk)
wait_for_calc(calc1)

# check walltime exceeded
assert calc1.res.exceeded_walltime is True
assert calc1.res.energy is not None
assert calc1.out.output_structure is not None
print("OK, walltime exceeded as expected")

# ------------------------------------------------------------------------------
# Set up and start the second calculation

# parameters
params2 = deepcopy(calc1.inp.parameters.get_dict())
del(params2['GLOBAL']['WALLTIME'])
del(params2['MOTION']['GEO_OPT']['MAX_FORCE'])
restart_wfn_fn = './parent_calc/aiida-RESTART.wfn'
params2['FORCE_EVAL']['DFT']['RESTART_FILE_NAME'] = restart_wfn_fn
params2['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS'] = 'RESTART'
params2['EXT_RESTART'] = {'RESTART_FILE_NAME': './parent_calc/aiida-1.restart'}

# structure
atoms2 = ase.build.molecule('H2O')
atoms2.center(vacuum=2.0)
atoms2.positions *= 0.0  # place all atoms at origin -> nuclear fusion :-)
structure2 = StructureData(ase=atoms2)

calc2 = code.new_calc()
calc2.use_structure(structure2)  # breaks simulation unless overwritten ...
calc2.use_parameters(ParameterData(dict=params2))  # ... by EXT_RESTART
calc2.use_parent_folder(calc1.out.remote_folder)
calc2.set_max_wallclock_seconds(2*60)
calc2.set_resources({"num_machines": 1})
calc2.store_all()
calc2.submit()
print("submitted calculation 2: PK=%s" % calc2.pk)
wait_for_calc(calc2)

# check energy
expected_energy = -17.1566455959
if abs(calc2.res.energy - expected_energy) < 1e-10:
    print("OK, energy has the expected value")

# if restart wfn is not found it will create a warning
assert calc2.res.nwarnings == 1

# ensure that this warning originates from overwritting coordinates
out_fn = calc2.out.retrieved.get_abs_path("aiida.out")
output = open(out_fn).read()
assert re.search("WARNING .* :: Overwriting coordinates", output)

sys.exit(0)
# EOF
