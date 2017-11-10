# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/cp2k/aiida-cp2k      #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################

import re
import ase.io
from StringIO import StringIO

from aiida.parsers.parser import Parser
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.structure import StructureData
from aiida.parsers.exceptions import OutputParsingError
from aiida_cp2k.calculations import Cp2kCalculation

class Cp2kParser(Parser):
    """
    Parser for the output of CP2K.
    """

    #---------------------------------------------------------------------------
    def __init__(self, calc):
        """
        Initialize the instance of Cp2kParser
        """
        super(Cp2kParser, self).__init__(calc)

        # check for valid input
        if not isinstance(calc, Cp2kCalculation):
            raise OutputParsingError("Input calc must be a Cp2kCalculation")

    #---------------------------------------------------------------------------  
    def parse_with_retrieved(self, retrieved):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """
        out_folder = retrieved[self._calc._get_linkname_retrieved()]

        new_nodes_list = []
        self._parse_stdout(out_folder, new_nodes_list)
        self._parse_trajectory(out_folder, new_nodes_list)

        return True, new_nodes_list

    #---------------------------------------------------------------------------
    def _parse_stdout(self, out_folder, new_nodes_list):
        fn = self._calc._OUTPUT_FILE_NAME
        if fn not in out_folder.get_folder_list():
            raise OutputParsingError("Cp2k output file not retrieved")

        result_dict = {}
        abs_fn = out_folder.get_abs_path(fn)
        with open(abs_fn, "r") as f:
            for line in f.readlines():
                if line.startswith(' ENERGY| '):
                    result_dict['energy'] = float(line.split()[8])
                    result_dict['energy_units'] = "a.u."
                if line.startswith(' The number of warnings for this run is :'):
                    result_dict['nwarnings'] = int(line.split()[-1])

        pair = (self.get_linkname_outparams(), ParameterData(dict=result_dict))
        new_nodes_list.append(pair)

    #---------------------------------------------------------------------------
    def _parse_trajectory(self, out_folder, new_nodes_list):
        fn = self._calc._TRAJ_FILE_NAME
        if fn not in out_folder.get_folder_list():
            return  # not every run type produces a trajectory

        abs_fn = out_folder.get_abs_path(fn)
        content = open(abs_fn).read()
        frames = re.findall(r"\n(REMARK.*?\nEND)", content, re.DOTALL)
        atoms = ase.io.read(StringIO(frames[-1]), format='proteindatabank')
        pair = (self.get_linkname_outstructure(), StructureData(ase=atoms))
        new_nodes_list.append(pair)

    #---------------------------------------------------------------------------
    def get_linkname_outstructure(self):
        """
        Returns the name of the link to the output_structure
        """
        return 'output_structure'


#EOF