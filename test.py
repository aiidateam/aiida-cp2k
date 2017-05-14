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

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

import sys
import os
import time
import subprocess
import ase.build

from aiida.common.example_helpers import test_and_get_code
from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData

timeout_secs = 5*60.
codename = 'cp2k@torquessh'

#-------------------------------------------------------------------------------
def main():
    # calc object
    code = test_and_get_code(codename, expected_code_type='cp2k')
    calc = code.new_calc()
    calc.label = "Test CP2K. Water molecule"
    calc.description = "Test calculation with the CP2K code. Water molecule"

    # structure
    ase_struct = ase.build.molecule('H2O')
    ase_struct.center(vacuum=2.0)
    structure = StructureData(ase=ase_struct)
    calc.use_structure(structure)

    # parameters
    parameters = ParameterData(dict={
        'force_eval': {
            'method': 'Quickstep',
            'dft': {
                'basis_set_file_name': 'BASIS_MOLOPT',
                'qs': {
                    'eps_default': 1.0e-12,
                    'wf_interpolation': 'ps',
                    'extrapolation_order': 3,
                },
                'mgrid': {
                    'ngrids': 4,
                    'cutoff':280,
                    'rel_cutoff': 30,
                },
                'xc': {
                    'xc_functional': {
                        '_': 'LDA',
                    },
                },
                'poisson': {
                    'periodic': 'none',
                    'psolver': 'MT',
                },
            },
            'subsys': {
                'kind': [
                    {'_':'O', 'basis_set':'DZVP-MOLOPT-SR-GTH',  'potential': 'GTH-LDA' },
                    {'_':'H', 'basis_set':'DZVP-MOLOPT-SR-GTH',  'potential': 'GTH-LDA' },
                ],
            },
        }
    })
    calc.use_parameters(parameters)

    # resources
    calc.set_max_wallclock_seconds(3*60) # 3 min
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 2})

    # store and submit
    calc.store_all()
    print "created calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid,calc.dbnode.pk)
    calc.submit()
    print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid,calc.dbnode.pk)

    # wait
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
            print subprocess.check_output(["verdi", "calculation", "list"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print "Note: the command failed, message: {}".format(e.message)
        if calc.has_finished():
            print "Calculation terminated its execution"
            exited_with_timeout = False
            break

    # check results
    expected_energy = -17.1566361119
    if exited_with_timeout:
        print "Timeout!! Calculation did not complete after {} seconds".format(
            timeout_secs)
        sys.exit(2)
    else:
        if abs(calc.res.energy - expected_energy) < 1e-10:
            print "OK, energy has the expected value"
            sys.exit(0)
        else:
            print "ERROR!"
            print "Expected free energy value: {}".format(expected_energy)
            print "Actual free energy value: {}".format(calc.res.energy)
            sys.exit(3)

main()
#EOF