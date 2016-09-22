#!/usr/bin/env python
import numpy as np
import sys
import os
from aiida import load_dbenv
from aiida.orm import Code, Computer
from aiida.orm import DataFactory
from aiida.common.example_helpers import test_and_get_code
from aiida.orm.data.gaussianbasis import upload_cp2k_basissetfile
from aiida.orm.data.gaussianpseudo import GaussianpseudoData as gpp

__license__ = "MIT license, see LICENSE.txt file"



try:
    dontsend = sys.argv[1]
    if dontsend == "--dont-send":
        submit_test = True
    elif dontsend == "--send":
        submit_test = False
    else:
        raise IndexError
except IndexError:
    print >> sys.stderr, ("The first parameter can only be either "
                          "--send or --dont-send")
    sys.exit(1)
try:
    codename = sys.argv[2]
except IndexError:
    codename = None


code = test_and_get_code(codename, expected_code_type='cp2k.CP2KCalculation')
#code = Code.get_from_string('cp2k3.0')

#Let's define a simple cubic structure
StructureData = DataFactory('structure')
alat = 9.8528 # angstrom
cell = [[alat, 0., 0.,],
        [0., alat, 0.,],
        [0., 0., alat,],
       ]
s = StructureData(cell=cell)
coords=np.loadtxt('H2O-32.xyz', dtype={'names': ('name','x','y','z'),
                  'formats':('S15', np.float, np.float,np.float)},
                  skiprows=2)
for l in coords:
    s.append_atom(position=(l[1],l[2],l[3]), symbols=l[0])


#Let's define some parameters
ParameterData = DataFactory('parameter')
parameters = ParameterData(dict={
          'global': {
              'run_type': 'MD',
              'timings': {
                  'threshold': 0.001,
              },
          },
          'motion': {
                'MD': {
                    'ensemble': 'NVE',
                    'steps': 5,
                    'timestep': 0.1,
                    'temperature':300,
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
                      'MAX_SCF': 10,
                      'EPS_SCF': 1.0E-07,
                      'OUTER_SCF': {
                          'MAX_SCF': 10,
                          'EPS_SCF': 1.0E-7,
                      },
                  },
              },
          },
})


#Set up the calculation:
calc = code.new_calc()
calc.set_max_wallclock_seconds(1*60*60)
calc.set_resources({"num_machines": 1, "num_mpiprocs_per_machine": 4})
calc.use_structure(s)
try:
    calc.use_basissets_type(["DZVP","GTH","PBETST"])
#    calc.use_basissets_type(["DZV"])
except :
#    raise ValueError("Basis set selection error")
    upload_cp2k_basissetfile("../testdata/cp2k.basis")
    calc.use_basissets_type(["DZVP","GTH","PBETST"])
try:
    calc.use_pseudo_type(gpp_type="GTH", xc="PBETST")
#    calc.use_pseudo_type(gpp_type="GTH")
except:
    gpp.upload_cp2k_gpp_file("../testdata/cp2k.pseudo")
    calc.use_pseudo_type(gpp_type="GTH", xc="PBETST")
calc.use_code(code)
calc.use_parameters(parameters)
calc.label = "Test CP2K run"
calc.description = "Test calculation with the CP2K code"

if submit_test:
    subfolder, script_filename = calc.submit_test()
    print "Test_submit for calculation (uuid='{}')".format(
        calc.uuid)
    print "Submit file in {}".format(os.path.join(
        os.path.relpath(subfolder.abspath),
        script_filename
    ))
else:
    calc.store_all()
    print "created calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)
    calc.submit()
    print "submitted calculation; calc=Calculation(uuid='{}') # ID={}".format(
        calc.uuid, calc.dbnode.pk)


