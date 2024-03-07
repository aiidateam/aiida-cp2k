"""Base work chain to run a CP2K calculation."""

from aiida import common, engine, orm, plugins

from .. import utils

Cp2kCalculation = plugins.CalculationFactory('cp2k')


class Cp2kBaseWorkChain(engine.BaseRestartWorkChain):
    """Workchain to run a CP2K calculation with automated error handling and restarts."""

    _process_class = Cp2kCalculation

    @classmethod
    def define(cls, spec):
        # yapf: disable
        super().define(spec)
        spec.expose_inputs(Cp2kCalculation, namespace='cp2k')

        spec.outline(
            cls.setup,
            engine.while_(cls.should_run_process)(
                cls.run_process,
                cls.inspect_process,
                cls.overwrite_input_structure,
            ),
            cls.results,
        )

        spec.expose_outputs(Cp2kCalculation)
        spec.output('final_input_parameters', valid_type=orm.Dict, required=False,
                    help='The input parameters used for the final calculation.')
        spec.exit_code(400, 'NO_RESTART_DATA', message="The calculation didn't produce any data to restart from.")
        spec.exit_code(300, 'ERROR_UNRECOVERABLE_FAILURE',
                       message='The calculation failed with an unidentified unrecoverable error.')
        spec.exit_code(310, 'ERROR_KNOWN_UNRECOVERABLE_FAILURE',
                       message='The calculation failed with a known unrecoverable error.')

    def setup(self):
        """Call the `setup` of the `BaseRestartWorkChain` and then create the inputs dictionary in `self.ctx.inputs`.

        This `self.ctx.inputs` dictionary will be used by the `BaseRestartWorkChain` to submit the calculations in the
        internal loop.
        """
        super().setup()
        self.ctx.inputs = common.AttributeDict(self.exposed_inputs(Cp2kCalculation, 'cp2k'))

    def _collect_all_trajetories(self):
        """Collect all trajectories from the children calculations."""
        trajectories = []
        for called in self.ctx.children:
            if isinstance(called, orm.CalcJobNode):
                try:
                    trajectories.append(called.outputs.output_trajectory)
                except AttributeError:
                    pass
        return trajectories

    def results(self):
        super().results()
        if self.inputs.cp2k.parameters != self.ctx.inputs.parameters:
            self.out('final_input_parameters', self.ctx.inputs.parameters)

        trajectories = self._collect_all_trajetories()
        if trajectories:
            self.report("Work chain completed successfully, collecting all trajectories")
            self.out("output_trajectory", utils.merge_trajectory_data_unique(*trajectories))

    def overwrite_input_structure(self):
        if "output_structure" in self.ctx.children[self.ctx.iteration-1].outputs:
            self.ctx.inputs.structure = self.ctx.children[self.ctx.iteration-1].outputs.output_structure

    @engine.process_handler(priority=401, exit_codes=[
        Cp2kCalculation.exit_codes.ERROR_OUT_OF_WALLTIME,
        Cp2kCalculation.exit_codes.ERROR_OUTPUT_INCOMPLETE,
    ], enabled=False)
    def restart_incomplete_calculation(self, calc):
        """This handler restarts incomplete calculations."""
        content_string = calc.outputs.retrieved.base.repository.get_object_content(calc.base.attributes.get('output_filename'))

        # CP2K was updating geometry - continue with that.
        restart_geometry_transformation = "Max. gradient              =" in content_string or "MD| Step number" in content_string
        end_inner_scf_loop = "Total energy: " in content_string
        # The message is written in the log file when the CP2K input parameter `LOG_PRINT_KEY` is set to True.
        if not (restart_geometry_transformation or end_inner_scf_loop or "Writing RESTART" in content_string):
            self.report("It seems that the restart of CP2K calculation wouldn't be able to fix the problem as the "
                        "previous calculation didn't produce any output to restart from. "
                        "Sending a signal to stop the Base work chain.")

            # Signaling to the base work chain that the problem could not be recovered.
            return engine.ProcessHandlerReport(True, self.exit_codes.NO_RESTART_DATA)

        self.ctx.inputs.parent_calc_folder = calc.outputs.remote_folder
        params = self.ctx.inputs.parameters

        params = utils.add_wfn_restart_section(params, orm.Bool('kpoints' in self.ctx.inputs))

        if restart_geometry_transformation:
            # Check if we need to fix restart snapshot in REFTRAJ MD
            first_snapshot = None
            try:
                first_snapshot = int(params['MOTION']['MD']['REFTRAJ']['FIRST_SNAPSHOT']) + calc.outputs.output_trajectory.get_shape('positions')[0]
                if first_snapshot:
                    params = utils.add_first_snapshot_in_reftraj_section(params, first_snapshot)
            except KeyError:
                pass
            params = utils.add_ext_restart_section(params)

        self.ctx.inputs.parameters = params  # params (new or old ones) that include the necessary restart information.
        self.report(
            "The CP2K calculation wasn't completed. The restart of the calculation might be able to "
            "fix the problem.")
        return engine.ProcessHandlerReport(False)
