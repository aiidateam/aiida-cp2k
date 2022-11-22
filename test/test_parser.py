###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test output parser."""
import os

from aiida_cp2k.utils.parser import (
    _parse_bands,
    parse_cp2k_output,
    parse_cp2k_output_advanced,
    parse_cp2k_trajectory,
)

THISDIR = os.path.dirname(os.path.realpath(__file__))


def test_bands_parser_51():
    """Test parsing bands in the output of CP2K 5.1"""

    with open(f"{THISDIR}/outputs/BANDS_output_v5.1.out") as fobj:
        lines = fobj.readlines()
        for i_line, line in enumerate(lines):
            if "KPOINTS| Band Structure Calculation" in line:
                kpoints, labels, bands = _parse_bands(lines, i_line, 5.1)
        assert (kpoints[4] == [0.2, 0.0, 0.2]).all()
        assert labels == [
            (0, "GAMMA"),
            (10, "X"),
            (20, "U"),
            (21, "K"),
            (31, "GAMMA"),
            (41, "L"),
            (51, "W"),
            (61, "X"),
        ]
        assert (
            bands[0] == [-6.84282475, 5.23143741, 5.23143741, 5.23143741, 7.89232311]
        ).all()


def test_bands_parser_81():
    """Test parsing bands in the the output of CP2K 8.1"""

    with open(f"{THISDIR}/outputs/BANDS_output_v8.1.out") as fobj:
        lines = fobj.readlines()
        for i_line, line in enumerate(lines):
            if "KPOINTS| Band Structure Calculation" in line:
                kpoints, labels, bands = _parse_bands(lines, i_line, 8.1)
        assert (kpoints[4] == [0.2, 0.0, 0.2]).all()
        assert labels == [
            (0, "GAMMA"),
            (10, "X"),
            (20, "U"),
            (21, "K"),
            (31, "GAMMA"),
            (41, "L"),
            (51, "W"),
            (61, "X"),
        ]
        assert (
            bands[0] == [-6.84282475, 5.23143741, 5.23143741, 5.23143741, 7.89232311]
        ).all()


def test_cp2k_output():
    """Test parse_cp2k_out"""
    with open(f"{THISDIR}/outputs/cdft_dos_cp2k_6.0.out") as fobj:
        lines = fobj.read()
        result_dict = parse_cp2k_output(lines)
        assert result_dict["energy"] == -1544.475602321840825
        assert result_dict["energy_units"] == "a.u."
        assert result_dict["nwarnings"] == 1


def test_cp2k_output_advanced():
    """Test parse_cp2k_advanced output"""
    with open(f"{THISDIR}/outputs/cdft_dos_cp2k_6.0.out") as fobj:
        lines = fobj.read()
        result_dict = parse_cp2k_output_advanced(lines)
        assert result_dict["cp2k_version"] == 6.0
        assert result_dict["energy_scf"] == -1544.47560232184082
        assert result_dict["nwarnings"] == 1
        assert result_dict["run_type"] == "ENERGY"
        assert result_dict["dft_type"] == "UKS"
        assert result_dict["integrated_abs_spin_dens"] == 6.4548954029
        assert result_dict["spin_square_ideal"] == 0.750000
        assert result_dict["spin_square_expectation"] == 2.827411
        assert result_dict["init_nel_spin1"] == 358
        assert result_dict["init_nel_spin2"] == 357
        assert result_dict["natoms"] == 194


def test_trajectory_parser_pbc():
    """Test parsing of boundary conditions from the restart-file"""
    files = [
        "PBC_output_xyz.restart",
        "PBC_output_xz.restart",
        "PBC_output_none.restart",
    ]
    boundary_conditions = [
        [True, True, True],
        [True, False, True],
        [False, False, False],
    ]

    for file, boundary_cond in zip(files, boundary_conditions):
        with open(f"{THISDIR}/outputs/{file}") as fobj:
            content = fobj.read()
            structure_data = parse_cp2k_trajectory(content)

            assert structure_data["pbc"] == boundary_cond
