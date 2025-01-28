###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K input plugin."""

import math
import re

import numpy as np


def parse_cp2k_output(fstring):
    """Parse CP2K output into a dictionary."""
    lines = fstring.splitlines()

    result_dict = {"exceeded_walltime": False}

    for line in lines:
        if line.startswith(" ENERGY| "):
            result_dict["energy"] = float(line.split()[8])
            result_dict["energy_units"] = "a.u."
        if "The number of warnings for this run is" in line:
            result_dict["nwarnings"] = int(line.split()[-1])

    return result_dict


def parse_cp2k_output_advanced(
    fstring,
):
    """Parse CP2K output into a dictionary (ADVANCED: more info parsed @ PRINT_LEVEL MEDIUM)."""
    lines = fstring.splitlines()

    result_dict = {"exceeded_walltime": False}
    result_dict["warnings"] = []
    line_is = None
    energy = None
    bohr2ang = 0.529177208590000

    for i_line, line in enumerate(lines):
        if line.startswith(" CP2K| version string:"):
            cp2k_version = float(line.split()[5])
            result_dict["cp2k_version"] = cp2k_version
        if line.startswith(" ENERGY| "):
            energy = float(line.split()[8])
            result_dict["energy"] = energy
            result_dict["energy_units"] = "a.u."
        if line.strip().startswith("Total energy: "):
            # In case of constrained geo opt, "ENERGY| ..." also contains the constraint energy
            # This only contains the electronic SCF energy
            energy_scf = float(line.split()[2])
            result_dict["energy_scf"] = energy_scf
        if "The number of warnings for this run is" in line:
            result_dict["nwarnings"] = int(line.split()[-1])
        if "KPOINTS| Band Structure Calculation" in line:
            kpoints, labels, bands = _parse_bands(lines, i_line, cp2k_version)
            result_dict["kpoint_data"] = {
                "kpoints": kpoints,
                "labels": labels,
                "bands": bands,
                "bands_unit": "eV",
            }
        if line.startswith(" GLOBAL| Run type"):
            result_dict["run_type"] = line.split()[-1]

        if line.startswith(" MD| Ensemble Type"):
            result_dict["run_type"] += "-"
            result_dict["run_type"] += line.split()[-1]  # e.g., 'MD-NPT_F'

        if line.startswith(" DFT| ") and "dft_type" not in result_dict.keys():
            result_dict["dft_type"] = line.split()[-1]  # RKS, UKS or ROKS

        if line.strip().startswith("Integrated absolute spin density"):
            if "integrated_abs_spin_dens" not in result_dict:
                result_dict["integrated_abs_spin_dens"] = []
            result_dict["integrated_abs_spin_dens"].append(float(line.split()[-1]))

        if line.strip().startswith("Ideal and single determinant"):
            s2_ideal, s2_expect = line.split()[-2:]
            if "spin_square_ideal" not in result_dict:
                result_dict["spin_square_ideal"] = float(s2_ideal)
            if "spin_square_expectation" not in result_dict:
                result_dict["spin_square_expectation"] = []
            result_dict["spin_square_expectation"].append(float(s2_expect))

        # Read the number of electrons in the first scf (NOTE: it may change but it is not updated!)
        if re.search("Number of electrons: ", line):
            if "init_nel_spin1" not in result_dict.keys():
                result_dict["init_nel_spin1"] = int(line.split()[3])
                if result_dict["dft_type"] == "RKS":
                    result_dict["init_nel_spin1"] //= 2  # // returns an integer
                    result_dict["init_nel_spin2"] = result_dict["init_nel_spin1"]
            elif "init_nel_spin2" not in result_dict.keys():
                result_dict["init_nel_spin2"] = int(line.split()[3])

        if re.search("- Atoms: ", line):
            result_dict["natoms"] = int(line.split()[-1])

        if re.search("Smear method", line):
            result_dict["smear_method"] = line.split()[-1]

        # Parse warnings
        if re.search(r"Using a non-square number of", line):
            result_dict["warnings"].append("Using a non-square number of MPI ranks")
        if re.search(r"SCF run NOT converged", line):
            warn = "One or more SCF run did not converge"
            if warn not in result_dict["warnings"]:
                result_dict["warnings"].append(warn)
        if re.search(r"Specific L-BFGS convergence criteria", line):
            result_dict["warnings"].append("LBFGS converged with specific criteria")

        # Parse eigenvalues.
        if "subspace spin" in line and "owest" not in line:
            if int(line.split()[-1]) == 1:
                line_is = "eigen_spin1_au"
                result_dict["eigen_spin1_au"] = []
            elif int(line.split()[-1]) == 2:
                line_is = "eigen_spin2_au"
                result_dict["eigen_spin2_au"] = []
            continue

        # If a tag has been detected, now read the following line knowing what they are
        if line_is in ["eigen_spin1_au", "eigen_spin2_au"]:
            if "------" in line or "*** WARNING" in line:
                continue
            splitted_line = line.split()
            try:
                result_dict[line_is] += [float(x) for x in splitted_line]
            except ValueError:
                line_is = None

        ####################################################################
        #  THIS SECTION PARSES THE PROPERTIES AT GOE_OPT/CELL_OPT/MD STEP  #
        #  BC: it can be not robust!                                         #
        ####################################################################
        if "run_type" in result_dict.keys() and result_dict["run_type"] in [
            "ENERGY",
            "ENERGY_FORCE",
            "GEO_OPT",
            "CELL_OPT",
            "MD",
            "MD-NVT",
            "MD-NPT_F",
        ]:
            # Initialization
            if "motion_step_info" not in result_dict:
                result_dict["motion_opt_converged"] = False
                result_dict["motion_step_info"] = {
                    "step": [],  # MOTION step
                    "energy_au": [],  # total energy
                    "dispersion_energy_au": [],  # Dispersion energy (if dispersion correction activated)
                    "pressure_bar": [],  # Total pressure on the cell
                    "cell_vol_angs3": [],  # Cell Volume
                    "cell_a_angs": [],  # Cell dimension A
                    "cell_b_angs": [],  # Cell dimension B
                    "cell_c_angs": [],  # Cell dimension C
                    "cell_alp_deg": [],  # Cell angle Alpha
                    "cell_bet_deg": [],  # Cell angle Beta
                    "cell_gam_deg": [],  # Cell angle Gamma
                    "max_step_au": [],  # Max atomic displacement (in optimization)
                    "rms_step_au": [],  # RMS atomic displacement (in optimization)
                    "max_grad_au": [],  # Max atomic force (in optimization)
                    "rms_grad_au": [],  # RMS atomic force (in optimization)
                    "edens_rspace": [],  # Total charge density on r-space grids (should stay small)
                    "scf_converged": [],  # SCF converged in this motions step (bool)
                }
                step = 0
                energy = None
                dispersion = None  # Needed if no dispersions are included
                pressure = None
                max_step = None
                rms_step = None
                max_grad = None
                rms_grad = None
                edens_rspace = None
                scf_converged = True

            dump_step_info = False
            data = line.split()
            # Parse general info
            if line.startswith(" CELL|"):
                if re.search(r"Volume", line):
                    cell_vol = float(data[3])
                if re.search(r"Vector a", line):
                    cell_a = float(data[9])
                if re.search(r"Vector b", line):
                    cell_b = float(data[9])
                if re.search(r"Vector c", line):
                    cell_c = float(data[9])
                if re.search(r"alpha", line):
                    cell_alp = float(data[5])
                if re.search(r"beta", line):
                    cell_bet = float(data[5])
                if re.search(r"gamma", line):
                    cell_gam = float(data[5])

            if re.search(r"Dispersion energy", line):
                dispersion = float(data[2])
            if re.search("Total charge density on r-space grids:", line):
                # Printed at every outer OT, and needed for understanding if something is going wrong (if !=0)
                edens_rspace = float(line.split()[-1])
            if re.search(r"SCF run NOT converged", line):
                scf_converged = False

            # Parse specific info
            if result_dict["run_type"] in ["ENERGY", "ENERGY_FORCE"]:
                if energy is not None and not result_dict["motion_step_info"]["step"]:
                    dump_step_info = True
            if result_dict["run_type"] in ["GEO_OPT", "CELL_OPT"]:
                # Note: with CELL_OPT/LBFGS there is no "STEP 0", while there is with CELL_OPT/BFGS

                # Getting the step number.
                if re.search(r"Informations at step", line):
                    step = int(data[5])
                elif re.search(
                    r"OPT\| Step number ", line
                ):  # Fix for new CP2K versions.
                    step = int(data[-1])

                # Getting the maximum step size.
                if re.search(
                    r"OPT\| Maximum step size\s*[-+]?\d*\.?\d+", line
                ) or re.search(r"Max. step size\s+=", line):
                    max_step = float(data[-1])

                # Getting the RMS step size.
                if re.search(
                    r"OPT\| RMS step size\s*[-+]?\d*\.?\d+", line
                ) or re.search(r"RMS step size\s+=", line):
                    rms_step = float(data[-1])

                # Getting the maximum gradient.
                if re.search(
                    r"OPT\| Maximum gradient\s*[-+]?\d*\.?\d+", line
                ) or re.search(r"Max. gradient\s+=", line):
                    max_grad = float(data[-1])

                # Getting the RMS gradient.
                if re.search(
                    r"OPT\| RMS gradient\s*[-+]?\d*\.?\d+",
                    line,
                ) or re.search(r"RMS gradient\s{3,}=", line):
                    rms_grad = float(data[-1])

                if (
                    len(data) == 1
                    and data[0] == "---------------------------------------------------"
                ) or re.search(r"OPT\| Estimated peak process memory", line):
                    dump_step_info = True  # 51('-')
                if re.search(
                    r"Reevaluating energy at the minimum", line
                ):  # not clear why it is doing a last one...
                    result_dict["motion_opt_converged"] = True

            if result_dict["run_type"] == "CELL_OPT":
                if re.search(r"Internal Pressure", line):
                    pressure = float(data[4])
            if result_dict["run_type"] == "MD-NVT":
                if re.search(r"STEP NUMBER", line):
                    step = int(data[3])
                if re.search(r"INITIAL PRESSURE\[bar\]", line):
                    pressure = float(data[3])
                    dump_step_info = True
                if re.search(r"PRESSURE \[bar\]", line):
                    pressure = float(data[3])
                    dump_step_info = True
            if result_dict["run_type"] == "MD-NPT_F":
                if re.search(r"^ STEP NUMBER", line):
                    step = int(data[3])
                if re.search(r"^ INITIAL PRESSURE\[bar\]", line):
                    pressure = float(data[3])
                    dump_step_info = True
                if re.search(r"^ PRESSURE \[bar\]", line):
                    pressure = float(data[3])
                if re.search(r"^ VOLUME\[bohr\^3\]", line):
                    cell_vol = float(data[3]) * (bohr2ang**3)
                if re.search(r"^ CELL LNTHS\[bohr\]", line):
                    cell_a = float(data[3]) * bohr2ang
                    cell_b = float(data[4]) * bohr2ang
                    cell_c = float(data[5]) * bohr2ang
                if re.search(r"^ CELL ANGLS\[deg\]", line):
                    cell_alp = float(data[3])
                    cell_bet = float(data[4])
                    cell_gam = float(data[5])
                    dump_step_info = True

            if dump_step_info and energy is not None:
                result_dict["motion_step_info"]["step"].append(step)
                result_dict["motion_step_info"]["energy_au"].append(energy)
                result_dict["motion_step_info"]["dispersion_energy_au"].append(
                    dispersion
                )
                result_dict["motion_step_info"]["pressure_bar"].append(pressure)
                result_dict["motion_step_info"]["cell_vol_angs3"].append(cell_vol)
                result_dict["motion_step_info"]["cell_a_angs"].append(cell_a)
                result_dict["motion_step_info"]["cell_b_angs"].append(cell_b)
                result_dict["motion_step_info"]["cell_c_angs"].append(cell_c)
                result_dict["motion_step_info"]["cell_alp_deg"].append(cell_alp)
                result_dict["motion_step_info"]["cell_bet_deg"].append(cell_bet)
                result_dict["motion_step_info"]["cell_gam_deg"].append(cell_gam)
                result_dict["motion_step_info"]["max_step_au"].append(max_step)
                result_dict["motion_step_info"]["rms_step_au"].append(rms_step)
                result_dict["motion_step_info"]["max_grad_au"].append(max_grad)
                result_dict["motion_step_info"]["rms_grad_au"].append(rms_grad)
                result_dict["motion_step_info"]["edens_rspace"].append(edens_rspace)
                result_dict["motion_step_info"]["scf_converged"].append(scf_converged)
                scf_converged = True
        ####################################################################
        #  END PARSING GEO_OPT/CELL_OPT/MD STEP                            #
        ####################################################################

    return result_dict


