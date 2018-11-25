from aiida.orm.code import Code
from aiida.orm.data.base import Float
from aiida.orm.utils import CalculationFactory, DataFactory
from aiida.work import workfunction as wf
from aiida.work.workchain import WorkChain, ToContext, Outputs, while_
from aiida.work.run import submit
from .dftutilities import default_options, empty_pd
from copy import deepcopy

# data objects
StructureData = DataFactory('structure')
ParameterData = DataFactory('parameter')
RemoteData = DataFactory('remote')

# workchains
from aiida_cp2k.workflows import Cp2kDftBaseWorkChain
from aiida_cp2k.workflows import Cp2kGeoOptWorkChain
from aiida_cp2k.workflows import Cp2kCellOptWorkChain
from aiida_cp2k.workflows import Cp2kMdWorkChain

@wf
def multiply_unit_cell (struct, threshold):
    """Resurns the multiplication factors (tuple of 3 int) for the cell vectors
    that are needed to respect: min(perpendicular_width) > threshold."""
    from math import cos, sin, sqrt, pi
    import numpy as np
    # angle between vectors
    def angle(v1,v2):
        return np.arccos(np.dot(v1,v2) / (np.linalg.norm(v1)*np.linalg.norm(v2)))

    threshold = threshold.value / 2.0

    a = np.linalg.norm(struct.cell[0])
    b = np.linalg.norm(struct.cell[1])
    c = np.linalg.norm(struct.cell[2])

    alpha = angle(struct.cell[1], struct.cell[2])
    beta = angle(struct.cell[0], struct.cell[2])
    gamma = angle(struct.cell[0], struct.cell[1])

    # first step is computing cell parameters according to  https://en.wikipedia.org/wiki/Fractional_coordinates
    # Note: this is the algorithm implemented in Raspa (framework.c/UnitCellBox). There also is a simpler one but it is less robust.
    v = sqrt(1-cos(alpha)**2-cos(beta)**2-cos(gamma)**2+2*cos(alpha)*cos(beta)*cos(gamma))
    cell=np.zeros((3,3))
    cell[0,:] = [a, 0, 0]
    cell[1,:] = [b*cos(gamma), b*sin(gamma),0]
    cell[2,:] = [c*cos(beta), c*(cos(alpha)-cos(beta)*cos(gamma))/(sin(gamma)),c*v/sin(gamma)]
    cell=np.array(cell)

    # diagonalizing the cell matrix: note that the diagonal elements are the perpendicolar widths because ay=az=bz=0
    diag = np.diag(cell)
    repeat = tuple(int(i) for i in np.ceil(threshold/diag*2.))
    return StructureData(ase=struct.get_ase().repeat(repeat)).store()

class Cp2kRobustGeoOptWorkChain(WorkChain):
    """Robust workflow that tries to optimize geometry combining molecular dynamics, cell optimization, and standard
    geometry optimization. It is under development!"""
    @classmethod
    def define(cls, spec):
        super(Cp2kRobustGeoOptWorkChain, cls).define(spec)

        # specify the inputs of the workchain
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input('parameters', valid_type=ParameterData, default=empty_pd)
        spec.input("min_cell_size", valid_type=Float, default=Float(10.0).store())
        spec.input('_options', valid_type=dict, default=deepcopy(default_options))
        spec.input('parent_folder', valid_type=RemoteData, default=None, required=False)

        # specify the chain of calculations
        spec.outline(
            cls.setup,
            cls.validate_inputs,
            cls.run_energy,
            cls.parse_calculation,
            cls.run_cellopt,
            cls.parse_calculation,
            cls.run_mdnvt,
            cls.parse_calculation,
            cls.run_geoopt,
            cls.parse_calculation,
            cls.run_cellopt,
            cls.parse_calculation,
            cls.return_results,
        )

        # specify the outputs of the workchain
        spec.output('output_structure', valid_type=StructureData)
        spec.output('output_parameters', valid_type=ParameterData)
        spec.output('remote_folder', valid_type=RemoteData)

    def setup(self):
        """Setup initial values of all the parameters."""
        self.ctx.structure = multiply_unit_cell(self.inputs.structure, self.inputs.min_cell_size)
        try:
            self.ctx.restart_calc = self.inputs.parent_folder
        except:
            self.ctx.restart_calc = None

    def validate_inputs(self):
        #TODO: implement some validations, if necessary
        pass

    def parse_calculation(self):
        """Get the output structure and remember the parent folder."""
        self.ctx.structure = self.ctx.cp2k['output_structure']
        self.ctx.restart_calc = self.ctx.cp2k['remote_folder']
        self.ctx.output_parameters = self.ctx.cp2k['output_parameters'] #from DftBase

    def run_energy(self):
        """Run ENERGY calculation."""
        inputs = {
            'code'                : self.inputs.code,
            'structure'           : self.ctx.structure,
            'parameters'          : self.inputs.parameters,
            '_options'            : self.inputs._options,
            '_label'              : 'Cp2kDftBaseWorkChain',
            }

        # restart wavefunctions if they are provided
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc

        # run the calculation
        running  = submit(Cp2kDftBaseWorkChain, **inputs)
        self.report("pk: {} | Running cp2k ENERGY".format(running.pid))
        return ToContext(cp2k=Outputs(running))

    def run_mdnvt(self):
        """Run MD NVT calculation."""
        inputs = {
            'code'                : self.inputs.code,
            'structure'           : self.ctx.structure,
            'parameters'          : self.inputs.parameters,
            '_options'            : self.inputs._options,
            '_label'              : 'Cp2kMdWorkChain',
            }

        # restart wavefunctions if they are provided
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc

        # run the calculation
        running  = submit(Cp2kMdWorkChain, **inputs)
        self.report("pk: {} | Running cp2k MD NVT".format(running.pid))
        return ToContext(cp2k=Outputs(running))

    def run_geoopt(self):
        """Run GEO_OPT calculation."""
        inputs = {
            'code'                : self.inputs.code,
            'structure'           : self.ctx.structure,
            'parameters'          : self.inputs.parameters,
            '_options'            : self.inputs._options,
            '_label'              : 'Cp2kGeoOptWorkChain',
            }

        # restart wavefunctions if they are provided
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc

        # run the calculation
        running  = submit(Cp2kGeoOptWorkChain, **inputs)
        self.report("pk: {} | Running cp2k GEO_OPT".format(running.pid))
        return ToContext(cp2k=Outputs(running))

    def run_cellopt(self):
        """Run CELL_OPT calculation."""
        inputs = {
            'code'                : self.inputs.code,
            'structure'           : self.ctx.structure,
            'parameters'          : self.inputs.parameters,
            '_options'            : self.inputs._options,
            '_label'              : 'Cp2kCellOptWorkChain',
            }

        # restart wavefunctions if they are provided
        if self.ctx.restart_calc:
            inputs['parent_folder'] = self.ctx.restart_calc

        # run the calculation
        running  = submit(Cp2kCellOptWorkChain, **inputs)
        self.report("pk: {} | Running cp2k CELL_OPT".format(running.pid))
        return ToContext(cp2k=Outputs(running))

    def return_results(self):
        """Return results of the workchain"""
        self.out('output_structure', self.ctx.structure)
        self.out('output_parameters', self.ctx.output_parameters)
        self.out('remote_folder', self.ctx.restart_calc)
