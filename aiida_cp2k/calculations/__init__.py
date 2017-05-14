# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/cp2k/aiida-cp2k      #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################

from aiida.orm.calculation.job import JobCalculation
from aiida.common.utils import classproperty
from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.remote import RemoteData
from aiida.common.datastructures import CalcInfo
from aiida.common.datastructures import CodeInfo
from aiida.common.exceptions import InputValidationError

class Cp2kCalculation(JobCalculation):
    """
    This is a Cp2kCalculation, subclass of JobCalculation, to prepare input for an
    ab-inition Cp2kCalculation.
    For information on CP2K, refer to: https://www.cp2k.org
    """

    #---------------------------------------------------------------------------
    def _init_internal_params(self):
        """
        Set parameters of instance
        """
        super(Cp2kCalculation, self)._init_internal_params()
        self._INPUT_FILE_NAME  = 'aiida.inp'
        self._OUTPUT_FILE_NAME = 'aiida.out'
        self.DEFAULT_INPUT_FILE  = self._INPUT_FILE_NAME
        self._DEFAULT_OUTPUT_FILE = self._OUTPUT_FILE_NAME
        #self._DEFAULT_ERROR_FILE
        self._COORDS_FILE_NAME = 'aiida.coords.xyz'
        self._default_parser = 'cp2k.Cp2kParser'

    #---------------------------------------------------------------------------
    @classproperty
    def _use_methods(cls):
        """
        Extend the parent _use_methods with further keys.
        This will be manually added to the _use_methods in each subclass
        """
        retdict = JobCalculation._use_methods
        retdict.update({
            "structure": {
               'valid_types': StructureData,
               'additional_parameter': None,
               'linkname': 'structure',
               'docstring': "Choose the input structure to use",
               },
            "settings": {
               'valid_types': ParameterData,
               'additional_parameter': None,
               'linkname': 'settings',
               'docstring': "Use an additional node for special settings",
               },
            "parameters": {
               'valid_types': ParameterData,
               'additional_parameter': None,
               'linkname': 'parameters',
               'docstring': "Use a node that specifies the input parameters for the namelists",
               },
               "parent_folder": {
               'valid_types': RemoteData,
               'additional_parameter': None,
               'linkname': 'parent_calc_folder',
               'docstring': "Use a remote folder as parent folder (for restarts and similar)",
               },
            })
        return retdict

    #---------------------------------------------------------------------------
    def _prepare_for_submission(self, tempfolder, inputdict):
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """

        params, structure, code, settings = self._verify_inlinks(inputdict)

        # write cp2k input file
        inp = Cp2kInput(params)
        for i, a in enumerate('ABC'):
            val = '{:<15} {:<15} {:<15}'.format(*structure.cell[i])
            inp.add_keyword('FORCE_EVAL/SUBSYS/CELL/'+a, val)
        inp.add_keyword("FORCE_EVAL/SUBSYS/TOPOLOGY/COORD_FILE_NAME", self._COORDS_FILE_NAME)
        inp.add_keyword("FORCE_EVAL/SUBSYS/TOPOLOGY/COORD_FILE_FORMAT", "xyz")
        inp_fn = tempfolder.get_abs_path(self._INPUT_FILE_NAME)
        with open(inp_fn, "w") as f:
            f.write(inp.render())

        # write structure file
        struct_fn = tempfolder.get_abs_path(self._COORDS_FILE_NAME)
        structure.export(struct_fn, 'xyz')

        # create code info
        codeinfo = CodeInfo()
        cmdline = settings.pop('cmdline', [])
        cmdline += ["-i", self._INPUT_FILE_NAME, "-o", self._OUTPUT_FILE_NAME]
        codeinfo.cmdline_params = cmdline
        codeinfo.stdout_name = self._OUTPUT_FILE_NAME
        codeinfo.code_uuid = code.uuid

        # create calc info
        calcinfo = CalcInfo()
        calcinfo.stdin_name = self._INPUT_FILE_NAME
        calcinfo.uuid = self.uuid
        calcinfo.cmdline_params = codeinfo.cmdline_params
        calcinfo.stdin_name = self._INPUT_FILE_NAME
        calcinfo.stdout_name = self._OUTPUT_FILE_NAME
        calcinfo.codes_info = [codeinfo]

        # file lists
        calcinfo.remote_symlink_list = []
        calcinfo.local_copy_list = []
        calcinfo.remote_copy_list = []
        add_retrieve_list = settings.pop('additional_retrieve_list', [])
        calcinfo.retrieve_list = [self._OUTPUT_FILE_NAME] + add_retrieve_list

        # check for left over settings
        if settings:
            msg = "The following keys have been found in the settings input node, "
            msg = "but were not understood: " + ",",join(settings_dict.keys())
            raise InputValidationError(msg)

        return calcinfo

    #---------------------------------------------------------------------------
    def _verify_inlinks(self, inputdict):
        # parameters
        try:
            params_node = inputdict.pop(self.get_linkname('parameters'))
        except KeyError:
            raise InputValidationError("No parameters specified for this calculation")
        if not isinstance(params_node, ParameterData):
            raise InputValidationError("parameters is not of type ParameterData")
        params = params_node.get_dict()

        # structure
        try:
            structure = inputdict.pop(self.get_linkname('structure'))
        except KeyError:
            raise InputValidationError("No structure specified for this calculation")
        if not isinstance(structure, StructureData):
            raise InputValidationError("structure is not of type StructureData")

        # code
        try:
            code = inputdict.pop(self.get_linkname('code'))
        except KeyError:
            raise InputValidationError("No code specified for this calculation")
        #TODO: check type of code

        # settings
        # ... if not provided fall back to empty dict
        settings_node = inputdict.pop(self.get_linkname('settings'), ParameterData())
        if not isinstance(settings_node, ParameterData):
            raise InputValidationError("settings, if specified, must be of type ParameterData")
        settings = settings_node.get_dict()

        # parent calc folder (not yet used)
        parent_calc_folder = inputdict.pop(self.get_linkname('parent_folder'), None)
        if parent_calc_folder is not None:
            if not isinstance(parent_calc_folder, RemoteData):
                raise InputValidationError("parent_calc_folder, if specified, must be of type RemoteData")

        #TODO: handle additional parameter files

        if inputdict:
            msg = "The following input data nodes are unrecognized: {}".format(inputdict.keys())
            raise InputValidationError(msg)

        return(params, structure, code, settings)


#===============================================================================
class Cp2kInput(object):
    def __init__(self, params):
        self.params = self._normalize(params)

    #---------------------------------------------------------------------------
    def _normalize(self, nested):
        """
        This method recursively converts all dict keys to uppercase.
        """
        if isinstance(nested, dict):
            for key in nested.keys():
                nested[key.upper()] = self._normalize(nested.pop(key))
            return nested
        elif isinstance(nested, list):
            return list([self._normalize(i) for i in nested])
        else:
            return nested

    #---------------------------------------------------------------------------
    def add_keyword(self, kwpath, value, params=None):
        self._add_keyword_low(kwpath.split("/"), value, self.params)

    #---------------------------------------------------------------------------
    def _add_keyword_low(self, kwpath, value, params):
        if len(kwpath)==1:
            params[kwpath[0]] = value
        elif kwpath[0] not in params.keys():
            new_subsection = {}
            params[kwpath[0]] = new_subsection
            self._add_keyword_low(kwpath[1:], value, new_subsection)
        else:
            self._add_keyword_low(kwpath[1:], value, params[kwpath[0]])

    #---------------------------------------------------------------------------
    def render(self):
        output = ["!!! Generated by AiiDA !!!"]
        self._render_section(output, self.params)
        print("\n".join(output))
        return "\n".join(output)

    #---------------------------------------------------------------------------
    def _render_section(self, output, params, indent=0):
        """
        It takes a dictionary and recurses through.

        For key-value pair it checks whether the value is a dictionary and prepends the key with &
        It passes the valued to the same function, increasing the indentation
        If the value is a list, I assume that this is something the user wants to store repetitively
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

        for key, val in params.items():
            if key.startswith('@') or key.startswith('$'):
                raise InputValidationError("CP2K internal input preprocessor not supported in AiiDA")
            if isinstance(val, dict):
                output.append('{}&{} {}'.format(' '*indent, key, val.pop('_', '')))
                self._render_section(output, val, indent + 3)
                output.append('{}&END {}'.format(' '*indent, key))
            elif isinstance(val, list):
                for listitem in val:
                    self._render_section(output,  {key:listitem}, indent)
            elif isinstance(val, bool):
                val_str = '.true.'  if val else '.false.'
                output.append('{}{}  {}'.format(' '*indent, key, val_str))
            else:
                output.append('{}{}  {}'.format(' '*indent, key, val))


#EOF