# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run DFT geometry optimization"""
from __future__ import print_function
from __future__ import absolute_import

import os
import sys
import click
import ase.build

from aiida.orm import (Code, Dict, SinglefileData, StructureData)
from aiida.engine import run
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

Cp2kCalculation = CalculationFactory('cp2k')


def example_geopt(cp2k_code):
    """Run DFT geometry optimization"""

    print("Testing CP2K GEO_OPT on H2 (DFT)...")

    pwd = os.path.dirname(os.path.realpath(__file__))

    # structure
    atoms = ase.build.molecule('H2')
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    # basis set
    basis_file = SinglefileData(file=os.path.join(pwd, "..", "files", "BASIS_MOLOPT"))

    # pseudopotentials
    pseudo_file = SinglefileData(file=os.path.join(pwd, "..", "files", "GTH_POTENTIALS"))

    # parameters
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
                            '_': 'LDA',
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
                            'POTENTIAL': 'GTH-LDA-q6'
                        },
                        {
                            '_': 'H',
                            'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                            'POTENTIAL': 'GTH-LDA-q1'
                        },
                    ],
                },
            }
        })

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        'structure': structure,
        'parameters': parameters,
        'code': cp2k_code,
        'file': {
            'basis': basis_file,
            'pseudo': pseudo_file,
        },
        'metadata': {
            'options': options,
        },
    }

    print("Submitted calculation...")
    calc = run(Cp2kCalculation, **inputs)

    # check walltime not exceeded
    assert calc['output_parameters'].dict.exceeded_walltime is False

    # check energy
    expected_energy = -1.14009973178
    if abs(calc['output_parameters'].dict.energy - expected_energy) < 1e-10:
        print("OK, energy has the expected value")
    else:
        print("ERROR!")
        print("Expected energy value: {}".format(expected_energy))
        print("Actual energy value: {}".format(calc['output_parameters'].dict.energy))
        sys.exit(3)

    # check geometry
    expected_dist = 0.736103879818
    dist = calc['output_structure'].get_ase().get_distance(0, 1)
    if abs(dist - expected_dist) < 1e-7:
        print("OK, H-H distance has the expected value")
    else:
        print("ERROR!")
        print("Expected dist value: {}".format(expected_dist))
        print("Actual dist value: {}".format(dist))
        sys.exit(3)


@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Click interface"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)
    example_geopt(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
