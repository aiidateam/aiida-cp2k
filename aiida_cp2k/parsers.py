# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

import io
import re

from aiida.parsers.parser import Parser
from aiida.parsers.exceptions import OutputParsingError

from aiida.orm import CalculationFactory
Cp2kCalculation = CalculationFactory('cp2k')


class Cp2kParser(Parser):
    """
    Parser for the output of CP2K.
    """

    def __init__(self, calc):
        """
        Initialize the instance of Cp2kParser
        """
        super(Cp2kParser, self).__init__(calc)

        # check for valid input
        if not isinstance(calc, Cp2kCalculation):
            raise OutputParsingError("Input calc must be a Cp2kCalculation")

    def parse_with_retrieved(self, retrieved):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """
        out_folder = retrieved['retrieved']

        new_nodes_list = []
        new_nodes_list += self._parse_stdout(out_folder)

        if self._calc._RESTART_FILE_NAME in out_folder.get_folder_list():
            new_nodes_list += self._parse_trajectory(out_folder)

        return True, new_nodes_list

    def _parse_stdout(self, out_folder):
        from aiida.orm.data.parameter import ParameterData

        fname = self._calc._OUTPUT_FILE_NAME

        if fname not in out_folder.get_folder_list():
            raise OutputParsingError("Cp2k output file not retrieved")

        result_dict = {
            'exceeded_walltime': False,
            }

        abs_fname = out_folder.get_abs_path(fname)

        with io.open(abs_fname, 'r', encoding='utf8') as fhandle:
            for line in fhandle.readlines():
                if line.startswith(' ENERGY| '):
                    # should we find the output energy multiple times, just use the last one
                    result_dict['energy'] = float(line.split()[8])
                    result_dict['energy_units'] = "a.u."

                if 'The number of warnings for this run is' in line:
                    result_dict['nwarnings'] = int(line.split()[-1])

                if 'exceeded requested execution time' in line:
                    result_dict['exceeded_walltime'] = True

        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly.")

        pair = ('output_parameters', ParameterData(dict=result_dict))
        return [pair]

    def _parse_trajectory(self, out_folder):
        from aiida.orm.data.structure import StructureData
        import ase
        import numpy as np

        # read restart file
        abs_fn = out_folder.get_abs_path(self._calc._RESTART_FILE_NAME)

        with io.open(abs_fn, 'r', encoding='utf8') as fhandle:
            content = fhandle.read()

        # parse coordinate section
        match = re.search(r'\n\s*&COORD\n(.*?)\n\s*&END COORD\n', content, re.DOTALL)
        coord_lines = [line.strip().split() for line in match.group(1).split("\n")]
        symbols = [line[0] for line in coord_lines]
        positions_str = [line[1:] for line in coord_lines]
        positions = np.array(positions_str, np.float64)

        # parse cell section
        match = re.search(r'\n\s*&CELL\n(.*?)\n\s*&END CELL\n', content, re.DOTALL)
        cell_lines = [line.strip().split() for line in match.group(1).split("\n")]
        cell_str = [line[1:] for line in cell_lines if line[0] in 'ABC']
        cell = np.array(cell_str, np.float64)

        # create StructureData
        atoms = ase.Atoms(symbols=symbols, positions=positions, cell=cell)
        return [('output_structure', StructureData(ase=atoms))]
