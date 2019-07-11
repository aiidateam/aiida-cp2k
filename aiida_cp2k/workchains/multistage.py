# -*- coding: utf-8 -*-
"""Multistage workchain"""
from __future__ import absolute_import
import yaml
import os
from copy import deepcopy

from aiida.common import AttributeDict
from aiida.engine import append_, while_, WorkChain, ToContext
from aiida.engine import workfunction as wf
from aiida.orm import Dict
from aiida.plugins import CalculationFactory

from aiida_cp2k.workchains import Cp2kBaseWorkChain

Cp2kCalculation = CalculationFactory('cp2k')  # pylint: disable=invalid-name

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
    p1_dict = p1.get_dict()
    p2_dict = p2.get_dict()
    merge_dict(p1_dict, p2_dict)
    return Dict(dict=p1_dict).store()

def get_kinds_section(structure, multistage_settings):
    """ Write the &KIND sections given the structure and the settings_dict"""
    kinds = []
    all_atoms = set(structure.get_ase().get_chemical_symbols())
    for a in all_atoms:
        kinds.append({
            '_': a,
            'BASIS_SET': multistage_settings['basis_set'][a],
            'POTENTIAL': multistage_settings['pseudopotential'][a],
            'MAGNETIZATION': multistage_settings['initial_magnetization'][a],
            })
    return { 'FORCE_EVAL': { 'SUBSYS': { 'KIND': kinds }}}

def get_input_multiplicity(structure, multistage_settings):
    multiplicity = 1
    all_atoms = structure.get_ase().get_chemical_symbols()
    for key, value in multistage_settings['initial_magnetization'].items():
        multiplicity += all_atoms.count(key) * value
    multiplicity = int(round(multiplicity))
    multiplicity_dict = {'FORCE_EVAL': {'DFT': {'MULTIPLICITY' :multiplicity}}}
    if multiplicity != 1:
        multiplicity_dict['FORCE_EVAL']['DFT']['UKS'] = True
    return multiplicity_dict

class Cp2kMultistageWorkChain(WorkChain):
    """Workchain to submit GEO_OPT/CELL_OPT/MD workchains with iterative fashion"""

    _calculation_class = Cp2kCalculation

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super(Cp2kMultistageWorkChain, cls).define(spec)
        spec.expose_inputs(Cp2kBaseWorkChain, namespace='base')

        spec.outline(
            cls.setup_multistage,
            cls.run_stage0
        )
        """
            while_(cls.should_run_stage0)(
              cls.run_stage,
              cls.inspect_settings,
            ),
            cls.inspect_stage,
            while_(cls.should_run_stage)(
                cls.run_stage,
                cls.inspect_stage,
            ),
            cls.results,
        )
        """
        spec.expose_outputs(Cp2kBaseWorkChain)

    def setup_multistage(self):
        """
        # Read the WorkChain inputs
        self.ctx.inputs = AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'base'))

        # Read yaml file
        yamlfullpath = os.path.realpath(__file__)[:-3] + "_standard.yaml"
        with open(yamlfullpath, 'r') as stream:
            input_yaml_dict = yaml.safe_load(stream)

        # Generate input parameters and store them
        self.ctx.parameters = deepcopy(input_yaml_dict['settings_0'])
        kinds = get_kinds_section(self.ctx.inputs['cp2k']['structure'], input_yaml_dict)
        merge_dict(self.ctx.parameters,kinds)
        multiplicity = get_input_multiplicity(self.ctx.inputs['cp2k']['structure'], input_yaml_dict)
        merge_dict(self.ctx.parameters,multiplicity)
        merge_dict(self.ctx.parameters,input_yaml_dict['stage_0'])
        merge_dict(self.ctx.parameters, self.ctx.inputs['cp2k']['parameters'].get_dict())
        self.ctx.inputs['cp2k']['parameters'] = Dict(dict = self.ctx.parameters).store()
        """
        self.ctx.inputs = AttributeDict(self.exposed_inputs(Cp2kBaseWorkChain, 'base'))

    def run_stage0(self):
        running_base = self.submit(Cp2kBaseWorkChain, **self.ctx.inputs)
        self.report("submitted Cp2kBaseWorkChain<{}> for settings_0/stage_0".format(running_base.pk))
        return ToContext(workchains=append_(running_base))
