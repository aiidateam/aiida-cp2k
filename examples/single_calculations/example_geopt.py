# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run DFT geometry optimization."""

import os
import sys

import ase.io
import click

from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import (Code, Dict, SinglefileData)
from aiida.plugins import DataFactory

StructureData = DataFactory('structure')  # pylint: disable=invalid-name


def example_geopt(cp2k_code):
    """Run DFT geometry optimization."""

    print("Testing CP2K GEO_OPT on H2O (DFT)...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # Structure.
    structure = StructureData(ase=ase.io.read(os.path.join(thisdir, '..', "files", 'h2.xyz')))

    # Basis set.
    basis_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "BASIS_MOLOPT"))

    # Pseudopotentials.
    pseudo_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "GTH_POTENTIALS"))

    # Parameters.
    parameters = Dict(
        dict={
            'GLOBAL': {
                'RUN_TYPE': 'GEO_OPT',
            },
            'FORCE_EVAL': {
                'METHOD': 'Quickstep',
                'DFT': {
                    'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
                    'POTENTIAL_FILE_NAME': 'GTH_POTENTIALS',
                    'QS': {
                        'EPS_DEFAULT': 1.0e-12,
                        'WF_INTERPOLATION': 'ps',
                        'EXTRAPOLATION_ORDER': 3,
                    },
                    'MGRID': {
                        'NGRIDS': 4,
                        'CUTOFF': 280,
                        'REL_CUTOFF': 30,
                    },
                    'XC': {
                        'XC_FUNCTIONAL': {
                            '_': 'PBE',
                        },
                    },
                    'POISSON': {
                        'PERIODIC': 'none',
                        'PSOLVER': 'MT',
                    },
                },
                'SUBSYS': {
                    'KIND': [
                        {
                            '_': 'O',
                            'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                            'POTENTIAL': 'GTH-PBE-q6'
                        },
                        {
                            '_': 'H',
                            'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                            'POTENTIAL': 'GTH-PBE-q1'
                        },
                    ],
                },
            }
        })

    # Construct process builder.
    builder = cp2k_code.get_builder()
    builder.structure = structure
    builder.parameters = parameters
    builder.code = cp2k_code
    builder.file = {
        'basis': basis_file,
        'pseudo': pseudo_file,
    }
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60

    print("Submitted calculation...")
    calc = run(builder)

    # Check walltime not exceeded.
    assert calc['output_parameters']['exceeded_walltime'] is False

    # Check energy.
    expected_energy = -1.17212345935
    if abs(calc['output_parameters']['energy'] - expected_energy) < 1e-10:
        print("OK, energy has the expected value.")
    else:
        print("ERROR!")
        print("Expected energy value: {}".format(expected_energy))
        print("Actual energy value: {}".format(calc['output_parameters']['energy']))
        sys.exit(3)

    # Check geometry.
    expected_dist = 0.732594809575
    dist = calc['output_structure'].get_ase().get_distance(0, 1)
    if abs(dist - expected_dist) < 1e-7:
        print("OK, H-H distance has the expected value.")
    else:
        print("ERROR!")
        print("Expected dist value: {}".format(expected_dist))
        print("Actual dist value: {}".format(dist))
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
    example_geopt(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
