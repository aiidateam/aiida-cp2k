# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
""" Test/example for the Cp2kMultistageWorkChain"""

from __future__ import print_function
from __future__ import absolute_import

import click
import ase.build

from aiida.engine import run
from aiida.orm import Code, Dict, StructureData, Float, Str
from aiida_cp2k.workchains import Cp2kMultistageWorkChain

@click.command('cli')
@click.argument('cp2k_code_string')
def main(cp2k_code_string):
    """Example usage: verdi run cp2k-5.1@localhost"""

    print("Testing CP2K multistage workchain on H2O")
    print(">>> Making it fail because of an unphysical Multiplicity")

    code = Code.get_from_string(cp2k_code_string)

    atoms = ase.build.molecule('H2O')
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }
    parameters = Dict(dict={
            'FORCE_EVAL': {
              'DFT': {
                'UKS': True,
                'MULTIPLICITY': 666,
    }}})
    inputs = {
        'protocol_tag': Str('test'),
        'cp2k_base': {
            'max_iterations': Int(1),
            'cp2k': {
                'parameters': parameters,
                'structure': structure,
                'code': code,
                'metadata': {
                    'options': options,
    }}}}
    run(Cp2kMultistageWorkChain, **inputs)

if __name__ == '__main__':
    main()
