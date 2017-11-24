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
    print("Usage: test_mm.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
code = test_and_get_code(codename, expected_code_type='cp2k')

print("Testing CP2K ENERGY on H2O (MM) ...")

# calc object
calc = code.new_calc()

# force field
with open("/tmp/water.pot", "w") as f:
    f.write("""BONDS
H    H       0.000     1.5139
O    H     450.000     0.9572

ANGLES
H    O    H      55.000   104.5200

DIHEDRALS

IMPROPER

NONBONDED
H      0.000000  -0.046000     0.224500
O      0.000000  -0.152100     1.768200

HBOND CUTHB 0.5

END""")
water_pot = SinglefileData(file="/tmp/water.pot")
calc.use_file(water_pot, linkname="water_pot")

# structure using pdb format, because it also carries topology information
atoms = ase.build.molecule('H2O')
atoms.center(vacuum=10.0)
atoms.write("/tmp/coords.pdb", format="proteindatabank")
cell = atoms.cell
coords_pdb = SinglefileData(file="/tmp/coords.pdb")
calc.use_file(coords_pdb, linkname="coords_pdb")

# parameters
# based on cp2k/tests/Fist/regtest-1-1/water_1.inp
parameters = ParameterData(dict={
        'FORCE_EVAL': {
            'METHOD': 'fist',
            'MM': {
                'FORCEFIELD': {
                    'PARM_FILE_NAME': 'water.pot',
                    'PARMTYPE': 'CHM',
                    'CHARGE': [
                        {'ATOM': 'O', 'CHARGE': -0.8476},
                        {'ATOM': 'H', 'CHARGE': 0.4238}]
                },
                'POISSON': {'EWALD': {
                    'EWALD_TYPE': 'spme',
                    'ALPHA': 0.44,
                    'GMAX': 24,
                    'O_SPLINE': 6
                }}
            },
            'SUBSYS': {
                'CELL': {
                    'ABC': '%f  %f  %f' % tuple(atoms.cell.diagonal()),
                },
                'TOPOLOGY': {
                    'COORD_FILE_NAME': 'coords.pdb',
                    'COORD_FILE_FORMAT': 'PDB',
                },
            },
        },
        'GLOBAL': {
            'CALLGRAPH': 'master',
            'CALLGRAPH_FILE_NAME': 'runtime'
        }
})
calc.use_parameters(parameters)

# settings
settings_dict = {'additional_retrieve_list': ["runtime.callgraph"]}
settings = ParameterData(dict=settings_dict)
calc.use_settings(settings)

# resources
calc.set_max_wallclock_seconds(3*60)  # 3 min
calc.set_resources({"num_machines": 1})

# store and submit
calc.store_all()
calc.submit()
print("submitted calculation: PK=%s" % calc.pk)

wait_for_calc(calc)

# check warnings
assert calc.res.nwarnings == 0

# check energy
expected_energy = 0.146927412614e-3
if abs(calc.res.energy - expected_energy) < 1e-10:
    print("OK, energy has the expected value")
else:
    print("ERROR!")
    print("Expected energy value: {}".format(expected_energy))
    print("Actual energy value: {}".format(calc.res.energy))
    sys.exit(3)

# check if callgraph is there
if "runtime.callgraph" in calc.out.retrieved.get_folder_list():
    print("OK, callgraph file was retrived")
else:
    print("ERROR!")
    print("Callgraph file was not retrieved.")
    sys.exit(3)

sys.exit(0)

# EOF
