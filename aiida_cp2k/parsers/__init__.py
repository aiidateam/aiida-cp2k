# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

import re
import ase
import numpy as np
from re import DOTALL

from aiida.parsers.parser import Parser
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.structure import StructureData
from aiida.parsers.exceptions import OutputParsingError
from aiida_cp2k.calculations import Cp2kCalculation


class Cp2kParser(Parser):
    """
    Parser for the output of CP2K.
    """

    # --------------------------------------------------------------------------
    def __init__(self, calc):
        """
        Initialize the instance of Cp2kParser
        """
        super(Cp2kParser, self).__init__(calc)

        # check for valid input
        if not isinstance(calc, Cp2kCalculation):
            raise OutputParsingError("Input calc must be a Cp2kCalculation")

    # --------------------------------------------------------------------------
    def parse_with_retrieved(self, retrieved):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """
        out_folder = retrieved['retrieved']

        new_nodes_list = []
        self._parse_stdout(out_folder, new_nodes_list)
        try:
            self._parse_trajectory(out_folder, new_nodes_list)
        except Exception:
            pass

        return True, new_nodes_list

    # --------------------------------------------------------------------------
    def _parse_stdout(self, out_folder, new_nodes_list):
        fn = self._calc._OUTPUT_FILE_NAME
        if fn not in out_folder.get_folder_list():
            raise OutputParsingError("Cp2k output file not retrieved")

        result_dict = {'exceeded_walltime': False}
        abs_fn = out_folder.get_abs_path(fn)
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

        pair = ('output_parameters', ParameterData(dict=result_dict))
        new_nodes_list.append(pair)

    # --------------------------------------------------------------------------
    def _parse_trajectory(self, out_folder, new_nodes_list):
        fn = self._calc._RESTART_FILE_NAME
        if fn not in out_folder.get_folder_list():
            return  # not every run type produces a trajectory

        # read restart file
        abs_fn = out_folder.get_abs_path(fn)
        content = open(abs_fn).read()

        # parse coordinate section
        m = re.search('\n\s*&COORD\n(.*?)\n\s*&END COORD\n', content, DOTALL)
        coord_lines = [line.strip().split() for line in m.group(1).split("\n")]
        symbols = [line[0] for line in coord_lines]
        positions_str = [line[1:] for line in coord_lines]
        positions = np.array(positions_str, np.float64)

        # parse cell section
        m = re.search('\n\s*&CELL\n(.*?)\n\s*&END CELL\n', content, re.DOTALL)
        cell_lines = [line.strip().split() for line in m.group(1).split("\n")]
        cell_str = [line[1:] for line in cell_lines if line[0] in 'ABC']
        cell = np.array(cell_str, np.float64)

        # create StructureData
        atoms = ase.Atoms(symbols=symbols, positions=positions, cell=cell)
        pair = ('output_structure', StructureData(ase=atoms))
        new_nodes_list.append(pair)

# EOF
