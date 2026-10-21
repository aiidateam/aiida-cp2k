###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test output parser."""

from pathlib import Path

import pytest

from aiida_cp2k.parsers import _update_bandgaps
from aiida_cp2k.utils import HARTREE2EV, ot_has_small_bandgap
from aiida_cp2k.utils.parser import (
    _parse_bands,
    parse_cp2k_output,
    parse_cp2k_output_advanced,
    parse_cp2k_trajectory,
)

THIS_DIR = Path(__file__).parent.resolve()
OUTPUTS_DIR = THIS_DIR / "outputs"


def dict_is_subset(a, b):
    return a.items() <= b.items()


def _parse_output(output):
    """Parse CP2K output and derive bandgaps, as Cp2kAdvancedParser does."""
    parsed_dict = parse_cp2k_output_advanced(output)
    _update_bandgaps(parsed_dict)
    return parsed_dict


def _parse_truncated(output_file, marker):
    """Parse the full output and the output cut at ``marker`` in its final MO group."""
    output = (OUTPUTS_DIR / output_file).read_text()
    final_group = output.rindex(
        "  Eigenvalues of the occupied subspace spin            1"
    )
    stop = output.index(marker, final_group)
    return _parse_output(output), _parse_output(output[:stop])


@pytest.mark.parametrize(
    "output_file, cp2k_version",
    [
        ("BANDS_output_v5.1.out", 5.1),
        ("BANDS_output_v8.1.out", 8.1),
    ],
)
def test_bands_parser(output_file, cp2k_version):
    with open(OUTPUTS_DIR / output_file) as fobj:
        lines = fobj.readlines()
        for i_line, line in enumerate(lines):
            if "KPOINTS| Band Structure Calculation" in line:
                kpoints, labels, bands = _parse_bands(lines, i_line, cp2k_version)

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


cdft_dos_cp2k_6_0_out_result = {
    "exceeded_walltime": False,
    "energy": -1544.4756023218408,
    "energy_units": "a.u.",
    "nwarnings": 1,
}
ot_v9_1_out_result = {
    "exceeded_walltime": False,
    "energy": -26352.215747926548,
    "energy_units": "a.u.",
    "nwarnings": 1,
}

bands_output_v5_1_result = {
    "exceeded_walltime": False,
    "energy": -7.944253454494698,
    "energy_units": "a.u.",
    "nwarnings": 3,
}

bands_output_v8_1_result = {
    "exceeded_walltime": False,
    "energy": -7.944253454478329,
    "energy_units": "a.u.",
    "nwarnings": 3,
}

bsse_output_v5_1_result = {"exceeded_walltime": False, "nwarnings": 0}


@pytest.mark.parametrize(
    "output_file, reference_dict",
    [
        ("BANDS_output_v5.1.out", bands_output_v5_1_result),
        ("BANDS_output_v8.1.out", bands_output_v8_1_result),
        ("BSSE_output_v5.1_.out", bsse_output_v5_1_result),
        ("cdft_dos_cp2k_6.0.out", cdft_dos_cp2k_6_0_out_result),
        ("OT_v9.1.out", ot_v9_1_out_result),
    ],
)
def test_cp2k_output_parser(output_file, reference_dict):
    with open(OUTPUTS_DIR / output_file) as fobj:
        lines = fobj.read()
        parsed_dict = parse_cp2k_output(lines)
        assert dict_is_subset(reference_dict, parsed_dict)


