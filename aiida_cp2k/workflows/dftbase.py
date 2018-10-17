from aiida.common.extendeddicts import AttributeDict
from aiida.work.run import submit
from aiida.work.workchain import WorkChain, Outputs
from aiida.orm import Code
from aiida.orm.data.base import Str
from aiida.orm.data.parameter import ParameterData
from aiida.orm.data.remote import RemoteData
from aiida.orm.data.structure import StructureData
from aiida.orm.utils import CalculationFactory
from aiida.work.workchain import ToContext, if_, while_

from .atomic_convention1 import spin, basis_set, pseudo

Cp2kCalculation = CalculationFactory('cp2k')

cp2k_default_parameters = {
    'FORCE_EVAL': {
        'METHOD': 'Quickstep',
        'DFT': {
            'CHARGE': 0,
            'BASIS_SET_FILE_NAME': [
               'BASIS_MOLOPT',
               'BASIS_MOLOPT_UCL',
            ],
            'POTENTIAL_FILE_NAME': 'GTH_POTENTIALS',
            'RESTART_FILE_NAME'  : './parent_calc/aiida-RESTART.wfn',
            'QS': {
                'METHOD':'GPW',
            },
            'POISSON': {
                'PERIODIC': 'XYZ',
            },
            'MGRID': {
                'CUTOFF':     600,
                'NGRIDS':       4,
                'REL_CUTOFF':  50,
            },
            'SCF':{
                'SCF_GUESS': 'ATOMIC',
                'EPS_SCF': 1.0e-6,
                'MAX_SCF': 50,
                'MAX_ITER_LUMO': 10000, #needed for the bandgap
                'OT':{
                    'MINIMIZER': 'DIIS',
                    'PRECONDITIONER': 'FULL_ALL',
                    },
                'OUTER_SCF':{
                    'EPS_SCF': 1.0e-6,
                    'MAX_SCF': 10,
                    },
            },
            'XC': {
                'XC_FUNCTIONAL': {
                    '_': 'PBE',
                },
                'VDW_POTENTIAL': {
                   'POTENTIAL_TYPE': 'PAIR_POTENTIAL',
                   'PAIR_POTENTIAL': {
                      'PARAMETER_FILE_NAME': 'dftd3.dat',
                      'TYPE': 'DFTD3(BJ)',
                      'REFERENCE_FUNCTIONAL': 'PBE',
                   },
                },
            },
            'PRINT': {
                'MO_CUBES': {
                    '_': 'ON', # this is to print the band gap
                    'WRITE_CUBE': 'F',
                    'STRIDE': '1 1 1',
                    'NLUMO': 1,
                    'NHOMO': 1,
                },
            },
        },
        'SUBSYS': {
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


def last_scf_loop(fpath):
    """
    Simple function that extracts all the output starting from the last SCF
    loop.
    """
    with open(fpath) as f:
        content = f.readlines()
    # find the last scf loop in the cp2k output file
    for n, line in enumerate(reversed(content)):
        if "SCF WAVEFUNCTION OPTIMIZATION" in line:
            break
    return content[-n-1:]

def scf_converged(fpath):
    """Take last SCF cycle and check whether it converged or not"""
    content = last_scf_loop(fpath)
    for line in content:
        if "SCF run converged in" in line:
            return True
    return False

def scf_was_diverging(fpath):
    """A function that detects diverging SCF: always diverging!"""
    return True
#    content = last_scf_loop(fpath)
#    for line in content:
#        if "Minimizer" in line and "CG" in line:
#            grep_string = "OT CG"
#            break
#
#        elif "Minimizer" in line and "DIIS" in line:
#            grep_string = "OT DIIS"
#            break
#
#    n_change = 7
#    difference = []
#    n_positive = 0
#    for line in content:
#        if grep_string in line:
#            difference.append(line.split()[n_change])
#    for number in difference[-12:]:
#        if float(number) > 0:
#            n_positive +=1
#
#    if n_positive>5:
#        return True
#    return False


def get_multiplicity(structure):
    multiplicity = 1
    all_atoms = structure.get_ase().get_chemical_symbols()
    for key, value in spin.iteritems():
        multiplicity += all_atoms.count(key) * value * 2.0
    return int(round(multiplicity))

def get_atom_kinds(structure):
    kinds = []
    all_atoms = set(structure.get_ase().get_chemical_symbols())
    for a in all_atoms:
        kinds.append({
            '_': a,
            'BASIS_SET': basis_set[a],
            'POTENTIAL': pseudo[a],
            'MAGNETIZATION': spin[a] * 2.0,
            })
    return kinds

default_options = {
    "resources": {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 2,
    },
    "max_wallclock_seconds": 3 * 60 * 60,
    }

class Cp2kDftBaseWorkChain(WorkChain):
    """A base workchain to be used for DFT calculations with CP2K"""
    @classmethod
    def define(cls, spec):
        super(Cp2kDftBaseWorkChain, cls).define(spec)
        spec.input('code', valid_type=Code)
        spec.input('structure', valid_type=StructureData)
        spec.input("parameters", valid_type=ParameterData,
                default=ParameterData(dict={}))
        spec.input("options", valid_type=ParameterData,
                default=ParameterData(dict=default_options))
        spec.input('parent_folder', valid_type=RemoteData,
                default=None, required=False)
        spec.input('_guess_multiplisity', valid_type=bool,
                default=False)

        spec.outline(
            cls.setup,
            while_(cls.should_run_calculation)(
                cls.prepare_calculation,
                cls.run_calculation,
                cls.inspect_calculation,
            ),
            cls.return_results,
        )
        spec.output('output_structure', valid_type=StructureData, required=False)
        spec.output('output_parameters', valid_type=ParameterData)
        spec.output('remote_folder', valid_type=RemoteData)

    def setup(self):
        """Perform initial setup"""
        self.ctx.done = False
        self.ctx.nruns = 0
        self.ctx.structure = self.inputs.structure
        try:
            self.ctx.restart_calc = self.inputs.parent_folder
        except:
            self.ctx.restart_calc = None
        self.ctx.parameters = cp2k_default_parameters
        user_params = self.inputs.parameters.get_dict()

        # As it should be possible to redefine the default atom kinds by user I
        # put the default values prior to merging self.ctx.parameters with
        # user_params
        kinds = get_atom_kinds(self.inputs.structure)
        self.ctx.parameters['FORCE_EVAL']['SUBSYS']['KIND'] = kinds

        dict_merge(self.ctx.parameters, user_params)

        self.ctx.options = self.inputs.options.get_dict()

        # Trying to guess the multiplicity of the system
        if self.inputs._guess_multiplisity:
            self.report("Guessing multiplicity")
            multiplicity = get_multiplicity(self.inputs.structure)
            self.ctx.parameters['FORCE_EVAL']['DFT']['MULTIPLICITY'] = multiplicity
            self.report("Obtained multiplicity: {}".format(multiplicity))
            if multiplicity != 1:
                self.ctx.parameters['FORCE_EVAL']['DFT']['LSD'] = True
                self.report("Switching to LSD calculation")
        # Otherwise take the default

    def should_run_calculation(self):
        return not self.ctx.done

    def prepare_calculation(self):
        """Prepare all the neccessary input links to run the calculation"""
        self.ctx.inputs = AttributeDict({
            'code': self.inputs.code,
            'structure'  : self.ctx.structure,
            '_options'    : self.ctx.options,
            })

        # restart from the previous calculation only if the necessary data are
        # provided
        if self.ctx.restart_calc:
            self.ctx.inputs['parent_folder'] = self.ctx.restart_calc
            self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS'] = 'RESTART'
        else:
            self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS'] = 'ATOMIC'

        # use the new parameters
        p = ParameterData(dict=self.ctx.parameters)
        p.store()
        self.ctx.inputs['parameters'] = p

    def run_calculation(self):
        """Run cp2k calculation."""

        # Create the calculation process and launch it
        process = Cp2kCalculation.process()
        future  = submit(process, **self.ctx.inputs)
        self.report("pk: {} | Running DFT calculation with"
                " cp2k".format(future.pid))
        self.ctx.nruns += 1
        return ToContext(calculation=Outputs(future))

    def inspect_calculation(self):
        """
        Analyse the results of CP2K calculation and decide weather there is a
        need to restart it. If yes, then decide exactly how to restart the
        calculation.
        """
        # TODO: check whether the CP2K did not stop the execution because of an
        # error that it detected. In that case the calculation will most
        # probably be in the status "PARSINGFAILED"

        # I will try to disprove those statements. I will not succeed in doing
        # so - the calculation will be considered as completed
        converged_geometry = True
        converged_scf = True
        exceeded_time = False

        # File to analyze
        outfile = self.ctx.calculation['retrieved'].get_abs_path() + '/path/aiida.out'
        self.ctx.restart_calc = self.ctx.calculation['remote_folder']
        self.ctx.output_parameters = self.ctx.calculation['output_parameters']

        #TODO: parse and analyse the bandgap

        # First (and the simplest) check is whether the runtime was exceeded
        exceeded_time = self.ctx.output_parameters.dict['exceeded_walltime']
        if exceeded_time:
            self.report("The time of the cp2k calculation has been exceeded")
        else:
            self.report("The time of the cp2k calculation has NOT been exceeded")

        # Second check is whether the last SCF did converge
        converged_scf = scf_converged(outfile)
        if not converged_scf and scf_was_diverging(outfile):
            # If, however, scf was even diverging I should go for more robust
            # minimizer.
            self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['OT']['MINIMIZER'] = 'CG'
            self.report("Going for more robust (but slow) SCF minimizer")
            # Also, to avoid being trapped in the wrong minimum I restart
            # from atomic wavefunctions.
            self.ctx.restart_calc = None
            self.report("Not going to restart from the previous wavefunctions")
            # I will disable outer_scf steps to enforce convergence
            self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['MAX_SCF'] = 2000
            self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['OUTER_SCF']['MAX_SCF'] = 0

            # TODO: I may also look for the forces here. For example a very
            # strong force may cause convergence problems, needs to be
            # implemented
            # UPDATE: from now forces are be printed by default


       # Third check:
       # TODO: check for the geometry convergence/divergence problems
       # useful for geo/cell-opt restart
       # if aiida-1.restart in retrieved (folder):
       #    self.ctx.parameters['EXT_RESTART'] = {'RESTART_FILE_NAME': './parent_calc/aiida-1.restart'}

        if converged_geometry and converged_scf and not exceeded_time:
            self.report("Calculation converged, terminating the workflow")
            self.ctx.done = True



    def return_results(self):
        self.out('output_structure', self.ctx.structure)
        self.out('output_parameters', self.ctx.output_parameters)
        self.out('remote_folder', self.ctx.restart_calc)
