# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run failing calculation"""
from __future__ import print_function
from __future__ import absolute_import

import sys
import click

from aiida.orm import (Code, Dict)
from aiida.common import NotExistent
from aiida.engine import run
from aiida.common.exceptions import OutputParsingError
from aiida.plugins import CalculationFactory

Cp2kCalculation = CalculationFactory('cp2k')


@click.command('cli')
@click.argument('codelabel')
def main(codelabel):
    """Run failing calculation"""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist".format(codelabel))
        sys.exit(1)

    print("Testing CP2K failure...")

    # a broken CP2K input
    parameters = Dict(dict={'GLOBAL': {'FOO_BAR_QUUX': 42}})
    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 2 * 60,
    }

    print("Submitted calculation...")
    inputs = {'parameters': parameters, 'code': code, 'metadata': {'options': options,}}
    try:
        run(Cp2kCalculation, **inputs)
        print("ERROR!")
        print("CP2K failure was not recognized")
        sys.exit(3)
    except OutputParsingError:
        print("CP2K failure correctly recognized")

    sys.exit(0)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