bands_output_v5_1_out_advanced_result = {
    "exceeded_walltime": False,
    "warnings": [],
    "cp2k_version": 5.1,
    "run_type": "ENERGY_FORCE",
    "motion_opt_converged": False,
    "motion_step_info": {
        "step": [0],
        "energy_au": [-7.944253454494698],
        "dispersion_energy_au": [None],
        "pressure_bar": [None],
        "cell_vol_angs3": [39.168],
        "cell_a_angs": [3.812],
        "cell_b_angs": [3.812],
        "cell_c_angs": [3.812],
        "cell_alp_deg": [60.0],
        "cell_bet_deg": [60.0],
        "cell_gam_deg": [60.0],
        "max_step_au": [None],
        "rms_step_au": [None],
        "max_grad_au": [None],
        "rms_grad_au": [None],
        "edens_rspace": [-1.4e-09],
        "scf_converged": [True],
    },
    "dft_type": "RKS",
    "natoms": 2,
    "smear_method": "FERMI_DIRAC",
    "init_nel_spin1": 4,
    "init_nel_spin2": 4,
    "energy_scf": -7.94319983408946,
    "energy": -7.944253454494698,
    "energy_units": "a.u.",
    "nwarnings": 3,
}

bands_output_v8_1_out_advanced_result = {
    "exceeded_walltime": False,
    "warnings": [],
    "cp2k_version": 8.1,
    "run_type": "ENERGY_FORCE",
    "motion_opt_converged": False,
    "motion_step_info": {
        "step": [0],
        "energy_au": [-7.944253454478329],
        "dispersion_energy_au": [None],
        "pressure_bar": [None],
        "cell_vol_angs3": [39.167875],
        "cell_a_angs": [3.81196],
        "cell_b_angs": [3.81196],
        "cell_c_angs": [3.81196],
        "cell_alp_deg": [60.0],
        "cell_bet_deg": [60.0],
        "cell_gam_deg": [60.0],
        "max_step_au": [None],
        "rms_step_au": [None],
        "max_grad_au": [None],
        "rms_grad_au": [None],
        "edens_rspace": [-1.5e-09],
        "scf_converged": [True],
    },
    "dft_type": "RKS",
    "natoms": 2,
    "smear_method": "FERMI_DIRAC",
    "init_nel_spin1": 4,
    "init_nel_spin2": 4,
    "energy_scf": -7.94319983402503,
    "energy": -7.944253454478329,
    "energy_units": "a.u.",
    "nwarnings": 3,
}

bsse_output_v5_1_out_advanced_result = {
    "exceeded_walltime": False,
    "warnings": [],
    "cp2k_version": 5.1,
    "run_type": "BSSE",
    "dft_type": "RKS",
    "natoms": 57,
    "init_nel_spin1": 141,
    "init_nel_spin2": 141,
    "energy_scf": -829.920698393915,
    # fmt: off
    "eigen_spin1_au": [
        -0.95359553, -0.91782227, -0.89011546, -0.88868094, -0.88549967, -0.88476466,
        -0.88416513, -0.88293638, -0.81576984, -0.8141112, -0.81399583, -0.81337999,
        -0.81205513, -0.81028306, -0.80101859, -0.80005959, -0.79971661, -0.79930587,
        -0.79840654, -0.79715039, -0.66220742, -0.65904684, -0.65776805, -0.59353184,
        -0.590447, -0.58921609, -0.54502325, -0.54023207, -0.53850651, -0.5001599,
        -0.4977, -0.49672543, -0.43873289, -0.43357481, -0.43173812, -0.43020343,
        -0.42320365, -0.42209191, -0.41877289, -0.4011139, -0.39787331, -0.39705241,
        -0.37338147, -0.37271964, -0.37227202, -0.37166414, -0.36898809, -0.3674872,
        -0.35702189, -0.35344988, -0.34995372, -0.34818092, -0.34638496, -0.34604289,
        -0.3455695, -0.34404292, -0.34250157, -0.33256782, -0.32758872, -0.32700531,
        -0.32071981, -0.31966953, -0.31654777, -0.30546259, -0.30502971, -0.30412345,
        -0.30313432, -0.29797487, -0.29745766, -0.29649641, -0.29495845, -0.29026869,
        -0.28936038, -0.28906975, -0.28783981, -0.28585149, -0.28529142, -0.28097825,
        -0.28037927, -0.27975634, -0.27896849, -0.27749085, -0.27485524, -0.27302662,
        -0.27245722, -0.27146719, -0.27089753, -0.26974259, -0.26877211, -0.26815236,
        -0.26728563, -0.26699091, -0.26524061, -0.26470812, -0.26396882, -0.26064591,
        -0.25885332, -0.25725706, -0.25560909, -0.25345166, -0.25284547, -0.24907573,
        -0.24873875, -0.2397483, -0.23637516, -0.23141455, -0.23082165, -0.22994444,
        -0.22742208, -0.22611678, -0.22376326, -0.21819019, -0.21713555, -0.21493914,
        -0.20937062, -0.20821483, -0.19604117, -0.18710574, -0.18570717, -0.18454341,
        -0.18141092, -0.18120769, -0.16895353, -0.1682233, -0.16213668, -0.16131245,
        -0.15811887, -0.15716976, -0.15337408, -0.15287082, -0.15211266, -0.15185745,
        -0.15142035, -0.1440524, -0.1386434, -0.13835902, -0.13555331, -0.12708042,
        -0.12399982, -0.12260058, -0.12020082, -0.11778906, -0.11701972, -0.11257783,
        -0.10711341, -0.10600515, -0.07548463, -0.07331737, -0.06796769
        ],
    # fmt: on
    "nwarnings": 0,
}


