#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

import os
import pytest
import numpy as np
import ase

from . import get_code


@pytest.mark.process_execution
def test_precision_roundtrip(new_database, new_workdir):
    from aiida.orm.data.structure import StructureData
    from aiida.orm.data.parameter import ParameterData
    from aiida.common.folders import SandboxFolder
    from aiida.orm.data.folder import FolderData
    import stat
    import subprocess

    from aiida_cp2k.parsers import Cp2kParser

    # structure
    epsilon = 1e-10  # expected precision in Angstrom
    dist = 0.74 + epsilon
    positions = [(0, 0, 0), (0, 0, dist)]
    cell = np.diag([4, -4, 4 + epsilon])
    atoms = ase.Atoms('H2', positions=positions, cell=cell)
    structure = StructureData(ase=atoms)

    # parameters
    parameters = ParameterData(dict={
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

    code = get_code(entry_point='cp2k')
    calc = code.new_calc()

    calc.label = "AiiDA CP2K test"
    calc.description = "Test job submission with the AiiDA CP2K plugin"

    # resources
    calc.set_max_wallclock_seconds(3*60)  # 3 min
    calc.set_withmpi(False)
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})

    calc.use_structure(structure)
    calc.use_parameters(parameters)

    calc.store_all()

    # output input files and scripts to temporary folder
    with SandboxFolder() as folder:

        subfolder, script_filename = calc.submit_test(folder=folder)
        print("inputs created at {}".format(subfolder.abspath))

        script_path = os.path.join(subfolder.abspath, script_filename)
        scheduler_stderr = calc._SCHED_ERROR_FILE  # pylint: disable=protected-access

        # we first need to make sure the script is executable
        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IEXEC)
        # now call script, NB: bash -l -c is required to access global variable loaded in .bash_profile
        returncode = subprocess.call(["bash", "-l", "-c", script_path], cwd=subfolder.abspath)

        if returncode:
            err_msg = "process failed (and couldn't find stderr file: {})".format(scheduler_stderr)
            stderr_path = os.path.join(subfolder.abspath, scheduler_stderr)
            if os.path.exists(stderr_path):
                with open(stderr_path) as f:
                    err_msg = "Process failed with stderr:\n{}".format(f.read())
            raise RuntimeError(err_msg)

        for outpath in [calc._OUTPUT_FILE_NAME, calc._RESTART_FILE_NAME]:
            subfolder.get_abs_path(outpath, check_existence=True)

        print("calculation completed execution")

        res = FolderData()
        res.replace_with_folder(subfolder.abspath)

        parser = Cp2kParser(calc)
        success, node_list = parser.parse_with_retrieved({'retrieved': res})

        # check that parsing worked
        assert success

        # make sure we got the expected output nodes
        node_dict = {n[0]: n[1] for n in node_list}
        assert all(key in node_dict.keys() for key in ['output_parameters', 'output_structure']), (
            "list of output nodes is missing some required nodes")

        # check the geometry
        atoms_out = node_dict['output_structure'].get_ase()
        assert np.all(atoms_out.positions[0] == 0.), "zeros not exactly preserved"
        assert abs(atoms_out.get_distance(0, 1) - dist) < epsilon, "test-distance not preserved accurately enough"
        assert np.amax(np.abs(atoms_out.cell - cell)) < epsilon, "cell not preserved accurately enough"
