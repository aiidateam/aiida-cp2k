# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test simple DFT calculations with Gaussian Datatypes"""

from io import StringIO

import pytest
import ase.build

from aiida.plugins import CalculationFactory, DataFactory
from aiida.common.exceptions import LoadingEntryPointError, MissingEntryPointError

from aiida.engine import run, run_get_node
from aiida.orm import Dict, StructureData
from aiida.engine.processes.calcjobs.tasks import PreSubmitException

try:
    BasisSet = DataFactory("gaussian.basisset")  # pylint: disable=invalid-name
    Pseudo = DataFactory("gaussian.pseudo")  # pylint: disable=invalid-name
except (LoadingEntryPointError, MissingEntryPointError):
    pytest.skip("Gaussian Datatypes are not available", allow_module_level=True)

# Note: the basissets and pseudos deliberately have a prefix to avoid matching
#       any CP2K provided entries which may creep in via the DATA_DIR

# pylint: disable=line-too-long, redefined-outer-name
BSET_DATA = {
    "simple":
        """\
 H  MY-DZVP-MOLOPT-GTH MY-DZVP-MOLOPT-GTH-q1
 1
 2 0 1 7 2 1
     11.478000339908  0.024916243200 -0.012512421400  0.024510918200
      3.700758562763  0.079825490000 -0.056449071100  0.058140794100
      1.446884268432  0.128862675300  0.011242684700  0.444709498500
      0.716814589696  0.379448894600 -0.418587548300  0.646207973100
      0.247918564176  0.324552432600  0.590363216700  0.803385018200
      0.066918004004  0.037148121400  0.438703133000  0.892971208700
      0.021708243634 -0.001125195500 -0.059693171300  0.120101316500

 O  MY-DZVP-MOLOPT-SR-GTH MY-DZVP-MOLOPT-SR-GTH-q6
 1
 2 0 2 5 2 2 1
     10.389228018317  0.126240722900  0.069215797900 -0.061302037200 -0.026862701100  0.029845227500
      3.849621072005  0.139933704300  0.115634538900 -0.190087511700 -0.006283021000  0.060939733900
      1.388401188741 -0.434348231700 -0.322839719400 -0.377726982800 -0.224839187800  0.732321580100
      0.496955043655 -0.852791790900 -0.095944016600 -0.454266086000  0.380324658600  0.893564918400
      0.162491615040 -0.242351537800  1.102830348700 -0.257388983000  1.054102919900  0.152954188700
""",
    "multiple_o":
        """\
 H  MY-DZVP-MOLOPT-GTH MY-DZVP-MOLOPT-GTH-q1
 1
 2 0 1 7 2 1
     11.478000339908  0.024916243200 -0.012512421400  0.024510918200
      3.700758562763  0.079825490000 -0.056449071100  0.058140794100
      1.446884268432  0.128862675300  0.011242684700  0.444709498500
      0.716814589696  0.379448894600 -0.418587548300  0.646207973100
      0.247918564176  0.324552432600  0.590363216700  0.803385018200
      0.066918004004  0.037148121400  0.438703133000  0.892971208700
      0.021708243634 -0.001125195500 -0.059693171300  0.120101316500

 O  MY-DZVP-MOLOPT-SR-GTH MY-DZVP-MOLOPT-SR-GTH-q6
 1
 2 0 2 5 2 2 1
     10.389228018317  0.126240722900  0.069215797900 -0.061302037200 -0.026862701100  0.029845227500
      3.849621072005  0.139933704300  0.115634538900 -0.190087511700 -0.006283021000  0.060939733900
      1.388401188741 -0.434348231700 -0.322839719400 -0.377726982800 -0.224839187800  0.732321580100
      0.496955043655 -0.852791790900 -0.095944016600 -0.454266086000  0.380324658600  0.893564918400
      0.162491615040 -0.242351537800  1.102830348700 -0.257388983000  1.054102919900  0.152954188700

 O  MY-TZVP-MOLOPT-GTH MY-TZVP-MOLOPT-GTH-q6
 1
 2 0 2 7 3 3 1
     12.015954705512 -0.060190841200  0.065738617900  0.041006765400  0.036543638800 -0.034210557400 -0.000592640200  0.014807054400
      5.108150287385 -0.129597923300  0.110885902200  0.080644802300  0.120927648700 -0.120619770900  0.009852349400  0.068186159300
      2.048398039874  0.118175889400 -0.053732406400 -0.067639801700  0.251093670300 -0.213719464600  0.001286509800  0.290576499200
      0.832381575582  0.462964485000 -0.572670666200 -0.435078312800  0.352639910300 -0.473674858400 -0.021872639500  1.063344189500
      0.352316246455  0.450353782600  0.186760006700  0.722792798300  0.294708645200  0.484848376400  0.530504764700  0.307656114200
      0.142977330880  0.092715833600  0.387201458600 -0.521378340700  0.173039869300  0.717465919700 -0.436184043700  0.318346834400
      0.046760918300 -0.000255945800  0.003825849600  0.175643142900  0.009726110600  0.032498979400  0.073329259500 -0.005771736600
""",
}

