# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
""" Test/example for the Cp2kMultistageWorkChain"""

from __future__ import print_function
from __future__ import absolute_import

import os
import click
import ase.build

from aiida.engine import run
from aiida.orm import Code, Dict, StructureData, Str, Int
from aiida_cp2k.workchains import Cp2kMultistageWorkChain


@click.command('cli')
@click.argument('codelabel')
def main(codelabel):
    """Example usage: verdi run thistest.py cp2k@localhost"""

    print("Testing CP2K multistage workchain on Al (RKS, needs smearing)...")
    print("EXPECTED: the OT (settings_0) will converge to a negative bandgap, then we switch to SMEARING (settings_1)")

    code = Code.get_from_string(codelabel)

    thisdir = os.path.dirname(os.path.abspath(__file__))
    structure = StructureData(ase=ase.io.read(os.path.join(thisdir, '../data/Al.cif')))

    # testing user change of parameters and protocol
    parameters = Dict(dict={'FORCE_EVAL': {'DFT': {'MGRID': {'CUTOFF': 250,}}}})
    protocol_mod = Dict(dict={
        'initial_magnetization': {
            'Al': 0
        },
        'settings_0': {
            'FORCE_EVAL': {
                'DFT': {
                    'SCF': {
                        'OUTER_SCF': {
                            'MAX_SCF': 5,
                        }
                    }
                }
            }
        }
    })
    options = {
        "resources": {
            "num_machines": 1,
            "num_mpiprocs_per_machine": 1,
        },
        "max_wallclock_seconds": 1 * 3 * 60,
    }
    inputs = {
        'structure': structure,
        'protocol_tag': Str('test'),
        'starting_settings_idx': Int(0),
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
