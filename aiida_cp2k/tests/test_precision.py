# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test structure roundtrip precision ase->aiida->cp2k->aiida->ase"""

from __future__ import print_function
from __future__ import absolute_import

import pytest

from . import get_computer, get_code


@pytest.mark.process_execution
def test_structure_roundtrip_precision(new_workdir):
    """Testing structure roundtrip precision ase->aiida->cp2k->aiida->ase..."""

    import ase.build
    import numpy as np

    from aiida.engine import run
    from aiida.plugins import CalculationFactory
    from aiida.orm import Dict, StructureData

    computer = get_computer(workdir=new_workdir)
    code = get_code(entry_point="cp2k", computer=computer)

    # structure
    epsilon = 1e-10  # expected precision in Angstrom
    dist = 0.74 + epsilon
    positions = [(0, 0, 0), (0, 0, dist)]
    cell = np.diag([4, -4, 4 + epsilon])
    atoms = ase.Atoms("H2", positions=positions, cell=cell)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = Dict(
        dict={
            "GLOBAL": {"RUN_TYPE": "MD"},
            "MOTION": {"MD": {"TIMESTEP": 0.0, "STEPS": 1}},  # do not move atoms
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                    "SCF": {"MAX_SCF": 1},
                    "XC": {"XC_FUNCTIONAL": {"_": "LDA"}},
                },
                "SUBSYS": {
                    "KIND": {
                        "_": "DEFAULT",
                        "BASIS_SET": "DZVP-MOLOPT-SR-GTH",
                        "POTENTIAL": "GTH-LDA",
                    }
                },
            },
        }
    )

    # resources
    options = {
        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        "max_wallclock_seconds": 1 * 60 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": code,
        "metadata": {"options": options},
    }

    result = run(CalculationFactory("cp2k"), **inputs)

    # check structure preservation
    atoms2 = result["output_structure"].get_ase()

    # zeros should be preserved exactly
    assert np.all(atoms2.positions[0] == 0.0)

    # other values should be preserved with epsilon precision
    dist2 = atoms2.get_distance(0, 1)
    assert abs(dist2 - dist) < epsilon

    # check cell preservation
    cell_diff = np.amax(np.abs(atoms2.cell - cell))
    assert cell_diff < epsilon
