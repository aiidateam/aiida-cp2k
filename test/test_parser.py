# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test parsing band structure."""
import os
from aiida_cp2k.utils.parser import _parse_bands

THISDIR = os.path.dirname(os.path.realpath(__file__))


def test_bands_parser_51():
    """Test that band structure is parsed correctly."""

    # Test parsing bands in the the output of CP2K 5.1
    with open(f"{THISDIR}/outputs/BANDS_output_v5.1.out") as fobj:
        lines = fobj.readlines()
        for i_line, line in enumerate(lines):
            if "KPOINTS| Band Structure Calculation" in line:
                kpoints, labels, bands = _parse_bands(lines, i_line, 5.1)
        assert (kpoints[4] == [0.2, 0., 0.2]).all()
        assert labels == [(0, 'GAMMA'), (10, 'X'), (11, 'X'), (21, 'U'), (22, 'K'), (32, 'GAMMA'), (33, 'GAMMA'),
                          (43, 'L'), (44, 'L'), (54, 'W'), (55, 'W'), (65, 'X')]
        assert (bands[0] == [-6.84282475, 5.23143741, 5.23143741, 5.23143741, 7.89232311]).all()


def test_bands_parser_81():
    """Test that band structure is parsed correctly."""
    # Test parsing bands in the the output of CP2K 8.1
    with open(f"{THISDIR}/outputs/BANDS_output_v8.1.out") as fobj:
        lines = fobj.readlines()
        for i_line, line in enumerate(lines):
            if "KPOINTS| Band Structure Calculation" in line:
                kpoints, labels, bands = _parse_bands(lines, i_line, 8.1)
        assert (kpoints[4] == [0.2, 0., 0.2]).all()
        assert labels == [(0, 'GAMMA'), (10, 'X'), (11, 'X'), (21, 'U'), (22, 'K'), (32, 'GAMMA'), (33, 'GAMMA'),
                          (43, 'L'), (44, 'L'), (54, 'W'), (55, 'W'), (65, 'X')]
        assert (bands[0] == [-6.84282475, 5.23143741, 5.23143741, 5.23143741, 7.89232311]).all()
