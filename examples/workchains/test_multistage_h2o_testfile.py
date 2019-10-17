# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
""" Test/example for the Cp2kMultistageWorkChain"""

from __future__ import print_function
from __future__ import absolute_import

import os
import click
import ase.build

from aiida.engine import run
from aiida.orm import Code, StructureData, SinglefileData
from aiida.plugins import WorkflowFactory

Cp2kMultistageWorkChain = WorkflowFactory('cp2k.multistage')


@click.command('cli')
@click.argument('codelabel')
def main(codelabel):
    """Example usage: verdi run thistest.py cp2k@localhost"""

    print("Testing CP2K multistage workchain on H2O")
    print(">>> Loading a custom protocol from file testfile.yaml")

    code = Code.get_from_string(codelabel)

    atoms = ase.build.molecule('H2O')
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    thisdir = os.path.dirname(os.path.abspath(__file__))

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }
    inputs = {
        'structure': structure,
        'protocol_yaml': SinglefileData(file=os.path.abspath(os.path.join(thisdir, '..', 'data', 'testfile.yaml'))),
        'cp2k_base': {
            'cp2k': {
                'code': code,
                'metadata': {
                    'options': options,
                }
            }
        }
    }

    run(Cp2kMultistageWorkChain, **inputs)


if __name__ == '__main__':
    main()  # pylint: disable=no-value-for-parameter
