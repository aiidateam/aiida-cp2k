from aiida.orm.calculation.job.cp2k import CP2KCalculation, convert_to_uppercase
from aiida.parsers.parser import Parser
from aiida.parsers.exceptions import OutputParsingError

class CP2KParsingError(OutputParsingError):
    pass
class CP2KBasicParser(Parser):
    """
    Basic class to parse CP2K calculations  
    """
    def __init__(self, calc):
        """
        Initialize the instance of PwParser
        """
        # check for valid input
        print calc
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
        from scipy.stats import linregress
        import numpy as np
        #~ from aiida.comm
        # import glob
        pos_regex = re.compile("""
        (?P<sym>[a-zA-Z0-9]+)\s+
        (?P<x>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)\s+
        (?P<y>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)\s+
        (?P<z>[-]?\d+[\.]?\d+([E | e][+|-]?\+)?)""", re.X)
            #~ ([ \t]* [A-Z][a-z]?  ([ \t]+ [-]?[0-9]+([\.][0-9]+([E | e][+|-]?[0-9]+)?)?){3} [ \t]* [\n])+
        pos_block_regex = re.compile("""
            (
                \s*   #White space in the beginning (maybe)
                [A-Za-z0-9]+  #A tag for a species
                (
                   \s+ [-]?\d+[\.]?\d+([E | e][+|-]?\+)?  #The number   ([E | e][+|-]?[0-9]+)?)?
                ){3} 
                \s* [\n] #White space and line break in the end
            )+ #A block should one or more lines
            """, re.X | re.M)

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

        output_file_path = os.path.join(out_folder.get_abs_path('.'),
                                self._calc._OUTPUT_FILE_NAME)
        
        with open(output_file_path) as f:
            txt = f.read()
            if not txt:
                raise CP2KParsingError('Empty output file')
            #TODO PARSE THE OUTPUT FILE HERE
            # 

        # PARSING THE ENERGY FILE:
        ener_file_path = os.path.join(out_folder.get_abs_path('.'),
                                self._calc._ENER_FILE_NAME)
        with open(ener_file_path) as f:
            txt = f.read()
            #read the energy file:
            data = [map(float,line.split())
                        for line in txt.split('\n')[1:-1]]
            steps, times, ekin, temp, epot, consqty, usedtime = zip(*data)
            #steps are integers!
            steps = map(int, steps)
            results = {}
            
            
            for key, var in [('kin_E', ekin), ('temperature',temp),('pot_E', epot),('conserved_Q',consqty)]:
                results[key] = {}
                slope, intercept, r_value, p_value, std_err = linregress(times,var)
                results[key]['slope'] = slope
                results[key]['intercept'] = intercept
                results[key]['r_value'] = r_value
                results[key]['p_value'] = p_value
                results[key]['std_err'] = std_err
                
            #~ total_time = np.sum(usedtime)
            results['total_time'] = np.sum(usedtime)
            results['time_p_timestep'] = np.mean(usedtime)
            #~ print results
        traj_file_path = os.path.join(out_folder.get_abs_path('.'),
                                self._calc._TRAJ_FILE_NAME)    
        with open(traj_file_path) as f:
            txt = f.read()
            #~ print calc_input
            timestep_in_fs = calc_input['MOTION']['MD'].get('TIMESTEP')
            print timestep_in_fs
            #~ traj_arr =  np.array([[[float(pos) for pos in line.split()[1:4] if line] 
                                        #~ for line in block.group(0).split('\n')[:-1] if block] 
                                            #~ for block in pos_regex.finditer(traj_txt)])
            blocks = [block for block in  pos_block_regex.finditer(txt)]
            print len(blocks)
            #~ print txt[:10000]
            #~ print '############'
            

            #~ print pos_block_regex_2.search(txt).group(0)
            
            #~ print len(blocks)
            #~ print txt
            traj = np.array([[[float(match.group('x')) ,float(match.group('y')) ,float(match.group('z'))] 
                    for  match in pos_regex.finditer(block.group(0))] 
                        for block in blocks])
            print traj.shape
            return_list.append({'content': {'array': traj_arr, 'timestep_in_fs':timestep_in_fs}})
    
        results['total_time'] = np.sum(usedtime)
        results['time_p_timestep'] = np.mean(usedtime)
        
        

            