cdft_dos_cp2k_6_0_out_advanced_result = {
    "cp2k_version": 6.0,
    "energy_scf": -1544.47560232184082,
    "nwarnings": 1,
    "run_type": "ENERGY",
    "dft_type": "UKS",
    "integrated_abs_spin_dens": [6.4548954029],
    "spin_square_ideal": 0.750000,
    "spin_square_expectation": [2.827411],
    "init_nel_spin1": 358,
    "init_nel_spin2": 357,
    "natoms": 194,
}

ot_v9_1_out_advanced_result = {
    "exceeded_walltime": False,
    "warnings": [],
    "cp2k_version": 9.1,
    "run_type": "ENERGY",
    "motion_opt_converged": False,
    "motion_step_info": {
        "step": [0],
        "energy_au": [-26352.215747926548],
        "dispersion_energy_au": [None],
        "pressure_bar": [None],
        "cell_vol_angs3": [69533.840649],
        "cell_a_angs": [35.375987],
        "cell_b_angs": [40.848671],
        "cell_c_angs": [48.118239],
        "cell_alp_deg": [90.0],
        "cell_bet_deg": [90.0],
        "cell_gam_deg": [90.0],
        "max_step_au": [None],
        "rms_step_au": [None],
        "max_grad_au": [None],
        "rms_grad_au": [None],
        "edens_rspace": [-2e-10],
        "scf_converged": [True],
    },
    "dft_type": "RKS",
    "natoms": 1101,
    "init_nel_spin1": 4560,
    "init_nel_spin2": 4560,
    "energy_scf": -26352.215747926548,
    "energy": -26352.215747926548,
    "energy_units": "a.u.",
    "nwarnings": 1,
}


geo_opt_v9_1_out_advanced_result = {
    "exceeded_walltime": False,
    "cp2k_version": 9.1,
    "run_type": "GEO_OPT",
    "motion_opt_converged": True,
    "motion_step_info": {
        "step": [0, 1, 2, 3],
        "energy_au": [
            -13.725689111701854,
            -13.726149722666982,
            -13.726193267757822,
            -13.726193434870883,
        ],
        "dispersion_energy_au": [
            -0.00046165125791,
            -0.00046785269957,
            -0.000470377617,
            -0.00047049995296,
        ],
        "pressure_bar": [None, None, None, None],
        "cell_vol_angs3": [1475.364128, 1475.364128, 1475.364128, 1475.364128],
        "cell_a_angs": [12.424154, 12.424154, 12.424154, 12.424154],
        "cell_b_angs": [11.874962, 11.874962, 11.874962, 11.874962],
        "cell_c_angs": [10.000004, 10.000004, 10.000004, 10.000004],
        "cell_alp_deg": [90.0, 90.0, 90.0, 90.0],
        "cell_bet_deg": [90.0, 90.0, 90.0, 90.0],
        "cell_gam_deg": [90.0, 90.0, 90.0, 90.0],
        "max_step_au": [None, 0.0376199092, 0.0155526726, 0.0003463701],
        "rms_step_au": [None, 0.0189431999, 0.0076510487, 0.000182772],
        "max_grad_au": [None, 0.0015528294, 0.0003036618, 7.28782e-05],
        "rms_grad_au": [None, 0.0007719361, 0.000107814, 2.58819e-05],
        "edens_rspace": [-0.0, -0.0, -0.0, -0.0],
        "scf_converged": [True, True, True, True],
    },
}

