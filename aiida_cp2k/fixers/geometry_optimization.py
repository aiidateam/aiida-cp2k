"""Fixers that can be applied to the geometry optimization jobs."""
from __future__ import absolute_import

from aiida.orm import Dict
from aiida.engine import calcfunction, ExitCode
from aiida_cp2k.utils import ErrorHandlerReport, merge_dict


@calcfunction
def add_restart_sections(input_dict):
    """Add restart section to the input dictionary."""
    params = input_dict.get_dict()
    restart_wfn_dict = {
        'FORCE_EVAL': {
            'DFT': {
                'RESTART_FILE_NAME': './parent_calc/aiida-RESTART.wfn',
                'SCF': {
                    'SCF_GUESS': 'RESTART',
                },
            },
        },
    }
    merge_dict(params, restart_wfn_dict)
    params['EXT_RESTART'] = {'RESTART_FILE_NAME': './parent_calc/aiida-1.restart'}
    return Dict(dict=params)


def resubmit_unconverged_geometry(workchain, calc):
    """Resubmit a calculation it is not converged, but can be recovered."""

    content_string = calc.outputs.retrieved.get_object_content(calc.get_attribute('output_filename'))

    time_not_exceeded = "PROGRAM ENDED AT"
    time_exceeded = "exceeded requested execution time"
    one_step_done = "Max. gradient              ="
    workchain.ctx.inputs.parent_calc_folder = calc.outputs.remote_folder
    params = workchain.ctx.inputs.parameters

    # If the problem is recoverable then do restart
    if (time_not_exceeded not in content_string or time_exceeded in content_string) and one_step_done in content_string:
        try:
            # Firts check if all the restart keys are present in the input dictionary
            wf_rest_fname_pointer = params['FORCE_EVAL']['DFT']['RESTART_FILE_NAME']
            scf_guess_pointer = params['FORCE_EVAL']['DFT']['SCF']['SCF_GUESS']
            restart_fname_pointer = params['EXT_RESTART']['RESTART_FILE_NAME']

            # Also check if they all have the right value
            if not (wf_rest_fname_pointer == './parent_calc/aiida-RESTART.wfn' and scf_guess_pointer == 'RESTART' and
                    restart_fname_pointer == './parent_calc/aiida-1.restart'):

                # If some values are incorrect add them to the input dictionary
                params = add_restart_sections(params)

        # If not all the restart keys are present, adding them to the input dictionary
        except KeyError:
            params = add_restart_sections(params)

        # Might be able to solve the problem
        workchain.ctx.inputs.parameters = params  # params (new or old ones) that for sure
        # include the necessary restart key-value pairs
        workchain.report(
            "The CP2K calculation wasn't completed. The restart of the calculation might be able to fix the problem.")
        return ErrorHandlerReport(True, True)

    # If the problem is not recoverable
    if (time_not_exceeded not in content_string or
            time_exceeded in content_string) and one_step_done not in content_string:

        workchain.report("It seems that the restart of CP2K calculation wouldn't be able to fix the problem. "
                         "Sending a signal to stop the Base work chain.")

        # Signaling to the base work chain that the problem could not be recovered.
        return ErrorHandlerReport(False, True, ExitCode(1))

    # If everything is alright
    return None
