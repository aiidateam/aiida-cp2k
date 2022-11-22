# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run simple Band Structure calculation"""

import os
import sys

import click
import numpy as np
from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import Dict, SinglefileData, load_code
from aiida.plugins import DataFactory
from ase.atoms import Atoms

StructureData = DataFactory("core.structure")  # pylint: disable=invalid-name
KpointsData = DataFactory("core.array.kpoints")  # pylint: disable=invalid-name


def example_bands(cp2k_code):
    """Run simple Band Structure calculation"""

    print("Computing Band Structure of Si...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

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

    # kpoints
    kpoints_mesh = KpointsData()
    kpoints_mesh.set_cell(cell)
    kpoints_mesh.set_kpoints_mesh_from_density(distance=0.5)

    # basis set
    basis_file = SinglefileData(
        file=os.path.join(thisdir, "..", "files", "BASIS_MOLOPT")
    )

    # pseudopotentials
    pseudo_file = SinglefileData(
        file=os.path.join(thisdir, "..", "files", "GTH_POTENTIALS")
    )

    # parameters
    parameters = Dict(
        {
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "CHARGE": 0,
                    "MGRID": {
                        "CUTOFF": 600,
                        "NGRIDS": 4,
                        "REL_CUTOFF": 50,
                    },
                    "UKS": False,
                    "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                    "POTENTIAL_FILE_NAME": "GTH_POTENTIALS",
                    "QS": {"METHOD": "GPW", "EXTRAPOLATION": "USE_GUESS"},
                    "POISSON": {
                        "PERIODIC": "XYZ",
                    },
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
                    "XC": {
                        "XC_FUNCTIONAL": {
                            "_": "PBE",
                        },
                    },
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
                            "POTENTIAL": "GTH-LDA-q4",
                        },
                    ]
                },
                "PRINT": {  # this is to print forces (may be necessary for problems
                    # detection)
                    "FORCES": {
                        "_": "ON",
                    }
                },
            },
            "GLOBAL": {
                "EXTENDED_FFT_LENGTHS": True,  # Needed for large systems
            },
        }
    )

    # Construct process builder
    builder = cp2k_code.get_builder()
    builder.structure = structure
    builder.parameters = parameters
    builder.kpoints = kpoints_mesh
    builder.code = cp2k_code
    builder.file = {
        "basis": basis_file,
        "pseudo": pseudo_file,
    }
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60

    builder.metadata.options.parser_name = "cp2k_advanced_parser"

    print("submitted calculation...")
    calc = run(builder)

    bands = calc["output_bands"]

    # check bands
    expected_gamma_kpoint = np.array(
        [-6.84282475, 5.23143741, 5.23143741, 5.23143741, 7.89232311]
    )

    if bands.get_kpoints().shape == (62, 3):
        print("OK, got expected kpoints set size.")
    else:
        print("Got unexpected kpoints set.")
        sys.exit(3)

    if bands.get_bands().shape == (62, 5):
        print("OK, got expected bands set size.")
    else:
        print("Got unexpected bands set.")
        sys.exit(3)

    if abs(max(bands.get_bands()[0] - expected_gamma_kpoint)) < 1e-7:
        print("Ok, got expected energy levels at GAMMA point.")
    else:
        print("Got unexpected energy levels at GAMMA point.")
        print(bands.get_bands()[0])
        print(expected_gamma_kpoint)
        sys.exit(3)


@click.command("cli")
@click.argument("codelabel")
def cli(codelabel):
    """Click interface"""
    try:
        code = load_code(codelabel)
    except NotExistent:
        print("The code '{codelabel}' does not exist.")
        sys.exit(1)
    example_bands(code)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
