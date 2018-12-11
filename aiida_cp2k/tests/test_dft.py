#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

import pytest

from . import get_code, calculation_execution_test


@pytest.mark.process_execution
def test_process(new_database, new_workdir):  # pylint: disable=unused-argument
    from aiida.orm.data.structure import StructureData
    from aiida.orm.data.parameter import ParameterData
    import ase.build

    code = get_code(entry_point='cp2k')

    atoms = ase.build.molecule('H2O')
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

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
                'KIND': [
                    {'_': 'O', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH', 'POTENTIAL': 'GTH-LDA-q6'},
                    {'_': 'H', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH', 'POTENTIAL': 'GTH-LDA-q1'},
                ],
            },
        }
    })

    calc = code.new_calc()

    calc.label = "AiiDA CP2K DFT test"
    calc.description = "Test job submission with the AiiDA CP2K plugin with DFT"

    # resources

    calc.set_max_wallclock_seconds(3*60)  # 3 min
    calc.set_withmpi(False)
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})

    calc.use_structure(structure)
    calc.use_parameters(parameters)

    # store and submit
    calc.store_all()

    calculation_execution_test(calc, check_paths=[calc._OUTPUT_FILE_NAME])
