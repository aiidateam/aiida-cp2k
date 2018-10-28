from aiida.common.extendeddicts import AttributeDict
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, Outputs
from aiida.work.workfunction import workfunction
from aiida.orm import Code
from aiida.orm.data.base import Str
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.remote import RemoteData
from aiida.orm.data.structure import StructureData
from aiida.orm.utils import CalculationFactory
from aiida.work.workchain import ToContext, if_, while_


Cp2kCalculation = CalculationFactory('cp2k')

val_elec = {
        "H"  : 1,
        "He" : 2,
        "Li" : 3,
        "Be" : 4,
        "B"  : 3,
        "C"  : 4,
        "N"  : 5,
        "O"  : 6,
        "F"  : 7,
        "Ne" : 8,
        "Na" : 9,
        "Mg" : 2,
        "Al" : 3,
        "Si" : 4,
        "P"  : 5,
        "S"  : 6,
        "Cl" : 7,
        "Ar" : 8,
        "K"  : 9,
        "Ca" : 10,
        "Sc" : 11,
        "Ti" : 12,
        "V"  : 13,
        "Cr" : 14,
        "Mn" : 15,
        "Fe" : 16,
        "Co" : 17,
        "Ni" : 18,
        "Cu" : 19,
        "Zn" : 12,
        "Zr" : 12,
        }

cp2k_default_parameters = {
    'FORCE_EVAL': {
        'METHOD': 'Quickstep',
        'DFT': {
            'CHARGE': 0,
            'BASIS_SET_FILE_NAME': 'BASIS_SET',
            'POTENTIAL_FILE_NAME': 'POTENTIAL',
            'RESTART_FILE_NAME'  : './parent_calc/aiida-RESTART.wfn',
            'QS': {
                'METHOD':'GPW',
                'EXTRAPOLATION': 'USE_GUESS'
            },
            'POISSON': {
                'PERIODIC': 'XYZ',
            },
            'MGRID': {
                'CUTOFF':     600,
                'NGRIDS':       4,
                'REL_CUTOFF':  50,
            },
            'SCF': {
                'EPS_SCF': 1.0E-4,
                'ADDED_MOS': 10,
                'SMEAR': {
                    'METHOD' : 'FERMI_DIRAC',
                    'ELECTRONIC_TEMPERATURE' : 300
                 },
                 'DIAGONALIZATION' : {
                    'ALGORITHM' : 'STANDARD',
                    'EPS_ADAPT' : 0.01
                 },
                 'MIXING' : {
                    'METHOD' : 'BROYDEN_MIXING',
                    'ALPHA' : 0.2,
                    'BETA' : 1.5,
                    'NBROYDEN' : 8
                 },
            },
            'XC': {
                'XC_FUNCTIONAL': {
                    '_': 'LDA',
                },
            },
            'KPOINTS' : {
               'SCHEME MONKHORST-PACK' : '1 1 1',
               'SYMMETRY' : 'OFF',
               'WAVEFUNCTIONS' :  'REAL',
               'FULL_GRID' :  '.TRUE.',
               'PARALLEL_GROUP_SIZE' :  0,
            },
            'PRINT': {
                'MO_CUBES': {   # this is to print the band gap
                    'STRIDE': '1 1 1',
                    'WRITE_CUBE': 'F',
                    'NLUMO': 1,
                    'NHOMO': 1,
                },
                'BAND_STRUCTURE' : {
                }
            },
        },
        'SUBSYS': {
            'KIND' : {
            }
        },
        'PRINT': { # this is to print forces (may be necessary for problems
            #detection)
            'FORCES':{
                '_': 'ON',
                }
            },
    },
    'GLOBAL':{
            "EXTENDED_FFT_LENGTHS": True, # Needed for large systems
            }
}


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


def get_atom_kinds(structure):
    kinds = []
    all_atoms = set(structure.get_ase().get_chemical_symbols())
    for a in all_atoms:
        kinds.append({
            '_': a,
            'BASIS_SET': 'DZV-GTH-PADE',
            'POTENTIAL': 'GTH-PADE',
            })
    return kinds

default_options = {
    "resources": {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 2,
    },
    "max_wallclock_seconds": 3 * 60 * 60,
    }


def add_condband(structure):
    dict = {}
    total = 0
    eatom = 0
    for i in range(len(structure.get_ase().get_chemical_symbols())):
        if not structure.get_ase().get_chemical_symbols()[i] in dict:
            dict[structure.get_ase().get_chemical_symbols()[i]] = 1
        else:
            dict[structure.get_ase().get_chemical_symbols()[i]] += 1
    for j in range(len(dict)):
        atom =list(dict.keys())[j]
        eatom = dict[atom] * val_elec[atom]
        total = total + eatom
    added_mos = total // (2*5)    #20% of conduction band
    return added_mos

