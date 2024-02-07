###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run molecular dynamics calculation."""

import os
import sys

import ase.io
import click
from aiida import common, engine, orm


def example_mm(cp2k_code):
    """Run molecular mechanics calculation."""

    print("Testing CP2K ENERGY on H2O (MM) ...")

    # Force field.
    with open(os.path.join("/tmp", "water.pot"), "w") as f:
        f.write(
            """BONDS
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

    water_pot = orm.SinglefileData(file=os.path.join("/tmp", "water.pot"))

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # structure using pdb format, because it also carries topology information
    atoms = ase.io.read(os.path.join(thisdir, "..", "files", "h2o.xyz"))
    atoms.center(vacuum=10.0)
    atoms.write(os.path.join("/tmp", "coords.pdb"), format="proteindatabank")
    coords_pdb = orm.SinglefileData(file=os.path.join("/tmp", "coords.pdb"))

    # Parameters.
    # Based on cp2k/tests/Fist/regtest-1-1/water_1.inp
    parameters = orm.Dict(
        {
            "FORCE_EVAL": {
                "METHOD": "fist",
                "STRESS_TENSOR": "analytical",
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
                    "CELL": {
                        "ABC": "%f  %f  %f" % tuple(atoms.cell.diagonal()),
                    },
                    "TOPOLOGY": {
                        "COORD_FILE_NAME": "coords.pdb",
                        "COORD_FILE_FORMAT": "PDB",
                    },
                },
            },
            "MOTION": {
                "CONSTRAINT": {},
                "MD": {
                    "THERMOSTAT": {"CSVR": {}, "TYPE": "csvr"},
                    "BAROSTAT": {},
                    "STEPS": 1000,
                    "ENSEMBLE": "npt_f",
                    "TEMPERATURE": 300.0,
                },
                "PRINT": {
                    "TRAJECTORY": {"EACH": {"MD": 5}},
                    "RESTART": {"EACH": {"MD": 5}},
                    "RESTART_HISTORY": {"_": "OFF"},
                    "CELL": {"EACH": {"MD": 5}},
                    "FORCES": {"EACH": {"MD": 5}, "FORMAT": "XYZ"},
                },
            },
            "GLOBAL": {
                "CALLGRAPH": "master",
                "CALLGRAPH_FILE_NAME": "runtime",
                "PRINT_LEVEL": "medium",
                "RUN_TYPE": "MD",
            },
        }
    )

    # Construct process builder.
    builder = cp2k_code.get_builder()
    builder.parameters = parameters
    builder.code = cp2k_code
    builder.file = {
        "water_pot": water_pot,
        "coords_pdb": coords_pdb,
    }
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60

    print("Submitted calculation...")
    calc = engine.run(builder)


@click.command("cli")
@click.argument("codelabel")
def cli(codelabel):
    """Click interface."""
    try:
        code = orm.load_code(codelabel)
    except common.NotExistent:
        print(f"The code '{codelabel}' does not exist.")
        sys.exit(1)
    example_mm(code)


if __name__ == "__main__":
    cli()
