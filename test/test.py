#!/usr/bin/env python
# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/cp2k/aiida-cp2k      #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################

import os
import sys
import time
import subprocess
import numpy as np
from os import path

import ase.build

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

from aiida.common.example_helpers import test_and_get_code
from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.singlefile import SinglefileData

#===============================================================================
def main():
    if len(sys.argv) != 2:
        print("Usage: test.py <code_name>")
        sys.exit(1)

    codename = sys.argv[1]
    code = test_and_get_code(codename, expected_code_type='cp2k')
    test_energy_mm(code)
    test_energy_dft(code)
    test_geo_opt_dft(code)
    test_no_structure_data(code)
    print("All tests passed :-)")
    sys.exit(0)

#===============================================================================
def test_energy_mm(code):
    print("Testing CP2K ENERGY on H2O (MM) ...")

    # calc object
    calc = code.new_calc()

    # parameters
    # based on cp2k/tests/Fist/regtest-1-1/water_1.inp
    parameters = ParameterData(dict={
            'FORCE_EVAL':{
                'METHOD': 'fist',
                'MM': {
                    'FORCEFIELD': {
                        'PARM_FILE_NAME': 'water.pot',
                        'PARMTYPE': 'CHM',
                        'CHARGE':[
                            {'ATOM':'O', 'CHARGE': -0.8476},
                            {'ATOM':'H', 'CHARGE': 0.4238},]
                    },
                    'POISSON': {'EWALD':{
                        'EWALD_TYPE':'spme',
                        'ALPHA': 0.44,
                        'GMAX': 24,
                        'O_SPLINE': 6
                    }}
                }
            },
            'GLOBAL': {
                'CALLGRAPH': 'master',
                'CALLGRAPH_FILE_NAME': 'runtime'
            }
    })
    calc.use_parameters(parameters)

    # force field
    with open("water.pot", "w") as f:
        f.write("""BONDS
H    H       0.000     1.5139
O    H     450.000     0.9572

ANGLES
H    O    H      55.000   104.5200

DIHEDRALS

IMPROPER

NONBONDED
H      0.000000  -0.046000     0.224500
O      0.000000  -0.152100     1.768200

HBOND CUTHB 0.5

END""")
    water_pot = SinglefileData(file=path.abspath("water.pot"))
    calc.use_file(water_pot, linkname="water_pot")

    # structure
    atoms = ase.build.molecule('H2O')
    atoms.center(vacuum=10.0)
    structure = StructureData(ase=atoms)
    calc.use_structure(structure)

    # settings
    settings = ParameterData(dict={'additional_retrieve_list':["runtime.callgraph"]})
    calc.use_settings(settings)

    # resources
    calc.set_max_wallclock_seconds(3*60) # 3 min
    calc.set_resources({"num_machines": 1})

    # store and submit
    calc.store_all()
    calc.submit()
    print "submitted calculation: UUID=%s, pk=%s"%(calc.uuid,calc.dbnode.pk)

    wait_for_calc(calc)

    # check warnings
    assert calc.res.nwarnings == 0

    # check energy
    expected_energy = 0.146927412614e-3
    if abs(calc.res.energy - expected_energy) < 1e-10:
        print "OK, energy has the expected value"
    else:
        print "ERROR!"
        print "Expected energy value: {}".format(expected_energy)
        print "Actual energy value: {}".format(calc.res.energy)
        sys.exit(3)

    # check if callgraph is there
    if "runtime.callgraph" in calc.out.retrieved.get_folder_list():
        print "OK, callgraph file was retrived"
    else:
        print "ERROR!"
        print "Callgraph file was not retrieved."
        sys.exit(3)

#===============================================================================
def test_energy_dft(code):
    print("Testing CP2K ENERGY on H2O (DFT)...")

    # calc object
    calc = code.new_calc()

    # structure
    atoms = ase.build.molecule('H2O')
    atoms.center(vacuum=2.0)
    structure = StructureData(ase=atoms)
    calc.use_structure(structure)

    # parameters
    parameters = ParameterData(dict={'FORCE_EVAL':get_force_eval()})
    calc.use_parameters(parameters)

    # resources
    calc.set_max_wallclock_seconds(3*60) # 3 min
    calc.set_resources({"num_machines": 1})

    # store and submit
    calc.store_all()
    calc.submit()
    print "submitted calculation: UUID=%s, pk=%s"%(calc.uuid,calc.dbnode.pk)

    wait_for_calc(calc)

    # check energy
    expected_energy = -17.1566368539
    if abs(calc.res.energy - expected_energy) < 1e-10:
        print "OK, energy has the expected value"
    else:
        print "ERROR!"
        print "Expected energy value: {}".format(expected_energy)
        print "Actual energy value: {}".format(calc.res.energy)
        sys.exit(3)

