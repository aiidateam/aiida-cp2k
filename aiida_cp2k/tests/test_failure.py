# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test detection of failed calculations"""

from __future__ import print_function
from __future__ import absolute_import

import pytest

from . import get_computer, get_code


@pytest.mark.process_execution
def test_run_failure(new_workdir):
    """Testing CP2K failure"""

    from aiida.engine import run
    from aiida.plugins import CalculationFactory
    from aiida.orm import Dict
    from aiida.common.exceptions import OutputParsingError

    computer = get_computer(workdir=new_workdir)
    code = get_code(entry_point="cp2k", computer=computer)

    # a broken CP2K input
    parameters = Dict(dict={"GLOBAL": {"FOO_BAR_QUUX": 42}})
    options = {
        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        "max_wallclock_seconds": 1 * 2 * 60,
    }

    print("Submitted calculation...")
    inputs = {"parameters": parameters, "code": code, "metadata": {"options": options}}

    with pytest.raises(OutputParsingError):
        run(CalculationFactory("cp2k"), **inputs)
