# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

import six
from aiida.engine import CalcJob
from aiida.orm import Dict, SinglefileData, StructureData, RemoteData
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
    _DEFAULT_PARENT_CALC_FOLDER_NAME = 'parent_calc/'
    _DEFAULT_COORDS_FILE_NAME = 'aiida.coords.xyz'
    _DEFAULT_PARSER = 'cp2k'

    @classmethod
    def define(cls, spec):
        super(Cp2kCalculation, cls).define(spec)

        # Input parameters
        spec.input('structure', valid_type=StructureData, help='the input structure')
        spec.input('parameters', valid_type=Dict, help='the input parameters')
        spec.input('settings', valid_type=Dict, required=False, help='additional input parameters')
        spec.input('resources', valid_type=dict, required=False, help='special settings')
        spec.input('parent_calc_folder', valid_type=RemoteData, required=False, help='remote folder used for restarts')
        spec.input_namespace('file', valid_type=SinglefileData, required=False, help='additional input files', dynamic=True)

        # Default file names, parser, etc..
        spec.input('metadata.options.input_filename', valid_type=six.string_types, default=cls._DEFAULT_INPUT_FILE, non_db=True)
        spec.input('metadata.options.output_filename', valid_type=six.string_types, default=cls._DEFAULT_OUTPUT_FILE, non_db=True)
        spec.input('metadata.options.parser_name', valid_type=six.string_types, default=cls._DEFAULT_PARSER, non_db=True)

        # Exit codes
        spec.exit_code(100, 'ERROR_NO_RETRIEVED_FOLDER', message='The retrieved folder data node could not be accessed.')

        # Output parameters
        spec.output('output_parameters', valid_type=Dict, required=True, help='the results of the calculation')
        spec.output('structure', valid_type=StructureData, required=False, help='optional relaxed structure')


    # --------------------------------------------------------------------------
    def prepare_for_submission(self, folder):
        """Create the input files from the input nodes passed to this instance of the `CalcJob`.
    
        :param folder: an `aiida.common.folders.Folder` to temporarily write files on disk
        :return: `aiida.common.datastructures.CalcInfo` instance
        """
        # create input structure
        structure = self.inputs.structure
        struct_fn = folder.get_abs_path(self._DEFAULT_COORDS_FILE_NAME)
        structure.export(struct_fn, fileformat="xyz")

        # create cp2k input file
        inp = Cp2kInput(self.inputs.parameters.get_dict())
        inp.add_keyword("GLOBAL/PROJECT", self._DEFAULT_PROJECT_NAME)
        for i, a in enumerate('ABC'):
            val = '{:<15} {:<15} {:<15}'.format(*structure.cell[i])
            inp.add_keyword('FORCE_EVAL/SUBSYS/CELL/'+a, val)
        topo = "FORCE_EVAL/SUBSYS/TOPOLOGY"
        inp.add_keyword(topo + "/COORD_FILE_NAME", self._DEFAULT_COORDS_FILE_NAME)
        inp.add_keyword(topo + "/COORD_FILE_FORMAT", "XYZ")
        inp_fn = folder.get_abs_path(self._DEFAULT_INPUT_FILE)
        with open(inp_fn, "w") as f:
            f.write(inp.render())

        if 'settings' in self.inputs:
            settings = self.inputs.settings.get_dict()
        else:
            settings = {}

        # create code info
        codeinfo = CodeInfo()
        cmdline = settings.pop('cmdline', [])
        cmdline += ["-i", self._DEFAULT_INPUT_FILE]
        codeinfo.cmdline_params = cmdline
        codeinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        codeinfo.join_files = True
        codeinfo.code_uuid = self.inputs.code.uuid

        # create calc info
        calcinfo = CalcInfo()
        calcinfo.stdin_name = self._DEFAULT_INPUT_FILE
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._DEFAULT_INPUT_FILE
        calcinfo.stdout_name = self._DEFAULT_OUTPUT_FILE
        calcinfo.codes_info = [codeinfo]

        # file lists
        calcinfo.remote_symlink_list = []
        if 'file' in self.inputs:
            local_copy_list = []
            # TODO, make sure that self.inputs.file is an array, and not something else
            for fl in self.inputs.file:
                filepath = os.path.join(fl._repository._get_base_folder().abspath, fl.filename)
                local_copy_list.append(filepath, fl.filename)
            calcinfo.local_copy_list = local_copy_list

        calcinfo.remote_copy_list = []
        calcinfo.retrieve_list = [self._DEFAULT_OUTPUT_FILE,
                                  self._DEFAULT_RESTART_FILE_NAME]
        calcinfo.retrieve_list += settings.pop('additional_retrieve_list', [])

        # symlinks
        if 'parent_calc_folder' in self.inputs:
            comp_uuid = self.inputs.parent_calc_folder.get_computer().uuid
            remote_path = parent_calc_folder.get_remote_path()
            symlink = (comp_uuid, remote_path, self._DEFAULT_PARENT_CALC_FOLDER_NAME)
            calcinfo.remote_symlink_list.append(symlink)

        # check for left over settings
        if settings:
            msg = "The following keys have been found "
            msg += "in the settings input node {}, ".format(self.pk)
            msg += "but were not understood: " + ",".join(settings.keys())
            raise InputValidationError(msg)

        return calcinfo

