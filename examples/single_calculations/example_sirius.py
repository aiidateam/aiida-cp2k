###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run simple DFT with calculation with SIRIUS."""

import os
import sys

import ase.io
import click
from aiida import common, engine, orm, plugins

StructureData = plugins.DataFactory("core.structure")


def example_sirius(cp2k_code, setup_sssp_pseudos):
    """Run simple DFT calculation."""

    print("Testing CP2K SIRIUS ENERGY on Si (DFT)...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # Structure.
    structure = StructureData(
        ase=ase.io.read(os.path.join(thisdir, "..", "files", "si.xyz"))
    )

    # Parameters.
    parameters = orm.Dict(
        {
            "FORCE_EVAL": {
                "METHOD": "SIRIUS",
                "STRESS_TENSOR": "ANALYTICAL",
                "PRINT": {
                    "FORCES": {"FILENAME": "requested-forces", "ADD_LAST": "SYMBOLIC"}
                },
                "PW_DFT": {
                    "CONTROL": {"VERBOSITY": 2},
                    "PARAMETERS": {
                        "ELECTRONIC_STRUCTURE_METHOD": "pseudopotential",
                        "USE_SYMMETRY": True,
                        "GK_CUTOFF": 5,
                        "PW_CUTOFF": 20,
                        "ENERGY_TOL": 0.1,
                        "DENSITY_TOL": 0.1,
                        "NUM_DFT_ITER": 400,
                        "SMEARING": "FERMI_DIRAC",
                        "SMEARING_WIDTH": 0.00225,
                    },
                    "ITERATIVE_SOLVER": {
                        "ENERGY_TOLERANCE": 0.001,
                        "NUM_STEPS": 20,
                        "SUBSPACE_SIZE": 4,
                        "CONVERGE_BY_ENERGY": 1,
                    },
                },
                "DFT": {
                    "XC": {
                        "XC_FUNCTIONAL": {
                            "GGA_X_PBE": {"_": ""},
                            "GGA_C_PBE": {"_": ""},
                        }
                    },
                    "PRINT": {
                        "MO": {
                            "_": "OFF",
                            "ADD_LAST": "SYMBOLIC",
                            "EIGENVALUES": True,
                            "OCCUPATION_NUMBERS": True,
                            "NDIGITS": 12,
                            "EACH": {"CELL_OPT": 0, "GEO_OPT": 0, "MD": 0, "QS_SCF": 0},
                        },
                        "MULLIKEN": {
                            "_": "ON",
                            "ADD_LAST": "SYMBOLIC",
                            "EACH": {"CELL_OPT": 0, "GEO_OPT": 0, "MD": 0},
                        },
                        "LOWDIN": {"_": "OFF"},
                        "HIRSHFELD": {"_": "OFF"},
                    },
                },
                "SUBSYS": {
                    "KIND": [
                        {
                            "_": "Si",
                            "POTENTIAL": "UPF Si.json",
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
    pseudo_family = orm.load_group("SSSP/1.3/PBE/efficiency")
    builder.pseudos_upf = pseudo_family.get_pseudos(structure=structure)
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60

    print("Submitted calculation...")
    engine.run(builder)


@click.command("cli")
@click.argument("codelabel")
def cli(codelabel):
    """Click interface."""
    try:
        code = orm.load_code(codelabel)
    except common.NotExistent:
        print(f"The code '{codelabel}' does not exist.")
        sys.exit(1)
    example_sirius(code, setup_sssp_pseudos=None)


if __name__ == "__main__":
    cli()