#===============================================================================
def test_geo_opt_dft(code):
    print("Testing CP2K GEO_OPT on H2 (DFT)...")

    # calc object
    calc = code.new_calc()

    # structure
    atoms = ase.build.molecule('H2')
    atoms.center(vacuum=2.0)
    vec = atoms.positions[0,:] - atoms.positions[1,:]
    structure = StructureData(ase=atoms)
    calc.use_structure(structure)

    # parameters
    parameters = ParameterData(dict={
        'GLOBAL': {
            'RUN_TYPE': 'GEO_OPT',
        },
        'FORCE_EVAL': get_force_eval()
    })
    calc.use_parameters(parameters)

    # resources
    calc.set_max_wallclock_seconds(3*60) # 3 min
    calc.set_resources({"num_machines": 1})

    # store and submit
    calc.store_all()
    calc.submit()
    print "submitted calculation: UUID=%s, pk=%s"%(calc.uuid,calc.dbnode.pk)

    wait_for_calc(calc)

    # check energy
    expected_energy = -1.14009973333
    if abs(calc.res.energy - expected_energy) < 1e-10:
        print "OK, energy has the expected value"
    else:
        print "ERROR!"
        print "Expected energy value: {}".format(expected_energy)
        print "Actual energy value: {}".format(calc.res.energy)
        sys.exit(3)

    # check geometry
    expected_dist = 0.737 # pdb format has only three digits
    dist = calc.out.output_structure.get_ase().get_distance(0, 1)
    if abs(dist - expected_dist) < 1e-7:
        print "OK, H-H distance has the expected value"
    else:
        print "ERROR!"
        print "Expected dist value: {}".format(expected_dist)
        print "Actual dist value: {}".format(dist)
        sys.exit(3)

#===============================================================================
def test_no_structure_data(code):
    print("Testing CP2K ENERGY on H2 (DFT) without StructureData...")

    # calc object
    calc = code.new_calc()

    # structure directly included in parameters
    force_eval = get_force_eval()
    force_eval['SUBSYS']['CELL'] = {'ABC': '4.0   4.0   4.75'}
    force_eval['SUBSYS']['COORD'] = {' ': ['H    2.0   2.0   2.737166',
                                           'H    2.0   2.0   2.000000']}

    # parameters
    parameters = ParameterData(dict={'FORCE_EVAL':force_eval})
    calc.use_parameters(parameters)

    # resources
    calc.set_max_wallclock_seconds(3*60) # 3 min
    calc.set_resources({"num_machines": 1})

    # store and submit
    calc.store_all()
    calc.submit()
    print "submitted calculation: UUID=%s, pk=%s"%(calc.uuid,calc.dbnode.pk)

    wait_for_calc(calc)

    # check energy
    expected_energy = -1.14005678487
    if abs(calc.res.energy - expected_energy) < 1e-10:
        print "OK, energy has the expected value"
    else:
        print "ERROR!"
        print "Expected energy value: {}".format(expected_energy)
        print "Actual energy value: {}".format(calc.res.energy)
        sys.exit(3)

#===============================================================================
def get_force_eval():
    return {
            'METHOD': 'Quickstep',
            'DFT': {
                'BASIS_SET_FILE_NAME': 'BASIS_MOLOPT',
                'QS': {
                    'EPS_DEFAULT': 1.0e-12,
                    'WF_INTERPOLATION': 'ps',
                    'EXTRAPOLATION_ORDER': 3,
                },
                'MGRID': {
                    'NGRIDS': 4,
                    'CUTOFF': 280,
                    'REL_CUTOFF': 30,
                },
                'XC': {
                    'XC_FUNCTIONAL': {
                        '_': 'LDA',
                    },
                },
                'POISSON': {
                    'PERIODIC': 'none',
                    'PSOLVER': 'MT',
                },
            },
            'SUBSYS': {
                'KIND': [
                    {'_': 'O', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH', 'POTENTIAL': 'GTH-LDA-q6' },
                    {'_': 'H', 'BASIS_SET': 'DZVP-MOLOPT-SR-GTH', 'POTENTIAL': 'GTH-LDA-q1' },
                ],
            },
        }

#===============================================================================
def wait_for_calc(calc, timeout_secs=5*60.0):
    print "Wating for end of execution..."
    start_time = time.time()
    exited_with_timeout = True
    while time.time() - start_time < timeout_secs:
        time.sleep(15) # Wait a few seconds
        # print some debug info, both for debugging reasons and to avoid
        # that the test machine is shut down because there is no output
        print "#"*78
        print "####### TIME ELAPSED: {} s".format(time.time() - start_time)
        print "#"*78
        print "Output of 'verdi calculation list':"
        try:
            cmd = ["verdi", "calculation", "list"]
            print subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print "Note: the command failed, message: {}".format(e.message)
        if calc.has_finished():
            print "Calculation terminated its execution."
            exited_with_timeout = False
            break

    # check for timeout
    if exited_with_timeout:
        print "Timeout!! Calculation did not complete after %i seconds" % timeout_secs
        os.system("cat ~/.aiida/daemon/log/aiida_daemon.log")
        sys.exit(2)

    # check calculation status
    if calc.has_failed():
        print "Calculation failed with state: " + calc.get_state()
        os.system("cat ~/.aiida/daemon/log/aiida_daemon.log")
        sys.exit(2)

#===============================================================================
if __name__ == "__main__":
    main()

#EOF
