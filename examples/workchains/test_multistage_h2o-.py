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
@click.argument('codelabel')
def main(codelabel):
    """Example usage: verdi run thistest.py cp2k@localhost"""

    print("Testing CP2K multistage workchain on 2xH2O- (UKS, no need for smearing)...")
    print("This is checking:")
    print(" > unit cell resizing")
    print(" > protocol modification")
    print(" > cp2k calc modification")

    code = Code.get_from_string(codelabel)

    atoms = ase.build.molecule('H2O')
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)

    protocol_mod = Dict(dict={'settings_0': {'FORCE_EVAL': {'DFT': {'MGRID': {'CUTOFF': 300,}}}}})
    parameters = Dict(dict={'FORCE_EVAL': {
        'DFT': {
            'UKS': True,
            'MULTIPLICITY': 3,
            'CHARGE': -2,
        }
    }})
    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }
    inputs = {
        'structure': structure,
        'min_cell_size': Float(4.1),  #this will make the cell expand in the x direction
        'protocol_tag': Str('test'),
        'protocol_modify': protocol_mod,
        'cp2k_base': {
            'cp2k': {
                'parameters': parameters,
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
