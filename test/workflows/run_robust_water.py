from aiida.common.example_helpers import test_and_get_code  # noqa
from aiida.orm.data.structure import StructureData  # noqa
from aiida.orm.data.parameter import ParameterData  # noqa
from aiida.orm.data.base import Str
from aiida.work.run import submit

import ase.build
from aiida_cp2k.workflows import Cp2kRobustGeoOptWorkChain

atoms = ase.build.molecule('H2O')
atoms.center(vacuum=2.0)
structure = StructureData(ase=atoms)
structure.label='H2O'
structure.store()
options_dict = {
    "resources": {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 2,
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
code = test_and_get_code('cp2k-5.1@localhost', expected_code_type='cp2k')
submit(Cp2kRobustGeoOptWorkChain,
        code=code,
        structure=structure,
        parameters=parameters,
        _options=options_dict,
        _label='MyFirstWokchain',
        _guess_multiplicity=True,
        )
