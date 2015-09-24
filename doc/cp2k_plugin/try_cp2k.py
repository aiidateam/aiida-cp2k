#!/usr/bin/env python
import os
from aiida import load_dbenv
load_dbenv()

from aiida.orm import Code, Computer
from aiida.orm import DataFactory


# Put the name of the computer you want to run
computer = Computer.get('thea')

# Put the code, cp2k, which uses the plugin cp2k.CP2KCalculation
code =  Code.get('cp2k')


#Let's define a simple cubic structure, e.g BaTO3
StructureData = DataFactory('structure')
alat = 4. # angstrom
cell = [[alat, 0., 0.,],
        [0., alat, 0.,],
        [0., 0., alat,],
       ]
s = StructureData(cell=cell)
s.append_atom(position=(0.,0.,0.),symbols='Ba')
s.append_atom(position=(alat/2.0,alat/2.,alat/2.),symbols='Ti')
s.append_atom(position=(alat/2.0,alat/2.,0.),symbols='O')
s.append_atom(position=(alat/2.,0.,alat/2.),symbols='O')
s.append_atom(position=(0.,alat/2.,alat/2.),symbols='O')



#Let's define some parameters
ParameterData = DataFactory('parameter')

parameters = ParameterData(dict={
          'global': {
              'print_level': 'low',
              'run_type': 'energy_force',
              },
          'force_eval': {
              'method': 'quickstep',
              'dft':
                  {
                  'qs':{
                      'eps_default': 1.0e-18,
                      },
                  'mgrid':{
                      'ngrids': 4,
                      'cutoff':150,
                      'rel_cutoff': 60,
                      },
                  'xc': {
                      'xc_functional': {
                          'keyword': 'PADE',
                          },
                       },   
                    },
                  'scf': {
                       'SCF_GUESS': ['ATOMIC','GUESS'],
                       'EPS_SCF': 1.0E-17,
                       'MAX_SCF': 300,
                       'ADDED_MOS': 10,
                       'DIAGONALIZATION': {
                          'keyword': 'ON',
                          'ALGORITHM': 'STANDARD',
                           },
                       'MIXING': {
                           'keyword': 'T',
                           'METHOD': 'BROYDEN_MIXING',
                           'ALPHA': 0.4,
                           'NBROYDEN': 8,
                           'SMEAR': {
                               'keyword': 'ON',
                               'METHOD': 'FERMI_DIRAC',
                               'ELECTRONIC_TEMPERATURE': ('K',300)
                               },
                            },
                        },
                    },
              })


#what about k-points?
#~ KpointsData = DataFactory('array.kpoints')
#~ kpoints = KpointsData()
#~ kpoints.set_kpoints_mesh([5,5,5])
#~ kpoints.set_kpoints_mesh([5,5,5],offset=(0.5,0.5,0.5))


#Set up the calculation:
calc = code.new_calc()
calc.set_computer(computer)
calc.set_max_wallclock_seconds(30*60) # 30 min
calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 1})

calc.use_structure(s)
calc.use_code(code)
calc.use_parameters(parameters)
#~ calc.use_kpoints(kpoints)
#~ calc.use_pseudos_from_family('all_uspp')


calc.label = "My first calculation"
#~ calc.store_all()
#I just want a submit-test
subfolder, script_filename = calc.submit_test()

print "Test submit file in {}".format(os.path.join(
            os.path.relpath(subfolder.abspath),
            script_filename
            ))

