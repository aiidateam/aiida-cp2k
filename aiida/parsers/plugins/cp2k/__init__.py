
class CP2KBasicParser():
    """
    Basic class to parse CP2K calculations  
    """
    def __init__(self, calc):
        """
        Initialize the instance of PwParser
        """
        # check for valid input
        if not isinstance(calc, CP2KCalculation):
            raise QEOutputParsingError("Input calc must be a CP2KCalculation")

        super(CP2KBasicParser, self).__init__(calc)

    def parse_with_retrieved(self, retrieved):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """
        from aiida.common.exceptions import InvalidOperation
        import os, re
        # import glob
        pos_regex = re.compile(
            """
            '^(?P<sym>[a-zA-Z0-9]+)\s+(?P<x>[\-]?\d+\.\d+)\s+(?P<y>[\-]?\d+\.\d+)\s+(?P<z>[\-]?\d+\.\d+)$'
            """)
            #~ ([ \t]* [A-Z][a-z]?  ([ \t]+ [-]?[0-9]+([\.][0-9]+([E | e][+|-]?[0-9]+)?)?){3} [ \t]* [\n])+

        successful = True
        return_dict = {}
        calc_input = self._calc.inp.parameters.get_dict()
        
        # look for eventual flags of the parser
        #~ try:
            #~ parser_opts = self._calc.inp.settings.get_dict()[self.get_parser_settings_key()]
        try:
            out_folder = retrieved[self._calc._get_linkname_retrieved()]
        except KeyError:
            self.logger.error("No retrieved folder found")
            return False, ()

        list_of_files = out_folder.get_folder_list()
        # at least the stdout should exist
        if not self._calc._OUTPUT_FILE_NAME in list_of_files:
            self.logger.error("Standard output not found")
            successful = False
            return successful, ()
            
        with open(self._calc._OUTPUT_FILE_NAME) as outputfile:
            output_text = outputfile.read()
            return_dict['final_energy'] = 5
            return_dict['final_force'] = 3
            energy_results = {}
            for key, var in [('kin_E', ekin), ('temperature',temp),('pot_E', epot),('conserved_Q',consqty)]:
                results[key] = {}
                slope, intercept, r_value, p_value, std_err = linregress(times,var)
                energy_results[key]['slope'] = slope
                energy_results[key]['intercept'] = intercept
                energy_results[key]['r_value'] = r_value
                energy_results[key]['p_value'] = p_value
                energy_results[key]['std_err'] = std_err
            results_dict [ 'energy_results'] = energy_results
            
        with open(self._calc._TRAJ_FILE_NAME) as trajfile:
            timestep_in_fs = calc_input['MOTION']['MD'].get('TIMESTEP'))
            traj_txt =  trajfile.read()
            #~ traj_arr =  np.array([[[float(pos) for pos in line.split()[1:4] if line] 
                                        #~ for line in block.group(0).split('\n')[:-1] if block] 
                                            #~ for block in pos_regex.finditer(traj_txt)])
            all_positions =  [(match.group('sym'), float(match.group('x')) ,float(match.group('y')) ,float(match.group('z')))
                            for match in pos_regex.finditer(traj_txt)])
            
            return_list.append({'content': {'array': traj_arr, 'timestep_in_fs':timestep_in_fs}})
    
    #~ total_time = np.sum(usedtime)
    results['total_time'] = np.sum(usedtime)
    results['time_p_timestep'] = np.mean(usedtime)
        
        
        
        with open(self._calc._ENER_FILE) as enerfile:
            txt = enerfile.read()
            data = [[float(val) for val in line.split()]
                        for line in txt.split('\n')[1:-1]]
            steps, times, ekin, temp, epot, consqty, usedtime = zip(*data)


            
            
