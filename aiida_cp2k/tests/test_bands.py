# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test simple Band Structure calculations"""

from __future__ import print_function
from __future__ import absolute_import

import pytest

from . import get_computer, get_code


@pytest.mark.process_execution
def test_band_structure_calc_Si(new_workdir):
    """Computing Band Structure of Si"""

    import numpy as np
    from ase.atoms import Atoms

    from aiida.engine import run
    from aiida.plugins import CalculationFactory
    from aiida.orm import Dict, StructureData

    computer = get_computer(workdir=new_workdir)
    code = get_code(entry_point="cp2k", computer=computer)

    # structure
    positions = [
        [0.0000000000, 0.0000000000, 2.6954627656],
        [4.0431941484, 4.0431941484, 4.0431941484],
    ]
    cell = [
        [0.0, 2.69546276561, 2.69546276561],
        [2.69546276561, 0.0, 2.69546276561],
        [2.69546276561, 2.69546276561, 0.0],
    ]
    atoms = Atoms("Si2", positions=positions, cell=cell)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = Dict(
        dict={
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "CHARGE": 0,
                    "KPOINTS": {
                        "SCHEME MONKHORST-PACK": "1 1 1",
                        "SYMMETRY": "OFF",
                        "WAVEFUNCTIONS": "REAL",
                        "FULL_GRID": ".TRUE.",
                        "PARALLEL_GROUP_SIZE": 0,
                    },
                    "MGRID": {"CUTOFF": 600, "NGRIDS": 4, "REL_CUTOFF": 50},
                    "UKS": False,
                    "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                    "POTENTIAL_FILE_NAME": "GTH_POTENTIALS",
                    "QS": {"METHOD": "GPW", "EXTRAPOLATION": "USE_GUESS"},
                    "POISSON": {"PERIODIC": "XYZ"},
                    "SCF": {
                        "EPS_SCF": 1.0e-4,
                        "ADDED_MOS": 1,
                        "SMEAR": {
                            "METHOD": "FERMI_DIRAC",
                            "ELECTRONIC_TEMPERATURE": 300,
                        },
                        "DIAGONALIZATION": {"ALGORITHM": "STANDARD", "EPS_ADAPT": 0.01},
                        "MIXING": {
                            "METHOD": "BROYDEN_MIXING",
                            "ALPHA": 0.2,
                            "BETA": 1.5,
                            "NBROYDEN": 8,
                        },
                    },
                    "XC": {"XC_FUNCTIONAL": {"_": "PBE"}},
                    "PRINT": {
                        "MO_CUBES": {  # this is to print the band gap
                            "STRIDE": "1 1 1",
                            "WRITE_CUBE": "F",
                            "NLUMO": 1,
                            "NHOMO": 1,
                        },
                        "BAND_STRUCTURE": {
                            "KPOINT_SET": [
                                {
                                    "NPOINTS": 10,
                                    "SPECIAL_POINT": [
                                        "GAMMA 0.0 0.0 0.0",
                                        "X 0.5 0.0 0.5",
                                    ],
                                    "UNITS": "B_VECTOR",
                                },
                                {
                                    "NPOINTS": 10,
                                    "SPECIAL_POINT": [
                                        "X 0.5 0.0 0.5",
                                        "U 0.625 0.25 0.625",
                                    ],
                                    "UNITS": "B_VECTOR",
                                },
                                {
                                    "NPOINTS": 10,
                                    "SPECIAL_POINT": [
                                        "K 0.375 0.375 0.75",
                                        "GAMMA 0.0 0.0 0.0",
                                    ],
                                    "UNITS": "B_VECTOR",
                                },
                                {
                                    "NPOINTS": 10,
                                    "SPECIAL_POINT": [
                                        "GAMMA 0.0 0.0 0.0",
                                        "L 0.5 0.5 0.5",
                                    ],
                                    "UNITS": "B_VECTOR",
                                },
                                {
                                    "NPOINTS": 10,
                                    "SPECIAL_POINT": [
                                        "L 0.5 0.5 0.5",
                                        "W 0.5 0.25 0.75",
                                    ],
                                    "UNITS": "B_VECTOR",
                                },
                                {
                                    "NPOINTS": 10,
                                    "SPECIAL_POINT": [
                                        "W 0.5 0.25 0.75",
                                        "X 0.5 0.0 0.5",
                                    ],
                                    "UNITS": "B_VECTOR",
                                },
                            ]
                        },
                    },
                },
                "SUBSYS": {
                    "KIND": [
                        {
                            "_": "Si",
                            "BASIS_SET": "DZVP-MOLOPT-SR-GTH",
                            "POTENTIAL": "GTH-PBE-q4",
                        }
                    ]
                },
                "PRINT": {  # this is to print forces (may be necessary for problems
                    # detection)
                    "FORCES": {"_": "ON"}
                },
            },
            "GLOBAL": {"EXTENDED_FFT_LENGTHS": True},  # Needed for large systems
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

    bands = result["output_bands"]

    # check bands
    expected_gamma_kpoint = np.array(
        [-5.71237757, 6.5718575, 6.5718575, 6.5718575, 8.88653953]
    )

    assert bands.get_kpoints().shape == (66, 3)
    assert bands.get_bands().shape == (66, 5)
    assert abs(max(bands.get_bands()[0] - expected_gamma_kpoint)) < 1e-7
