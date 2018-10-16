from aiida.orm.code import Code
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.structure import StructureData
from aiida.work.workchain import WorkChain
from aiida.work.run import run

from cp2k import Cp2kDftBaseWorkChain



class Cp2kGeoOptWorkChain(Cp2kDftBaseWorkChain):
    """
    Workchain to run SCF calculation wich CP2K
    """
    @classmethod
    def define(cls, spec):
        super(Cp2kScfWorkChain, cls).define(spec)

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
            '_options'   : options,
            '_label'     : "SCFwithCP2k",
        }

        # Create the calculation process and launch it
        future  = submit(Cp2kCalculation, **inputs)
        self.report("pk: {} | Running cp2k to compute the charge-density")
        return ToContext(cp2k=Outputs(future))

    def inspect_calculation(self):
        pass

    def return_results(self):
        pass
