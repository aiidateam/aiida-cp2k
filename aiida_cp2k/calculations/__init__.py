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
        local_copy_list = []
        for key, val in inputdict.items():
            if isinstance(val, SinglefileData):
                inputdict.pop(key)
                local_copy_list.append((val.get_file_abs_path(), val.filename))

        if inputdict:
            msg = "unrecognized input nodes: " + str(inputdict.keys())
            raise InputValidationError(msg)

        return (params, structure, code, settings, local_copy_list, parent_calc_folder)


class Cp2kInput(object):
    def __init__(self, params):
        self._params = params

    def add_keyword(self, kwpath, value):
        _add_keyword(kwpath.split("/"), value, self._params)

    def to_file(self, fhandle):
        fhandle.write("!!! Generated by AiiDA !!!\n")
        for line in _render_cp2k_section(self._params):
            fhandle.write(f"{line}\n")


def _add_keyword(kwpath, value, params):
    if len(kwpath) == 1:  # simple key/value for the current params
        params[kwpath[0]] = value

    else:  # the keyword is not for the current level
        if kwpath[0] not in params.keys():  # make sure that the section exists
            params[kwpath[0]] = {}

        _add_keyword(kwpath[1:], value, params[kwpath[0]])


def _render_cp2k_section(params, indent=0, indent_width=3):
    """
    It takes a nested dictionary/list structure and yields line for a CP2K input file.

    For key-value pair it checks whether the value is a dictionary
    and prepends the key with & (CP2K section).
    It passes the value to the same function, increasing the indentation
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

    from collections.abc import Mapping, Sequence

    for key, val in sorted(params.items()):
        if key.upper() != key:  # keys are not case-insensitive, ensure that they follow the current scheme
            raise InputValidationError("keyword '%s' not upper case" % key)

        if key.startswith('@') or key.startswith('$'):
            raise InputValidationError("CP2K preprocessor directives not supported")

        ispace = ' ' * indent

        if isinstance(val, Mapping):
            section_param = val.pop('_', '')

            yield f"{ispace}&{key} {section_param}"
            yield from _render_cp2k_section(val, indent + indent_width)
            yield f"{ispace}&END {key}"

        elif isinstance(val, Sequence):
            for listitem in val:
                yield from _render_cp2k_section({key: listitem}, indent)

        elif isinstance(val, bool):
            val_str = '.TRUE.' if val else '.FALSE.'
            yield f"{ispace}{key} {val_str}"

        else:
            yield f"{ispace}{key} {val}"
