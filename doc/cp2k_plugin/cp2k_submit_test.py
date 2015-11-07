#!/usr/bin/env python
import os
import json
from aiida import load_dbenv
load_dbenv()

from aiida.orm import Code, Computer
from aiida.orm import DataFactory


# Read computer and code from file (local_config.json)
with open('local_config.json') as f:
    in_dict = json.load(f)
    computer = Computer.get(in_dict['computer'])
    code = Code.get(in_dict['code'])



#Let's define a simple cubic structure, e.g BaTO3
StructureData = DataFactory('structure')
alat = 9.8528 # angstrom
cell = [[alat, 0., 0.,],
        [0., alat, 0.,],
        [0., 0., alat,],
       ]
s = StructureData(cell=cell)
s.importfile("cp2k_submit_test.xyz")

#Let's define some parameters
ParameterData = DataFactory('parameter')

parameters = ParameterData(dict={
          'global': {
              'project': 'H2O-32',
              'print_level': 'medium',
              'run_type': 'energy',
              'timings': {
                  'threshold': 0.001,
              },
          },
          'force_eval': {
              'method': 'quickstep',
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
                          '_': 'PADE',
                      },
                  },
                  'scf': {
                      'SCF_GUESS': 'ATOMIC',
                      'OT': {
                          '_': 'ON',
                          'MINIMIZER': 'DIIS',
                      },
                      'MAX_SCF': 20,
                      'EPS_SCF': 1.0E-07,
                      'OUTER_SCF': {
                          'MAX_SCF': 10,
                          'EPS_SCF': 1.0E-7,
                      },
                      'PRINT': {
                          'RESTART': {
                              '_': 'OFF',
                          },
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

