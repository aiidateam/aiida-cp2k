# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run DFT calculation with structure specified in the input file"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import click

from aiida.orm import (Code, Dict)
from aiida.engine import run
from aiida.common import NotExistent
from aiida.plugins import CalculationFactory

Cp2kCalculation = CalculationFactory('cp2k')


@click.command('cli')
@click.argument('codelabel')
def main(codelabel):
    """Run DFT calculation with structure specified in the input file"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)

    print("Testing CP2K ENERGY on H2 (DFT) without StructureData...")

    # parameters
    parameters = Dict(
        dict={
            'FORCE_EVAL': {
                'METHOD': 'Quickstep',
                'DFT': {
                    'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
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
                    # structure directly included in parameters
                    'CELL': {
                        'ABC': '4.0   4.0   4.75'
                    },
                    'COORD': {
                        ' ': ['H    2.0   2.0   2.737166', 'H    2.0   2.0   2.000000']
                    },
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

    # resources
    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {'parameters': parameters, 'code': code, 'metadata': {'options': options,}}

    print("submitted calculation...")
    calc = run(Cp2kCalculation, **inputs)

    # check energy
    expected_energy = -1.14005678487
    if abs(calc['output_parameters'].dict.energy - expected_energy) < 1e-10:
        print("OK, energy has the expected value")
    else:
        print("ERROR!")
        print("Expected energy value: {}".format(expected_energy))
        print("Actual energy value: {}".format(calc['output_parameters'].dict.energy))
        sys.exit(3)

    sys.exit(0)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
