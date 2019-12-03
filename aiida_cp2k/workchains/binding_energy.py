# -*- coding: utf-8 -*-
"""Binding energy workchain"""

from __future__ import absolute_import

import os
from copy import deepcopy
import ruamel.yaml as yaml  # does not convert OFF to False

from aiida.common import AttributeDict
from aiida.engine import append_, while_, WorkChain, ToContext
from aiida.engine import calcfunction
from aiida.orm import Dict, Int, SinglefileData, Str, StructureData
from aiida.plugins import WorkflowFactory

from aiida_cp2k.utils import merge_dict
from aiida_cp2k.utils import get_kinds_with_ghost_section, get_bsse_section, get_input_multiplicity
from aiida_cp2k.utils import ot_has_small_bandgap, aiida_structure_merge
from aiida_cp2k.utils import HARTREE2EV

Cp2kBaseWorkChain = WorkflowFactory('cp2k.base')  # pylint: disable=invalid-name


@calcfunction
def get_output_parameters(**cp2k_out_dict):
    """Extracts important results to include in the output_parameters."""
    output_dict = {"motion_step_info": {}}
    output_dict["motion_opt_converged"] = cp2k_out_dict["final_geo_opt"]["motion_opt_converged"]
    selected_motion_keys = [
        "dispersion_energy_au", "energy_au", "max_grad_au", "max_step_au", "rms_grad_au", "rms_step_au", "scf_converged"
    ]
    for key in selected_motion_keys:
        output_dict["motion_step_info"][key] = cp2k_out_dict["final_geo_opt"]["motion_step_info"][key]

    selected_bsse_keys = [
        "binding_energy_raw", "binding_energy_corr", "binding_energy_bsse", "binding_energy_unit",
        "binding_energy_dispersion"
    ]
    for key in selected_bsse_keys:
        if key in cp2k_out_dict['bsse'].get_dict():  # "binding_energy_dispersion" may miss
            output_dict[key] = cp2k_out_dict['bsse'][key]

    return Dict(dict=output_dict)


