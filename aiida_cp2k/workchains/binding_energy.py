# -*- coding: utf-8 -*-
"""Binding energy workchain"""

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
from aiida_cp2k.utils import get_kinds_with_ghost_section , get_input_multiplicity, ot_has_small_bandgap
from aiida_cp2k.utils import aiida_structure_merge
from aiida_cp2k.utils import HARTREE2EV

Cp2kBaseWorkChain = WorkflowFactory('cp2k.base')  # pylint: disable=invalid-name


@calcfunction
def extract_results(resize, **kwargs):
    """Extracts restults form the output_parameters"""
    return Dict(dict=output_dict)


class BindingEnergyWorkChain(WorkChain):
    """Submits Cp2kBase work chain for structure + molecule system, first optimizing the geometry of the molecule and
    later computing the BSSE corrected interaction energy.
    This work chain is inspired to Cp2kMultistage, and shares some logics and data from it.
    """

    @classmethod
    def define(cls, spec):
        super(BindingEnergyWorkChain, cls).define(spec)

        spec.expose_inputs(Cp2kBaseWorkChain,
                           namespace='cp2k_base',
                           exclude=['cp2k.structure', 'cp2k.parameters', 'cp2k.metadata.options.parser_name'])
        spec.input('structure',
            valid_type=StructureData,
            required=True,
            help='Input structure that contains the molecule.')
        spec.input('molecule',
            valid_type=StructureData,
            required=True,
            help='Input molecule in the unit cell of the structure.')
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

        # Workchain outline
        spec.outline(
            cls.setup,
            while_(cls.should_run_geo_opt)(
                cls.run_stage,
                cls.inspect_and_update_settings_geo_opt,
            ),
            cls.run_bsse,
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
        self.ctx.settings_idx = 0
        self.ctx.settings_tag = 'settings_{}'.format(self.ctx.settings_idx)

        self.ctx.system = aiida_structure_merge(self.inputs.structure, self.inputs.molecule)
        self.ctx.natoms_molecule = len(list(self.inputs.molecule.get_ase().symbols))

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
        kinds = get_kinds_with_ghost_section(self.ctx.system, self.ctx.protocol)
        merge_dict(self.ctx.cp2k_param, kinds)
        multiplicity = get_input_multiplicity(self.ctx.structure, self.ctx.protocol)
        merge_dict(self.ctx.cp2k_param, multiplicity)
        merge_dict(self.ctx.cp2k_param, {
            'GLOBAL': { 'RUN_TYPE': 'GEO_OPT' },
            'FORCE_EVAL': {'DFT' : {'SCF': {'SCF_GUESS': 'ATOMIC' }}},
            'MOTION': { 'GEO_OPT': { 'MAX_ITER': 200 }}}) # CP2K default: 200 iter.

    def should_run_geo_opt(self):
        """Returns True if it is the first iteration or the settings are not ok."""
        return not self.ctx.settings_ok


    def run_geo_opt(self):
        """Check for restart, prepare input, submit and direct output to context."""

        self.ctx.base_inp['cp2k']['structure'] = self.ctx.system

        # Overwrite the generated input with the custom cp2k/parameters
        if 'parameters' in self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']:
            merge_dict(
                self.ctx.cp2k_param,
                self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']['parameters'].get_dict())
        self.ctx.base_inp['cp2k']['parameters'] = Dict(dict=self.ctx.cp2k_param)

        self.ctx.base_inp['metadata'].update({'label': 'geo_opt_molecule', 'call_link_label': 'run_geo_opt_molecule'})
        self.ctx.base_inp['cp2k']['metadata'].update({'label': 'GEO_OPT'})
        self.ctx.base_inp['cp2k']['metadata']['options']['parser_name'] = 'cp2k_bsse_parser'

        running_base = self.submit(Cp2kBaseWorkChain, **self.ctx.base_inp)
        self.report("submitted Cp2kBaseWorkChain to geo-opt the molecule")
        return ToContext(stages=append_(running_base))

    def inspect_and_update_settings_geo_opt(self):  # pylint: disable=inconsistent-return-statements
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

    def run_bsse(self):
        """Update parameters and run BSSE calculation."""



    def results(self):
        """Gather final outputs of the workchain."""
