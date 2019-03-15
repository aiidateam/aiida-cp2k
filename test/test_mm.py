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
import ase.build

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

from aiida.orm import Code, Dict, StructureData, SinglefileData
from aiida.engine import run
from aiida.common import NotExistent
from aiida_cp2k.calculations import Cp2kCalculation


# ==============================================================================
if len(sys.argv) != 2:
    print("Usage: test_mm.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
try:
    code = Code.get_from_string(codename)
except NotExistent:
    print ("The code '{}' does not exist".format(codename))
    sys.exit(1)


print("Testing CP2K ENERGY on H2O (MM) ...")


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
water_pot = SinglefileData(filepath="/tmp/water.pot")

# structure using pdb format, because it also carries topology information
atoms = ase.build.molecule('H2O')
atoms.center(vacuum=10.0)
atoms.write("/tmp/coords.pdb", format="proteindatabank")
cell = atoms.cell
coords_pdb = SinglefileData(filepath="/tmp/coords.pdb")

# parameters
# based on cp2k/tests/Fist/regtest-1-1/water_1.inp
parameters = Dict(dict={
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

# settings
settings = Dict(dict={'additional_retrieve_list': ["runtime.callgraph"]})


# resources
options = {
    "resources": {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    },
    "max_wallclock_seconds": 1 * 3 * 60, # 3 minutes
}


# collect all inputs
inputs = {
    'parameters':parameters,
    'settings': settings,
    'code': code,
    'file':{
        'water_pot': water_pot,
        'coords_pdb': coords_pdb,
        },
    'metadata': {
            'options': options,
            }
}

print("Submitted calculation...")
calc = run(Cp2kCalculation, **inputs)

# check warnings
assert calc['output_parameters'].dict.nwarnings == 0

# check energy
expected_energy = 0.146927412614e-3
if abs(calc['output_parameters'].dict.energy - expected_energy) < 1e-10:
    print("OK, energy has the expected value")
else:
    print("ERROR!")
    print("Expected energy value: {}".format(expected_energy))
    print("Actual energy value: {}".format(calc['output_parameters'].dict.energy))
    sys.exit(3)

# check if callgraph is there
if "runtime.callgraph" in calc['retrieved']._repository.list_object_names():
    print("OK, callgraph file was retrived")
else:
    print("ERROR!")
    print("Callgraph file was not retrieved.")
    sys.exit(3)

sys.exit(0)

# EOF