geo_opt_v2024_3_out_advanced_result = {
    "exceeded_walltime": False,
    "cp2k_version": 2024.3,
    "run_type": "GEO_OPT",
    "motion_opt_converged": True,
    "motion_step_info": {
        "step": [0, 1, 2, 3],
        "energy_au": [
            -13.725689111701852,
            -13.726149722666458,
            -13.726193267757864,
            -13.726193434870929,
        ],
        "dispersion_energy_au": [
            -0.00046165125791,
            -0.00046785269954,
            -0.00047037761701,
            -0.00047049995297,
        ],
        "pressure_bar": [None, None, None, None],
        "cell_vol_angs3": [1475.364128, 1475.364128, 1475.364128, 1475.364128],
        "cell_a_angs": [12.424154, 12.424154, 12.424154, 12.424154],
        "cell_b_angs": [11.874962, 11.874962, 11.874962, 11.874962],
        "cell_c_angs": [10.000004, 10.000004, 10.000004, 10.000004],
        "cell_alp_deg": [90.0, 90.0, 90.0, 90.0],
        "cell_bet_deg": [90.0, 90.0, 90.0, 90.0],
        "cell_gam_deg": [90.0, 90.0, 90.0, 90.0],
        "max_step_au": [None, 0.037619909, 0.0155526727, 0.0003463702],
        "rms_step_au": [None, 0.0189431999, 0.0076510488, 0.000182772],
        "max_grad_au": [None, 0.0015528293, 0.0003036619, 7.28784e-05],
        "rms_grad_au": [None, 0.0007719361, 0.000107814, 2.58819e-05],
        "edens_rspace": [-0.0, -0.0, -0.0, -0.0],
        "scf_converged": [True, True, True, True],
    },
}


@pytest.mark.parametrize(
    "output_file, reference_dict",
    [
        ("BANDS_output_v5.1.out", bands_output_v5_1_out_advanced_result),
        ("BANDS_output_v8.1.out", bands_output_v8_1_out_advanced_result),
        ("BSSE_output_v5.1_.out", bsse_output_v5_1_out_advanced_result),
        ("cdft_dos_cp2k_6.0.out", cdft_dos_cp2k_6_0_out_advanced_result),
        ("OT_v9.1.out", ot_v9_1_out_advanced_result),
        ("GEO_OPT_v9.1.out", geo_opt_v9_1_out_advanced_result),
        ("GEO_OPT_v2024.3.out", geo_opt_v2024_3_out_advanced_result),
    ],
)
def test_cp2k_output_advanced(output_file, reference_dict):
    """Test parse_cp2k_advanced output"""
    with open(OUTPUTS_DIR / output_file) as fobj:
        lines = fobj.read()
        parsed_dict = parse_cp2k_output_advanced(lines)
        assert dict_is_subset(reference_dict, parsed_dict)


