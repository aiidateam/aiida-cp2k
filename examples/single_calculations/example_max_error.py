# pylint: disable=invalid-name
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
from aiida.common import NotExistent
from aiida.engine import run_get_node
from aiida.orm import Dict, SinglefileData, load_code
from aiida.plugins import CalculationFactory, DataFactory

StructureData = DataFactory("core.structure")  # pylint: disable=invalid-name
Cp2kCalculation = CalculationFactory("cp2k")


def example_dft(cp2k_code):
    """Run simple DFT calculation."""

    print("Testing CP2K GEO_OPT ERROR MAX on H2O (DFT)...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # Structure.
    structure = StructureData(
        ase=ase.io.read(os.path.join(thisdir, "..", "files", "h2o.xyz"))
    )

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
                "RUN_TYPE": "GEO_OPT",
            },
            "MOTION": {
                "GEO_OPT": {
                    "OPTIMIZER": "BFGS",
                    "MAX_ITER": "2",
                    "MAX_DR": 0.0001,
                    "RMS_DR": 0.00005,
                    "MAX_FORCE": 0.000015,
                    "RMS_FORCE": 0.00001,
                },
            },
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                    "POTENTIAL_FILE_NAME": "GTH_POTENTIALS",
                    "QS": {"EPS_DEFAULT": 1.0e-8, "EXTRAPOLATION": "use_prev_p"},
                    "MGRID": {
                        "NGRIDS": 4,
                        "CUTOFF": 200,
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
    calc = run_get_node(builder)
    assert (
        calc[1].exit_status
        == Cp2kCalculation.exit_codes.ERROR_MAXIMUM_NUMBER_OPTIMIZATION_STEPS_REACHED.status
    )


@click.command("cli")
@click.argument("codelabel")
def cli(codelabel):
    """Click interface."""
    try:
        code = load_code(codelabel)
    except NotExistent:
        print(f"The code '{codelabel}' does not exist.")
        sys.exit(1)
    example_dft(code)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
