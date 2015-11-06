# -*- coding: utf-8 -*-


from aiida.orm.calculation.job import JobCalculation
from aiida.common.utils import classproperty #Do i need this?
from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.remote import RemoteData 

from aiida.common.datastructures import CalcInfo
from aiida.common.datastructures import CodeInfo

from aiida.common.exceptions import InputValidationError

import collections

class CP2KCalculation(JobCalculation):   
    """
    This is a CP2KCalculation, subclass of JobCalculation, to prepare input for cp2k
    """
    # The files that we need:
    _PROJECT_NAME = 'AIIDA-PROJECT'
    _INPUT_FILE_NAME = 'aiida.in'
    _OUTPUT_FILE_NAME = 'aiida.out'  
    _TRAJ_FILE_NAME = '{}-pos-1.xyz'.format(_PROJECT_NAME)
    _VEL_FILE_NAME = '{}-vel-1.xyz'.format(_PROJECT_NAME)
    _FORCES_FILE_NAME = '{}-frc-1.xyz'.format(_PROJECT_NAME)
    _ENER_FILE_NAME = '{}-1.ener'.format(_PROJECT_NAME)
    _COORDS_FILE_NAME = 'aiida.coords.xyz'

    # List of keywords which are not allowed when running CP2K under AiiDA
    _KEYWORDS_BLACKLIST = [
            # We block all possible changes to file names since it may
            # interfere with AiiDA's file retrieval.
            'ALL_CONF_FILE_NAME',
            'BASIS_SET_FILE_NAME',
            'BINARY_RESTART_FILE_NAME',
            'BOX2_FILE_NAME',
            'CALLGRAPH_FILE_NAME',
            'CELL_FILE_NAME',
            'CONN_FILE_NAME',
            'COORD_FILE_NAME',
            'COORDINATE_FILE_NAME',
            'DATA_FILE_NAME',
            'ENERGY_FILE_NAME',
            'FFTW_WISDOM_FILE_NAME',
            'IMAGE_RESTART_FILE_NAME',
            'INPUT_FILE_NAME',
            'KERNEL_FILE_NAME',
            'LOCHOMO_RESTART_FILE_NAME',
            'LOCLUMO_RESTART_FILE_NAME',
            'MAX_DISP_FILE_NAME',
            'MM_POTENTIAL_FILE_NAME',
            'MOLECULES_FILE_NAME',
            'MOVES_FILE_NAME',
            'NICS_FILE_NAME',
            'NMC_FILE_NAME',
            'OPTIMIZE_FILE_NAME',
            'OUTPUT_FILE_NAME',
            'PARAMETER_FILE_NAME',
            'PARAM_FILE_NAME',
            'PARM_FILE_NAME',
            'POTENTIAL_FILE_NAME',
            'REF_CELL_FILE_NAME',
            'REF_FORCE_FILE_NAME',
            'REF_TRAJ_FILE_NAME',
            'RESTART_FILE_NAME',
            'TRAJ_FILE_NAME',
            'WALKERS_FILE_NAME',
            'WFN_RESTART_FILE_NAME',
            # the following keys/sections are (over)written by AiiDA
            'CELL',
            'COORD',
            'KIND',
            'TOPOLOGY',
            ]

    def _init_internal_params(self):
        super(CP2KCalculation, self)._init_internal_params()
    
    @classproperty
    def _use_methods(cls):
        """
        This will be manually added to the _use_methods in each subclass
        """
        retdict = JobCalculation._use_methods
        # So far we need a structure, parameters, settings, and a parent_folder if we are restarting.
        # Potentials and basis sets need to be put as well
        # Anything else??
        
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
               'docstring': ("Use a node that specifies the input parameters "
                             "for the namelists"),
               },
            "parent_folder": {
               'valid_types': RemoteData,
               'additional_parameter': None,
               'linkname': 'parent_calc_folder',
               'docstring': ("Use a remote folder as parent folder (for "
                             "restarts and similar"),
               },
            })
        return retdict


    def _prepare_for_submission(self,tempfolder, inputdict):        
        """
        This is the routine to be called when you want to create
        the input files and related stuff with a plugin.
        
        :param tempfolder: a aiida.common.folders.Folder subclass where
                           the plugin should put all its files.
        :param inputdict: a dictionary with the input nodes, as they would
                be returned by get_inputdata_dict (without the Code!)
        """
        from aiida.common.utils import get_unique_filename, get_suggestion
        import re



        def nested_key_iter(nested):
            """
            Iterator for nested mixed list and dict structure,
            yielding keys only.
            """
            if isinstance(nested, collections.Mapping):
                for key, value in nested.items():
                    yield key
                    for inner_key in nested_key_iter(value):
                        yield inner_key

            elif isinstance(nested, collections.MutableSequence):
                for value in nested:
                    for inner_key in nested_key_iter(value):
                        yield inner_key

        local_copy_list = []  
        remote_copy_list = []  
        remote_symlink_list = []
        
        try:
            parameters = inputdict.pop(self.get_linkname('parameters'))
        except KeyError:
            raise InputValidationError("No parameters specified for this calculation")
        if not isinstance(parameters, ParameterData):
            raise InputValidationError("parameters is not of type ParameterData")
        
        try:
            structure = inputdict.pop(self.get_linkname('structure'))
        except KeyError:
            raise InputValidationError("No structure specified for this calculation")
        if not isinstance(structure, StructureData):
            raise InputValidationError("structure is not of type StructureData")
        try:
            code = inputdict.pop(self.get_linkname('code'))
        except KeyError:
            raise InputValidationError("No code specified for this calculation")

        # Settings can be undefined, and defaults to an empty dictionary/ParameterData
        settings = inputdict.pop(self.get_linkname('settings'), ParameterData())

        if not isinstance(settings, ParameterData):
            raise InputValidationError("settings, if specified, must be of "
                                        "type ParameterData")
        # Settings converted to uppercase
        settings_dict = convert_to_uppercase(settings.get_dict())

        parent_calc_folder = inputdict.pop(self.get_linkname('parent_folder'),None)
        if parent_calc_folder is not None:
            if not isinstance(parent_calc_folder, RemoteData):
                raise InputValidationError("parent_calc_folder, if specified,"
                    "must be of type RemoteData")

        # Here, there should be no more parameters...
        if inputdict:
            raise InputValidationError("The following input data nodes are "
                "unrecognized: {}".format(inputdict.keys()))

        
        ######################## LET'S START WRITING SOME INPUT #######################
        # I have the parameters stored in the dictionary
        # First of all, I want everything to be stored uppercase, if the user did not bother.
        # It will make sure that there is no ambiguoity in the queries, everything is uppercase!
        def print_parameters_cp2k_style(infile, params, indent = 0):
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
                     
            if the value is a tuple, I assume the first or the second piece is a unit
                dict['TEMP'] = (300, 'K')
                ===> TEMP [K] 300   
                dict['TEMP'] = ('K', 300)
                ===> TEMP [K] 300   
            TODO: Needs to be better defined here, how about TEMP__UNIT == 'K' 
            
            """
            
            
            for key, val in params.items():
                if type(val) == dict:
                    infile.write('{}&{} {}\n'.format(' '*indent, key, val.pop('_', '')))
                    print_parameters_cp2k_style(infile, val, indent + 3)
                    infile.write('{}&END {}\n'.format(' '*indent, key))
                elif type(val) == list:
                    for listitem in val:
                        print_parameters_cp2k_style(infile,  {key:listitem}, indent)
                # There is (yet) no good possibility to give the units 
                # elif type(val) == tuple:
                #    try:
                #        floatvalue, unit = float(val[0]), val[1]
                #    except ValueError:
                #        floatvalue, unit = float(val[1]), val[0]
                #    infile.write('{}{} [{}] {}\n'.format(' '*indent, key, unit, floatvalue))
                
                elif type(val) == bool:    
                    infile.write('{}{}  {}\n'.format(' '*indent, key, '.true.' if val else '.false.'))
                else:    
                    infile.write('{}{}  {}\n'.format(' '*indent, key, val))
        
        parameters_dict = convert_to_uppercase(parameters.get_dict())
        # Whatever the user wrote, the project  name is set by aiida, otherwise file retrieving will not work
        parameters_dict['GLOBAL']['PROJECT'] = self._PROJECT_NAME

        for key in nested_key_iter(parameters_dict):
            if key.startswith('@') or key.startswith('$'):
                raise InputValidationError("CP2K internal input preprocessor "
                        "not supported in AiiDA")
            if key in self._KEYWORDS_BLACKLIST:
                raise InputValidationError("Manually specifying {} for CP2K "
                        "not supported in AiiDA".format(key))

        #I will take the structure data and append it to the parameter dictionary.
        # Makes sure everything has the same output...
        # TODO: potentials, basis sets?
      
        
        subsysdict = {}
        
        ######### PATCH ################
        ### A patch to  make it work right now...
        potentials_dict = {}
        potentials_dict['H'] = 'GTH-PBE-q1'
        potentials_dict['O'] = 'GTH-PBE-q6'
        basis_set_dict = {}
        #~ basis_set_dict['H'] = 'TZV2P-GTH'
        basis_set_dict['H'] = 'DZV-GTH-PBE'
        basis_set_dict['O'] = 'DZVP-GTH-PBE'
        #~ basis_set_dict['O'] = 'TZV2P-GTH'
        basis_set_file_name = '../../GTH_BASIS_SETS'
        potential_file_name = '../../POTENTIAL'
        ########## PATCH #################
        
        #~ parameters_dict['FORCE_EVAL']['DFT']['BASIS_SET_FILE_NAME'] = basis_set_file_name
        #~ parameters_dict['FORCE_EVAL']['DFT']['POTENTIAL_FILE_NAME'] = potential_file_name
        
        ######HERE I am writing the cards KIND:
        subsysdict['KIND'] = [{'_': kind.name,
                                'ELEMENT':kind.name,
                                'BASIS_SET': basis_set_dict[kind.name],
                                'POTENTIAL': potentials_dict[kind.name],
                                'MASS': kind.mass,
                                } 
                                for kind in structure.kinds]
        # Deal with the cell:
        subsysdict['CELL'] = {cell_direction:'{:<15} {:<15} {:<15}'.format(*structure.cell[index]) 
                        for index,cell_direction in enumerate(['A', 'B', 'C'])}

        # Export the structure as XYZ file and make CP2K use that one
        # TODO: CP2K recommends PDB, but AiiDA does not have a PDB exporter yet
        subsysdict['TOPOLOGY'] = {
                'COORD_FILE_NAME': self._COORDS_FILE_NAME,
                'COORD_FILE_FORMAT': "xyz",
                }
        structure.export(tempfolder.get_abs_path(self._COORDS_FILE_NAME), 'xyz')

        # Here I am appending to the parameter - dictionary
        parameters_dict['FORCE_EVAL']['SUBSYS'] = subsysdict
        
        #THIS IS THE INPUT FILE:
        input_filename = tempfolder.get_abs_path(self._INPUT_FILE_NAME)

        # Writing to input file:
        with open(input_filename,'w') as infile:
            print_parameters_cp2k_style(infile, parameters_dict)
            
            #~ infile.write('{}'.format(parameters_dict))

        
        # TODO: Retrieving, commandline:
        settings_retrieve_list = settings_dict.pop('ADDITIONAL_RETRIEVE_LIST', [])
        cmdline_params = settings_dict.pop('CMDLINE', [])
        
        
        # Initialize codeinfo, set attributes...
        codeinfo = CodeInfo()
        codeinfo.cmdline_params = (list(cmdline_params)
                                   + ["-i", self._INPUT_FILE_NAME, "-o", self._OUTPUT_FILE_NAME])
        #calcinfo.stdin_name = self._INPUT_FILE_NAME
        #~ codeinfo.stdout_name = self._OUTPUT_FILE_NAME
        codeinfo.code_uuid = code.uuid
        
        
        calcinfo = CalcInfo()

        calcinfo.uuid = self.uuid
        #~ calcinfo.cmdline_params = (list(cmdline_params)
                #~ + ["-in", self._INPUT_FILE_NAME, "-o", self._OUTPUT_FILE_NAME])
        calcinfo.local_copy_list = local_copy_list
        calcinfo.remote_copy_list = remote_copy_list
        calcinfo.stdin_name = self._INPUT_FILE_NAME
        #~ calcinfo.stdout_name = self._OUTPUT_FILE_NAME
        calcinfo.remote_symlink_list = remote_symlink_list
        calcinfo.codes_info = [codeinfo]
        # Retrieve by default the output file and the xml file
        calcinfo.retrieve_list = []        
        calcinfo.retrieve_list.append(self._OUTPUT_FILE_NAME)
        calcinfo.retrieve_list.append(self._TRAJ_FILE_NAME)
        calcinfo.retrieve_list.append(self._VEL_FILE_NAME)
        calcinfo.retrieve_list.append(self._ENER_FILE_NAME)
        calcinfo.retrieve_list.append(self._FORCES_FILE_NAME)
        calcinfo.retrieve_list += settings_retrieve_list
        #~ calcinfo.retrieve_list += self._internal_retrieve_list
        if settings_dict:
            try:
                Parserclass = self.get_parserclass()
                parser = Parserclass(self)
                parser_opts = parser.get_parser_settings_key()
                settings_dict.pop(parser_opts)
            except (KeyError,AttributeError): # the key parser_opts isn't inside the dictionary
                raise InputValidationError("The following keys have been found in "
                  "the settings input node, but were not understood: {}".format(
                  ",".join(settings_dict.keys())))
        return calcinfo

def convert_to_uppercase(item_in_dict):
    """
    This method recursively goes through a dictionary
    and converts all the keys to uppercase.
    On the fly, it also converts the values (if strings) to upppercase
    """
    try:
        for key in item_in_dict.keys():
            item_in_dict[key.upper()] = convert_to_uppercase(item_in_dict.pop(key))
    except AttributeError:
        try:
            return item_in_dict.upper()
        except AttributeError:
            return item_in_dict
    return item_in_dict
