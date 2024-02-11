###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run simple DFT calculation."""

import os
import sys

import ase.io
import click
import numpy as np
from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import Dict, SinglefileData, load_code
from aiida.plugins import DataFactory
from ase import Atoms

StructureData = DataFactory("core.structure")
TrajectoryData = DataFactory("core.array.trajectory")


def example_dft_md_reftraj(cp2k_code):
    """Run simple DFT calculation."""

    print("Testing CP2K ENERGY on H2O (DFT)...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # Structure.
    structure = StructureData(
        ase=ase.io.read(os.path.join(thisdir, "..", "files", "h2.xyz"))
    )

    # Trajectory.
    positions = np.array(
        [
            [[2, 2, 2.73], [2, 2, 2.0]],
            [[2, 2, 2.74], [2, 2, 2.0]],
            [[2, 2, 2.75], [2, 2, 2.0]],
        ]
    )
    cells = np.array(
        [
            [[4, 0, 0], [0, 4, 0], [0, 0, 4.75]],
            [[4.4, 0, 0], [0, 4.2, 0], [0, 0, 4.76]],
            [[4, 0, 0], [0, 4.1, 0], [0, 0, 4.75]],
        ]
    )
    symbols = ["H", "H"]
    trajectory = TrajectoryData()
    trajectory.set_trajectory(symbols, positions, cells=cells)

    # Basis set.
    basis_file = SinglefileData(
        file=os.path.join(thisdir, "..", "files", "BASIS_MOLOPT")
    )

    # Pseudopotentials.
    pseudo_file = SinglefileData(
        file=os.path.join(thisdir, "..", "files", "GTH_POTENTIALS")
    )

    # Parameters.
    parameters = Dict(
        {
            "GLOBAL": {
                "RUN_TYPE": "MD",
                "PRINT_LEVEL": "LOW",
                "WALLTIME": 600,
                "PROJECT": "aiida",
            },
            "MOTION": {
                "MD": {
                    "ENSEMBLE": "REFTRAJ",
                    "STEPS": 3,
                    "REFTRAJ": {
                        "FIRST_SNAPSHOT": 1,
                        "LAST_SNAPSHOT": 3,
                        "EVAL_FORCES": ".TRUE.",
                        "TRAJ_FILE_NAME": "trajectory.xyz",
                        "CELL_FILE_NAME": "reftraj.cell",
                        "VARIABLE_VOLUME": ".TRUE.",
                    },
                },
                "PRINT": {
                    "RESTART": {
                        "EACH": {
                            "MD": 1,
                        },
                    },
                    "FORCES": {
                        "EACH": {
                            "MD": 1,
                        },
                    },
                    "CELL": {
                        "EACH": {
                            "MD": 1,
                        },
                    },
                },
            },
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                    "POTENTIAL_FILE_NAME": "GTH_POTENTIALS",
                    "QS": {
                        "EPS_DEFAULT": 1.0e-12,
                        "WF_INTERPOLATION": "ps",
                        "EXTRAPOLATION_ORDER": 3,
                    },
                    "MGRID": {
                        "NGRIDS": 4,
                        "CUTOFF": 280,
                        "REL_CUTOFF": 30,
                    },
                    "XC": {
                        "XC_FUNCTIONAL": {
                            "_": "LDA",
                        },
                    },
                    "POISSON": {
                        "PERIODIC": "none",
                        "PSOLVER": "MT",
                    },
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
                    ],
                },
            },
        }
    )

    # Construct process builder.
    builder = cp2k_code.get_builder()
    builder.structure = structure
    builder.trajectory = trajectory
    builder.parameters = parameters
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

    print("Submitted calculation...")
    run(builder)


@click.command("cli")
@click.argument("codelabel")
def cli(codelabel):
    """Click interface."""
    try:
        code = load_code(codelabel)
    except NotExistent:
        print(f"The code '{codelabel}' does not exist.")
        sys.exit(1)
    example_dft_md_reftraj(code)


if __name__ == "__main__":
    cli()
