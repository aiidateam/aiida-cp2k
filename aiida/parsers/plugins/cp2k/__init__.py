from aiida.orm.calculation.job.cp2k import CP2KCalculation, convert_to_uppercase
from aiida.orm.data.parameter import ParameterData
from aiida.parsers.parser import Parser
from aiida.parsers.exceptions import OutputParsingError
from aiida.orm.data.array.trajectory import TrajectoryData

from aiida.parsers.plugins.cp2k.readers import (
        CP2KOutputFileReader,
        CP2KEnergyFileReader,
        CP2KTrajectoryFileReader
        )

class CP2KOutputParsingError(OutputParsingError):
    pass

class CP2KBasicParser(Parser):
    """
    Basic class to parse CP2K calculations
    """
    def __init__(self, calc):
        """
        Initialize the instance of CP2KBasicParser
        """
        # check for valid input
        if not isinstance(calc, CP2KCalculation):
            raise CP2KOutputParsingError("Input calc must be a CP2KCalculation")

        super(CP2KBasicParser, self).__init__(calc)

    def parse_with_retrieved(self, retrieved):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """
        from os import path

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

        # parse the CP2K output log file
        output_file_path = path.join(out_folder.get_abs_path('.'),
                                self._calc._OUTPUT_FILE_NAME)
        cp2koutput = CP2KOutputFileReader(output_file_path)
        cp2koutput.parse()

        # parse the energy file
#        ener_file_path = path.join(out_folder.get_abs_path('.'),
#                                self._calc._ENER_FILE_NAME)
#        energies = CP2KEnergyFileReader(ener_file_path)
#        energies.parse()
#        
#        # parse the trajectory file
#        traj_file_path = path.join(out_folder.get_abs_path('.'),
#                                self._calc._TRAJ_FILE_NAME)
#        trajectories = CP2KTrajectoryFileReader(traj_file_path,
#                calc_input['MOTION']['MD'].get('TIMESTEP'))
#        trajectories.parse()
#
#        traj = TrajectoryData()
#        traj.set_trajectory(steps=raw_trajectory['steps'],
#                            cells=raw_trajectory['cells'],
#                            symbols=raw_trajectory['symbols'],
#                            positions=raw_trajectory['positions_ordered'],
#                            times=raw_trajectory['times'],
#                            velocities=raw_trajectory['velocities_ordered'],
#        )
#
#        for this_name in evp_keys:
#            traj.set_array(this_name, raw_trajectory[this_name])
#        new_nodes_list = [(self.get_linkname_trajectory(), traj)]

       
        # Update the result dictionary with the parsed data
        return_dict.update(cp2koutput.data)
#        return_dict.update(energies.data)
#        return_dict.update(trajectories.data)
        output_params = ParameterData(dict=return_dict)
        new_nodes_list = [ (self.get_linkname_outparams(),output_params) ]
        return successful, new_nodes_list
