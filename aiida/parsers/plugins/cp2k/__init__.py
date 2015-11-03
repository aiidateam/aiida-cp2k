
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
        import os
        import glob

        successful = True

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
