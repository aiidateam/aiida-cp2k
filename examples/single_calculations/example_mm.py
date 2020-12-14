# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run molecular mechanics calculation."""

import os
import sys

import ase.io
import click

from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import (Code, Dict, SinglefileData)


def example_mm(cp2k_code):
    """Run molecular mechanics calculation."""

    print("Testing CP2K ENERGY on H2O (MM) ...")

    # Force field.
    with open(os.path.join("/tmp", "water.pot"), "w") as f:
        f.write("""BONDS
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

    END""")

    water_pot = SinglefileData(file=os.path.join("/tmp", "water.pot"))  # pylint: disable=no-value-for-parameter

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # structure using pdb format, because it also carries topology information
    atoms = ase.io.read(os.path.join(thisdir, '..', 'files', 'h2o.xyz'))
    atoms.center(vacuum=10.0)
    atoms.write(os.path.join("/tmp", "coords.pdb"), format="proteindatabank")
    coords_pdb = SinglefileData(file=os.path.join("/tmp", "coords.pdb"))

    # Parameters.
    # Based on cp2k/tests/Fist/regtest-1-1/water_1.inp
    parameters = Dict(
        dict={
            'FORCE_EVAL': {
                'METHOD': 'fist',
                'MM': {
                    'FORCEFIELD': {
                        'PARM_FILE_NAME': 'water.pot',
                        'PARMTYPE': 'CHM',
                        'CHARGE': [{
                            'ATOM': 'O',
                            'CHARGE': -0.8476
                        }, {
                            'ATOM': 'H',
                            'CHARGE': 0.4238
                        }]
                    },
                    'POISSON': {
                        'EWALD': {
                            'EWALD_TYPE': 'spme',
                            'ALPHA': 0.44,
                            'GMAX': 24,
                            'O_SPLINE': 6
                        }
                    }
                },
                'SUBSYS': {
                    'CELL': {
                        'ABC': '%f  %f  %f' % tuple(atoms.cell.diagonal()),
                    },
                    'TOPOLOGY': {
                        'COORD_FILE_NAME': 'coords.pdb',
                        'COORD_FILE_FORMAT': 'PDB',
                    },
                },
            },
            'GLOBAL': {
                'CALLGRAPH': 'master',
                'CALLGRAPH_FILE_NAME': 'runtime'
            }
        })

    # Settings.
    settings = Dict(dict={'additional_retrieve_list': ["runtime.callgraph"]})

    # Construct process builder.
    builder = cp2k_code.get_builder()
    builder.parameters = parameters
    builder.settings = settings
    builder.code = cp2k_code
    builder.file = {
        'water_pot': water_pot,
        'coords_pdb': coords_pdb,
    }
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60

    print("Submitted calculation...")
    calc = run(builder)

    # Check energy.
    expected_energy = 0.146927412614e-3
    if abs(calc['output_parameters']['energy'] - expected_energy) < 1e-10:
        print("OK, energy has the expected value.")
    else:
        print("ERROR!")
        print("Expected energy value: {}".format(expected_energy))
        print("Actual energy value: {}".format(calc['output_parameters']['energy']))
        sys.exit(3)

    # Check if callgraph is there.
    if "runtime.callgraph" in calc['retrieved']._repository.list_object_names():  # pylint: disable=protected-access
        print("OK, callgraph file was retrived.")
    else:
        print("ERROR!")
        print("Callgraph file was not retrieved.")
        sys.exit(3)


@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Click interface."""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist.".format(codelabel))
        sys.exit(1)
    example_mm(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
