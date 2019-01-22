#!/usr/bin/env python
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

import os
import pytest

from . import get_code, calculation_execution_test, get_retrieved

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'files/mm')


def get_calc(new_workdir):
    from aiida.orm.data.structure import StructureData
    from aiida.orm.data.parameter import ParameterData
    from aiida.orm.data.singlefile import SinglefileData
    import ase.build

    water_pot = SinglefileData(file=os.path.join(FIXTURE_DIR, "water.pot"))

    # structure using pdb format, because it also carries topology information
    atoms = ase.build.molecule('H2O')
    atoms.center(vacuum=10.0)

    coords_pdb_path = os.path.join(new_workdir, "coords.pdb")
    atoms.write(coords_pdb_path, format="proteindatabank")
    coords_pdb = SinglefileData(file=coords_pdb_path)

    # parameters, based on cp2k/tests/Fist/regtest-1-1/water_1.inp
    parameters = ParameterData(dict={
        'FORCE_EVAL': {
            'METHOD': 'fist',
            'MM': {
                'FORCEFIELD': {
                    'PARM_FILE_NAME': 'water.pot',
                    'PARMTYPE': 'CHM',
                    'CHARGE': [
                        {'ATOM': 'O', 'CHARGE': -0.8476},
                        {'ATOM': 'H', 'CHARGE': 0.4238}]
                },
                'POISSON': {'EWALD': {
                    'EWALD_TYPE': 'spme',
                    'ALPHA': 0.44,
                    'GMAX': 24,
                    'O_SPLINE': 6
                }}
            },
            'SUBSYS': {
                'CELL': {
                    'ABC': '%f  %f  %f' % tuple(atoms.cell.diagonal()),
                },
                'TOPOLOGY': {
                    'COORD_FILE_NAME': 'coords.pdb',
                    'COORD_FILE_FORMAT': 'PDB',
                },
            },
        },
        'GLOBAL': {
            'CALLGRAPH': 'master',
            'CALLGRAPH_FILE_NAME': 'runtime'
        }
    })

    settings = ParameterData(dict={'additional_retrieve_list': ["runtime.callgraph"]})

    code = get_code(entry_point='cp2k')
    calc = code.new_calc()
    calc.use_file(water_pot, linkname="water_pot")
    calc.use_file(coords_pdb, linkname="coords_pdb")
    calc.use_parameters(parameters)
    calc.use_settings(settings)

    # resources
    calc.set_max_wallclock_seconds(3*60)  # 3 min
    calc.set_withmpi(False)
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})

    return calc


@pytest.mark.process_execution
def test_calc(new_database, new_workdir):
    calc = get_calc(new_workdir)

    # store and submit
    calc.store_all()

    check_paths = [calc._OUTPUT_FILE_NAME, "runtime.callgraph"]

    calculation_execution_test(calc, check_paths=check_paths)


def test_parser(new_database, new_workdir):
    """Test the CP2K output parser"""

    from aiida_cp2k.parsers import Cp2kParser

    calc = get_calc(new_workdir)
    parser = Cp2kParser(calc)
    check_paths = [calc._OUTPUT_FILE_NAME, "runtime.callgraph"]
    success, node_list = parser.parse_with_retrieved(get_retrieved(FIXTURE_DIR, check_paths))

    # check that parsing worked
    assert success

    # make sure we got the expected output nodes
    node_dict = {n[0]: n[1] for n in node_list}
    assert all(key in node_dict.keys() for key in ['output_parameters']), (
        "list of output nodes is missing some required nodes")

    # check warnings
    assert not node_dict['output_parameters'].get_dict()['nwarnings']

    # check the parsed energy
    expected_energy = 0.146927412614e-3
    energy = node_dict['output_parameters'].get_dict()['energy']
    assert abs(energy - expected_energy) < 1e-10, (
        f"calculated energy value {energy} differs from reference {expected_energy}")
