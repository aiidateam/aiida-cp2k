# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test molecular mechanics calculation"""

from __future__ import print_function
from __future__ import absolute_import

import io
from os import path

import pytest

from . import get_computer, get_code


@pytest.mark.process_execution
def test_cp2k_energy_on_H2O(new_workdir, new_filedir):
    """Testing CP2K ENERGY on H2O (MM)"""

    import ase.build

    from aiida.engine import run
    from aiida.plugins import CalculationFactory
    from aiida.orm import Dict, SinglefileData

    computer = get_computer(workdir=new_workdir)
    code = get_code(entry_point="cp2k", computer=computer)

    # force field
    potfile_fn = path.join(new_filedir, "water.pot")
    with io.open(potfile_fn, mode="w", encoding="utf8") as fhandle:
        fhandle.write(
            u"""\
BONDS
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

END"""
        )

    water_pot = SinglefileData(
        file=potfile_fn
    )  # pylint: disable=no-value-for-parameter

    # structure using pdb format, because it also carries topology information
    pdbfile_fn = path.join(new_filedir, "coords.pdb")
    atoms = ase.build.molecule("H2O")
    atoms.center(vacuum=10.0)
    atoms.write(pdbfile_fn, format="proteindatabank")
    coords_pdb = SinglefileData(
        file=pdbfile_fn
    )  # pylint: disable=no-value-for-parameter

    # parameters
    # based on cp2k/tests/Fist/regtest-1-1/water_1.inp
    parameters = Dict(
        dict={
            "FORCE_EVAL": {
                "METHOD": "fist",
                "MM": {
                    "FORCEFIELD": {
                        "PARM_FILE_NAME": "water.pot",
                        "PARMTYPE": "CHM",
                        "CHARGE": [
                            {"ATOM": "O", "CHARGE": -0.8476},
                            {"ATOM": "H", "CHARGE": 0.4238},
                        ],
                    },
                    "POISSON": {
                        "EWALD": {
                            "EWALD_TYPE": "spme",
                            "ALPHA": 0.44,
                            "GMAX": 24,
                            "O_SPLINE": 6,
                        }
                    },
                },
                "SUBSYS": {
                    "CELL": {"ABC": "%f  %f  %f" % tuple(atoms.cell.diagonal())},
                    "TOPOLOGY": {
                        "COORD_FILE_NAME": "coords.pdb",
                        "COORD_FILE_FORMAT": "PDB",
                    },
                },
            },
            "GLOBAL": {"CALLGRAPH": "master", "CALLGRAPH_FILE_NAME": "runtime"},
        }
    )

    # settings
    settings = Dict(dict={"additional_retrieve_list": ["runtime.callgraph"]})

    # resources
    options = {
        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        "max_wallclock_seconds": 1 * 3 * 60,  # 3 minutes
    }

    # collect all inputs
    inputs = {
        "parameters": parameters,
        "settings": settings,
        "code": code,
        "file": {"water_pot": water_pot, "coords_pdb": coords_pdb},
        "metadata": {"options": options},
    }

    result = run(CalculationFactory("cp2k"), **inputs)

    # check warnings
    assert result["output_parameters"].dict.nwarnings == 0

    # check energy
    expected_energy = 0.146927412614e-3
    assert abs(result["output_parameters"].dict.energy - expected_energy) < 1e-10

    # check if callgraph is there
    assert (
        "runtime.callgraph" in result["retrieved"]._repository.list_object_names()
    )  # pylint: disable=protected-access
