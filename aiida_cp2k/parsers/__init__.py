# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
import os
import re
import ase
import numpy as np
from re import DOTALL

from aiida.parsers import Parser
from aiida.orm import Dict, StructureData
from aiida.common import OutputParsingError
from aiida_cp2k.calculations import Cp2kCalculation


class Cp2kParser(Parser):
    """Parser for the output of CP2K."""

    # --------------------------------------------------------------------------
    def __init__(self, calc):
        """Initialize the instance of Cp2kParser"""
        super(Cp2kParser, self).__init__(calc)

        # check for valid input
        # skipped because it was causing problems
        #if not isinstance(calc, Cp2kCalculation):
        #    raise OutputParsingError("Input calc must be a Cp2kCalculation")

    # --------------------------------------------------------------------------
    def parse(self, **kwargs):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """

        try:
            out_folder = self.retrieved
        except exceptions.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        results = self._parse_stdout(out_folder)
        self.out('output_parameters', results)
        
        try:
            structure = self._parse_trajectory(out_folder)
            self.out('output_structure', structure)
        except Exception:
            pass




    # --------------------------------------------------------------------------
    def _parse_stdout(self, out_folder):
        fn = self.node.load_process_class()._DEFAULT_OUTPUT_FILE
        if fn not in out_folder._repository.list_object_names():
            raise OutputParsingError("Cp2k output file not retrieved")

        result_dict = {'exceeded_walltime': False}
        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fn)
        with open(abs_fn, "r") as f:
            for line in f.readlines():
                if line.startswith(' ENERGY| '):
                    result_dict['energy'] = float(line.split()[8])
                    result_dict['energy_units'] = "a.u."
                if 'The number of warnings for this run is' in line:
                    result_dict['nwarnings'] = int(line.split()[-1])
                if 'exceeded requested execution time' in line:
                    result_dict['exceeded_walltime'] = True

        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly.")

        return Dict(dict=result_dict)

    # --------------------------------------------------------------------------
    def _parse_trajectory(self, out_folder):
        fn = self.node.load_process_class()._DEFAULT_RESTART_FILE_NAME
        if fn not in out_folder._repository.list_object_names():
            raise Exception  # not every run type produces a trajectory

        # read restart file
        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fn)
        content = open(abs_fn).read()

        # parse coordinate section
        m = re.search(r'\n\s*&COORD\n(.*?)\n\s*&END COORD\n', content, DOTALL)
        coord_lines = [line.strip().split() for line in m.group(1).split("\n")]
        symbols = [line[0] for line in coord_lines]
        positions_str = [line[1:] for line in coord_lines]
        positions = np.array(positions_str, np.float64)

        # parse cell section
        m = re.search(r'\n\s*&CELL\n(.*?)\n\s*&END CELL\n', content, re.DOTALL)
        cell_lines = [line.strip().split() for line in m.group(1).split("\n")]
        cell_str = [line[1:] for line in cell_lines if line[0] in 'ABC']
        cell = np.array(cell_str, np.float64)

        # create StructureData
        atoms = ase.Atoms(symbols=symbols, positions=positions, cell=cell)
        return StructureData(ase=atoms)

# EOF
