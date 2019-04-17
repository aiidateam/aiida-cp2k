# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test geometry optimizations"""

from __future__ import print_function
from __future__ import absolute_import

import pytest

from . import get_computer, get_code


@pytest.mark.process_execution
def test_cp2k_energy_on_H2O(new_workdir):
    """Testing CP2K GEO_OPT on H2 (DFT)"""

    import ase.build

    from aiida.engine import run
    from aiida.plugins import CalculationFactory
    from aiida.orm import Dict, StructureData

    computer = get_computer(workdir=new_workdir)
    code = get_code(entry_point="cp2k", computer=computer)

    # structure
    atoms = ase.build.molecule("H2")
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = Dict(
        dict={
            "GLOBAL": {"RUN_TYPE": "GEO_OPT"},
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

    options = {
        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": code,
        "metadata": {"options": options},
    }

    result = run(CalculationFactory("cp2k"), **inputs)

    assert result["output_parameters"].dict.exceeded_walltime is False

    expected_energy = -1.14009973178
    assert abs(result["output_parameters"].dict.energy - expected_energy) < 1e-10

    # check geometry
    expected_dist = 0.736103879818
    dist = result["output_structure"].get_ase().get_distance(0, 1)
    assert abs(dist - expected_dist) < 1e-7
