# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K input plugin"""

from __future__ import absolute_import

import io
import six
from six.moves import map

from aiida.engine import CalcJob
from aiida.orm import Computer, Dict, SinglefileData, StructureData, RemoteData, BandsData
from aiida.common import CalcInfo, CodeInfo, InputValidationError


class Cp2kCalculation(CalcJob):
    """
    This is a Cp2kCalculation, subclass of JobCalculation,
    to prepare input for an ab-initio CP2K calculation.
    For information on CP2K, refer to: https://www.cp2k.org
    """

    # Defaults
    _DEFAULT_INPUT_FILE = 'aiida.inp'
    _DEFAULT_OUTPUT_FILE = 'aiida.out'
    _DEFAULT_PROJECT_NAME = 'aiida'
    _DEFAULT_RESTART_FILE_NAME = _DEFAULT_PROJECT_NAME + '-1.restart'
    _DEFAULT_TRAJECT_FILE_NAME = _DEFAULT_PROJECT_NAME + '-pos-1.dcd'
    _DEFAULT_PARENT_CALC_FLDR_NAME = 'parent_calc/'
    _DEFAULT_COORDS_FILE_NAME = 'aiida.coords.xyz'
    _DEFAULT_PARSER = 'cp2k_base_parser'

    @classmethod
    def define(cls, spec):
        super(Cp2kCalculation, cls).define(spec)

        # Input parameters
        spec.input('parameters', valid_type=Dict, help='the input parameters')
        spec.input('structure', valid_type=StructureData, required=False, help='the main input structure')
        spec.input('settings', valid_type=Dict, required=False, help='additional input parameters')
        spec.input('resources', valid_type=dict, required=False, help='special settings')
        spec.input('parent_calc_folder', valid_type=RemoteData, required=False, help='remote folder used for restarts')
        spec.input_namespace('file',
                             valid_type=(SinglefileData, StructureData),
                             required=False,
                             help='additional input files',
                             dynamic=True)

        # Specify default parser
        spec.input('metadata.options.parser_name',
                   valid_type=six.string_types,
                   default=cls._DEFAULT_PARSER,
                   non_db=True)

        # Use mpi by default
        spec.input('metadata.options.withmpi', valid_type=bool, default=True)

        # Exit codes
        spec.exit_code(100,
                       'ERROR_NO_RETRIEVED_FOLDER',
                       message='The retrieved folder data node could not be accessed.')

        # Output parameters
        spec.output('output_parameters', valid_type=Dict, required=True, help='the results of the calculation')
        spec.output('output_structure', valid_type=StructureData, required=False, help='optional relaxed structure')
        spec.output('output_bands', valid_type=BandsData, required=False, help='optional band structure')
        spec.default_output_node = 'output_parameters'

    def prepare_for_submission(self, folder):
        """Create the input files from the input nodes passed to this instance of the `CalcJob`.

        :param folder: an `aiida.common.folders.Folder` to temporarily write files on disk
        :return: `aiida.common.datastructures.CalcInfo` instance
        """
        from aiida_cp2k.utils import Cp2kInput

        # create cp2k input file
        inp = Cp2kInput(self.inputs.parameters.get_dict())
        inp.add_keyword("GLOBAL/PROJECT", self._DEFAULT_PROJECT_NAME)

        # create input structure(s)
        if 'structure' in self.inputs:
            # As far as I understand self.inputs.structure can't deal with tags
            # self.inputs.structure.export(folder.get_abs_path(self._DEFAULT_COORDS_FILE_NAME), fileformat="xyz")
            self._write_structure(self.inputs.structure, folder, self._DEFAULT_COORDS_FILE_NAME)

            # modify the input dictionary accordingly
            for i, letter in enumerate('ABC'):
                inp.add_keyword('FORCE_EVAL/SUBSYS/CELL/' + letter,
                                '{:<15} {:<15} {:<15}'.format(*self.inputs.structure.cell[i]),
                                override=False,
                                conflicting_keys=['ABC', 'ALPHA_BETA_GAMMA', 'CELL_FILE_NAME'])

            topo = "FORCE_EVAL/SUBSYS/TOPOLOGY"
            inp.add_keyword(topo + "/COORD_FILE_NAME", self._DEFAULT_COORDS_FILE_NAME, override=False)
            inp.add_keyword(topo + "/COORD_FILE_FORMAT", "XYZ", override=False, conflicting_keys=['COORDINATE'])

        with io.open(folder.get_abs_path(self._DEFAULT_INPUT_FILE), mode="w", encoding="utf-8") as fobj:
            try:
                fobj.write(inp.render())
            except ValueError as exc:
                six.raise_from(InputValidationError("invalid keys or values in input parameters found"), exc)

        settings = self.inputs.settings.get_dict() if 'settings' in self.inputs else {}

        # create code info
        codeinfo = CodeInfo()
        codeinfo.cmdline_params = settings.pop('cmdline', []) + ["-i", self._DEFAULT_INPUT_FILE]
        codeinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        codeinfo.join_files = True
        codeinfo.code_uuid = self.inputs.code.uuid

        # create calc info
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._DEFAULT_INPUT_FILE
        calcinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        calcinfo.codes_info = [codeinfo]

        # files or additional structures
        if 'file' in self.inputs:
            calcinfo.local_copy_list = []
            for name, obj in self.inputs.file.items():
                if isinstance(obj, SinglefileData):
                    calcinfo.local_copy_list.append((obj.uuid, obj.filename, obj.filename))
                elif isinstance(obj, StructureData):
                    self._write_structure(obj, folder, name + '.xyz')

        calcinfo.retrieve_list = [
            self._DEFAULT_OUTPUT_FILE, self._DEFAULT_RESTART_FILE_NAME, self._DEFAULT_TRAJECT_FILE_NAME
        ]
        calcinfo.retrieve_list += settings.pop('additional_retrieve_list', [])

        # symlinks
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        if 'parent_calc_folder' in self.inputs:
            comp_uuid = self.inputs.parent_calc_folder.computer.uuid
            remote_path = self.inputs.parent_calc_folder.get_remote_path()
            copy_info = (comp_uuid, remote_path, self._DEFAULT_PARENT_CALC_FLDR_NAME)
            if self.inputs.code.computer.uuid == comp_uuid:  # if running on the same computer - make a symlink
                # if not - copy the folder
                calcinfo.remote_symlink_list.append(copy_info)
            else:
                calcinfo.remote_copy_list.append(copy_info)

        # check for left over settings
        if settings:
            raise InputValidationError("The following keys have been found " +
                                       "in the settings input node {}, ".format(self.pk) + "but were not understood: " +
                                       ",".join(settings.keys()))

        return calcinfo

    @staticmethod
    def _write_structure(structure, folder, name):
        """Function that writes a structure and takes care of element tags"""

        # create file with the structure
        from operator import add
        s_ase = structure.get_ase()
        elem_tags = ['' if t == 0 else str(t) for t in s_ase.get_tags()]
        elem_symbols = list(map(add, s_ase.get_chemical_symbols(), elem_tags))
        elem_coords = ['{:25.16f} {:25.16f} {:25.16f}'.format(p[0], p[1], p[2]) for p in s_ase.get_positions()]
        with io.open(folder.get_abs_path(name), mode="w", encoding="utf-8") as fobj:
            fobj.write(u'{}\n\n'.format(len(elem_coords)))
            fobj.write(u'\n'.join(map(add, elem_symbols, elem_coords)))
