# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel
"""Base workchain command"""

import click

from aiida.cmdline.params import options, types
from aiida.cmdline.utils import decorators, echo

from . import cmd_launch
from ..utils import cp2k_options, launch_process
from ..utils.structure import structure_from_cp2k_inp


@cmd_launch.command('base')
@options.CODE(required=True, type=types.CodeParamType(entry_point='cp2k'))
@click.argument('cp2k-input-file', type=click.File('r'))
@click.option('-l', '--label', type=str)
@click.option('-m', '--description', type=str)
@cp2k_options.STRUCTURE()
@cp2k_options.DAEMON()
@decorators.with_dbenv()
def cmd_launch_workflow(code, daemon, cp2k_input_file, label, description, structure):
    """Run a CP2K calculation with a given input file through AiiDA"""

    from aiida.orm import Dict
    from aiida.plugins import WorkflowFactory
    from cp2k_input_tools.parser import CP2KInputParserSimplified

    parser = CP2KInputParserSimplified(key_trafo=str.upper,
                                       multi_value_unpack=False,
                                       repeated_section_unpack=False,
                                       level_reduction_blacklist=["KIND"])
    tree = parser.parse(cp2k_input_file)

    builder = WorkflowFactory('cp2k.base').get_builder()

    builder.cp2k.code = code

    if structure:
        builder.cp2k.structure = structure

        try:
            tree["FORCE_EVAL"]["SUBSYS"]["TOPOLOGY"].pop("COORD_FILE_NAME")
            echo.echo_info("The explicitly given structure overrides the structure referenced in the input file")
        except KeyError:
            pass

    else:
        try:
            with open(cp2k_input_file.name, "r") as fhandle:
                builder.cp2k.structure = structure_from_cp2k_inp(fhandle)
            builder.cp2k.structure.store()
            echo.echo("Created StructureData<{}> from file {}]\n".format(builder.cp2k.structure.pk,
                                                                         cp2k_input_file.name))
        except ValueError as err:
            echo.echo_critical(str(err))

    builder.cp2k.metadata.options = {
        "resources": {
            "num_machines": 1,
        },
    }
    builder.cp2k.parameters = Dict(dict=tree)

    if label:
        builder.metadata.label = label

    if description:
        builder.metadata.description = description

    launch_process(builder, daemon)
