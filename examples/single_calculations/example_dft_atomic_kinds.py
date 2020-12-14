# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run DFT calculation with different atomic kinds."""

import os
import sys
import click

import ase

from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import (Code, Dict, SinglefileData)
from aiida.plugins import DataFactory

StructureData = DataFactory('structure')  # pylint: disable=invalid-name


def example_dft_atomic_kinds(cp2k_code):
    """Run DFT calculation with different atomic kinds."""

    print("Testing CP2K GEOP_OPT on Si with different atomic kinds (DFT)...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # Structure.
    pos = [[0., 0., 0.], [1.90598, 1.10041807, 0.77811308]]
    cell = [[3.81196, 0.0, 0.0], [1.90598, 3.3012541982101, 0.0], [1.90598, 1.10041806607, 3.1124523066333]]
    tags = [0, 1]
    atoms = ase.Atoms(symbols='Si2', pbc=True, cell=cell, positions=pos, tags=tags)
    structure = StructureData(ase=atoms)

    # Basis set.
    basis_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "BASIS_MOLOPT"))

    # Pseudopotentials.
    pseudo_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "GTH_POTENTIALS"))

    # Parameters.
    parameters = Dict(
        dict={
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
    run(builder)


@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Click interface."""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist.".format(codelabel))
        sys.exit(1)
    example_dft_atomic_kinds(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
