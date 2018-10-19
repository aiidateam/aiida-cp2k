from aiida.orm.code import Code
from aiida.orm.utils import CalculationFactory, DataFactory
from aiida.work.workchain import WorkChain, ToContext, Outputs, while_
from aiida.work.run import submit
from .dftutilities import default_options_dict
# data objects
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')

from aiida_cp2k.workflows import Cp2kDftBaseWorkChain
from aiida_cp2k.workflows import Cp2kGeoOptWorkChain
from aiida_cp2k.workflows import Cp2kCellOptWorkChain
from aiida_cp2k.workflows import Cp2kMDNVTWorkChain

class Cp2k4StepsWorkChain(WorkChain):
    """
    Workchain to run SCF calculation wich CP2K
    """
    @classmethod
    def define(cls, spec):
        super(Cp2k4StepsWorkChain, cls).define(spec)
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input('parameters', valid_type=ParameterData, default=ParameterData(dict={}))
        spec.input('options', valid_type=ParameterData, default=ParameterData(dict=default_options_dict))
        spec.input('parent_folder', valid_type=RemoteData, default=None, required=False)
        spec.input('_guess_multiplicity', valid_type=bool, default=False)

        spec.outline(
            cls.setup,
            cls.validate_inputs,
            cls.run_energy,
            cls.parse_calculation,
            cls.run_mdnvt,
            cls.parse_calculation,
            cls.run_geoopt,
            cls.parse_calculation,
            cls.run_cellopt,
            cls.parse_calculation,
            cls.return_results,
        )

    def setup(self):
        self.ctx.structure = self.inputs.structure
        try:
            self.ctx.restart_calc = self.inputs.parent_folder
        except:
            self.ctx.restart_calc = None

    def validate_inputs(self):
        pass

    def parse_calculation(self):
        """ Get the output structure and remember the parent folder """
        self.ctx.structure = self.ctx.cp2k['output_structure']
        self.ctx.restart_calc = self.ctx.cp2k['remote_folder']

    def run_energy(self):
        """Run ENERGY calculation."""
        inputs = {
            'code'      : self.inputs.code,
            'structure' : self.ctx.structure,
            'parameters': self.inputs.parameters,
            'options'   : self.inputs.options,
            '_guess_multiplicity': self.inputs._guess_multiplicity,
            }
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc
        running  = submit(Cp2kDftBaseWorkChain, **inputs)
        self.report("pk: {} | Running cp2k ENERGY")
        return ToContext(cp2k=Outputs(running))

    def run_mdnvt(self):
        """Run MD NVT calculation."""
        inputs = {
            'code'      : self.inputs.code,
            'structure' : self.ctx.structure,
            'parameters': self.inputs.parameters,
            'options'   : self.inputs.options,
            '_guess_multiplicity': self.inputs._guess_multiplicity,
            }
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc
        future  = submit(Cp2kMDNVTWorkChain, **inputs)
        self.report("pk: {} | Running cp2k MD NVT ")
        return ToContext(cp2k=Outputs(future))

    def run_geoopt(self):
        """Run GEO_OPT calculation."""
        inputs = {
            'code'      : self.inputs.code,
            'structure' : self.ctx.structure,
            'parameters': self.inputs.parameters,
            'options'   : self.inputs.options,
            '_guess_multiplicity': self.inputs._guess_multiplicity,
            }
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc
        future  = submit(Cp2kGeoOptWorkChain, **inputs)
        self.report("pk: {} | Running cp2k GEO_OPT")
        return ToContext(cp2k=Outputs(future))

    def run_cellopt(self):
        """Run CELL_OPT calculation."""
        inputs = {
            'code'      : self.inputs.code,
            'structure' : self.ctx.structure,
            'parameters': self.inputs.parameters,
            'options'   : self.inputs.options,
            '_guess_multiplicity': self.inputs._guess_multiplicity,
            }
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc
        future  = submit(Cp2kCellOptWorkChain, **inputs)
        self.report("pk: {} | Running cp2k CELL_OPT")
        return ToContext(cp2k=Outputs(future))

    def return_results(self):
        pass
