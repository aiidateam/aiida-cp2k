# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test CP2K restart"""
from __future__ import print_function
from __future__ import absolute_import

import re
import sys
from copy import deepcopy

import ase.build

from aiida.orm import Code, Dict, StructureData
from aiida.engine import run
from aiida.common import NotExistent
from aiida_cp2k.calculations import Cp2kCalculation

# ==============================================================================
if len(sys.argv) != 2:
    print("Usage: test_restart.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
codename = sys.argv[1]
try:
    code = Code.get_from_string(codename)
except NotExistent:
    print("The code '{}' does not exist".format(codename))
    sys.exit(1)

print("Testing CP2K restart...")

# structure
atoms1 = ase.build.molecule("H2O")
atoms1.center(vacuum=2.0)
structure1 = StructureData(ase=atoms1)

# CP2K input
params1 = Dict(
    dict={
        "GLOBAL": {"RUN_TYPE": "GEO_OPT", "WALLTIME": "00:00:10"},  # too short
        "MOTION": {
            "GEO_OPT": {
                "MAX_FORCE": 1e-20,  # impossible to reach
                "MAX_ITER": 100000,  # run forever
            }
        },
        "FORCE_EVAL": {
            "METHOD": "Quickstep",
            "DFT": {
                "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                "QS": {
                    "EPS_DEFAULT": 1.0e-12,
                    "WF_INTERPOLATION": "ps",
                    "EXTRAPOLATION_ORDER": 3,
                },
                "MGRID": {"NGRIDS": 4, "CUTOFF": 280, "REL_CUTOFF": 30},
                "XC": {"XC_FUNCTIONAL": {"_": "LDA"}},
                "POISSON": {"PERIODIC": "none", "PSOLVER": "MT"},
                "SCF": {"PRINT": {"RESTART": {"_": "ON"}}},
            },
            "SUBSYS": {
                "KIND": [
                    {
                        "_": "O",
                        "BASIS_SET": "DZVP-MOLOPT-SR-GTH",
                        "POTENTIAL": "GTH-LDA-q6",
                    },
                    {
                        "_": "H",
                        "BASIS_SET": "DZVP-MOLOPT-SR-GTH",
                        "POTENTIAL": "GTH-LDA-q1",
                    },
                ]
            },
        },
    }
)

# ------------------------------------------------------------------------------
# Set up the first calculation

options = {
    "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
    "max_wallclock_seconds": 1 * 2 * 60,
}
inputs = {
    "structure": structure1,
    "parameters": params1,
    "code": code,
    "metadata": {"options": options},
}

print("submitted calculation 1:")
calc1 = run(Cp2kCalculation, **inputs)

# check walltime exceeded
assert calc1["output_parameters"].dict.exceeded_walltime is True
assert calc1["output_parameters"].dict.energy is not None
assert "output_structure" in calc1
print("OK, walltime exceeded as expected")

# ------------------------------------------------------------------------------
# Set up and start the second calculation

# parameters
params2 = deepcopy(params1.get_dict())
del params2["GLOBAL"]["WALLTIME"]
del params2["MOTION"]["GEO_OPT"]["MAX_FORCE"]
restart_wfn_fn = "./parent_calc/aiida-RESTART.wfn"
params2["FORCE_EVAL"]["DFT"]["RESTART_FILE_NAME"] = restart_wfn_fn
params2["FORCE_EVAL"]["DFT"]["SCF"]["SCF_GUESS"] = "RESTART"
params2["EXT_RESTART"] = {"RESTART_FILE_NAME": "./parent_calc/aiida-1.restart"}
params2 = Dict(dict=params2)

# structure
atoms2 = ase.build.molecule("H2O")
atoms2.center(vacuum=2.0)
atoms2.positions *= 0.0  # place all atoms at origin -> nuclear fusion :-)
structure2 = StructureData(ase=atoms2)

inputs2 = {
    "structure": structure2,
    "parameters": params2,
    "code": code,
    "parent_calc_folder": calc1["remote_folder"],
    "metadata": {"options": options},
}
print("submitted calculation 2")
calc2 = run(Cp2kCalculation, **inputs2)

# check energy
expected_energy = -17.1566455959
if abs(calc2["output_parameters"].dict.energy - expected_energy) < 1e-10:
    print("OK, energy has the expected value")

# if restart wfn is not found it will create a warning
assert calc2["output_parameters"].dict.nwarnings == 1

# ensure that this warning originates from overwritting coordinates
output = calc2["retrieved"]._repository.get_object_content(
    "aiida.out"
)  # pylint: disable=protected-access
assert re.search("WARNING .* :: Overwriting coordinates", output)

sys.exit(0)
# EOF
