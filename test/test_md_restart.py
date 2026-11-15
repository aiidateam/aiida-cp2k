###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
#                                                                            #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k.     #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Regression test for MD restart after an interruption without a checkpoint."""

from pathlib import Path
from shlex import quote

from aiida import engine, orm
from ase import Atoms

from aiida_cp2k.calculations import Cp2kCalculation
from aiida_cp2k.workchains import Cp2kBaseWorkChain


def test_md_restart_reuses_checkpoint(cp2k_code, aiida_local_code_factory, tmp_path):
    """Continue MD after a retry writes no restart file."""
    wrapper = tmp_path / "cp2k-md-restart"
    interruption = quote(str(tmp_path / "interrupted"))
    executable = quote(str(cp2k_code.filepath_executable))
    wrapper.write_text(
        f"""#!/bin/sh
set -eu
if [ ! -e parent_calc ]; then
    {executable} "$@"
    echo 'MD run terminated - exceeded requested execution time'
elif [ ! -e {interruption} ]; then
    touch {interruption}
    echo 'Total energy: 0.0'
    echo 'MD run terminated - exceeded requested execution time'
else
    exec {executable} "$@"
fi
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    code = aiida_local_code_factory(
        entry_point="cp2k",
        executable=str(wrapper),
        prepend_text=cp2k_code.prepend_text,
    )

    files = Path(__file__).resolve().parents[1] / "examples" / "files"
    builder = Cp2kBaseWorkChain.get_builder()
    builder.handler_overrides = orm.Dict(
        {"restart_incomplete_calculation": {"enabled": True}}
    )
    builder.max_iterations = orm.Int(3)
    builder.cp2k.code = code
    builder.cp2k.structure = orm.StructureData(
        ase=Atoms("H2", positions=[(4, 4, 4), (4, 4, 4.75)], cell=[8, 8, 8], pbc=True)
    )
    builder.cp2k.file = {
        "basis": orm.SinglefileData(files / "BASIS_MOLOPT"),
        "pseudo": orm.SinglefileData(files / "GTH_POTENTIALS"),
    }
    builder.cp2k.parameters = orm.Dict(
        {
            "GLOBAL": {"RUN_TYPE": "MD"},
            "FORCE_EVAL": {
                "METHOD": "Quickstep",
                "DFT": {
                    "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                    "POTENTIAL_FILE_NAME": "GTH_POTENTIALS",
                    "MGRID": {"CUTOFF": 120},
                    "XC": {"XC_FUNCTIONAL": {"_": "PBE"}},
                },
                "SUBSYS": {
                    "KIND": {
                        "_": "H",
                        "BASIS_SET": "DZVP-MOLOPT-SR-GTH",
                        "POTENTIAL": "GTH-PBE-q1",
                    },
                },
            },
            "MOTION": {
                "MD": {"ENSEMBLE": "NVE", "STEPS": 1, "TEMPERATURE": 10},
                "PRINT": {
                    "RESTART": {"EACH": {"MD": 1}},
                    "TRAJECTORY": {"EACH": {"MD": 1}},
                },
            },
        }
    )
    builder.cp2k.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.cp2k.metadata.options.withmpi = False

    outputs, node = engine.run_get_node(builder)
    first, interrupted, resumed = sorted(
        (child for child in node.called if isinstance(child, orm.CalcJobNode)),
        key=lambda calc: calc.pk,
    )
    assert first.exit_status == Cp2kCalculation.exit_codes.ERROR_OUT_OF_WALLTIME.status
    assert interrupted.exit_status == first.exit_status
    restart_filename = Cp2kCalculation._DEFAULT_RESTART_FILE_NAME
    assert restart_filename in first.outputs.retrieved.list_object_names()
    assert restart_filename not in interrupted.outputs.retrieved.list_object_names()
    assert resumed.inputs.parent_calc_folder.uuid == first.outputs.remote_folder.uuid
    assert node.is_finished_ok, node.exit_message
    assert outputs["output_trajectory"].get_stepids().tolist() == [0, 1, 2]