@pytest.mark.parametrize(
    "output_file, gaps_ev, frontiers_au, n_gap_warnings",
    [
        ("OT_v9.1.out", [0.009679, 0.009679], [(-0.06436553, -0.06400983)], 0),
        (
            "OT_UKS_with_warnings.out",
            [2.811670, 2.798202],
            [(-0.11270121, -0.00937424), (-0.17710200, -0.07426995)],
            0,
        ),
        (
            "OT_RKS_multiple_steps.out",
            [11.791197, 11.791197],
            [(-0.34398766, 0.08933089)],
            0,
        ),
        (
            "OT_UKS_multiple_steps.out",
            [9.586630, 9.049087],
            [(-0.19515752, 0.15714467), (-0.42953873, -0.09699089)],
            0,
        ),
        # BSSE fragments have 282, 16 and 298 electrons, but init_nel comes from
        # the first one, so only the printed gap describes the final group.
        ("BSSE_output_v5.1_.out", [2.183774, 2.183774], [], 2),
        (
            "GEO_OPT_v2024.3.out",
            [5.770362, 5.770362],
            [(-0.24103549, -0.02897857)],
            0,
        ),
        ("GEO_OPT_v9.1.out", [5.770362, 5.770362], [(-0.24103549, -0.02897857)], 0),
        (
            "cdft_dos_cp2k_6.0.out",
            [1.729910, 0.731308],
            [(-0.07246038, -0.00888736), (-0.07243564, -0.04556056)],
            0,
        ),
        (
            "tddft_cp2k_6.0.out",
            [3.248614, 3.254121],
            [(-0.22006268, -0.10067832), (-0.21991109, -0.10032433)],
            0,
        ),
    ],
)
def test_reference_outputs_bandgaps(output_file, gaps_ev, frontiers_au, n_gap_warnings):
    """Frontier orbitals and gaps come from the final MO group of each output."""
    parsed_dict = _parse_output((OUTPUTS_DIR / output_file).read_text())

    # Gap numbering restarts in every MO group; RKS mirrors spin 1 to spin 2.
    assert {key for key in parsed_dict if key.startswith("printed_bandgap_")} == {
        "printed_bandgap_spin1_ev",
        "printed_bandgap_spin2_ev",
    }
    for spin, gap_ev in enumerate(gaps_ev, start=1):
        assert parsed_dict[f"printed_bandgap_spin{spin}_ev"] == pytest.approx(gap_ev)
        bandgap_ev = parsed_dict[f"bandgap_spin{spin}_au"] * HARTREE2EV
        assert bandgap_ev == pytest.approx(gap_ev)
    for spin, (homo, lumo) in enumerate(frontiers_au, start=1):
        assert parsed_dict[f"eigenvalue_homo_spin{spin}_au"] == pytest.approx(homo)
        assert parsed_dict[f"eigenvalue_lumo_spin{spin}_au"] == pytest.approx(lumo)
    gap_warnings = [
        warning
        for warning in parsed_dict["warnings"]
        if "differs from CP2K printed gap" in warning
    ]
    assert len(gap_warnings) == n_gap_warnings


@pytest.mark.parametrize(
    "electron_counts",
    [{}, {"init_nel_spin1": 0}],
    ids=["no_electron_count", "zero_electrons"],
)
def test_update_bandgaps_without_usable_electron_count(electron_counts):
    """Without a usable electron count, only the printed gap is reported."""
    result_dict = {
        "warnings": [],
        "dft_type": "UKS",
        "eigen_spin1_au": [-0.3, -0.2],
        "unoccupied_eigen_spin1_au": [0.1],
        "printed_bandgap_spin1_ev": 8.0,
        **electron_counts,
    }
    _update_bandgaps(result_dict)

    assert result_dict["bandgap_spin1_au"] * HARTREE2EV == pytest.approx(8.0)
    assert not any(key.startswith("eigenvalue_") for key in result_dict)
    assert result_dict["warnings"] == []