def _parse_kpoint_cp2k_lower_81(lines, line_n):
    """Parse one k-point in the output of CP2K <8.1"""

    splitted = lines[line_n].split()
    spin = int(splitted[3])
    kpoint = tuple(float(p) for p in splitted[-3:])
    nlines = int(math.ceil(int(lines[line_n + 1]) / 4))
    bands = [
        float(v) for v in " ".join(lines[line_n + 2 : line_n + 2 + nlines]).split()
    ]
    return spin, kpoint, bands


def _parse_bands_cp2k_greater_81(lines, line_n):
    """Parse one k-point in the output of CP2K >=8.1"""

    splitted = lines[line_n].split()
    assert (
        splitted[1] == "Point" and splitted[3] == "Spin"
    ), "Did not find required keywords in kpoint line"
    spin = int(splitted[4][:-1])  # strip the ':'
    kpoint = tuple(float(p) for p in splitted[5:8])  # ignore optional weight
    bands = []
    for line in lines[line_n + 2 :]:
        try:
            bands.append(float(line.split()[1]))
        except ValueError:
            break
    return spin, kpoint, bands


def _parse_bands(lines, n_start, cp2k_version):
    """Parse band structure from the CP2K output."""

    kpoints = []
    labels = []
    bands_s1 = []
    bands_s2 = []
    known_kpoints = {}

    if cp2k_version < 8.1:
        parse_one_kpoint = _parse_kpoint_cp2k_lower_81
        pattern = re.compile(r".*?Nr.*?Spin.*?K-Point.*?", re.DOTALL)
        unspecified = ["not", "specified"]
    else:
        parse_one_kpoint = _parse_bands_cp2k_greater_81
        pattern = re.compile(r".*?Point.*?Spin.*?", re.DOTALL)
        unspecified = ["not", "specifi"]

    selected_lines = lines[n_start:]
    for line_n, line in enumerate(selected_lines):
        if "KPOINTS| Special" in line:
            splitted = line.split()
            kpoint = tuple(float(p) for p in splitted[-3:])
            if splitted[-5:-3] != unspecified:
                label = splitted[-4]
                known_kpoints[kpoint] = label

        elif pattern.match(line):
            spin, kpoint, bands = parse_one_kpoint(selected_lines, line_n)

            # When doing a path Γ-X-K, CP2K does Γ-X, X-K and we would
            # end up with repeated points in the path. If we already have
            # kpoints in the the list and we got exactly the same KP again,
            # skip adding the kpoint, the label and the bands.
            if kpoints and (kpoints[-1] == kpoint):
                continue

            if spin == 1:
                if kpoint in known_kpoints:
                    labels.append((len(kpoints), known_kpoints[kpoint]))
                kpoints.append(kpoint)
                bands_s1.append(bands)
            elif spin == 2:
                bands_s2.append(bands)

    if bands_s2:
        bands = [bands_s1, bands_s2]
    else:
        bands = bands_s1

    return np.array(kpoints), labels, np.array(bands)


def parse_cp2k_trajectory(content):
    """CP2K trajectory parser."""
    # Parse coordinate section
    match = re.search(r"\n\s*&COORD\n(.*?)\n\s*&END COORD\n", content, re.DOTALL)
    coord_lines = [line.strip().split() for line in match.group(1).splitlines()]

    # splitting element name and the tag (if present)
    symbols = []
    tags = []
    for atomic_kind in [line[0] for line in coord_lines]:
        symbols.append("".join([s for s in atomic_kind if not s.isdigit()]))
        try:
            tag = int("".join([s for s in atomic_kind if s.isdigit()]))
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

    # parse periodic boundary conditions
    cell_pbc = [True, True, True]  # In case keyword is not set: Default in cp2k is XYZ
    for line in cell_lines:
        if line[0] == "PERIODIC":
            cell_pbc_str = line[-1]
            cell_pbc = [(dir in cell_pbc_str) for dir in ["X", "Y", "Z"]]

    return {
        "symbols": symbols,
        "positions": positions,
        "cell": cell,
        "tags": tags,
        "pbc": cell_pbc,
    }
