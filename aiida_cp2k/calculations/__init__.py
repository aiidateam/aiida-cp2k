# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K input plugin."""

import io
from operator import add

from aiida.engine import CalcJob
from aiida.common import CalcInfo, CodeInfo, InputValidationError
from aiida.orm import Computer, Dict, RemoteData, SinglefileData
from aiida.plugins import DataFactory

from ..utils.datatype_helpers import (
    validate_basissets,
    validate_pseudos,
    validate_basissets_namespace,
    validate_pseudos_namespace,
    write_basissets,
    write_pseudos,
)
from ..utils import Cp2kInput

BandsData = DataFactory('array.bands')  # pylint: disable=invalid-name
StructureData = DataFactory('structure')  # pylint: disable=invalid-name


class Cp2kCalculation(CalcJob):
    """This is a Cp2kCalculation, subclass of JobCalculation, to prepare input for an ab-initio CP2K calculation.

    For information on CP2K, refer to: https://www.cp2k.org.
    """

    # Defaults.
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

        # Input parameters.
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

        spec.input_namespace(
            "basissets",
            dynamic=True,
            required=False,
            validator=validate_basissets_namespace,
            help=('A dictionary of basissets to be used in the calculations: key is the atomic symbol,'
                  ' value is either a single basisset or a list of basissets. If multiple basissets for'
                  ' a single symbol are passed, it is mandatory to specify a KIND section with a BASIS_SET'
                  ' keyword matching the names (or aliases) of the basissets.'))

        spec.input_namespace(
            "pseudos",
            dynamic=True,
            required=False,
            validator=validate_pseudos_namespace,
            help=('A dictionary of pseudopotentials to be used in the calculations: key is the atomic symbol,'
                  ' value is either a single pseudopotential or a list of pseudopotentials. If multiple pseudos'
                  ' for a single symbol are passed, it is mandatory to specify a KIND section with a PSEUDOPOTENTIAL'
                  ' keyword matching the names (or aliases) of the pseudopotentials.'))

        # Specify default parser.
        spec.input('metadata.options.parser_name', valid_type=str, default=cls._DEFAULT_PARSER, non_db=True)

        # Add input_filename attribute.
        spec.input('metadata.options.input_filename', valid_type=str, default=cls._DEFAULT_INPUT_FILE)

        # Add output_filename attribute.
        spec.input('metadata.options.output_filename', valid_type=str, default=cls._DEFAULT_OUTPUT_FILE)

        # Use mpi by default.
        spec.input('metadata.options.withmpi', valid_type=bool, default=True)

        # Unrecoverable errors: resources like the retrieved folder or its expected contents are missing.
        spec.exit_code(200,
                       'ERROR_NO_RETRIEVED_FOLDER',
                       message='The retrieved folder data node could not be accessed.')
        spec.exit_code(210,
                       'ERROR_OUTPUT_MISSING',
                       message='The retrieved folder did not contain the required output file.')

        # Unrecoverable errors: required retrieved files could not be read, parsed or are otherwise incomplete.
        spec.exit_code(301, 'ERROR_OUTPUT_READ', message='The output file could not be read.')
        spec.exit_code(302, 'ERROR_OUTPUT_PARSE', message='The output file could not be parsed.')
        spec.exit_code(303, 'ERROR_OUTPUT_INCOMPLETE', message='The output file was incomplete.')
        spec.exit_code(304, 'ERROR_OUTPUT_CONTAINS_ABORT', message='The output file contains the word "ABORT"')
        spec.exit_code(312, 'ERROR_STRUCTURE_PARSE', message='The output structure could not be parsed.')
        spec.exit_code(350, 'ERROR_UNEXPECTED_PARSER_EXCEPTION', message='The parser raised an unexpected exception.')

        # Significant errors but calculation can be used to restart.
        spec.exit_code(400,
                       'ERROR_OUT_OF_WALLTIME',
                       message='The calculation stopped prematurely because it ran out of walltime.')
        spec.exit_code(500,
                       'ERROR_GEOMETRY_CONVERGENCE_NOT_REACHED',
                       message='The ionic minimization cycle did not converge for the given thresholds.')

        # Output parameters.
        spec.output('output_parameters', valid_type=Dict, required=True, help='the results of the calculation')
        spec.output('output_structure', valid_type=StructureData, required=False, help='optional relaxed structure')
        spec.output('output_bands', valid_type=BandsData, required=False, help='optional band structure')
        spec.default_output_node = 'output_parameters'

        spec.outputs.dynamic = True

    def prepare_for_submission(self, folder):
        """Create the input files from the input nodes passed to this instance of the `CalcJob`.

        :param folder: an `aiida.common.folders.Folder` to temporarily write files on disk
        :return: `aiida.common.datastructures.CalcInfo` instance
        """

        # pylint: disable=too-many-statements,too-many-branches

        # create cp2k input file
        inp = Cp2kInput(self.inputs.parameters.get_dict())
        inp.add_keyword("GLOBAL/PROJECT", self._DEFAULT_PROJECT_NAME)

        # Create input structure(s).
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

        if 'basissets' in self.inputs:
            validate_basissets(inp, self.inputs.basissets,
                               self.inputs.structure if 'structure' in self.inputs else None)
            write_basissets(inp, self.inputs.basissets, folder)

        if 'pseudos' in self.inputs:
            validate_pseudos(inp, self.inputs.pseudos, self.inputs.structure if 'structure' in self.inputs else None)
            write_pseudos(inp, self.inputs.pseudos, folder)

        with io.open(folder.get_abs_path(self._DEFAULT_INPUT_FILE), mode="w", encoding="utf-8") as fobj:
            try:
                fobj.write(inp.render())
            except ValueError as exc:
                raise InputValidationError("Invalid keys or values in input parameters found") from exc

        settings = self.inputs.settings.get_dict() if 'settings' in self.inputs else {}

        # Create code info.
        codeinfo = CodeInfo()
        codeinfo.cmdline_params = settings.pop('cmdline', []) + ["-i", self._DEFAULT_INPUT_FILE]
        codeinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        codeinfo.join_files = True
        codeinfo.code_uuid = self.inputs.code.uuid

        # Create calc info.
        calcinfo = CalcInfo()
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._DEFAULT_INPUT_FILE
        calcinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        calcinfo.codes_info = [codeinfo]

        # Files or additional structures.
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

        # Symlinks.
        calcinfo.remote_symlink_list = []
        calcinfo.remote_copy_list = []
        if 'parent_calc_folder' in self.inputs:
            comp_uuid = self.inputs.parent_calc_folder.computer.uuid
            remote_path = self.inputs.parent_calc_folder.get_remote_path()
            copy_info = (comp_uuid, remote_path, self._DEFAULT_PARENT_CALC_FLDR_NAME)

            # If running on the same computer - make a symlink.
            if self.inputs.code.computer.uuid == comp_uuid:
                calcinfo.remote_symlink_list.append(copy_info)
            # If not - copy the folder.
            else:
                calcinfo.remote_copy_list.append(copy_info)

        # Check for left over settings.
        if settings:
            raise InputValidationError("The following keys have been found " +
                                       "in the settings input node {}, ".format(self.pk) + "but were not understood: " +
                                       ",".join(settings.keys()))

        return calcinfo

    @staticmethod
    def _write_structure(structure, folder, name):
        """Function that writes a structure and takes care of element tags."""

        # Create file with the structure.
        s_ase = structure.get_ase()
        elem_tags = ['' if t == 0 else str(t) for t in s_ase.get_tags()]
        elem_symbols = list(map(add, s_ase.get_chemical_symbols(), elem_tags))
        elem_coords = ['{:25.16f} {:25.16f} {:25.16f}'.format(p[0], p[1], p[2]) for p in s_ase.get_positions()]
        with io.open(folder.get_abs_path(name), mode="w", encoding="utf-8") as fobj:
            fobj.write(u'{}\n\n'.format(len(elem_coords)))
            fobj.write(u'\n'.join(map(add, elem_symbols, elem_coords)))
