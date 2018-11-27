from aiida.common.example_helpers import test_and_get_code  # noqa
from aiida.orm.data.structure import StructureData  # noqa
from aiida.orm.data.parameter import ParameterData  # noqa
from aiida.orm.data.base import Str
from aiida.work.run import submit

from ase.io import read
from aiida_cp2k.workflows import Cp2kRobustGeoOptWorkChain

atoms = read('Cu-MOF-74.cif')
structure = StructureData(ase=atoms)
structure.label='Cu-MOF-74'
structure.store()

options_dict = {
    "resources": {
        "num_machines": 2,
    },
    "max_wallclock_seconds": 1 * 60 * 60,
    }

params_dict = {
        'MOTION':{
            'MD':{
                'STEPS': 5,
                },
            'GEO_OPT': {
                'MAX_ITER': 5,
            },
            'CELL_OPT': {
                'MAX_ITER': 5,
            },
        },
}
parameters = ParameterData(dict=params_dict)
code = test_and_get_code('cp2k@fidis-debug', expected_code_type='cp2k')
submit(Cp2kRobustGeoOptWorkChain,
        code=code,
        structure=structure,
        parameters=parameters,
        _options=options_dict,
        _label='MyFirstWokchain',
        _guess_multiplicity=True,
        )
