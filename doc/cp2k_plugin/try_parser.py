from aiida.parsers.plugins.cp2k import  CP2KBasicParser




calc = Calculation.get_subclass_from_pk(52)
CP2KBasicParser(calc)

