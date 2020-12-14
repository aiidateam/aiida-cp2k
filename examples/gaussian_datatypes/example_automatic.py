# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Simple DFT calculations with Gaussian Datatypes examples"""

import os
import sys

import click
import ase.io

from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import (Code, Dict)
from aiida.plugins import DataFactory

from gdt_data import load_data

StructureData = DataFactory('structure')  # pylint: disable=invalid-name


def example_gdt(cp2k_code):
    """
    Testing CP2K with the Basis Set and Pseudopotential stored in gaussian.basisset/pseudo.
    In this example the KIND section is omitted completely and the aiida-cp2k plugin will
    automatically assign basissets and pseudopotential data based on the different kinds of
    the structure. This only works if the assignment can be done unambiguously, hence the
    need to give a list of basissets and pseudos to be used. You can also not give more
    basissets or pseudos than actually required to avoid false links in the provenance graph.
    """

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # Structure.
    structure = StructureData(ase=ase.io.read(os.path.join(thisdir, '..', "files", 'h2o.xyz')))

    bsets, pseudos = load_data(prefix="MY-AUTO-")
    # in your code you will probably use something like:
    #   bsets = [
    #     BasisSet.get(element="H", name="DZVP-MOLOPT-GTH")
    #     BasisSet.get(element="O", name="DZVP-MOLOPT-SR-GTH")
    #   ]
    # ...

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

    # Construct process builder.
    builder = cp2k_code.get_builder()
    builder.structure = structure
    builder.parameters = parameters
    builder.code = cp2k_code
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 3 * 60
    builder.basissets = bsets
    builder.pseudos = pseudos

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
    example_gdt(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
