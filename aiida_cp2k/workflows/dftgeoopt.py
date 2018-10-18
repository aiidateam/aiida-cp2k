from aiida.orm.code import Code
from aiida.orm.utils import CalculationFactory, DataFactory
from aiida.work.workchain import WorkChain, ToContext, Outputs, while_
from aiida.work.run import submit

# data objects
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')

def dict_merge(dct, merge_dct):
    """ Taken from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
    Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, dict_merge recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct
    :return: None
    """
    import collections
    for k, v in merge_dct.iteritems():
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            dict_merge(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]

from aiida_cp2k.workflows import Cp2kDftBaseWorkChain
cp2k_motion ={
            'MOTION': {
                'GEO_OPT': {
                    'TYPE': 'MINIMIZATION',                     #default: MINIMIZATION
                    'OPTIMIZER': 'BFGS',                        #default: BFGS
                    'MAX_ITER': 50,                             #default: 200
                    'MAX_DR':    '[bohr] 0.0030',               #default: [bohr] 0.0030
                    'RMS_DR':    '[bohr] 0.0015',               #default: [bohr] 0.0015
                    'MAX_FORCE': '[bohr^-1*hartree] 0.00045',   #default: [bohr^-1*hartree] 0.00045
                    'RMS_FORCE': '[bohr^-1*hartree] 0.00030',   #default: [bohr^-1*hartree] 0.00030
                    'BFGS' : {
                        'TRUST_RADIUS': '[angstrom] 0.25',      #default: [angstrom] 0.25
                    },
                },
                'PRINT': {
                    'TRAJECTORY': {
                        'FORMAT': 'DCD_ALIGNED_CELL',
                        'EACH': {
                            'GEO_OPT': 1,
                        },
                    },
                    'RESTART':{
                        'BACKUP_COPIES': 0,
                        'EACH': {
                            'GEO_OPT': 1,
                        },
                    },
                    'RESTART_HISTORY':{
                        'EACH': {
                            'GEO_OPT': 100,
                        },
                    },
                    'CELL': {
                        '_': 'OFF',
                    },
                    'VELOCITIES': {
                        '_': 'OFF',
                    },
                    'FORCES': {
                        '_': 'OFF',
                    },
                    'STRESS': {
                        '_': 'OFF',
                    },
                },
            },
}


default_options = {
    "resources": {
        "num_machines": 4,
        "num_mpiprocs_per_machine": 12,
    },
    "max_wallclock_seconds": 3 * 60 * 60,
}

class Cp2kGeoOptWorkChain(WorkChain):
    """
    Workchain to run SCF calculation wich CP2K
    """
    @classmethod
    def define(cls, spec):
        super(Cp2kGeoOptWorkChain, cls).define(spec)
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input("parameters", valid_type=ParameterData,
                default=ParameterData(dict={}))
        spec.input("options", valid_type=ParameterData,
                default=ParameterData(dict=default_options))
        spec.input('parent_folder', valid_type=RemoteData,
                default=None, required=False)

        #spec.output('output_structure', valid_type=StructureData)

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_calculation)(
                cls.prepare_calculation,
                cls.run_calculation,
                cls.inspect_calculation,
            ),
            cls.return_results,
        )

    def setup(self):
        self.ctx.structure = self.inputs.structure
        self.ctx.converged = False
        self.ctx.parameters = cp2k_motion
        dict_merge(self.ctx.parameters, {'GLOBAL':{'RUN_TYPE':'GEO_OPT'}})
        dict_merge(self.ctx.parameters, {'FORCE_EVAL':{'DFT':{'PRINT':{'MO_CUBES':{'_': 'OFF'}}}}})
        dict_merge(self.ctx.parameters, {'FORCE_EVAL':{'DFT':{'PRINT':{'MULLIKEN':{'_': 'OFF'}}}}})
        dict_merge(self.ctx.parameters, {'FORCE_EVAL':{'DFT':{'PRINT':{'LOWDIN':{'_': 'OFF'}}}}})
        dict_merge(self.ctx.parameters, {'FORCE_EVAL':{'DFT':{'PRINT':{'HIRSHFELD':{'_': 'OFF'}}}}})
        user_params = self.inputs.parameters.get_dict()
        dict_merge(self.ctx.parameters, user_params)

    def validate_inputs(self):
        pass

    def should_run_calculation(self):
        return not self.ctx.converged

    def prepare_calculation(self):
        """Prepare all the neccessary input links to run the calculation"""
        self.ctx.inputs = {
            'code'      : self.inputs.code,
            'structure' : self.ctx.structure,
            '_options'  : self.inputs.options,
            }
        # use the new parameters
        p = ParameterData(dict=self.ctx.parameters)
        p.store()
        self.ctx.inputs['parameters'] = p

    def run_calculation(self):
        """Run scf calculation."""
        # Create the calculation process and launch it
        future  = submit(Cp2kDftBaseWorkChain, **self.ctx.inputs)
        self.report("pk: {} | Running cp2k GEO_OPT")
        return ToContext(cp2k=Outputs(future))

    def inspect_calculation(self):
        self.ctx.converged = True

    def return_results(self):
        pass