PSEUDO_DATA = {
    "simple":
        """\
#
H MY-GTH-PADE-q1 MY-GTH-LDA-q1 MY-GTH-PADE MY-GTH-LDA
    1
     0.20000000    2    -4.18023680     0.72507482
    0

O MY-GTH-PADE-q6 MY-GTH-LDA-q6 MY-GTH-PADE MY-GTH-LDA
    2    4
     0.24762086    2   -16.58031797     2.39570092
    2
     0.22178614    1    18.26691718
     0.25682890    0
""",
}


@pytest.fixture()
def bsdataset():
    """Use a fixture for the next fixtures parameter for easier overriding"""
    return "simple"


@pytest.fixture(scope='function')
def cp2k_basissets(bsdataset):
    """Returns basisset objects from the data above"""
    fhandle = StringIO(BSET_DATA[bsdataset])
    bsets = {}
    for bset in BasisSet.from_cp2k(fhandle):
        bset.store()  # store because the validator accesses it when raising an error

        if bset.element in bsets:
            # if we have multiple basissets per element, pass them as a list
            if not isinstance(bsets[bset.element], list):
                bsets[bset.element] = [bsets[bset.element]]
            bsets[bset.element] += [bset]
        else:
            bsets[bset.element] = bset
    return bsets


@pytest.fixture()
def pdataset():
    """Use a fixture for the next fixtures parameter for easier overriding"""
    return "simple"


@pytest.fixture(scope='function')
def cp2k_pseudos(pdataset):
    """Returns pseudo objects from the data above"""
    fhandle = StringIO(PSEUDO_DATA[pdataset])
    return {p.element: p for p in Pseudo.from_cp2k(fhandle)}


def test_validation(cp2k_code, cp2k_basissets, cp2k_pseudos, clear_database):  # pylint: disable=unused-argument
    """Testing CP2K with the Basis Set stored in gaussian.basisset"""

    # structure
    atoms = ase.build.molecule("H2O")
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = Dict(
        dict={
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "QS": {
                        "EPS_DEFAULT": 1.0e-12,
                        "WF_INTERPOLATION": "ps",
                        "EXTRAPOLATION_ORDER": 3,
                    },
                    "MGRID": {
                        "NGRIDS": 4,
                        "CUTOFF": 280,
                        "REL_CUTOFF": 30
                    },
                    "XC": {
                        "XC_FUNCTIONAL": {
                            "_": "LDA"
                        }
                    },
                    "POISSON": {
                        "PERIODIC": "none",
                        "PSOLVER": "MT"
                    },
                },
                "SUBSYS": {
                    "KIND": [
                        {
                            "_": "O",
                            "POTENTIAL": "GTH " + cp2k_pseudos["O"].name,
                            "BASIS_SET": cp2k_basissets["O"].name,
                        },
                        {
                            "_": "H",
                            "POTENTIAL": "GTH " + cp2k_pseudos["H"].name,
                            "BASIS_SET": cp2k_basissets["H"].name,
                        },
                    ]
                },
            }
        })

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": cp2k_code,
        "metadata": {
            "options": options
        },
        "basissets": cp2k_basissets,
        "pseudos": cp2k_pseudos,
    }

    _, calc_node = run_get_node(CalculationFactory("cp2k"), **inputs)
    assert calc_node.exit_status == 0