# ==============================================================================
class Cp2kInput(object):
    def __init__(self, params):
        self.params = params

    # --------------------------------------------------------------------------
    def add_keyword(self, kwpath, value, params=None):
        self._add_keyword_low(kwpath.split("/"), value, self.params)

    # --------------------------------------------------------------------------
    def _add_keyword_low(self, kwpath, value, params):
        if len(kwpath) == 1:
            params[kwpath[0]] = value
        elif kwpath[0] not in params.keys():
            new_subsection = {}
            params[kwpath[0]] = new_subsection
            self._add_keyword_low(kwpath[1:], value, new_subsection)
        else:
            self._add_keyword_low(kwpath[1:], value, params[kwpath[0]])

    # --------------------------------------------------------------------------
    def render(self):
        output = ["!!! Generated by AiiDA !!!"]
        self._render_section(output, self.params)
        return "\n".join(output)

    # --------------------------------------------------------------------------
    def _render_section(self, output, params, indent=0):
        """
        It takes a dictionary and recurses through.

        For key-value pair it checks whether the value is a dictionary
        and prepends the key with &
        It passes the valued to the same function, increasing the indentation
        If the value is a list, I assume that this is something the user
        wants to store repetitively
        eg:
            dict['KEY'] = ['val1', 'val2']
            ===>
            KEY val1
            KEY val2

            or

            dict['KIND'] = [{'_': 'Ba', 'ELEMENT':'Ba'},
                            {'_': 'Ti', 'ELEMENT':'Ti'},
                            {'_': 'O', 'ELEMENT':'O'}]
            ====>
                  &KIND Ba
                     ELEMENT  Ba
                  &END KIND
                  &KIND Ti
                     ELEMENT  Ti
                  &END KIND
                  &KIND O
                     ELEMENT  O
                  &END KIND
        """

        for key, val in sorted(params.items()):
            if key.upper() != key:
                raise InputValidationError("keyword '%s' not upper case" % key)
            if key.startswith('@') or key.startswith('$'):
                raise InputValidationError("CP2K preprocessor not supported")
            if isinstance(val, dict):
                output.append('%s&%s %s' % (' '*indent, key, val.pop('_', '')))
                self._render_section(output, val, indent + 3)
                output.append('%s&END %s' % (' '*indent, key))
            elif isinstance(val, list):
                for listitem in val:
                    self._render_section(output,  {key: listitem}, indent)
            elif isinstance(val, bool):
                val_str = '.true.' if val else '.false.'
                output.append('%s%s  %s' % (' '*indent, key, val_str))
            else:
                output.append('%s%s  %s' % (' '*indent, key, val))


# EOF
