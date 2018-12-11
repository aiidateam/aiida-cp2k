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
    from aiida.orm.data.parameter import ParameterData

    # a broken CP2K input
    parameters = ParameterData(dict={'GLOBAL': {'FOO_BAR_QUUX': 42}})

    code = get_code(entry_point='cp2k')

    calc = code.new_calc()

    calc.label = "AiiDA CP2K Failure test"
    calc.description = "Test job submission with the AiiDA CP2K plugin with invalid config"

    # resources

    calc.set_max_wallclock_seconds(3*60)  # 3 min
    calc.set_withmpi(False)
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})

    calc.use_parameters(parameters)

    # store and submit
    calc.store_all()

    with pytest.raises(RuntimeError):
        calculation_execution_test(calc, check_paths=[calc._OUTPUT_FILE_NAME])
