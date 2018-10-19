from aiida.common.example_helpers import test_and_get_code  # noqa
from aiida.orm.data.structure import StructureData  # noqa
from aiida.orm.data.parameter import ParameterData  # noqa
from aiida.orm.data.base import Str
from aiida.work.run import submit

from ase.io import read
from aiida_cp2k.workflows import Cp2k4StepsWorkChain

atoms = read('/home/daniele/Dropbox (LSMO)/proj44_studycasesCP2K/CELL_OPT/13150N_CoRE-COF_4layers.cif')
structure = StructureData(ase=atoms)
structure.label='13150Nx4layers'
structure.store()
options_dict = {
    "resources": {
        "num_machines": 2,
        },
    "max_wallclock_seconds": 3 * 60 * 60,
    }
options = ParameterData(dict=options_dict)

params_dict = {}

parameters = ParameterData(dict=params_dict)
code = test_and_get_code('cp2k-5.1@fidis', expected_code_type='cp2k')
submit(Cp2k4StepsWorkChain,
        code=code,
        structure=structure,
        parameters=parameters,
        options=options,
        _label='MyFirstWokchain',
        )
