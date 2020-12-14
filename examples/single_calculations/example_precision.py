# -*- coding: utf-8 -*-
# pylint: disable=invalid-name
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test structure roundtrip precision ase->aiida->cp2k->aiida->ase."""

import os
import sys
import click

import ase
import numpy as np

from aiida.common import NotExistent
from aiida.engine import run
from aiida.orm import (Code, Dict, SinglefileData)
from aiida.plugins import DataFactory

StructureData = DataFactory('structure')  # pylint: disable=invalid-name


def example_precision(cp2k_code):
    """Test structure roundtrip precision ase->aiida->cp2k->aiida->ase."""

    print("Testing structure roundtrip precision ase->aiida->cp2k->aiida->ase...")

    thisdir = os.path.dirname(os.path.realpath(__file__))

    # Structure.
    epsilon = 1e-10  # expected precision in Angstrom
    dist = 0.74 + epsilon
    positions = [(0, 0, 0), (0, 0, dist)]
    cell = np.diag([4, -4, 4 + epsilon])
    atoms = ase.Atoms('H2', positions=positions, cell=cell)
    structure = StructureData(ase=atoms)

    # Basis set.
    basis_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "BASIS_MOLOPT"))

    # Pseudopotentials.
    pseudo_file = SinglefileData(file=os.path.join(thisdir, "..", "files", "GTH_POTENTIALS"))

    # Parameters.
    parameters = Dict(
        dict={
            'GLOBAL': {
                'RUN_TYPE': 'MD',
            },
            'MOTION': {
                'MD': {
                    'TIMESTEP': 0.0,  # do not move atoms
                    'STEPS': 1,
                },
            },
            'FORCE_EVAL': {
                'METHOD': 'Quickstep',
                'DFT': {
                    'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
                    'POTENTIAL_FILE_NAME': 'GTH_POTENTIALS',
                    'SCF': {
                        'MAX_SCF': 1,
                    },
                    'XC': {
                        'XC_FUNCTIONAL': {
                            '_': 'LDA',
                        },
                    },
                },
                'SUBSYS': {
                    'KIND': {
                        '_': 'DEFAULT',
                        'BASIS_SET': 'DZVP-MOLOPT-SR-GTH',
                        'POTENTIAL': 'GTH-LDA',
                    },
                },
            },
        })

    # Construct process builder.
    builder = cp2k_code.get_builder()
    builder.structure = structure
    builder.parameters = parameters
    builder.code = cp2k_code
    builder.file = {
        'basis': basis_file,
        'pseudo': pseudo_file,
    }
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 1 * 60 * 60

    print("Submitted calculation...")
    calc = run(builder)

    # Check structure preservation.
    atoms2 = calc['output_structure'].get_ase()

    # Zeros should be preserved exactly.
    if np.all(atoms2.positions[0] == 0.0):
        print("OK, zeros in structure were preserved exactly.")
    else:
        print("ERROR!")
        print("Zeros in structure changed: ", atoms2.positions[0])
        sys.exit(3)

    # Other values should be preserved with epsilon precision.
    dist2 = atoms2.get_distance(0, 1)
    if abs(dist2 - dist) < epsilon:
        print("OK, structure preserved with %.1e Angstrom precision" % epsilon)
    else:
        print("ERROR!")
        print("Structure changed by %e Angstrom" % abs(dist - dist2))
        sys.exit(3)

    # Check cell preservation.
    cell_diff = np.amax(np.abs(atoms2.cell - cell))
    if cell_diff < epsilon:
        print("OK, cell preserved with %.1e Angstrom precision" % epsilon)
    else:
        print("ERROR!")
        print("Cell changed by %e Angstrom" % cell_diff)
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
    example_precision(code)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
