# -*- coding: utf-8 -*-
"""Multistage workchain"""

from __future__ import absolute_import

import os
from copy import deepcopy
import six
import ruamel.yaml as yaml  # does not convert OFF to False

from aiida.common import AttributeDict
from aiida.engine import append_, while_, WorkChain, ToContext
from aiida.engine import calcfunction
from aiida.orm import Dict, Int, Float, SinglefileData, Str, RemoteData, StructureData
from aiida.plugins import WorkflowFactory

from aiida_cp2k.utils import merge_dict
from aiida_cp2k.utils import get_kinds_section, get_input_multiplicity, ot_has_small_bandgap
from aiida_cp2k.utils import check_resize_unit_cell, resize_unit_cell
from aiida_cp2k.utils import HARTREE2EV

Cp2kBaseWorkChain = WorkflowFactory('cp2k.base')  # pylint: disable=invalid-name


@calcfunction
def extract_results(resize, **kwargs):
    """Extracts restults form the output_parameters of the single calculations (i.e., scf-converged stages)
    into a single Dict output.
    - resize (Dict) contains the unit cell resizing values
    - kwargs contains all the output_parameters for the stages and the extra initial change of settings, e.g.:
      'out_0': cp2k's output_parameters with Dict.label = 'settings_0_stage_0_discard'
      'out_1': cp2k's output_parameters with Dict.label = 'settings_1_stage_0_valid'
      'out_2': cp2k's output_parameters with Dict.label = 'settings_1_stage_0_valid'
      'out_3': cp2k's output_parameters with Dict.label = 'settings_1_stage_0_valid'
      This will be read as: output_dict = {'nstages_valid': 3, 'nsettings_discarded': 1}."""

    output_dict = {}

    # Sort the stages by key and cound the number of valid and descarded stages
    sorted_values = [key_val[1] for key_val in sorted(kwargs.items(), key=lambda k: int(k[0][4:]))]
    nstages_valid = sum(value.label.split('_')[-1] == 'valid' for value in sorted_values)
    nsettings_discarded = len(sorted_values) - nstages_valid

    # General info
    output_dict['nstages_valid'] = nstages_valid
    output_dict['nsettings_discarded'] = nsettings_discarded
    output_dict['last_tag'] = sorted_values[-1].label.split()[-1]
    output_dict['cell_resized'] = '{}x{}x{}'.format(resize['nx'], resize['ny'], resize['nz'])

    # Create stage_info dictionary
    output_dict['stage_info'] = {
        'nsteps': [],
        'opt_converged': [],
        'final_edens_rspace': [],
        'bandgap_spin1_au': [],
        'bandgap_spin2_au': [],
    }

    # Create step_info dictionary
    step_info_list = [
        'step', 'energy_au', 'dispersion_energy_au', 'pressure_bar', 'cell_vol_angs3', 'cell_a_angs', 'cell_b_angs',
        'cell_c_angs', 'cell_alp_deg', 'cell_bet_deg', 'cell_gam_deg', 'max_step_au', 'rms_step_au', 'max_grad_au',
        'rms_grad_au', 'scf_converged'
    ]
    output_dict['step_info'] = {}
    for step_info in step_info_list:
        output_dict['step_info'][step_info] = []

    # Fill stage_info and step_info with the results (skip all stage0 attempts with discarded settings)
    for i in six.moves.range(nsettings_discarded, len(kwargs)):  #
        kwarg = kwargs['out_{}'.format(i)]
        output_dict['stage_info']['nsteps'].append(kwarg['motion_step_info']['step'][-1])
        output_dict['stage_info']['opt_converged'].append(kwarg['motion_opt_converged'])
        output_dict['stage_info']['final_edens_rspace'].append(kwarg['motion_step_info']['edens_rspace'][-1])
        output_dict['stage_info']['bandgap_spin1_au'].append(kwarg['bandgap_spin1_au'])
        output_dict['stage_info']['bandgap_spin2_au'].append(kwarg['bandgap_spin1_au'])
        for istep, step in enumerate(kwarg['motion_step_info']['step']):
            # Exclude redoundant zeroth calculations but remember that LBFGS starts from 1:
            # i.e., print when it is the first entry OR not first entry but step>0
            if not (step == 0 and output_dict['step_info']['step']):
                for step_info in step_info_list:
                    output_dict['step_info'][step_info].append(kwarg['motion_step_info'][step_info][istep])

    # Outputs from the last stage only
    output_dict['natoms'] = kwarg['natoms']
    output_dict['dft_type'] = kwarg['dft_type']
    output_dict['final_bandgap_spin1_au'] = kwarg['bandgap_spin1_au']
    output_dict['final_bandgap_spin2_au'] = kwarg['bandgap_spin2_au']

    return Dict(dict=output_dict)


