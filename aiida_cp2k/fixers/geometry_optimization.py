"""Fixers that can be applied to the geometry optimization jobs."""
from __future__ import absolute_import

from aiida.orm import Dict
from aiida.engine import calcfunction, ExitCode
from aiida_cp2k.utils import ErrorHandlerReport, merge_dict


@calcfunction
def add_restart_section(input_dict):
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

    if (time_not_exceeded not in content_string or time_exceeded in content_string) and one_step_done in content_string:
        workchain.ctx.inputs.parameters = add_restart_section(workchain.ctx.inputs.parameters)
        workchain.ctx.inputs.parent_calc_folder = calc.outputs.remote_folder
        workchain.report("Could fix the problem")
        return ErrorHandlerReport(True, True)

    if (time_not_exceeded not in content_string or
            time_exceeded in content_string) and one_step_done not in content_string:
        workchain.report("Could NOT fix the problem")
        return ErrorHandlerReport(False, True, ExitCode(555))

    workchain.report("No problems!")

    return None
