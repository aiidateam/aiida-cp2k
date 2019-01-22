# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from aiida.orm.calculation.job import JobCalculation
from aiida.common.utils import classproperty
from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.singlefile import SinglefileData
from aiida.orm.data.remote import RemoteData
from aiida.common.datastructures import CalcInfo, CodeInfo
from aiida.common.exceptions import InputValidationError

from .utils import Cp2kInput


class Cp2kCalculation(JobCalculation):
    """
    This is a Cp2kCalculation, subclass of JobCalculation, to prepare input for a Cp2kCalculation.
    For information on CP2K, refer to: https://www.cp2k.org
    """

    def _init_internal_params(self):
        """
        Set parameters of instance
        """
        super(Cp2kCalculation, self)._init_internal_params()

        self._INPUT_FILE_NAME = 'aiida.inp'
        self._OUTPUT_FILE_NAME = 'aiida.out'
        self._DEFAULT_INPUT_FILE = self._INPUT_FILE_NAME
        self._DEFAULT_OUTPUT_FILE = self._OUTPUT_FILE_NAME
        self._PROJECT_NAME = 'aiida'
        self._RESTART_FILE_NAME = self._PROJECT_NAME + '-1.restart'
        self._PARENT_CALC_FOLDER_NAME = 'parent_calc/'
        self._COORDS_FILE_NAME = 'aiida.coords.xyz'
        self._default_parser = 'cp2k'

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
                'docstring': "Use a node that specifies the "
                             "input parameters for the namelists",
                },
            "parent_folder": {
                'valid_types': RemoteData,
                'additional_parameter': None,
                'linkname': 'parent_calc_folder',
                'docstring': "Use a remote folder as parent folder "
                             "(for restarts and similar)",
                },
            "file": {
                'valid_types': SinglefileData,
                'additional_parameter': "linkname",
                'linkname': cls._get_linkname_file,
                'docstring': "Use files to provide additional parameters",
                },
            })
        return retdict

    @classmethod
    def _get_linkname_file(cls, linkname):
        return linkname

    def _prepare_for_submission(self, tempfolder, inputdict):
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.

        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """

        in_nodes = self._verify_inlinks(inputdict)
        params, structure, code, settings, local_copy_list, parent_calc_folder = in_nodes

        # write cp2k input file
        inp = Cp2kInput(params)
        inp.add_keyword("GLOBAL/PROJECT", self._PROJECT_NAME)

        if structure is not None:
            struct_fn = tempfolder.get_abs_path(self._COORDS_FILE_NAME)
            structure.export(struct_fn, fileformat="xyz")

            for idx, dim in enumerate('ABC'):
                inp.add_keyword(f"FORCE_EVAL/SUBSYS/CELL/{dim}",
                               "{:<15} {:<15} {:<15}".format(*structure.cell[idx]))

            topo = "FORCE_EVAL/SUBSYS/TOPOLOGY"
            inp.add_keyword(f"{topo}/COORD_FILE_NAME", self._COORDS_FILE_NAME)
            inp.add_keyword(f"{topo}/COORD_FILE_FORMAT", "XYZ")

        inp_fn = tempfolder.get_abs_path(self._INPUT_FILE_NAME)

        with open(inp_fn, 'w') as fhandle:
            inp.to_file(fhandle)

        # create code info
        codeinfo = CodeInfo()
        cmdline = settings.pop('cmdline', [])
        cmdline += ["-i", self._INPUT_FILE_NAME]
        codeinfo.cmdline_params = cmdline
        codeinfo.stdout_name = self._OUTPUT_FILE_NAME
        codeinfo.join_files = True
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
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = []
        calcinfo.retrieve_list = [self._OUTPUT_FILE_NAME, self._RESTART_FILE_NAME]
        calcinfo.retrieve_list += settings.pop('additional_retrieve_list', [])

        # symlinks
        if parent_calc_folder is not None:
            comp_uuid = parent_calc_folder.get_computer().uuid
            remote_path = parent_calc_folder.get_remote_path()
            symlink = (comp_uuid, remote_path, self._PARENT_CALC_FOLDER_NAME)
            calcinfo.remote_symlink_list.append(symlink)

        # check for left over settings
        if settings:
            msg = "The following keys have been found in the settings input node {}, ".format(self.pk)
            msg += "but were not understood: " + ",".join(settings.keys())
            raise InputValidationError(msg)

        return calcinfo

    def _verify_inlinks(self, inputdict):
        # parameters
        params_node = inputdict.pop('parameters', None)
        if params_node is None:
            raise InputValidationError("No parameters specified")
        if not isinstance(params_node, ParameterData):
            raise InputValidationError("parameters type not ParameterData")
        params = params_node.get_dict()

        # structure
        structure = inputdict.pop('structure', None)
        if structure is not None:
            if not isinstance(structure, StructureData):
                raise InputValidationError("structure type not StructureData")

        # code
        code = inputdict.pop(self.get_linkname('code'), None)
        if code is None:
            raise InputValidationError("No code specified")

        # settings
        # ... if not provided fall back to empty dict
        settings_node = inputdict.pop('settings', ParameterData())
        if not isinstance(settings_node, ParameterData):
            raise InputValidationError("settings type not ParameterData")
        settings = settings_node.get_dict()

        # parent calc folder
        parent_calc_folder = inputdict.pop('parent_calc_folder', None)
        if parent_calc_folder is not None:
            if not isinstance(parent_calc_folder, RemoteData):
                msg = "parent_calc_folder type not RemoteData"
                raise InputValidationError(msg)

        # handle additional parameter files
        local_copy_list = [(v.get_file_abs_path(), v.filename) for v in inputdict.values() if isinstance(v, SinglefileData)]

        # and filter them from the inputdict
        inputdict = {k: v for k, v in inputdict.items() if not isinstance(v, SinglefileData)}

        if inputdict:
            msg = "unrecognized input nodes: " + str(inputdict.keys())
            raise InputValidationError(msg)

        return (params, structure, code, settings, local_copy_list, parent_calc_folder)