def test_update_bandgaps_warns_when_printed_gap_differs():
    """Test non-fatal warning for distinct printed and eigenvalue gaps."""

    result_dict = {
        "warnings": [],
        "dft_type": "UKS",
        "init_nel_spin1": 3,
        "eigen_spin1_au": [-4.1, -3.8, -2.0, -1.6, -1.5],
        "unoccupied_eigen_spin1_au": [-1.3, -1.0],
        "printed_bandgap_spin1_ev": 0.2 * HARTREE2EV,
    }
    _update_bandgaps(result_dict)

    assert result_dict["bandgap_spin1_au"] == pytest.approx(0.2)
    assert result_dict["eigenvalue_homo_spin1_au"] == pytest.approx(-2.0)
    assert result_dict["eigenvalue_lumo_spin1_au"] == pytest.approx(-1.6)
    assert result_dict["eigenvalue_bandgap_spin1_au"] == pytest.approx(0.4)
    assert len(result_dict["warnings"]) == 1
    assert "differs from CP2K printed gap" in result_dict["warnings"][0]


@pytest.mark.parametrize(
    "output_file, marker",
    [
        ("OT_RKS_multiple_steps.out", "  Lowest Eigenvalues"),
        ("OT_UKS_multiple_steps.out", "  Lowest Eigenvalues"),
        (
            "OT_UKS_multiple_steps.out",
            "  Eigenvalues of the occupied subspace spin            2",
        ),
    ],
)
def test_ot_final_group_without_lumos_has_no_gaps(output_file, marker):
    """Output that stops before the final LUMOs must not reuse an earlier step."""
    full, parsed_dict = _parse_truncated(output_file, marker)

    assert "eigen_spin1_au" in parsed_dict
    for key in ("eigen_spin1_au", "eigen_spin2_au"):
        if key in parsed_dict:
            assert parsed_dict[key] == full[key]
    assert not any(
        key.startswith(
            ("unoccupied_eigen_", "printed_bandgap_", "bandgap_", "eigenvalue_")
        )
        for key in parsed_dict
    )


@pytest.mark.parametrize(
    "output_file, marker, printed_spins",
    [
        ("OT_RKS_multiple_steps.out", " HOMO - LUMO gap", []),
        ("OT_UKS_multiple_steps.out", " HOMO - LUMO gap", []),
        ("OT_UKS_multiple_steps.out", " HOMO - LUMO gap [eV] :    9.049087", [1]),
    ],
)
def test_ot_final_group_without_printed_gaps_uses_eigenvalues(
    output_file, marker, printed_spins
):
    """Missing gap lines fall back to the final group's eigenvalue gap."""
    full, parsed_dict = _parse_truncated(output_file, marker)

    assert {key for key in parsed_dict if key.startswith("printed_bandgap_")} == {
        f"printed_bandgap_spin{spin}_ev" for spin in printed_spins
    }
    for spin in (1, 2):
        if spin in printed_spins:
            expected = full[f"bandgap_spin{spin}_au"]
        else:
            expected = full[f"eigenvalue_bandgap_spin{spin}_au"]
        assert parsed_dict[f"bandgap_spin{spin}_au"] == pytest.approx(expected)
    assert parsed_dict["warnings"] == []


def test_ot_has_small_bandgap_with_and_without_lumo():
    """The OT small-gap check uses the parsed gap and tolerates its absence."""
    cp2k_input = {"FORCE_EVAL": {"DFT": {"SCF": {"OT": {}}}}}
    full, without_lumo = _parse_truncated(
        "OT_RKS_multiple_steps.out", "  Lowest Eigenvalues"
    )

    # Final printed gap is 11.791197 eV.
    assert ot_has_small_bandgap(cp2k_input, full, 12.0)
    assert not ot_has_small_bandgap(cp2k_input, full, 11.0)
    assert not ot_has_small_bandgap(cp2k_input, without_lumo, 12.0)


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
        with open(OUTPUTS_DIR / file) as fobj:
            content = fobj.read()
            structure_data = parse_cp2k_trajectory(content)
            assert structure_data["pbc"] == boundary_cond