class Cp2kMultistageWorkChain(WorkChain):
    """Submits Cp2kBase workchains for ENERGY, GEO_OPT, CELL_OPT and MD jobs iteratively

    The protocol_yaml file contains a series of settings_x and stage_x:
    the workchains starts running the settings_0/stage_0 calculation, and, in case of a failure, changes the settings
    untill the SCF of stage_0 converges. Then it uses the same settings to run the next stages (i.e., stage_1, etc.)."""

    @classmethod
    def define(cls, spec):
        super(Cp2kMultistageWorkChain, cls).define(spec)

        # Inputs
        spec.expose_inputs(Cp2kBaseWorkChain,
                           namespace='cp2k_base',
                           exclude=['cp2k.structure', 'cp2k.parameters', 'cp2k.metadata.options.parser_name'])
        spec.input('structure', valid_type=StructureData, required=False, help='Input structure')
        spec.input('protocol_tag',
                   valid_type=Str,
                   default=Str('standard'),
                   required=False,
                   help='The tag of the protocol to be read from {tag}.yaml unless protocol_yaml input is specified')
        spec.input('protocol_yaml',
                   valid_type=SinglefileData,
                   required=False,
                   help='Specify a custom yaml file with the multistage settings (and ignore protocol_tag)')
        spec.input('protocol_modify',
                   valid_type=Dict,
                   default=Dict(dict={}),
                   required=False,
                   help='Specify custom settings that overvrite the yaml settings')
        spec.input('starting_settings_idx',
                   valid_type=Int,
                   default=Int(0),
                   required=False,
                   help='If idx>0 is chosen, jumps directly to overwrite settings_0 with settings_{idx}')
        spec.input('min_cell_size',
                   valid_type=Float,
                   default=Float(0.0),
                   required=False,
                   help='To avoid using k-points, extend the cell so that min(perp_width)>min_cell_size')
        spec.input('parent_calc_folder',
                   valid_type=RemoteData,
                   required=False,
                   help='Provide an initial parent folder that contains the wavefunction for restart')
        spec.input(
            'cp2k_base.cp2k.parameters',
            valid_type=Dict,
            required=False,
            help='Specify custom CP2K settings to overwrite the input dictionary just before submitting the CalcJob')
        spec.input('cp2k_base.cp2k.metadata.options.parser_name',
                   valid_type=six.string_types,
                   default='cp2k_advanced_parser',
                   non_db=True,
                   help='Parser of the calculation: the default is cp2k_advanced_parser to get the necessary info')

        # Workchain outline
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

        # Exit codes
        spec.exit_code(901, 'ERROR_MISSING_INITIAL_SETTINGS',
                       'Specified starting_settings_idx that is not existing, or any in between 0 and idx is missing')
        spec.exit_code(902, 'ERROR_NO_MORE_SETTINGS',
                       'Settings for Stage0 are not ok but there are no more robust settings to try')
        spec.exit_code(903, 'ERROR_PARSING_OUTPUT',
                       'Something important was not printed correctly and the parsing of the first calculation failed')

        # Outputs
        spec.expose_outputs(Cp2kBaseWorkChain, include=['remote_folder'])
        spec.output('output_structure',
                    valid_type=StructureData,
                    required=False,
                    help='Processed structure (missing if only ENERGY calculation is performed)')
        spec.output('last_input_parameters',
                    valid_type=Dict,
                    required=False,
                    help='CP2K input parameters used (and possibly working) used in the last stage')
        spec.output('output_parameters',
                    valid_type=Dict,
                    required=False,
                    help='Output CP2K parameters of all the stages, merged together')

    def setup_multistage(self):
        """Setup initial parameters."""

        # Store the workchain inputs in context (to be modified later)
        self.ctx.base_inp = AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base'))

        # Check if an input parent_calc_folder is provided
        if 'parent_calc_folder' in self.inputs:
            self.ctx.parent_calc_folder = self.inputs.parent_calc_folder
        else:
            self.ctx.parent_calc_folder = None

        # Read yaml file selected as SinglefileData or chosen with the tag, and overwrite with custom modifications
        if 'protocol_yaml' in self.inputs:
            self.ctx.protocol = yaml.safe_load(self.inputs.protocol_yaml.open())
        else:
            thisdir = os.path.dirname(os.path.abspath(__file__))
            yamlfullpath = os.path.join(thisdir, 'multistage_protocols', self.inputs.protocol_tag.value + '.yaml')
            with open(yamlfullpath, 'r') as stream:
                self.ctx.protocol = yaml.safe_load(stream)
        merge_dict(self.ctx.protocol, self.inputs.protocol_modify.get_dict())

        # Initialize
        self.ctx.settings_ok = False
        self.ctx.stage_idx = 0
        self.ctx.stage_tag = 'stage_{}'.format(self.ctx.stage_idx)
        self.ctx.settings_idx = 0
        self.ctx.settings_tag = 'settings_{}'.format(self.ctx.settings_idx)
        self.ctx.structure = self.inputs.structure

        # Resize the unit cell if min(perp_with) < inputs.min_cell_size
        self.ctx.resize = check_resize_unit_cell(self.ctx.structure, self.inputs.min_cell_size)  # Dict
        if self.ctx.resize['nx'] > 1 or self.ctx.resize['ny'] > 1 or self.ctx.resize['nz'] > 1:
            resized_struct = resize_unit_cell(self.ctx.structure, self.ctx.resize)
            self.ctx.structure = resized_struct
            self.report("Unit cell resized by {}x{}x{} (StructureData<{}>)".format(self.ctx.resize['nx'],
                                                                                   self.ctx.resize['ny'],
                                                                                   self.ctx.resize['nz'],
                                                                                   resized_struct.pk))
        else:
            self.report("Unit cell was NOT resized")

        # Generate input parameters and store them
        self.ctx.cp2k_param = deepcopy(self.ctx.protocol['settings_0'])
        while self.inputs.starting_settings_idx < self.ctx.settings_idx:
            # overwrite untill the desired starting setting are obtained
            self.ctx.settings_idx += 1
            self.ctx.settings_tag = 'settings_{}'.format(self.ctx.settings_idx)
            if self.ctx.settings_tag in self.ctx.protocol:
                merge_dict(self.ctx.cp2k_param, self.ctx.protocol[self.ctx.settings_tag])
            else:
                return self.exit_codes.ERROR_MISSING_INITIAL_SETTINGS  # pylint: disable=no-member
        kinds = get_kinds_section(self.ctx.structure, self.ctx.protocol)
        merge_dict(self.ctx.cp2k_param, kinds)
        multiplicity = get_input_multiplicity(self.ctx.structure, self.ctx.protocol)
        merge_dict(self.ctx.cp2k_param, multiplicity)
        merge_dict(self.ctx.cp2k_param, self.ctx.protocol['stage_0'])

    def should_run_stage0(self):
        """Returns True if it is the first iteration or the settings are not ok."""
        return not self.ctx.settings_ok

    def run_stage(self):
        """Check for restart, prepare input, submit and direct output to context."""

        # Update structure
        self.ctx.base_inp['cp2k']['structure'] = self.ctx.structure

        # Check if it is needed to restart the calculation and provide the parent folder and new structure
        if self.ctx.parent_calc_folder:
            self.ctx.base_inp['cp2k']['parent_calc_folder'] = self.ctx.parent_calc_folder
            self.ctx.cp2k_param['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS'] = 'RESTART'
            self.ctx.cp2k_param['FORCE_EVAL']['DFT']['WFN_RESTART_FILE_NAME'] = './parent_calc/aiida-RESTART.wfn'
        else:
            self.ctx.cp2k_param['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS'] = 'ATOMIC'

        # Overwrite the generated input with the custom cp2k/parameters
        if 'parameters' in self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']:
            merge_dict(
                self.ctx.cp2k_param,
                AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']['parameters'].get_dict()))
        self.ctx.base_inp['cp2k']['parameters'] = Dict(dict=self.ctx.cp2k_param).store()

        # Update labels
        self.ctx.base_inp['metadata'].update({
            'label': '{}_{}'.format(self.ctx.stage_tag, self.ctx.settings_tag),
            'call_link_label': 'run_{}_{}'.format(self.ctx.stage_tag, self.ctx.settings_tag),
        })
        self.ctx.base_inp['cp2k']['metadata'].update(
            {'label': self.ctx.base_inp['cp2k']['parameters'].get_dict()['GLOBAL']['RUN_TYPE']})

        running_base = self.submit(Cp2kBaseWorkChain, **self.ctx.base_inp)
        self.report("submitted Cp2kBaseWorkChain for {}/{}".format(self.ctx.stage_tag, self.ctx.settings_tag))
        return ToContext(stages=append_(running_base))

    def inspect_and_update_settings_stage0(self):  # pylint: disable=inconsistent-return-statements
        """Inspect the stage0/settings_{idx} calculation and check if it is
        needed to update the settings and resubmint the calculation."""
        self.ctx.settings_ok = True

        # Settings/structure are bad: there are problems in parsing the output file
        # and, most probably, the calculation didn't even start the scf cycles
        if 'output_parameters' in self.ctx.stages[-1].outputs:
            cp2k_out = self.ctx.stages[-1].outputs.output_parameters
        else:
            self.report('ERROR_PARSING_OUTPUT')
            return self.exit_codes.ERROR_PARSING_OUTPUT  # pylint: disable=no-member

        # Settings are bad: the SCF did not converge in the final step
        if not cp2k_out["motion_step_info"]["scf_converged"][-1]:
            self.report("BAD SETTINGS: the SCF did not converge")
            self.ctx.settings_ok = False
            self.ctx.settings_idx += 1
        else:
            # SCF converged, but the computed bandgap needs to be checked
            self.report("Bandgaps spin1/spin2: {:.3f} and {:.3f} ev".format(cp2k_out["bandgap_spin1_au"] * HARTREE2EV,
                                                                            cp2k_out["bandgap_spin2_au"] * HARTREE2EV))
            bandgap_thr_ev = self.ctx.protocol['bandgap_thr_ev']
            if ot_has_small_bandgap(self.ctx.cp2k_param, cp2k_out, bandgap_thr_ev):
                self.report("BAD SETTINGS: band gap is < {:.3f} eV".format(bandgap_thr_ev))
                self.ctx.settings_ok = False
                self.ctx.settings_idx += 1

        # Update the settings tag, check if it is available and overwrite
        if not self.ctx.settings_ok:
            cp2k_out.label = '{}_{}_discard'.format(self.ctx.stage_tag, self.ctx.settings_tag)
            next_settings_tag = 'settings_{}'.format(self.ctx.settings_idx)
            if next_settings_tag in self.ctx.protocol:
                self.ctx.settings_tag = next_settings_tag
                merge_dict(self.ctx.cp2k_param, self.ctx.protocol[self.ctx.settings_tag])
            else:
                return self.exit_codes.ERROR_NO_MORE_SETTINGS  # pylint: disable=no-member

    def inspect_and_update_stage(self):
        """Update geometry, parent folder and the new &MOTION settings."""
        last_stage = self.ctx.stages[-1]

        if 'output_structure' in last_stage.outputs:
            self.ctx.structure = last_stage.outputs.output_structure
            self.report('Structure updated for next stage')
        else:
            self.report('New structure NOT found and NOT updated for next stage')

        self.ctx.parent_calc_folder = last_stage.outputs.remote_folder
        last_stage.outputs.output_parameters.label = '{}_{}_valid'.format(self.ctx.stage_tag, self.ctx.settings_tag)

        self.ctx.stage_idx += 1
        next_stage_tag = 'stage_{}'.format(self.ctx.stage_idx)

        if next_stage_tag in self.ctx.protocol:
            self.ctx.stage_tag = next_stage_tag
            self.ctx.next_stage_exists = True
            merge_dict(self.ctx.cp2k_param, self.ctx.protocol[self.ctx.stage_tag])
        else:
            self.ctx.next_stage_exists = False
            self.report("All stages computed, finishing...")

    def should_run_stage(self):
        """Return True if it exists a new stage to compute."""
        return self.ctx.next_stage_exists

    def results(self):
        """Gather final outputs of the workchain."""

        # Gather all the ouput_parameters in a final Dict
        all_output_parameters = {}
        for i, stage in enumerate(self.ctx.stages):
            all_output_parameters['out_{}'.format(i)] = stage.outputs.output_parameters
        self.out('output_parameters', extract_results(resize=self.ctx.resize, **all_output_parameters))
        # Output the final parameters that worked as a Dict
        self.out('last_input_parameters', self.ctx.base_inp['cp2k']['parameters'])
        # Output the final remote folder
        self.out_many(self.exposed_outputs(self.ctx.stages[-1], Cp2kBaseWorkChain))
        # Output the final structure only if it was modified (there is any MD or OPT stage)
        if 'output_structure' in self.ctx.stages[-1].outputs:
            self.out('output_structure', self.ctx.stages[-1].outputs.output_structure)
            self.report("Outputs: Dict<{}> and StructureData<{}>".format(self.outputs['output_parameters'].pk,
                                                                         self.outputs['output_structure'].pk))
        else:
            self.report("Outputs: Dict<{}> and NO StructureData".format(self.outputs['output_parameters'].pk))
