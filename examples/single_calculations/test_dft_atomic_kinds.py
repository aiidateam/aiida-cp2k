# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run DFT calculation with different atomic kinds"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import ase.build
import click

from aiida.engine import run
from aiida.orm import (Code, Dict, StructureData)
from aiida.common import NotExistent
from aiida_cp2k.calculations import Cp2kCalculation


@click.command('cli')
@click.argument('codelabel')
def main(codelabel):
    """Run DFT calculation with different atomic kinds"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)

    print("Testing CP2K GEOP_OPT on Si with different atomic kinds (DFT)...")

    # structure
    pos = [[0., 0., 0.], [1.90598, 1.10041807, 0.77811308]]
    cell = [[3.81196, 0.0, 0.0], [1.90598, 3.3012541982101, 0.0], [1.90598, 1.10041806607, 3.1124523066333]]
    tags = [0, 1]
    atoms = ase.Atoms(symbols='Si2', pbc=True, cell=cell, positions=pos, tags=tags)
    structure = StructureData(ase=atoms)

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
                    'KIND': [
                        {
                            '_': 'Si',
                            'ELEMENT': 'Si',
                            'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                            'POTENTIAL': 'GTH-LDA-q4'
                        },
                        {
                            '_': 'Si1',
                            'ELEMENT': 'Si',
                            'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                            'POTENTIAL': 'GTH-LDA-q4'
                        },
                    ],
                },
            },
            'MOTION': {
                'GEO_OPT': {
                    'MAX_FORCE': 1e-4,
                    'MAX_ITER': '3',
                    'OPTIMIZER': 'BFGS',
                    'BFGS': {
                        'TRUST_RADIUS': '[bohr] 0.1',
                    },
                },
            },
            'GLOBAL': {
                'RUN_TYPE': 'GEO_OPT',
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
        'code': code,
        'metadata': {
            'options': options,
        }
    }

    print("Submitted calculation...")
    run(Cp2kCalculation, **inputs)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
