#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
from __future__ import print_function

import sys
import ase.build
from utils import wait_for_calc

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

from aiida.orm import Code, Dict, StructureData, SinglefileData  # noqa
from aiida.engine import submit
from aiida.common import NotExistent
from aiida_cp2k.calculations import Cp2kCalculation


# =============================================================================
if len(sys.argv) != 2:
    print("Usage: test_dft.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
try:
    code = Code.get_from_string(codename)
except NotExistent:
    print ("The code {} does not exist".format(codename))
    sys.exit(1)

print("Testing CP2K ENERGY on H2O (DFT)...")

# structure
atoms = ase.build.molecule('H2O')
atoms.center(vacuum=2.0)
structure = StructureData(ase=atoms)


# parameters
parameters = Dict(dict={
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
options = {
    "resources": {
        "num_machines": 1,
#        "num_mpiprocs_per_machine": 1,
    },
    "max_wallclock_seconds": 1 * 60 * 60,
}
inputs = {
        'structure': structure,
        'parameters':parameters,
        'code': code,
        'metadata': {
            'options': options,
        }
}

submit(Cp2kCalculation, **inputs)
