from aiida.parsers.plugins.cp2k import  CP2KBasicParser




calc = Calculation.get_subclass_from_pk(66)
parser = CP2KBasicParser(calc)

parser.parse_with_retrieved({'retrieved':calc.get_retrieved_node()})
