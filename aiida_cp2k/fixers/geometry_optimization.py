from __future__ import absolute_import

from aiida.orm import Dict
from aiida_cp2k.utils import merge_dict
from aiida.engine import calcfunction
from aiida_cp2k.utils import ErrorHandlerReport


@calcfunction
def add_restart_section(input_Dict):
    params = input_Dict.get_dict()
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


def get_file_content(calc):
    fname = calc.get_attribute('output_filename')
    return calc.outputs.retrieved.get_object_content(fname)


def resubmit_unconverged_geometry(workchain, calc):
    output_fname = calc.get_option('output_filename')
    content_string = get_file_content(calc)

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
        return ErrorHandlerReport(False, True)

    workchain.report("No problems!")

    return None
