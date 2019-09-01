# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K input plugin"""

from __future__ import absolute_import
from __future__ import division

import re
import math


def parse_cp2k_output(fobj):
    """Parse CP2K output into a dictionary"""
    lines = fobj.readlines()

    result_dict = {"exceeded_walltime": False}

    for i_line, line in enumerate(lines):
        if line.startswith(" ENERGY| "):
            result_dict["energy"] = float(line.split()[8])
            result_dict["energy_units"] = "a.u."
        elif "The number of warnings for this run is" in line:
            result_dict["nwarnings"] = int(line.split()[-1])
        elif "exceeded requested execution time" in line:
            result_dict["exceeded_walltime"] = True
        elif "KPOINTS| Band Structure Calculation" in line:
            kpoints, labels, bands = _parse_bands(lines, i_line)
            result_dict["kpoint_data"] = {
                "kpoints": kpoints,
                "labels": labels,
                "bands": bands,
                "bands_unit": "eV",
            }
        else:
            # ignore all other lines
            pass

    return result_dict


def _parse_bands(lines, n_start):
    """Parse band structure from cp2k output"""

    import numpy as np

    kpoints = []
    labels = []
    bands_s1 = []
    bands_s2 = []
    known_kpoints = {}
    pattern = re.compile(".*?Nr.*?Spin.*?K-Point.*?", re.DOTALL)

    selected_lines = lines[n_start:]
    for current_line, line in enumerate(selected_lines):
        splitted = line.split()
        if "KPOINTS| Special K-Point" in line:
            kpoint = tuple(float(p) for p in splitted[-3:])
            if " ".join(splitted[-5:-3]) != "not specified":
                label = splitted[-4]
                known_kpoints[kpoint] = label
        elif pattern.match(line):
            spin = int(splitted[3])
            kpoint = tuple(float(p) for p in splitted[-3:])
            kpoint_n_lines = int(math.ceil(int(selected_lines[current_line + 1]) / 4))
            band = [
                float(v) for v in " ".join(selected_lines[current_line + 2:current_line + 2 + kpoint_n_lines]).split()
            ]

            if spin == 1:
                if kpoint in known_kpoints:
                    labels.append((len(kpoints), known_kpoints[kpoint]))
                kpoints.append(kpoint)
                bands_s1.append(band)
            elif spin == 2:
                bands_s2.append(band)

    if bands_s2:
        bands = [bands_s1, bands_s2]
    else:
        bands = bands_s1

    return np.array(kpoints), labels, np.array(bands)


def parse_cp2k_trajectory(fobj):
    """CP2K trajectory parser"""

    import numpy as np

    # pylint: disable=protected-access

    content = fobj.read()

    # parse coordinate section
    match = re.search(r'\n\s*&COORD\n(.*?)\n\s*&END COORD\n', content, re.DOTALL)
    coord_lines = [line.strip().split() for line in match.group(1).splitlines()]

    # splitting element name and the tag (if present)
    symbols = []
    tags = []
    for atomic_kind in [l[0] for l in coord_lines]:
        symbols.append(''.join([s for s in atomic_kind if not s.isdigit()]))
        try:
            tag = int(''.join([s for s in atomic_kind if s.isdigit()]))
        except ValueError:
            tag = 0
        tags.append(tag)

    # get positions
    positions_str = [line[1:] for line in coord_lines]
    positions = np.array(positions_str, np.float64)

    # parse cell section
    match = re.search(r"\n\s*&CELL\n(.*?)\n\s*&END CELL\n", content, re.DOTALL)
    cell_lines = [line.strip().split() for line in match.group(1).splitlines()]
    cell_str = [line[1:] for line in cell_lines if line[0] in "ABC"]
    cell = np.array(cell_str, np.float64)

    return {"symbols": symbols, "positions": positions, "cell": cell, "tags": tags}