def test_validation_fail(cp2k_code, cp2k_basissets, cp2k_pseudos, clear_database):  # pylint: disable=unused-argument
    """Testing CP2K with the Basis Set stored in gaussian.basisset but missing one"""

    # structure
    atoms = ase.build.molecule("H2O")
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = Dict(
        dict={
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "QS": {
                        "EPS_DEFAULT": 1.0e-12,
                        "WF_INTERPOLATION": "ps",
                        "EXTRAPOLATION_ORDER": 3,
                    },
                    "MGRID": {
                        "NGRIDS": 4,
                        "CUTOFF": 280,
                        "REL_CUTOFF": 30
                    },
                    "XC": {
                        "XC_FUNCTIONAL": {
                            "_": "LDA"
                        }
                    },
                    "POISSON": {
                        "PERIODIC": "none",
                        "PSOLVER": "MT"
                    },
                },
                "SUBSYS": {
                    "KIND": [
                        {
                            "_": "O",
                            "POTENTIAL": cp2k_pseudos["O"].name,
                            "BASIS_SET": cp2k_basissets["O"].name,
                        },
                        {
                            "_": "H",
                            "POTENTIAL": cp2k_pseudos["H"].name,
                            "BASIS_SET": cp2k_basissets["H"].name,
                        },
                    ]
                },
            }
        })

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": cp2k_code,
        "metadata": {
            "options": options
        },
        # add only one of the basis sets to inputs
        "basissets": {
            "H": cp2k_basissets["H"]
        },
        "pseudos": cp2k_pseudos,
    }

    with pytest.raises(PreSubmitException) as exc_info:  # the InputValidationError is masked by the process runner
        run(CalculationFactory("cp2k"), **inputs)

    assert "not found in basissets input namespace" in str(exc_info.value.__context__)


@pytest.mark.parametrize('bsdataset', ['multiple_o'])
def test_validation_unused(cp2k_code, cp2k_basissets, cp2k_pseudos, clear_database):  # pylint: disable=unused-argument
    """Pass more basissets than used in the input configuration"""

    # structure
    atoms = ase.build.molecule("H2O")
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = Dict(
        dict={
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "QS": {
                        "EPS_DEFAULT": 1.0e-12,
                        "WF_INTERPOLATION": "ps",
                        "EXTRAPOLATION_ORDER": 3,
                    },
                    "MGRID": {
                        "NGRIDS": 4,
                        "CUTOFF": 280,
                        "REL_CUTOFF": 30
                    },
                    "XC": {
                        "XC_FUNCTIONAL": {
                            "_": "LDA"
                        }
                    },
                    "POISSON": {
                        "PERIODIC": "none",
                        "PSOLVER": "MT"
                    },
                },
                "SUBSYS": {
                    "KIND": [
                        {
                            "_": "O",
                            "POTENTIAL": cp2k_pseudos["O"].name,
                            "BASIS_SET": cp2k_basissets["O"][0].name,
                        },
                        {
                            "_": "H",
                            "POTENTIAL": cp2k_pseudos["H"].name,
                            "BASIS_SET": cp2k_basissets["H"].name,
                        },
                    ]
                },
            }
        })

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": cp2k_code,
        "metadata": {
            "options": options
        },
        "basissets": cp2k_basissets,
        "pseudos": cp2k_pseudos,
    }

    with pytest.raises(PreSubmitException) as exc_info:  # the InputValidationError is masked by the process runner
        run(CalculationFactory("cp2k"), **inputs)

    assert "not used in input" in str(exc_info.value.__context__)


