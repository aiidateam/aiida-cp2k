from aiida.common.example_helpers import test_and_get_code  # noqa
from aiida.orm.data.structure import StructureData  # noqa
from aiida.orm.data.parameter import ParameterData  # noqa
from aiida.orm.data.base import Str
from aiida.work.run import submit

from ase.io import read
from cp2k import Cp2kDftBaseWorkChain

atoms = read('Fe-MOF-74_h111.xyz')
atoms.cell = [[6.96775, 0.00000, 0.00000],
        [-2.33067, 15.22261, 0.00000],
        [ -2.32566, -7.57517, 13.22945]]

structure = StructureData(ase=atoms)
structure.store()
options_dict = {
    "resources": {
        "num_machines": 2,
        "num_mpiprocs_per_machine": 12,
    },
    "max_wallclock_seconds": 8 * 60 * 60,
    }
options = ParameterData(dict=options_dict)
code = test_and_get_code('cp2k@daint', expected_code_type='cp2k')
submit(Cp2kDftBaseWorkChain,
        code=code,
        structure=structure,
        options=options,
        ) 
