# -*- coding: utf-8 -*-
"""Multistage workchain"""
from __future__ import absolute_import
import ruamel.yaml as yaml #does not convert OFF to False
import os
from copy import deepcopy

from aiida.common import AttributeDict
from aiida.engine import append_, while_, WorkChain, ToContext
from aiida.engine import workfunction as wf
from aiida.orm import Dict, Int, Float, SinglefileData, Str, RemoteData, StructureData
from aiida.plugins import CalculationFactory

from aiida_cp2k.workchains import Cp2kBaseWorkChain

Cp2kCalculation = CalculationFactory('cp2k')  # pylint: disable=invalid-name

hartree2ev = 27.2114

def merge_dict(dct, merge_dct):
    """ Taken from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
    Recursive dict merge. Inspired by :meth:``dict.update()``, instead of
    updating only top-level keys, merge_dict recurses down into dicts nested
    to an arbitrary depth, updating keys. The ``merge_dct`` is merged into
    ``dct``.
    :param dct: dict onto which the merge is executed
    :param merge_dct: dct merged into dct (overwrites dct data if in both)
    :return: None
    """
    import collections
    for k, v in merge_dct.items(): # it was .iteritems() in python2
        if (k in dct and isinstance(dct[k], dict)
                and isinstance(merge_dct[k], collections.Mapping)):
            merge_dict(dct[k], merge_dct[k])
        else:
            dct[k] = merge_dct[k]

@wf
def merge_Dict(p1, p2):
    """ Overwrite the second Dict into the first Dict """
    p1_dict = p1.get_dict()
    p2_dict = p2.get_dict()
    merge_dict(p1_dict, p2_dict)
    return Dict(dict=p1_dict).store()

def get_kinds_section(structure, protocol_settings):
    """ Write the &KIND sections given the structure and the settings_dict"""
    kinds = []
    all_atoms = set(structure.get_ase().get_chemical_symbols())
    for a in all_atoms:
        kinds.append({
            '_': a,
            'BASIS_SET': protocol_settings['basis_set'][a],
            'POTENTIAL': protocol_settings['pseudopotential'][a],
            'MAGNETIZATION': protocol_settings['initial_magnetization'][a],
            })
    return { 'FORCE_EVAL': { 'SUBSYS': { 'KIND': kinds }}}

def get_input_multiplicity(structure, protocol_settings):
    """ Compute the total multiplicity of the structure,
    by counting the atomic magnetizations.
    """
    multiplicity = 1
    all_atoms = structure.get_ase().get_chemical_symbols()
    for key, value in protocol_settings['initial_magnetization'].items():
        multiplicity += all_atoms.count(key) * value
    multiplicity = int(round(multiplicity))
    multiplicity_dict = {'FORCE_EVAL': {'DFT': {'MULTIPLICITY' :multiplicity}}}
    if multiplicity != 1:
        multiplicity_dict['FORCE_EVAL']['DFT']['UKS'] = True
    return multiplicity_dict

def ot_has_small_bandgap(cp2k_input, cp2k_output):
    """ Returns True if the calculation used OT and had a smaller bandgap then
    the guess needed for the OT.
    NOTE: It has been observed also negative bandgap with OT in CP2K!
    """
    list_true = [True, 'T', 't', '.TRUE.', 'True', 'true'] #add more?
    try:
      ot_settings = cp2k_input['FORCE_EVAL']['DFT']['SCF']['OT']
      if ('_' not in ot_settings.keys()) or (ot_settings['_'] in list_true):
          using_ot = True
      else:
          using_ot = False
    except KeyError:
        using_ot = False
    min_bandgap_ev = min(cp2k_output["bandgap_spin1_au"],cp2k_output["bandgap_spin2_au"])*hartree2ev
    is_bandgap_small = (min_bandgap_ev < 0.1)
    return (using_ot and is_bandgap_small)

