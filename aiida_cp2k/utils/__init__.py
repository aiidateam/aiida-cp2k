###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K utils"""

from .input_generator import (
    Cp2kInput,
    add_ext_restart_section,
    add_first_snapshot_in_reftraj_section,
    add_wfn_restart_section,
)
from .parser import parse_cp2k_output, parse_cp2k_output_advanced, parse_cp2k_trajectory
from .workchains import (
    HARTREE2EV,
    HARTREE2KJMOL,
    check_resize_unit_cell,
    get_input_multiplicity,
    get_kinds_section,
    merge_dict,
    merge_Dict,
    ot_has_small_bandgap,
    resize_unit_cell,
)

__all__ = [
    "Cp2kInput",
    "add_ext_restart_section",
    "add_first_snapshot_in_reftraj_section",
    "add_wfn_restart_section",
    "parse_cp2k_output",
    "parse_cp2k_output_advanced",
    "parse_cp2k_trajectory",
    "HARTREE2EV",
    "HARTREE2KJMOL",
    "check_resize_unit_cell",
    "get_input_multiplicity",
    "get_kinds_section",
    "merge_dict",
    "merge_Dict",
    "ot_has_small_bandgap",
    "resize_unit_cell",
]