def get_kpoints_path_cp2k(point_coord, path):
    Kpath = []
    for i in range(len(path)):
        p1 = (" ".join(str(x) for x in point_coord[path[i][0]]))
        p2 = (" ".join(str(x) for x in point_coord[path[i][1]]))
        Kpath.append({
        '_' : "",
         'UNITS' :  'B_VECTOR',
         'NPOINTS' : 10,
         'SPECIAL_POINT' : [p1, p2]
        })
    return Kpath

class Cp2kBandStructureWorkChain(WorkChain):
    @classmethod
    def define(cls, spec):
        super(Cp2kBandStructureWorkChain, cls).define(spec)
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input("parameters", valid_type=ParameterData,
                default=ParameterData(dict={}))
        spec.input("options", valid_type=ParameterData,
                default=ParameterData(dict=default_options))

        spec.outline(
            cls.setup,
            cls.run_seekpath,
            cls.prepare_bands_calculation,
            cls.run_bands_calculation,
            cls.return_results,
            )

        spec.output('output_structure', valid_type=StructureData, required=False)
        spec.output('output_parameters', valid_type=ParameterData)


#ctx it is a variable of WorkChain

    def setup(self):
        """Perform initial setup"""
        self.report("setup")
        self.ctx.structure = self.inputs.structure
        self.ctx.parameters = cp2k_default_parameters
        user_params = self.inputs.parameters.get_dict()

        # As it should be possible to redefine the default atom kinds by user I
        # put the default values prior to merging self.ctx.parameters with
        # user_params
        kinds = get_atom_kinds(self.inputs.structure)
        self.ctx.parameters['FORCE_EVAL']['SUBSYS']['KIND'] = kinds
        dict_merge(self.ctx.parameters, user_params)

        self.ctx.options = self.inputs.options.get_dict()

    def run_seekpath(self):
        """
        Run Seekpath to get the primitive structure
        N.B. If, after cell optimization the symmetry change,
        the primitive cell will be different!
        """

        seekpath_parameters = ParameterData(dict={})

        self.ctx.seekpath_result = seekpath_structure_analysis(self.ctx.structure, seekpath_parameters)
        self.ctx.structure = self.ctx.seekpath_result['primitive_structure']
        self.ctx.kpoints = self.ctx.seekpath_result['parameters']

    def prepare_bands_calculation(self):
        """Prepare all the neccessary input links to run the calculation"""
        self.report("prepare calculation 1")
        self.ctx.inputs = AttributeDict({
            'code': self.inputs.code,
            'structure'  : self.ctx.structure,
            '_options'    : self.ctx.options,
            })


        # Conduction band
        cond_band = add_condband(self.ctx.structure)
        self.report("number of states")
        self.report(cond_band)
        self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['ADDED_MOS'] = cond_band



        # Define path kpoints generated by seekpath
        path = []
        point_coord = {}
        path = self.ctx.kpoints.dict['path']
        point_coord = self.ctx.kpoints.dict['point_coords']

        #self.ctx.parameters = self.ctx.parameters
        kpath = get_kpoints_path_cp2k(point_coord, path)
        self.ctx.parameters['FORCE_EVAL']['DFT']['PRINT']['BAND_STRUCTURE']['KPOINT_SET'] = kpath
        #self.ctx.parameters['FORCE_EVAL']['DFT']['PRINT']['KPOINT_SET']['NPOINTS'] = 14

        # use the new parameters
        p = ParameterData(dict=self.ctx.parameters)
        p.store()
        self.ctx.inputs['parameters'] = p

    def run_bands_calculation(self):
        """Run cp2k calculation."""

        # Create the calculation process and launch it
        process = Cp2kCalculation.process()   # cp2k plugin
        future  = submit(process, **self.ctx.inputs)
        self.report("pk: {} | Running DFT calculation with"
                " cp2k".format(future.pid))
        return ToContext(calculation=Outputs(future))



    def return_results(self):
        # Extract output_parameters
        self.ctx.output_parameters = self.ctx.calculation['output_parameters']
        self.out('output_structure', self.ctx.structure)
        self.out('output_parameters', self.ctx.output_parameters)

@workfunction
def seekpath_structure_analysis(structure, parameters):
    """
    This workfunction will take a structure and pass it through SeeKpath to get the
    primitive cell and the path of high symmetry k-points through its Brillouin zone.
    Note that the returned primitive cell may differ from the original structure in
    which case the k-points are only congruent with the primitive cell.
    """
    from aiida.tools import get_kpoints_path
    return get_kpoints_path(structure, **parameters.get_dict())