@wf
def multiply_unit_cell(struct, threshold):
    """Returns the multiplication factors (tuple of 3 int) for the cell vectors
    to respect, in every direction: min(perpendicular_width) > threshold
    """
    from math import cos, sin, sqrt, pi, fabs, ceil
    import numpy as np

    # Parsing structure's cell
    def angle(v1,v2):
        return np.arccos(np.dot(v1,v2) / (np.linalg.norm(v1)*np.linalg.norm(v2)))

    a = np.linalg.norm(struct.cell[0])
    b = np.linalg.norm(struct.cell[1])
    c = np.linalg.norm(struct.cell[2])

    alpha = angle(struct.cell[1], struct.cell[2])
    beta = angle(struct.cell[0], struct.cell[2])
    gamma = angle(struct.cell[0], struct.cell[1])

    # Computing triangular cell matrix
    v = np.sqrt(1 - cos(alpha)**2 - cos(beta)**2 - cos(gamma)**2 +
             2 * cos(alpha) * cos(beta) * cos(gamma))
    cell = np.zeros((3, 3))
    cell[0, :] = [a, 0, 0]
    cell[1, :] = [b * cos(gamma), b * sin(gamma), 0]
    cell[2, :] = [
        c * cos(beta),
        c * (cos(alpha) - cos(beta) * cos(gamma)) / (sin(gamma)),
        c * v / sin(gamma)
    ]
    cell = np.array(cell)

    # Computing perpendicular widths, as implemented in Raspa
    # for the check (simplified for triangular cell matrix)
    axc1 = cell[0,0] * cell[2,2]
    axc2 = - cell[0,0] * cell[2,1]
    bxc1 = cell[1,1] * cell[2,2]
    bxc2 = - cell[1,0] * cell[2,2]
    bxc3 = cell[1,0] * cell[2,1] - cell[1,1] * cell[2,0]
    det = fabs(cell[0,0] * cell[1,1] * cell[2,2])
    perpwidth = np.zeros(3)
    perpwidth[0] = det / sqrt(bxc1**2 + bxc2**2 + bxc3**2)
    perpwidth[1] = det / sqrt(axc1**2 + axc2**2)
    perpwidth[2] = cell[2,2]

    #prevent from crashing if threshold.value is zero
    if threshold.value==0:
        thr=0.1
    else:
        thr=threshold.value

    multiply = tuple(int(ceil(thr / perpwidth[i])) for i in range(3))

    return  StructureData(ase=struct.get_ase().repeat(multiply)).store()

@wf
def extract_results(**kwargs):
    """ Extracts restults form the output_parameters of the single calculations
    (i.e., scf-converged stages) into a single Dict output. kwargs contains all
    the output_parameters for the stages and the extra initial change of settings
    """
    output_dict = {}
    stages_arg = {}
    nstages=0
    for key, value in kwargs.items():
        if value.label != 'from_discarded_settings':
            stages_arg[value.label] = key
            nstages+=1
    output_dict['nstages'] = nstages
    output_dict['last_stage_tag'] = 'stage_{}'.format(nstages-1)
    output_dict['nruns_stage0'] = len(kwargs)
    output_dict['stage_opt_converged'] = []
    output_dict['stage_nsteps'] = []
    output_dict['step_info'] = {}
    step_info_list = ['step','energy_au','dispersion_energy_au','pressure_bar',
                      'cell_vol_angs3','cell_a_angs','cell_b_angs','cell_c_angs',
                      'cell_alp_deg','cell_bet_deg','cell_gam_deg',
                      'max_step_au','rms_step_au','max_grad_au','rms_grad_au','scf_converged']
    for step_info in step_info_list:
        output_dict['step_info'][step_info]= []
    for istage in range(nstages): # avoid the stage0 with failing settings
        key = stages_arg['stage_{}'.format(istage)]
        kwarg = kwargs[key].get_dict()
        output_dict['stage_opt_converged'].append(kwarg['motion_opt_converged'])
        nsteps = kwarg['motion_step_info']['step'][-1]
        output_dict['stage_nsteps'].append(nsteps)
        for istep,step in enumerate(kwarg['motion_step_info']['step']):
            # Exclude redoundant zeroth calculations but remember that LBFGS starts from 1!
            if not (istage>0 and step==0):
                for step_info in step_info_list:
                    output_dict['step_info'][step_info].append(kwarg['motion_step_info'][step_info][istep])

    # Outputs from the last stage only
    output_dict['dft_type'] = kwargs[key].get_dict()['dft_type']
    output_dict['bandgap_spin1_au'] = kwargs[key].get_dict()['bandgap_spin1_au']
    output_dict['bandgap_spin2_au'] = kwargs[key].get_dict()['bandgap_spin2_au']

    return Dict(dict=output_dict).store()

