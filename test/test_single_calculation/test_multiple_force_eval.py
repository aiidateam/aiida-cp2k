# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run simple DFT calculation"""

from __future__ import print_function
from __future__ import absolute_import

import sys
import ase

from aiida.engine import run
from aiida.orm import (Code, Dict, StructureData)
from aiida.common import NotExistent
from aiida_cp2k.calculations import Cp2kCalculation

# =============================================================================
if len(sys.argv) != 2:
    print("Usage: test_dft.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
try:
    code = Code.get_from_string(codename)
except NotExistent:
    print("The code '{}' does not exist".format(codename))
    sys.exit(1)

print("Testing CP2K ENERGY on H2O dimer (Mixed: DFT+MM)...")

# structure
pos = [[0.934, 2.445, 1.844], [1.882, 2.227, 1.982], [0.81, 3.165, 2.479], [3.59, 2.048, 2.436], [4.352, 2.339, 1.906],
       [3.953, 1.304, 2.946]]
atoms = ase.Atoms(symbols='OH2OH2', pbc=True, cell=[5.0, 5.0, 5.0])
atoms.set_positions(pos)
structure = StructureData(ase=atoms)

# parameters
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
