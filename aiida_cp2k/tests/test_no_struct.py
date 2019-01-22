#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

import os
import pytest

from . import get_code, calculation_execution_test, get_retrieved


FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'files/no_struct')


def get_calc():
    """prepare a calculation object"""

    from aiida.orm.data.parameter import ParameterData

    parameters = ParameterData(dict={
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
                'CELL': {'ABC': '4.0   4.0   4.75'},
                'COORD': {' ': ['H    2.0   2.0   2.737166',
                                'H    2.0   2.0   2.000000']},
                'KIND': [
                    {'_': 'O', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                        'POTENTIAL': 'GTH-LDA-q6'},
                    {'_': 'H', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                        'POTENTIAL': 'GTH-LDA-q1'},
                ],
            },
        }
    })

    code = get_code(entry_point='cp2k')
    calc = code.new_calc()

    calc.label = "AiiDA CP2K test"
    calc.description = "Test job submission with the AiiDA CP2K plugin"

    # resources

    calc.set_max_wallclock_seconds(3*60)  # 3 min
    calc.set_withmpi(False)
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})

    calc.use_parameters(parameters)

    return calc


@pytest.mark.process_execution
def test_calc(new_database, new_workdir):
    calc = get_calc()

    # store and submit
    calc.store_all()

    calculation_execution_test(calc, check_paths=[calc._OUTPUT_FILE_NAME])


def test_parser(new_database, new_workdir):
    """Test the CP2K output parser"""

    from aiida_cp2k.parsers import Cp2kParser

    parser = Cp2kParser(get_calc())
    success, node_list = parser.parse_with_retrieved(get_retrieved(FIXTURE_DIR, ['aiida.out']))

    # check that parsing worked
    assert success

    # make sure we got the expected output nodes
    node_dict = {n[0]: n[1] for n in node_list}
    assert all(key in node_dict.keys() for key in ['output_parameters']), (
        "list of output nodes is missing some required nodes")

    # check the parsed energy
    expected_energy = -1.14005678487
    energy = node_dict['output_parameters'].get_dict()['energy']
    assert abs(energy - expected_energy) < 1e-10, (
        f"calculated energy value {energy} differs from reference {expected_energy}")
