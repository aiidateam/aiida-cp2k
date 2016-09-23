from os import path
import numpy as np
from aiida.orm.calculation.job.cp2k import Cp2kCalculation, convert_to_uppercase
from aiida.orm.data.parameter import ParameterData
from aiida.parsers.parser import Parser
from aiida.parsers.exceptions import OutputParsingError
from aiida.orm.data.array.trajectory import TrajectoryData

from aiida.parsers.plugins.cp2k.readers import (
        Cp2kOutputFileReader,
        Cp2kEnergyFileReader,
        Cp2kTrajectoryFileReader
        )

class Cp2kOutputParsingError(OutputParsingError):
    pass

class Cp2kBasicParser(Parser):
    """
    Basic class to parse CP2K calculations
    """
    def __init__(self, calc):
        """
        Initialize the instance of CP2KBasicParser
        """
        # check for valid input
        if not isinstance(calc, Cp2kCalculation):
            raise Cp2kOutputParsingError("Input calc must be a Cp2kCalculation")

        super(Cp2kBasicParser, self).__init__(calc)

    def parse_with_retrieved(self, retrieved):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """

        successful = True
        return_dict = {}

        calc_input = convert_to_uppercase(self._calc.inp.parameters.get_dict())

        # look for eventual flags of the parser
        #~ try:
            #~ parser_opts = self._calc.inp.settings.get_dict()[self.get_parser_settings_key()]
        try:
            out_folder = retrieved[self._calc._get_linkname_retrieved()]
        except KeyError:
            self.logger.error("No retrieved folder found")
            return False, ()
        folder_path = out_folder.get_abs_path()
        list_of_files = out_folder.get_folder_list()
        # at least the stdout should exists
        if not self._calc._OUTPUT_FILE_NAME in list_of_files:
            self.logger.error("Standard output not found")
            successful = False
            return successful, ()

        # parse the Cp2k output log file
        output_file_path = path.join(out_folder.get_abs_path('.'),
                                self._calc._OUTPUT_FILE_NAME)
        cp2koutput = Cp2kOutputFileReader(output_file_path)
        cp2koutput.parse()
        return_dict.update(cp2koutput.data)

        # parse the energy file
        ener_file_path = path.join(out_folder.get_abs_path('.'),
                                self._calc._ENER_FILE_NAME)
        if (path.isfile(ener_file_path)):
            energies = Cp2kEnergyFileReader(ener_file_path)
            energies.parse()
            return_dict.update(energies.data)

        
#        # parse the trajectory file
        traj_file_path = path.join(out_folder.get_abs_path('.'),
                                self._calc._TRAJ_FILE_NAME)
        



        output_params = ParameterData(dict=return_dict)
        new_nodes_list = [ (self.get_linkname_outparams(),output_params) ]

	if (path.isfile(ener_file_path)):
            trajectories = Cp2kTrajectoryFileReader(traj_file_path,
                           calc_input['MOTION']['MD'].get('TIMESTEP'))
            trajectories.parse(self._calc)
    
    #        return_dict.update(trajectories.data)
            
            raw_trajectory = trajectories.data
            traj = TrajectoryData()
            traj.set_trajectory(stepids=raw_trajectory['steps'],
                                cells=raw_trajectory['cells'],
                                symbols=raw_trajectory['symbols'],
                                positions=raw_trajectory['positions_ordered'],
                                #times=raw_trajectory['times'],
                                #velocities=raw_trajectory['velocities_ordered'],
            )
#            return_dict.append((self.get_linkname_outtrajectory(),traj))
            for x in raw_trajectory.iteritems():
            	traj.set_array(x[0],np.array(x[1]))
            new_nodes_list.append((self.get_linkname_outtrajectory(),traj))
            struct=trajectories.output_structure
            new_nodes_list.append((self.get_linkname_outstructure(),struct))

        
        return successful, new_nodes_list

    def get_linkname_outtrajectory(self):
        """
        Returns the name of the link to the output_trajectory.
        Node exists in case of calculation='md', 'vc-md', 'relax', 'vc-relax'
        """
        return 'output_trajectory'
    def get_linkname_outstructure(self):
        """
        Returns the name of the link to the output_structure
        Node exists if positions or cell changed.
        """
        return 'output_structure'