class Cp2kMultistageWorkChain(WorkChain):
    """Workchain to submit GEO_OPT/CELL_OPT/MD workchains with iterative fashion

    NOTE:
    1) There are different CP2K's input parameters that are updated in parallel:
    - AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'base')) is the initial one
      that contains the custom setting from the run.
    - self.ctx.base_inp is a Dict that is copied from the previous one and updated.
      It also contains metadata (e.g., labels) and can contain extra inputs for the base
    - self.ctx.parameters is a dict that contains only cp2k parameters.
      Just before the calculation it is merged into the previous one.
    - self.ctx.parameters_yaml is a dict that contains the parameter from the protocol
      and is used to update self.ctx.parameters et every change of settings/stage

    """

    _calculation_class = Cp2kCalculation

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super(Cp2kMultistageWorkChain, cls).define(spec)
        spec.expose_inputs(Cp2kBaseWorkChain, namespace='cp2k_base', exclude=['parameters'])
        spec.input('protocol_tag', valid_type=Str, default=Str('standard'), required=False,
                     help='The tag of the protocol: to be read from the multistage_{tag}.yaml')
        spec.input('protocol_yaml', valid_type=SinglefileData, required=False,
                     help='Specify a custom yaml file with the multistage settings')
        spec.input('protocol_modify', valid_type=Dict, default=Dict(dict={}), required=False,
                     help='Specify custom settings that overvrite the yaml settings')
        spec.input('starting_settings_idx', valid_type=Int, default=Int(0), required=False,
                     help='If idx>0 is chosen, the calculation jumps directly to overwrite settings_0 with settings_{idx}')
        spec.input('min_cell_size', valid_type=Float, default=Float(0.0), required=False,
                     help='To avoid the use of k-points, extend the unic cell so that min(perpendicular_width)>min_cell_size')
        spec.input('parent_calc_folder', valid_type=RemoteData, required=False,
                     help='Provide an initial parent folder that contains the wavefunction, to which restart')


        spec.outline(
            cls.setup_multistage,
            while_(cls.should_run_stage0)(
              cls.run_stage,
              cls.inspect_and_update_settings_stage0,
            ),
            cls.inspect_and_update_stage,
            while_(cls.should_run_stage)(
                cls.run_stage,
                cls.inspect_and_update_stage,
            ),
            cls.results,
        )
        spec.exit_code(901,'ERROR_MISSING_INITIAL_SETTINGS',
            'Specified starting_settings_idx that is not existing, or any in between 0 and idx is missing.')
        spec.exit_code(902,'ERROR_NO_MORE_SETTINGS',
            'Settings for Stage0 are not ok but there are no more robust settings to try')
        spec.expose_outputs(Cp2kBaseWorkChain, include=('output_structure','remote_folder'))
        spec.output('last_input_parameters', valid_type=Dict, required=True)
        spec.output('output_parameters', valid_type=Dict, required=True)


    def setup_multistage(self):

        # Store the workchain inputs in context (to be modified later). ctx.base_inp = { base_settings, cp2k: { calculation_settings}}
        self.ctx.base_inp = AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base'))

        #check if an input parent_calc_folder is provided
        try:
            self.ctx.parent_calc_folder = self.inputs.parent_calc_folder
        except:
            self.ctx.parent_calc_folder = None

        # Read yaml file chosen with the tag and overwrite with custom modifications
        dir = os.path.dirname(os.path.abspath(__file__))
        yamlfullpath = '{}/multistage_protocols/{}.yaml'.format(dir, self.inputs.protocol_tag.value)
        with open(yamlfullpath, 'r') as stream:
            self.ctx.parameters_yaml = yaml.safe_load(stream)
        merge_dict(self.ctx.parameters_yaml,self.inputs.protocol_modify.get_dict())

        # Initialize
        self.ctx.stage_idx = 0
        self.ctx.stage_tag = 'stage_{}'.format(self.ctx.stage_idx)
        self.ctx.settings_idx = 0
        self.ctx.settings_tag = 'settings_{}'.format(self.ctx.settings_idx)
        self.ctx.structure_new = None

        #Multiply the unit cell if min(perp_with) < inputs.min_cell_size
        self.ctx.base_inp['cp2k']['structure'] = multiply_unit_cell(self.ctx.base_inp['cp2k']['structure'], self.inputs.min_cell_size) #TEST if this recursive thing works

        # Generate input parameters and store them
        self.ctx.parameters = deepcopy(self.ctx.parameters_yaml['settings_0'])
        while self.inputs.starting_settings_idx != self.ctx.settings_idx:
            # overwrite untill the desired starting setting are obtained
            self.ctx.settings_idx += 1
            self.ctx.settings_tag = 'settings_{}'.format(self.ctx.settings_idx)
            if  self.ctx.settings_tag in self.ctx.parameters_yaml.keys():
                merge_dict(self.ctx.parameters,self.ctx.parameters_yaml[self.ctx.settings_tag])
            else:
                return self.exit_codes.ERROR_MISSING_INITIAL_SETTINGS
        kinds = get_kinds_section(self.ctx.base_inp['cp2k']['structure'], self.ctx.parameters_yaml)
        merge_dict(self.ctx.parameters,kinds)
        multiplicity = get_input_multiplicity(self.ctx.base_inp['cp2k']['structure'], self.ctx.parameters_yaml)
        merge_dict(self.ctx.parameters,multiplicity)
        merge_dict(self.ctx.parameters,self.ctx.parameters_yaml['stage_0'])

    def should_run_stage0(self):
        """ Returns True if it is the first iteration or the settings are not ok """
        try:
            return not self.ctx.settings_ok
        except AttributeError:
            return True

    def run_stage(self):
        """Check for restart, prepare input, submit and direct output to context"""

        # Check if it is needed to restart the calculation and provide the parent folder and new structure
        if self.ctx.parent_calc_folder:
            self.ctx.base_inp['cp2k']['parent_calc_folder'] = self.ctx.parent_calc_folder
            self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS'] = 'RESTART'
            self.ctx.parameters['FORCE_EVAL']['DFT']['WFN_RESTART_FILE_NAME'] = './parent_calc/aiida-RESTART.wfn'
            if self.ctx.structure_new:
                self.ctx.base_inp['cp2k']['structure'] = self.ctx.structure_new
        else:
            self.ctx.parameters['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS'] = 'ATOMIC'

        # Overwrite the generated input with the custom cp2k/parameters and give a label to BaseWC and Cp2kCalc
        if 'parameters' in self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']:
            merge_dict(self.ctx.parameters, AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'base')['cp2k']['parameters'].get_dict()))
        self.ctx.base_inp['cp2k']['parameters'] = Dict(dict = self.ctx.parameters).store()
        self.ctx.base_inp['metadata']['label'] = 'base({}/{})'.format(self.ctx.stage_tag,self.ctx.settings_tag,)
        self.ctx.base_inp['cp2k']['metadata']['label'] = self.ctx.base_inp['cp2k']['parameters'].get_dict()['GLOBAL']['RUN_TYPE']

        running_base = self.submit(Cp2kBaseWorkChain, **self.ctx.base_inp)
        self.report("submitted Cp2kBaseWorkChain<{}> for {}/{}".format(running_base.pk,self.ctx.stage_tag,self.ctx.settings_tag))
        return ToContext(stages=append_(running_base))


    def inspect_and_update_settings_stage0(self):
        """ Inspect the stage0/settings_{idx} calculation and check if it is
        needed to update the settings and resubmint the calculation
        """
        self.ctx.settings_ok = True

        # Settings/structure bad: something very bad happened and the calculation is not doing even the scf cycles
        # if base.is_ko
        #

        # Settings bad: base did not converge
        if not self.ctx.stages[-1].outputs.output_parameters["motion_step_info"]["scf_converged"][-1]:
            self.report("BAD SETTINGS: the SCF did not converge")
            self.ctx.settings_ok = False
            self.ctx.settings_idx += 1

        # Settings bad: OT and small (or negative!) bandgap
        cp2k_inp = self.ctx.parameters
        cp2k_out = self.ctx.stages[-1].outputs.output_parameters
        self.report("Bandgaps spin1/spin2: {:.3f} and {:.3f} ev".format(
            cp2k_out["bandgap_spin1_au"]*hartree2ev,cp2k_out["bandgap_spin2_au"]*hartree2ev))
        if ot_has_small_bandgap(cp2k_inp,cp2k_out):
            self.report("BAD SETTINGS: band gap is < 0.1eV")
            self.ctx.settings_ok = False
            self.ctx.settings_idx += 1

        # Update the settings tag, check if it is available and overwrite
        if not self.ctx.settings_ok:
            self.ctx.stages[-1].outputs.output_parameters.label = 'from_discarded_settings'
            self.ctx.settings_tag = 'settings_{}'.format(self.ctx.settings_idx)
            if self.ctx.settings_tag in self.ctx.parameters_yaml.keys():
                merge_dict(self.ctx.parameters,self.ctx.parameters_yaml[self.ctx.settings_tag])
            else:
                return self.exit_codes.ERROR_NO_MORE_SETTINGS

    def inspect_and_update_stage(self):
        """ Update geometry, parent folder and the new &MOTION settings"""
        last_stage = self.ctx.stages[-1]
        self.ctx.structure_new = last_stage.outputs.output_structure
        self.ctx.parent_calc_folder = last_stage.outputs.remote_folder
        last_stage.outputs.output_parameters.label = self.ctx.stage_tag

        self.ctx.stage_idx += 1
        self.ctx.stage_tag = 'stage_{}'.format(self.ctx.stage_idx)

        if self.ctx.stage_tag in self.ctx.parameters_yaml.keys():
            self.ctx.next_stage_exists = True
            merge_dict(self.ctx.parameters,self.ctx.parameters_yaml[self.ctx.stage_tag])
        else:
            self.ctx.next_stage_exists = False
            self.report("All stages computed, finishing...")

    def should_run_stage(self):
        """ Return True if it exists a new stage to compute """
        return self.ctx.next_stage_exists

    def results(self):
        """ Gather final outputs of the workchain """

        all_output_parameters = {}
        for i,stage in enumerate(self.ctx.stages):
            all_output_parameters['arg{}'.format(i)] = stage.outputs.output_parameters

        self.out('output_parameters', extract_results(**all_output_parameters))
        self.out('last_input_parameters',self.ctx.base_inp['cp2k']['parameters'])
        self.out_many(self.exposed_outputs(self.ctx.stages[-1], Cp2kBaseWorkChain)) #(output_structure and remote_folder)
        self.report("Outputs: Dict<{}> and StructureData<{}>".format(self.outputs['output_parameters'].pk,self.outputs['output_structure'].pk))

        return
