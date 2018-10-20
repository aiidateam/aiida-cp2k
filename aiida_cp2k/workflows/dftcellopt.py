from aiida.orm.code import Code
from aiida.orm.utils import CalculationFactory, DataFactory
from aiida.work.workchain import WorkChain, ToContext, Outputs, while_
from aiida.work.run import submit
from .dftutilities import dict_merge, default_options_dict, disable_printing_charges_dict

# data objects
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')

# workchains
from aiida_cp2k.workflows import Cp2kDftBaseWorkChain

cp2k_motion ={
    'MOTION': {
        'CELL_OPT': {
            'TYPE': 'DIRECT_CELL_OPT',                 #default: DIRECT_CELL_OPT
            'KEEP_ANGLES' : True,                      #default: structure
            'KEEP_SYMMETRY': False,                    #default: False (works only if symm is specified in the &CELL)
            'OPTIMIZER': 'BFGS',                       #default: BFGS
            'MAX_ITER': 100,                           #default: 200
            'EXTERNAL_PRESSURE': '[bar] 0.0',          #default: [bar] 100 0 0 0 100 0 0 0 100
            'PRESSURE_TOLERANCE': '[bar] 100',         #default: [bar] 100
            'MAX_DR':    '[bohr] 0.1',                 #default: [bohr] 0.0030
            'RMS_DR':    '[bohr] 0.1',                 #default: [bohr] 0.0015
            'MAX_FORCE': '[bohr^-1*hartree] 0.002',    #default: [bohr^-1*hartree] 0.00045
            'RMS_FORCE': '[bohr^-1*hartree] 0.001',    #default: [bohr^-1*hartree] 0.00030
            'BFGS' : {
                'TRUST_RADIUS': '[angstrom] 0.25',     #default: [angstrom] 0.25
            },
        },
        'PRINT': {
            'TRAJECTORY': {
                'FORMAT': 'DCD_ALIGNED_CELL',
                'EACH': {
                    'CELL_OPT': 1,
                },
            },
            'RESTART':{
                'BACKUP_COPIES': 0,
                'EACH': {
                    'CELL_OPT': 1,
                },
            },
            'RESTART_HISTORY':{
                'EACH': {
                    'CELL_OPT': 100,
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

class Cp2kCellOptWorkChain(WorkChain):
    """Workchain to run DFT-based CELL_OPT calculation which CP2K."""
    @classmethod
    def define(cls, spec):
        super(Cp2kCellOptWorkChain, cls).define(spec)

        # specify the inputs of the workchain
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input("parameters", valid_type=ParameterData, default=ParameterData(dict={}))
        spec.input("options", valid_type=ParameterData, default=ParameterData(dict=default_options_dict))
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
        self.ctx.parameters = cp2k_motion

        # add things to the input parameters dictionary
        dict_merge(self.ctx.parameters, {'GLOBAL':{'RUN_TYPE':'CELL_OPT'}})
        dict_merge(self.ctx.parameters, disable_printing_charges_dict)
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
        p = ParameterData(dict=self.ctx.parameters)
        p.store()
        self.ctx.inputs = {
            'code'                : self.inputs.code,
            'structure'           : self.ctx.structure,
            'options'             : self.inputs.options,
            'parameters'          : p,
            '_guess_multiplicity' : self.inputs._guess_multiplicity,
            }

        # Cp2kDftBaseWorkChain will take care of modifying the input file to restart from the previous calculation
        if self.ctx.restart_calc:
            self.ctx.inputs['parent_folder'] = self.ctx.restart_calc

    def run_calculation(self):
        """Run scf calculation."""
        # Create the calculation process and launch it
        running = submit(Cp2kDftBaseWorkChain, **self.ctx.inputs)
        self.report("pk: {} | Running cp2k CELL_OPT")
        return ToContext(cp2k=Outputs(running))

    def inspect_calculation(self):
        # TODO: for the moment we do not perform any convergence checks, one should think wheter it is appropriate to
        # put them here
        self.ctx.converged = True
        self.ctx.structure = self.ctx.cp2k['output_structure'] #from DftBase
        self.ctx.output_parameters = self.ctx.cp2k['output_parameters'] #from DftBase
        self.ctx.restart_calc = self.ctx.cp2k['remote_folder']

    def return_results(self):
        self.out('output_structure', self.ctx.structure)
        self.out('output_parameters', self.ctx.output_parameters)
        self.out('remote_folder', self.ctx.restart_calc)
