###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""An example testing the restart calculation handler for geo_opt run in CP2K."""

import os
import random
import sys

import ase.io
import click
import numpy as np
from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import Dict, SinglefileData, load_code
from aiida.plugins import DataFactory, WorkflowFactory
from ase import Atoms

Cp2kBaseWorkChain = WorkflowFactory("cp2k.base")
StructureData = DataFactory("core.structure")
TrajectoryData = DataFactory("core.array.trajectory")


def example_base(cp2k_code):
    """Run simple DFT calculation through a workchain."""

    thisdir = os.path.dirname(os.path.realpath(__file__))

    print("Testing CP2K ENERGY on H2O (DFT) through a workchain...")

    # Basis set.
    basis_file = SinglefileData(
        file=os.path.join(thisdir, "..", "files", "BASIS_MOLOPT")
    )

    # Pseudopotentials.
    pseudo_file = SinglefileData(
        file=os.path.join(thisdir, "..", "files", "GTH_POTENTIALS")
    )

    # Structure.
    structure = StructureData(
        ase=ase.io.read(os.path.join(thisdir, "..", "files", "h2.xyz"))
    )

    # Trajectory.
    steps = 20
    positions = np.array(
        [[[2, 2, 2.73 + 0.05 * random.random()], [2, 2, 2]] for i in range(steps)]
    )
    cells = np.array(
        [
            [[4, 0, 0], [0, 4, 0], [0, 0, 4.75 + 0.05 * random.random()]]
            for i in range(steps)
        ]
    )
    symbols = ["H", "H"]
    trajectory = TrajectoryData()
    trajectory.set_trajectory(symbols, positions, cells=cells)

    # Parameters.
    parameters = Dict(
        {
            "GLOBAL": {
                "RUN_TYPE": "MD",
                "PRINT_LEVEL": "LOW",
                "WALLTIME": 5,
                "PROJECT": "aiida",
            },
            "MOTION": {
                "MD": {
                    "ENSEMBLE": "REFTRAJ",
                    "STEPS": steps,
                    "REFTRAJ": {
                        "FIRST_SNAPSHOT": 1,
                        "LAST_SNAPSHOT": steps,
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
    builder = Cp2kBaseWorkChain.get_builder()

    # Switch on resubmit_unconverged_geometry disabled by default.
    builder.handler_overrides = Dict(
        {"restart_incomplete_calculation": {"enabled": True}}
    )

    # Input structure.
    builder.cp2k.structure = structure
    builder.cp2k.trajectory = trajectory
    builder.cp2k.parameters = parameters
    builder.cp2k.code = cp2k_code
    builder.cp2k.file = {
        "basis": basis_file,
        "pseudo": pseudo_file,
    }
    builder.cp2k.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.cp2k.metadata.options.max_wallclock_seconds = 1 * 3 * 60

    print("Submitted calculation...")
    calc = run(builder)

    if "EXT_RESTART" in calc["final_input_parameters"].dict:
        print("OK, EXT_RESTART section is present in the final_input_parameters.")
    else:
        print(
            "ERROR, EXT_RESTART section is NOT present in the final_input_parameters."
        )
        sys.exit(3)


@click.command("cli")
@click.argument("codelabel")
def cli(codelabel):
    """Click interface."""
    try:
        code = load_code(codelabel)
    except NotExistent:
        print(f"The code '{codelabel}' does not exist")
        sys.exit(1)
    example_base(code)


if __name__ == "__main__":
    cli()
