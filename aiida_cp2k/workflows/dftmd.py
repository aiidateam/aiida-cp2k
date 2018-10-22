from aiida.orm.code import Code
from aiida.orm.utils import CalculationFactory, DataFactory
from aiida.work.workchain import WorkChain, ToContext, Outputs, while_
from aiida.work.run import submit
from .dftutilities import dict_merge, default_options, disable_printing_charges_dict, empty_pd
from copy import deepcopy

# data objects
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')

# workchains
from aiida_cp2k.workflows import Cp2kDftBaseWorkChain

cp2k_motion ={
    'MOTION': {
        'MD': {
            'ENSEMBLE': 'NVT',                      #main options: NVT, NPT_F
            'STEPS': 50,                            #default: 3
            'TIMESTEP': '[fs] 0.5',                 #default: [fs] 0.5
            'TEMPERATURE': '[K] 300',               #default: [K] 300
            'DISPLACEMENT_TOL': '[angstrom] 1.0',   #default: [bohr] 100
            'THERMOSTAT' : {
                'REGION': 'GLOBAL',                 #default: GLOBAL
                'TYPE': 'CSVR',
                'CSVR': {
                    'TIMECON': 0.1,                 #default: 1000, use: 0.1 for equilibration, 50~100 for production
                },
            },
            'BAROSTAT': {                           #by default the barosthat uses the same thermo as the partricles
                'PRESSURE': '[bar] 1.0',            #default: 0.0
                'TIMECON': '[fs] 1000',             #default: 1000, good for crystals
                'VIRIAL': 'XYZ',                    #default: XYZ
            },
            'PRINT': {
                'ENERGY': {
                    '_': 'OFF',                     #default: LOW (print .ener file)
                },
            },
        },
        'PRINT': {
            'TRAJECTORY': {
                'FORMAT': 'DCD_ALIGNED_CELL',
                'EACH': {
                    'MD': 1,
                },
            },
            'RESTART':{
                'BACKUP_COPIES': 0,
                'EACH': {
                    'MD': 1,
                },
            },
            'RESTART_HISTORY':{
                'EACH': {
                    'MD': 100,
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

class Cp2kMdWorkChain(WorkChain):
    """Workchain to run DFT-based MD simulations with CP2K"""
    @classmethod
    def define(cls, spec):
        super(Cp2kMdWorkChain, cls).define(spec)

        # specify the inputs of the workchain
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input("parameters", valid_type=ParameterData, default=empty_pd)
        spec.input("_options", valid_type=dict, default=deepcopy(default_options))
        spec.input('parent_folder', valid_type=RemoteData, default=None, required=False)
        spec.input('_guess_multiplicity', valid_type=bool, default=False)

        # specify the chain of calculations
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

        # specify the outputs of the workchain
        spec.output('output_structure', valid_type=StructureData)
        spec.output('output_parameters', valid_type=ParameterData)
        spec.output('remote_folder', valid_type=RemoteData)

    def setup(self):
        """Setup initial values of all the parameters."""
        self.ctx.structure = self.inputs.structure
        self.ctx.converged = False
        self.ctx.parameters = deepcopy(cp2k_motion)

        # add things to the input parameters dictionary
        dict_merge(self.ctx.parameters, {'GLOBAL':{'RUN_TYPE':'MD'}})
        dict_merge(self.ctx.parameters, deepcopy(disable_printing_charges_dict))
        dict_merge(self.ctx.parameters, {'FORCE_EVAL':{'PRINT':{'FORCES':{'_': 'OFF'}}}})
        # take user-provided parameters and merge them with the ones specified above. User-provided parameters are
        # treated with higher priority
        user_params = self.inputs.parameters.get_dict()
        dict_merge(self.ctx.parameters, user_params)

        # try to restart if restart object is provided
        try:
            self.ctx.restart_calc = self.inputs.parent_folder
        except:
            self.ctx.restart_calc = None

    def validate_inputs(self):
        # TODO: provide some validation steps
        pass

    def should_run_calculation(self):
        return not self.ctx.converged

    def prepare_calculation(self):
        """Prepare all the neccessary input links to run the calculation"""
        parameters = ParameterData(dict=self.ctx.parameters).store()
        self.ctx.inputs = {
            'code'                : self.inputs.code,
            'structure'           : self.ctx.structure,
            'parameters'          : parameters,
            '_options'            : self.inputs._options,
            '_guess_multiplicity' : self.inputs._guess_multiplicity,
            '_label'              : 'Cp2kDftBaseWorkChain',
            }

        # Cp2kDftBaseWorkChain will take care of modifying the input file to restart from the previous calculation
        if self.ctx.restart_calc:
            self.ctx.inputs['parent_folder'] = self.ctx.restart_calc

    def run_calculation(self):
        """Run scf calculation."""
        # Create the calculation process and launch it
        running = submit(Cp2kDftBaseWorkChain, **self.ctx.inputs)
        self.report("pk: {} | Running cp2k MD NVT".format(running.pid))
        return ToContext(cp2k=Outputs(running))

    def inspect_calculation(self):
        # TODO: for the moment we do not perform any convergence checks, one should think wheter it makes sence to
        # put them here
        self.ctx.converged = True
        self.ctx.structure = self.ctx.cp2k['output_structure']
        self.ctx.output_parameters = self.ctx.cp2k['output_parameters']
        self.ctx.restart_calc = self.ctx.cp2k['remote_folder']

    def return_results(self):
        self.out('output_structure', self.ctx.structure)
        self.out('output_parameters', self.ctx.output_parameters)
        self.out('remote_folder', self.ctx.restart_calc)
