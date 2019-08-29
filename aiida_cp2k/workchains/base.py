# -*- coding: utf-8 -*-
"""Base workchain to run a CP2K calculation"""
from __future__ import absolute_import

from aiida.common import AttributeDict
from aiida.engine import while_
from aiida.plugins import CalculationFactory

from aiida_cp2k.workchains.aiida_base_restart import BaseRestartWorkChain

Cp2kCalculation = CalculationFactory('cp2k')  # pylint: disable=invalid-name


class Cp2kBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a CP2K calculation with automated error handling and restarts."""

    _calculation_class = Cp2kCalculation

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super(Cp2kBaseWorkChain, cls).define(spec)
        spec.expose_inputs(Cp2kCalculation, namespace='cp2k')

        spec.outline(
            cls.setup,
            while_(cls.should_run_calculation)(
                cls.run_calculation,
                cls.inspect_calculation,
            ),
            cls.results,
        )

        spec.expose_outputs(Cp2kCalculation)

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.

        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """
        super(Cp2kBaseWorkChain, self).setup()
        self.ctx.inputs = AttributeDict(self.exposed_inputs(Cp2kCalculation, 'cp2k'))