def test_validation_mfe_noauto(cp2k_code, cp2k_basissets, cp2k_pseudos, clear_database):  # pylint: disable=unused-argument
    """Test that multiple FORCE_EVAL without explicit assignment is rejected"""

    # structure
    pos = [[0.934, 2.445, 1.844], [1.882, 2.227, 1.982], [0.81, 3.165, 2.479], [3.59, 2.048, 2.436],
           [4.352, 2.339, 1.906], [3.953, 1.304, 2.946]]
    atoms = ase.Atoms(symbols='OH2OH2', pbc=True, cell=[5.0, 5.0, 5.0])
    atoms.set_positions(pos)
    structure = StructureData(ase=atoms)

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
                    # SUBSYS section omitted, forcing into automated assignment mode,
                    # which is not yet supported for multiple FORCE_EVAL
                },
            ]
        })

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": cp2k_code,
        "metadata": {
            "options": options
        },
        "basissets": cp2k_basissets,
        "pseudos": cp2k_pseudos,
    }

    with pytest.raises(PreSubmitException) as exc_info:  # the InputValidationError is masked by the process runner
        run(CalculationFactory("cp2k"), **inputs)

    assert "Automated BASIS_SET keyword creation is not yet supported with multiple FORCE_EVALs" in str(
        exc_info.value.__context__)


def test_validation_mfe(cp2k_code, cp2k_basissets, cp2k_pseudos, clear_database):  # pylint: disable=unused-argument
    """Test that multiple FORCE_EVAL without explicit assignment is rejected"""

    # structure
    pos = [[0.934, 2.445, 1.844], [1.882, 2.227, 1.982], [0.81, 3.165, 2.479], [3.59, 2.048, 2.436],
           [4.352, 2.339, 1.906], [3.953, 1.304, 2.946]]
    atoms = ase.Atoms(symbols='OH2OH2', pbc=True, cell=[5.0, 5.0, 5.0])
    atoms.set_positions(pos)
    structure = StructureData(ase=atoms)

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
                                'BASIS_SET': 'ORB MY-DZVP-MOLOPT-SR-GTH-q6',
                                'POTENTIAL': 'GTH MY-GTH-PADE-q6'
                            },
                            {
                                '_': 'H',
                                'BASIS_SET': 'ORB MY-DZVP-MOLOPT-GTH-q1',
                                'POTENTIAL': 'GTH MY-GTH-PADE-q1'
                            },
                        ],
                    },
                },
            ]
        })

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": cp2k_code,
        "metadata": {
            "options": options
        },
        "basissets": cp2k_basissets,
        "pseudos": cp2k_pseudos,
    }

    _, calc_node = run_get_node(CalculationFactory("cp2k"), **inputs)
    assert calc_node.exit_status == 0


def test_without_kinds(cp2k_code, cp2k_basissets, cp2k_pseudos, clear_database):  # pylint: disable=unused-argument
    """Testing CP2K with the Basis Set stored in gaussian.basisset but without a KIND section"""

    # structure
    atoms = ase.build.molecule("H2O")
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = Dict(
        dict={
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "QS": {
                        "EPS_DEFAULT": 1.0e-12,
                        "WF_INTERPOLATION": "ps",
                        "EXTRAPOLATION_ORDER": 3,
                    },
                    "MGRID": {
                        "NGRIDS": 4,
                        "CUTOFF": 280,
                        "REL_CUTOFF": 30
                    },
                    "XC": {
                        "XC_FUNCTIONAL": {
                            "_": "LDA"
                        }
                    },
                    "POISSON": {
                        "PERIODIC": "none",
                        "PSOLVER": "MT"
                    },
                },
            }
        })

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }

    inputs = {
        "structure": structure,
        "parameters": parameters,
        "code": cp2k_code,
        "metadata": {
            "options": options
        },
        "basissets": cp2k_basissets,
        "pseudos": cp2k_pseudos,
    }

    _, calc_node = run_get_node(CalculationFactory("cp2k"), **inputs)
    assert calc_node.exit_status == 0
