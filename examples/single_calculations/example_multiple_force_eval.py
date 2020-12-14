# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run DFT calculation with multiple force eval sections."""

import os
import sys
import click

import ase

from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import (Code, Dict, SinglefileData)
from aiida.plugins import DataFactory

StructureData = DataFactory('structure')  # pylint: disable=invalid-name


def example_multiple_force_eval(cp2k_code):
    """Run DFT calculation with multiple force eval sections."""

    print("Testing CP2K ENERGY on H2O dimer (Mixed: DFT+MM)...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # structure
    pos = [[0.934, 2.445, 1.844], [1.882, 2.227, 1.982], [0.81, 3.165, 2.479], [3.59, 2.048, 2.436],
           [4.352, 2.339, 1.906], [3.953, 1.304, 2.946]]
    atoms = ase.Atoms(symbols='OH2OH2', pbc=True, cell=[5.0, 5.0, 5.0])
    atoms.set_positions(pos)
    structure = StructureData(ase=atoms)

    # Basis set.
    basis_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "BASIS_MOLOPT"))

    # Pseudopotentials.
    pseudo_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "GTH_POTENTIALS"))

    # Parameters.
    parameters = Dict(
        dict={
            'MULTIPLE_FORCE_EVALS': {
                'FORCE_EVAL_ORDER': '2 3',
                'MULTIPLE_SUBSYS': 'T',
            },
            'FORCE_EVAL': [
                {
                    'METHOD': 'MIXED',
                    'MIXED': {
                        'MIXING_TYPE': 'GENMIX',
                        'GENERIC': {
                            'ERROR_LIMIT': 1.0E-10,
                            'MIXING_FUNCTION': 'E1+E2',
                            'VARIABLES': 'E1 E2',
                        },
                        'MAPPING': {
                            'FORCE_EVAL_MIXED': {
                                'FRAGMENT': [
                                    {
                                        '_': 1,
                                        '1': '3'
                                    },
                                    {
                                        '_': 2,
                                        '4': '6'
                                    },
                                ],
                            },
                            'FORCE_EVAL': [{
                                '_': 1,
                                'DEFINE_FRAGMENTS': '1 2',
                            }, {
                                '_': 2,
                                'DEFINE_FRAGMENTS': '1 2',
                            }],
                        }
                    },
                },
                {
                    'METHOD': 'FIST',
                    'MM': {
                        'FORCEFIELD': {
                            'SPLINE': {
                                'EPS_SPLINE': 1.30E-5,
                                'EMAX_SPLINE': 0.8,
                            },
                            'CHARGE': [
                                {
                                    'ATOM': 'H',
                                    'CHARGE': 0.0,
                                },
                                {
                                    'ATOM': 'O',
                                    'CHARGE': 0.0,
                                },
                            ],
                            'BOND': {
                                'ATOMS': 'H O',
                                'K': 0.0,
                                'R0': 2.0,
                            },
                            'BEND': {
                                'ATOMS': 'H O H',
                                'K': 0.0,
                                'THETA0': 2.0,
                            },
                            'NONBONDED': {
                                'LENNARD-JONES': [
                                    {
                                        'ATOMS': 'H H',
                                        'EPSILON': 0.2,
                                        'SIGMA': 2.4,
                                    },
                                    {
                                        'ATOMS': 'H O',
                                        'EPSILON': 0.4,
                                        'SIGMA': 3.0,
                                    },
                                    {
                                        'ATOMS': 'O O',
                                        'EPSILON': 0.8,
                                        'SIGMA': 3.6,
                                    },
                                ]
                            },
                        },
                        'POISSON': {
                            'EWALD': {
                                'EWALD_TYPE': 'none',
                            }
                        }
                    },
                    'SUBSYS': {
                        'TOPOLOGY': {
                            'CONNECTIVITY': 'GENERATE',
                            'GENERATE': {
                                'CREATE_MOLECULES': True,
                            }
                        }
                    }
                },
                {
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
                },
            ]
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
    example_multiple_force_eval(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
