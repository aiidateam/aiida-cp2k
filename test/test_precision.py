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
import numpy as np
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
    print("Usage: test_precision.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
code = test_and_get_code(codename, expected_code_type='cp2k')

print("Testing structure roundtrip precision ase->aiida->cp2k->aiida->ase...")

# calc object
calc = code.new_calc()

# structure
epsilon = 1e-10  # expected precision in Angstrom
dist = 0.74 + epsilon
positions = [(0, 0, 0), (0, 0, dist)]
cell = np.diag([4, -4, 4 + epsilon])
atoms = ase.Atoms('H2', positions=positions, cell=cell)
structure = StructureData(ase=atoms)
calc.use_structure(structure)


# parameters
parameters = ParameterData(dict={
    'GLOBAL': {
        'RUN_TYPE': 'MD',
    },
    'MOTION': {
        'MD': {
            'TIMESTEP': 0.0,  # do not move atoms
            'STEPS': 1,
        },
    },
    'FORCE_EVAL': {
        'METHOD': 'Quickstep',
        'DFT': {
            'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
            'SCF': {
                 'MAX_SCF': 1,
            },
            'XC': {
                'XC_FUNCTIONAL': {
                    '_': 'LDA',
                },
            },
        },
        'SUBSYS': {
            'KIND': {
                '_': 'DEFAULT',
                'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                'POTENTIAL': 'GTH-LDA',
            },
        },
    },
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

# check structure preservation
atoms2 = calc.out.output_structure.get_ase()

# zeros should be preserved exactly
if np.all(atoms2.positions[0] == 0.0):
    print("OK, zeros in structure were preserved exactly")
else:
    print("ERROR!")
    print("Zeros in structure changed: ", atoms2.positions[0])
    sys.exit(3)

# other values should be preserved with epsilon precision
dist2 = atoms2.get_distance(0, 1)
if abs(dist2 - dist) < epsilon:
    print("OK, structure preserved with %.1e Angstrom precision" % epsilon)
else:
    print("ERROR!")
    print("Structure changed by %e Angstrom" % abs(dist - dist2))
    sys.exit(3)

# check cell preservation
cell_diff = np.amax(np.abs(atoms2.cell - cell))
if cell_diff < epsilon:
    print("OK, cell preserved with %.1e Angstrom precision" % epsilon)
else:
    print("ERROR!")
    print("Cell changed by %e Angstrom" % cell_diff)
    sys.exit(3)

sys.exit(0)

# EOF
