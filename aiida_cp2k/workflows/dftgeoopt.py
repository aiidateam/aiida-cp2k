from aiida.orm.code import Code
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.structure import StructureData
from aiida.work.workchain import WorkChain
from aiida.work.run import run

from cp2k import Cp2kDftBaseWorkChain

#TODO:
# change GLOBAL/RUN_TYPE to GEO_OPT
# SET FORCE_EVAL/DFT/PRINT/MO_CUBES OFF

cp2k_motion={
            'GEO_OPT': {
                'TYPE': 'MINIMIZATION',
                'OPTIMIZER': 'BFGS',
                'MAX_ITER': 50,
                'MAX_DR': '[bohr] 0.0030',
                'RMS_DR': '[bohr] 0.0015',
                'MAX_FORCE': '[bohr^-1*hartree] 0.00045',
                'RMS_FORCE': '[bohr^-1*hartree] 0.00030',
                'BFGS' : {
                    'TRUST_RADIUS': '[angstrom] 0.25',
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
                    }
                }
                'RESTART_HISTORY':{
                    'EACH': {
                        'GEO_OPT': 100,
                    }
                }
                'CELL': {
                    '_': 'OFF',
                }
                'VELOCITIES': {
                    '_': 'OFF',
                },
                'FORCES': {
                    '_': 'OFF',
                },
                'STRESS': {
                    '_': 'OFF',
                },
            }
        }

class Cp2kGeoOptWorkChain(Cp2kDftBaseWorkChain):
    """
    Workchain to run SCF calculation wich CP2K
    """
    @classmethod
    def define(cls, spec):
        super(Cp2kScfWorkChain, cls).define(spec)
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input("parameters", valid_type=ParameterData,
                default=ParameterData(dict=cp2k_motion))
        spec.input("options", valid_type=ParameterData,
                default=ParameterData(dict=default_options))
        spec.input('parent_folder', valid_type=RemoteData,
                default=None, required=False)


        spec.output('output_structure', valid_type=StructureData)

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            while_(cls.should_run_calculation)(
                cls.prepare_calculation,
                cls.run_calculation,
                cls.inspect_calculation,
            ),
            cls.results,
        )

    def setup(self):
        ctx.converged = False
        multiplicity = get_multiplicity(self.inputs.structure)
        kinds = get_kinds(self.inputs.structure)

    def validate_inputs(self):
        pass

    def should_run_calculation(self):
        return converged

    def run_calculation(self): """
        Run scf calculation.
        """
        options = {
            "resources": {
                "num_machines": 4,
                "num_mpiprocs_per_machine": 12,
            },
            "max_wallclock_seconds": 3 * 60 * 60,
        }

        inputs = {
            'code'       : self.inputs.code,
            'structure'  : self.inputs.structure,
            'parameters' : self.inputs.parameters,
            'options'   : options,
            '_label'     : "SCFwithCP2k",
        }

        # Create the calculation process and launch it
        future  = submit(Cp2kDftBaseWorkChain, **inputs)
        self.report("pk: {} | Running cp2k to compute the charge-density")
        return ToContext(cp2k=Outputs(future))

    def inspect_calculation(self):
        pass

    def return_results(self):
        pass
