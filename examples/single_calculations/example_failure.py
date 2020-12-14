# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Run failing calculation."""

import sys
import click

from aiida.common import NotExistent
from aiida.engine import run_get_node
from aiida.orm import (Code, Dict)


def example_failure(cp2k_code):
    """Run failing calculation."""

    print("Testing CP2K failure...")

    # a broken CP2K input
    parameters = Dict(dict={'GLOBAL': {'FOO_BAR_QUUX': 42}})

    print("Submitted calculation...")

    # Construct process builder
    builder = cp2k_code.get_builder()
    builder.parameters = parameters
    builder.code = cp2k_code
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 2 * 60

    _, calc_node = run_get_node(builder)

    if calc_node.exit_status == 304:
        print("CP2K failure correctly recognized.")
    else:
        print("ERROR!")
        print("CP2K failure was not recognized.")
        sys.exit(3)


@click.command('cli')
@click.argument('codelabel')
def cli(codelabel):
    """Click interface."""
    try:
        code = Code.get_from_string(codelabel)
    except NotExistent:
        print("The code '{}' does not exist.".format(codelabel))
        sys.exit(1)
    example_failure(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