@calcfunction
def get_loaded_molecule(loaded_structure, input_molecule):
    """Return only the molecule's atoms in the unit cell as a StructureData object."""
    natoms_molecule = len(input_molecule.get_ase())
    molecule_ase = loaded_structure.get_ase()[-natoms_molecule:]
    return StructureData(ase=molecule_ase)


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
        spec.input(
            'cp2k_base.cp2k.parameters',
            valid_type=Dict,
            required=False,
            help='Specify custom CP2K settings to overwrite the input dictionary just before submitting the CalcJob')

        # Workchain outline
        spec.outline(
            cls.setup,
            while_(cls.should_run_geo_opt)(
                cls.run_geo_opt,
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
        spec.output('loaded_molecule', valid_type=StructureData, help='Molecule geometry in the unit cell.')
        spec.output('loaded_structure', valid_type=StructureData, help='Geometry of the system with both fragments.')
        spec.output('output_parameters', valid_type=Dict, help='Info regarding the binding energy of the system.')

    def setup(self):
        """Setup initial parameters."""

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
        self.ctx.natoms_structure = len(self.inputs.structure.get_ase())
        self.ctx.natoms_molecule = len(self.inputs.molecule.get_ase())

        # Generate input parameters
        self.ctx.cp2k_param = deepcopy(self.ctx.protocol['settings_0'])
        while self.inputs.starting_settings_idx < self.ctx.settings_idx:
            # overwrite untill the desired starting setting are obtained
            self.ctx.settings_idx += 1
            self.ctx.settings_tag = 'settings_{}'.format(self.ctx.settings_idx)
            if self.ctx.settings_tag in self.ctx.protocol:
                merge_dict(self.ctx.cp2k_param, self.ctx.protocol[self.ctx.settings_tag])
            else:
                return self.exit_codes.ERROR_MISSING_INITIAL_SETTINGS  # pylint: disable=no-member
        merge_dict(self.ctx.cp2k_param, get_kinds_with_ghost_section(self.ctx.system, self.ctx.protocol))
        merge_dict(self.ctx.cp2k_param, get_input_multiplicity(self.ctx.system, self.ctx.protocol))
        merge_dict(
            self.ctx.cp2k_param,
            {
                'GLOBAL': {
                    'RUN_TYPE': 'GEO_OPT'
                },
                'FORCE_EVAL': {
                    'DFT': {
                        'SCF': {
                            'SCF_GUESS': 'ATOMIC'
                        }
                    }
                },
                'MOTION': {
                    'GEO_OPT': {
                        'MAX_ITER': 200
                    },  # Can be adjusted from builder.cp2k_base.cp2k.parameters
                    'CONSTRAINT': {
                        'FIXED_ATOMS': {
                            'LIST': "1..{}".format(self.ctx.natoms_structure)
                        }
                    }
                }
            })

    def should_run_geo_opt(self):
        """Returns True if it is the first iteration or the settings are not ok."""
        return not self.ctx.settings_ok

    def run_geo_opt(self):
        """Prepare inputs, submit and direct output to context."""

        self.ctx.base_inp = AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base'))
        self.ctx.base_inp['cp2k']['structure'] = self.ctx.system

        # Overwrite the generated input with the custom cp2k/parameters, update metadata and submit
        if 'parameters' in self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']:
            merge_dict(self.ctx.cp2k_param,
                       self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']['parameters'].get_dict())
        self.ctx.base_inp['cp2k']['parameters'] = Dict(dict=self.ctx.cp2k_param)
        self.ctx.base_inp['metadata'].update({'label': 'geo_opt_molecule', 'call_link_label': 'run_geo_opt_molecule'})
        self.ctx.base_inp['cp2k']['metadata'].update({'label': 'GEO_OPT'})
        self.ctx.base_inp['cp2k']['metadata']['options']['parser_name'] = 'cp2k_advanced_parser'
        running_base = self.submit(Cp2kBaseWorkChain, **self.ctx.base_inp)
        self.report("Optimize molecule position in the structure.")
        return ToContext(stages=append_(running_base))

    def inspect_and_update_settings_geo_opt(self):  # pylint: disable=inconsistent-return-statements
        """Inspect the settings_{idx} calculation and check if it is
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
        """Update parameters and run BSSE calculation. BSSE assumes that the molecule has no charge and unit
        multiplicity: this can be customized from builder.cp2k_base.cp2k.parameters.
        """

        self.ctx.cp2k_param['GLOBAL']['RUN_TYPE'] = 'BSSE'
        merge_dict(
            self.ctx.cp2k_param,
            get_bsse_section(natoms_a=self.ctx.natoms_structure,
                             natoms_b=self.ctx.natoms_molecule,
                             mult_a=self.ctx.cp2k_param['FORCE_EVAL']['DFT']['MULTIPLICITY'],
                             mult_b=1,
                             charge_a=0,
                             charge_b=0))

        # Overwrite the generated input with the custom cp2k/parameters, update structure and metadata, and submit
        if 'parameters' in self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']:
            merge_dict(self.ctx.cp2k_param,
                       self.exposed_inputs(Cp2kBaseWorkChain, 'cp2k_base')['cp2k']['parameters'].get_dict())
        self.ctx.base_inp['cp2k']['parameters'] = Dict(dict=self.ctx.cp2k_param)
        self.ctx.base_inp['cp2k']['structure'] = self.ctx.stages[-1].outputs.output_structure
        self.ctx.base_inp['metadata'].update({'label': 'bsse', 'call_link_label': 'run_bsse'})
        self.ctx.base_inp['cp2k']['metadata'].update({'label': 'BSSE'})
        self.ctx.base_inp['cp2k']['metadata']['options']['parser_name'] = 'cp2k_bsse_parser'
        running_base = self.submit(Cp2kBaseWorkChain, **self.ctx.base_inp)
        self.report("Run BSSE calculation to compute corrected binding energy.")

        return ToContext(stages=append_(running_base))

    def results(self):
        """Gather final outputs of the workchain."""

        # Expose the loaded_structure remote_folder
        self.out_many(self.exposed_outputs(self.ctx.stages[-2], Cp2kBaseWorkChain))

        # Return parameters, loaded structure and molecule
        cp2k_out_dict = {
            "final_geo_opt": self.ctx.stages[-2].outputs.output_parameters,
            "bsse": self.ctx.stages[-1].outputs.output_parameters
        }
        self.out('output_parameters', get_output_parameters(**cp2k_out_dict))
        self.out('loaded_structure', self.ctx.stages[-2].outputs.output_structure)
        self.out('loaded_molecule', get_loaded_molecule(self.outputs['loaded_structure'], self.inputs['molecule']))
        self.report("Completed! Ouput Dict<{}>, loaded StructureData<{}>, loaded molecule StructureData<{}>".format(
            self.outputs['output_parameters'].pk, self.outputs['loaded_structure'].pk,
            self.outputs['loaded_molecule'].pk))
