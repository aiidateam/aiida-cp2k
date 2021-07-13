# -*- coding: utf-8 -*-
"""Base work chain to run a CP2K calculation."""

from aiida.common import AttributeDict
from aiida.engine import BaseRestartWorkChain, ExitCode, ProcessHandlerReport, process_handler, while_
from aiida.orm import Dict
from aiida.plugins import CalculationFactory

from ..utils import add_restart_sections

Cp2kCalculation = CalculationFactory('cp2k')  # pylint: disable=invalid-name


class Cp2kBaseWorkChain(BaseRestartWorkChain):
    """Workchain to run a CP2K calculation with automated error handling and restarts."""

    _process_class = Cp2kCalculation

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super(Cp2kBaseWorkChain, cls).define(spec)
        spec.expose_inputs(Cp2kCalculation, namespace='cp2k')

        spec.outline(
            cls.setup,
            while_(cls.should_run_process)(
                cls.run_process,
                cls.inspect_process,
                cls.overwrite_input_structure,
            ),
            cls.results,
        )

        spec.expose_outputs(Cp2kCalculation)
        spec.output('final_input_parameters', valid_type=Dict, required=False,
                    help='The input parameters used for the final calculation.')

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.

        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """

        super(Cp2kBaseWorkChain, self).setup()
        self.ctx.inputs = AttributeDict(self.exposed_inputs(Cp2kCalculation, 'cp2k'))

    def results(self):
        super().results()
        if self.inputs.cp2k.parameters != self.ctx.inputs.parameters:
            self.out('final_input_parameters', self.ctx.inputs.parameters)

    def overwrite_input_structure(self):
        self.ctx.inputs.structure = self.ctx.children[self.ctx.iteration-1].outputs.output_structure



    @process_handler(priority=400, enabled=False)
    def resubmit_unconverged_geometry(self, calc):
        """Resubmit a calculation it is not converged, but can be recovered."""

        self.report("Checking the geometry convergence.")

        content_string = calc.outputs.retrieved.get_object_content(calc.get_attribute('output_filename'))

        time_not_exceeded = "PROGRAM ENDED AT"
        time_exceeded = "exceeded requested execution time"
        one_step_done = "Max. gradient              ="
        self.ctx.inputs.parent_calc_folder = calc.outputs.remote_folder
        params = self.ctx.inputs.parameters

        # If the problem is recoverable then do restart
        if (time_not_exceeded not in content_string or time_exceeded in content_string) and one_step_done in content_string:  # pylint: disable=line-too-long
            try:
                # Firts check if all the restart keys are present in the input dictionary
                wf_rest_fname_pointer = params['FORCE_EVAL']['DFT']['RESTART_FILE_NAME']
                scf_guess_pointer = params['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS']
                restart_fname_pointer = params['EXT_RESTART']['RESTART_FILE_NAME']

                # Also check if they all have the right value
                if not (wf_rest_fname_pointer == './parent_calc/aiida-RESTART.wfn' and
                        scf_guess_pointer == 'RESTART' and
                        restart_fname_pointer == './parent_calc/aiida-1.restart'):

                    # If some values are incorrect add them to the input dictionary
                    params = add_restart_sections(params)

            # If not all the restart keys are present, adding them to the input dictionary
            except (AttributeError, KeyError):
                params = add_restart_sections(params)

            # Might be able to solve the problem
            self.ctx.inputs.parameters = params  # params (new or old ones) that for sure
            # include the necessary restart key-value pairs
            self.report(
                "The CP2K calculation wasn't completed. The restart of the calculation might be able to "
                "fix the problem.")
            return ProcessHandlerReport(False)

        # If the problem is not recoverable
        if (time_not_exceeded not in content_string or
                time_exceeded in content_string) and one_step_done not in content_string:

            self.report("It seems that the restart of CP2K calculation wouldn't be able to fix the problem as the "
                        "geometry optimization couldn't complete a single step. Sending a signal to stop the Base "
                        "work chain.")

            # Signaling to the base work chain that the problem could not be recovered.
            return ProcessHandlerReport(True, ExitCode(1))

        self.report("The geometry seem to be converged.")
        # If everything is alright
        return None

    def restart_cell_opt(self, calc):
        self.report("Checking the cell convergence.")
        input_structure = calc.inputs.structure
        output_structure = calc.outputs.output_structure
        delta_volume= abs(input_structure.get_cell_volume()-output_structure.get_cell_volume())
        delta_l = 0
        delta_angle = 0
        for i in range(3):
            delta_l = max(delta_l, abs(input_structure.cell_lengths[i]-output_structure.cell_lengths[i])/abs(input_structure.cell_lengths[i]))
            delta_angle = max(delta_angle, abs(input_structure.cell_angles[i]-output_structure.cell_angles[i])/abs(input_structure.cell_angles[i]))
        if delta_volume > 0.01 or delta_l > 0.01 or delta_angle > 0.05:
            return ProcessHandlerReport(False, ExitCode(1))
        else:
            return None
