#!/usr/bin/env python
# -*- coding: utf-8 -*-

from aiida import load_dbenv, is_dbenv_loaded
from aiida.backends import settings
if not is_dbenv_loaded():
    load_dbenv(profile=settings.AIIDADB_PROFILE)

from aiida.common.example_helpers import test_and_get_code
from aiida.orm.data.structure import StructureData
from aiida.orm.data.parameter import ParameterData
from aiida.orm import CalculationFactory

import ase.build

def main():
    # build structure
    ase_struct = ase.build.molecule('H2O')
    ase_struct.center(vacuum=2.0)
    structure = StructureData(ase=ase_struct)
    print(structure)
    #structure.store()

    # simulation parameters
    parameters = ParameterData(dict={
        'force_eval': {
            'method': 'Quickstep',
            'dft': {
                'qs': {
                    'eps_default': 1.0e-12,
                    'wf_interpolation': 'ps',
                    'extrapolation_order': 3,
                },
                'mgrid': {
                    'ngrids': 4,
                    'cutoff':280,
                    'rel_cutoff': 30,
                },
                'xc': {
                    'xc_functional': {
                        '_': 'LDA',
                    },
                },
                'poisson': {
                    'periodic': 'none',
                    'psolver': 'MT',
                },
            },
            'subsys': {
                'kind': [
                    {'_':'O', 'basis_set':'DZVP-MOLOPT-SR-GTH',  'potential': 'GTH-LDA' },
                    {'_':'H', 'basis_set':'DZVP-MOLOPT-SR-GTH',  'potential': 'GTH-LDA' },
                ],
            },
        }
    })

    #Set up the calculation:
    code = test_and_get_code("cp2k", expected_code_type='cp2k.cp2k')
    #code = Code.get_from_string('cp2k3.0')
    calc = code.new_calc()
    calc.set_max_wallclock_seconds(60) # one minute
    calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 4})
    calc.use_structure(structure)
    #calc.use_code(code)
    calc.use_parameters(parameters)
    calc.label = "Test CP2K run"
    calc.description = "Test calculation with the CP2K code"
    calc.submit_test()

# if submit_test:
#     subfolder, script_filename = calc.submit_test()
#     print "Test_submit for calculation (uuid='{}')".format(
#         calc.uuid)
#     print "Submit file in {}".format(os.path.join(
#         os.path.relpath(subfolder.abspath),
#         script_filename
#     ))
# else:
#     calc.store_all()
#     print "created calculation; calc=Calculation(uuid='{}') # ID={}".format(
#         calc.uuid, calc.dbnode.pk)
#     calc.submit()
#     print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
#         calc.uuid, calc.dbnode.pk)
# 

if __name__ == "__main__":
    main()


#       &GLOBAL
#   PROJECT cp2k
#&END GLOBAL
#&FORCE_EVAL
#   METHOD Quickstep
#   STRESS_TENSOR ANALYTICAL
#   &PRINT
#      &STRESS_TENSOR ON
#      &END STRESS_TENSOR
#   &END PRINT
#   &DFT
#      BASIS_SET_FILE_NAME BASIS_MOLOPT
#      POTENTIAL_FILE_NAME POTENTIAL
#      &MGRID
#         CUTOFF [eV] 5.442277204873448682e+03
#      &END MGRID
#      &SCF
#         MAX_SCF 50
#      &END SCF
#      &LS_SCF
#         MAX_SCF 50
#      &END LS_SCF
#      &XC
#         &XC_FUNCTIONAL LDA
#         &END XC_FUNCTIONAL
#      &END XC
#      &POISSON
#         PERIODIC NONE
#         PSOLVER  MT
#      &END POISSON
#   &END DFT
#   &SUBSYS
#      &COORD
#         O 2.000000000000000000e+00 2.763239000000000445e+00 2.596308999999999756e+00
#         H 2.000000000000000000e+00 3.526478000000000446e+00 1.999999999999999778e+00
#         H 2.000000000000000000e+00 2.000000000000000444e+00 1.999999999999999778e+00
#      &END COORD
#      &CELL
#         PERIODIC NONE
#         A 4.000000000000000000e+00 0.000000000000000000e+00 0.000000000000000000e+00
#         B 0.000000000000000000e+00 5.526478000000000002e+00 0.000000000000000000e+00
#         C 0.000000000000000000e+00 0.000000000000000000e+00 4.596308999999999756e+00
#      &END CELL
#      &KIND H
#         BASIS_SET DZVP-MOLOPT-SR-GTH
#         POTENTIAL GTH-LDA
#      &END KIND
#      &KIND O
#         BASIS_SET DZVP-MOLOPT-SR-GTH
#         POTENTIAL GTH-LDA
#      &END KIND
#   &END SUBSYS
#&END FORCE_EVAL


#EOF