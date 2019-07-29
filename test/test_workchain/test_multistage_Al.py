# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from __future__ import print_function
from __future__ import absolute_import

import sys
import ase.build

from aiida.engine import run
from aiida.orm import (Code, Dict, StructureData)
from aiida.common import NotExistent
from aiida_cp2k.workchains import Cp2kMultistageWorkChain

# =============================================================================
if len(sys.argv) != 2:
    print("Usage: test.py <code_name>")
    sys.exit(1)

codename = sys.argv[1]
try:
    code = Code.get_from_string(codename)
except NotExistent:
    print("The code '{}' does not exist".format(codename))
    sys.exit(1)

print("Testing CP2K multistage workchain on Al (RKS, needs smearing)...")
print("EXPECTED: the OT (settings_0) will converge to a negative bandgap, then we switch to SMEARING (settings_1)")

# structure
structure = StructureData(ase=ase.io.read('../data/Al.cif'))

# lowering the settings for acheaper calculation
parameters = Dict(dict={
        'FORCE_EVAL': {
          'DFT': {
            'MGRID': {
              'CUTOFF': 280,
              'REL_CUTOFF': 30,
}}}})

protocol_mod = Dict(dict= {
    'initial_magnetization': {
        'Al': 0
        },
    'settings_0': {
        'FORCE_EVAL': {
            'DFT': {
                'SCF': {
                    'OUTER_SCF': {
                        'MAX_SCF': 5,
}}}}}})

options = {
    "resources": {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    },
    "max_wallclock_seconds": 1 * 3 * 60,
}
inputs = {
    'protocol_tag': 'test',
    'starting_settings_idx': Int(0),
    'protocol_modify': protocol_mod,
    'base': {
        'cp2k': {
            'structure': structure,
            'parameters': parameters,
            'code': code,
            'metadata': {
                'options': options,
            }
        }
    }
}

run(Cp2kMultistageWorkChain, **inputs)
