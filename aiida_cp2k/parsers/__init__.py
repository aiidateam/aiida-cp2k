###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K output parser."""

import re

import ase
import numpy as np
from aiida import common, engine, orm, parsers, plugins

from .. import utils

StructureData = plugins.DataFactory("core.structure")
BandsData = plugins.DataFactory("core.array.bands")


class Cp2kBaseParser(parsers.Parser):
    """Basic AiiDA parser for the output of CP2K."""

    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        self.SEVERE_ERRORS = [
            self.exit_codes.ERROR_OUTPUT_CONTAINS_ABORT,
        ]

        try:
            _ = self.retrieved
        except common.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        exit_code = self._parse_stdout()

        # Even though the simpulation might have failed, we still want to parse the output structure.
        last_structure = None
        try:
            last_structure = self._parse_final_structure()
            if isinstance(last_structure, StructureData):
                self.out("output_structure", last_structure)
        except common.NotExistent:
            self.logger.warning("No restart file found in the retrieved folder.")

        trajectory = None
        try:
            if last_structure is not None:
                trajectory = self._parse_trajectory(last_structure)
                if isinstance(trajectory, orm.TrajectoryData):
                    self.out("output_trajectory", trajectory)
        except common.NotExistent:
            self.logger.warning("No trajectory file found in the retrieved folder.")

        if exit_code is not None:
            return exit_code
        if isinstance(last_structure, engine.ExitCode):
            return last_structure
        if isinstance(trajectory, engine.ExitCode):
            return trajectory

        return engine.ExitCode(0)

    def _parse_stdout(self):
        """Basic CP2K output file parser."""

        # Read the standard output of CP2K.
        exit_code, output_string = self._read_stdout()
        if exit_code:
            return exit_code

        # Check the standard output for errors.
        exit_code = self._check_stdout_for_errors(output_string)

        # Return the error code if an error was severe enough to stop the parsing.
        if exit_code in self.SEVERE_ERRORS:
            return exit_code

        # Parse the standard output.
        result_dict = utils.parse_cp2k_output(output_string)
        self.out("output_parameters", orm.Dict(dict=result_dict))
        return exit_code

    def _parse_final_structure(self):
        """CP2K trajectory parser."""
        fname = self.node.process_class._DEFAULT_RESTART_FILE_NAME

        # Check if the restart file is present.
        if fname not in self.retrieved.base.repository.list_object_names():
            raise common.NotExistent(
                "No restart file available, so the output trajectory can't be extracted"
            )

        # Read the restart file.
        try:
            output_string = self.retrieved.base.repository.get_object_content(fname)
        except OSError:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ

        return StructureData(
            ase=ase.Atoms(**utils.parse_cp2k_trajectory(output_string))
        )

    def _check_stdout_for_errors(self, output_string):
        """This function checks the CP2K output file for some basic errors."""

        if "ABORT" in output_string:
            if (
                "SCF run NOT converged. To continue the calculation regardless"
                in output_string
            ):
                return self.exit_codes.ERROR_SCF_NOT_CONVERGED
            return self.exit_codes.ERROR_OUTPUT_CONTAINS_ABORT

        if "exceeded requested execution time" in output_string:
            return self.exit_codes.ERROR_OUT_OF_WALLTIME

        if "PROGRAM STOPPED IN" not in output_string:
            return self.exit_codes.ERROR_OUTPUT_INCOMPLETE

        if "MAXIMUM NUMBER OF OPTIMIZATION STEPS REACHED" in output_string:
            return self.exit_codes.ERROR_MAXIMUM_NUMBER_OPTIMIZATION_STEPS_REACHED

        return None

    def _read_stdout(self):
        """Read the standard output file. If impossible, return a non-zero exit code."""

        fname = self.node.base.attributes.get("output_filename")

        if fname not in self.retrieved.base.repository.list_object_names():
            return self.exit_codes.ERROR_OUTPUT_STDOUT_MISSING, None
        try:
            output_string = self.retrieved.base.repository.get_object_content(fname)
        except OSError:
            return self.exit_codes.ERROR_OUTPUT_READ, None

        return None, output_string

    def _parse_trajectory(self, structure):
        """CP2K trajectory parser."""

        symbols = [re.sub(r"\d+", "", str(site.kind_name)) for site in structure.sites]

        # Handle the positions trajectory
        xyz_traj_fname = self.node.process_class._DEFAULT_TRAJECT_XYZ_FILE_NAME

        # Read the trajectory file.
        try:
            output_xyz_pos = self.retrieved.base.repository.get_object_content(
                xyz_traj_fname
            )
        except OSError:
            return self.exit_codes.ERROR_COORDINATES_TRAJECTORY_READ

        from cp2k_output_tools.trajectories.xyz import parse

        positions_traj = []
        stepids_traj = []
        energies_traj = []
        for frame in parse(output_xyz_pos):
            _, positions = zip(*frame["atoms"])
            positions_traj.append(positions)
            comment_split = frame["comment"].split(",")
            stepids_traj.append(int(comment_split[0].split()[-1]))
            energy_index = next(
                (i for i, s in enumerate(comment_split) if "E =" in s), None
            )
            energies_traj.append(float(comment_split[energy_index].split()[-1]))
        positions_traj = np.array(positions_traj)
        stepids_traj = np.array(stepids_traj)
        energies_traj = np.array(energies_traj)

        cell_traj = None
        cell_traj_fname = self.node.process_class._DEFAULT_TRAJECT_CELL_FILE_NAME
        try:
            if cell_traj_fname in self.retrieved.base.repository.list_object_names():
                output_cell_pos = self.retrieved.base.repository.get_object_content(
                    cell_traj_fname
                )
                cell_traj = np.array(
                    [
                        np.fromstring(line, sep=" ")[2:-1].reshape(3, 3)
                        for line in output_cell_pos.splitlines()[1:]
                    ]
                )
        except OSError:
            return self.exit_codes.ERROR_CELLS_TRAJECTORY_READ

        forces_traj = None
        forces_traj_fname = self.node.process_class._DEFAULT_TRAJECT_FORCES_FILE_NAME
        try:
            if forces_traj_fname in self.retrieved.base.repository.list_object_names():
                output_forces = self.retrieved.base.repository.get_object_content(
                    forces_traj_fname
                )
                forces_traj = []
                for frame in parse(output_forces):
                    _, forces = zip(*frame["atoms"])
                    forces_traj.append(forces)
                forces_traj = np.array(forces_traj)
        except OSError:
            return self.exit_codes.ERROR_FORCES_TRAJECTORY_READ

        trajectory = orm.TrajectoryData()
        trajectory.set_trajectory(
            stepids=stepids_traj,
            cells=cell_traj,
            symbols=symbols,
            positions=positions_traj,
        )
        trajectory.set_array("energies", energies_traj)
        if forces_traj is not None:
            trajectory.set_array("forces", forces_traj)

        return trajectory


class Cp2kAdvancedParser(Cp2kBaseParser):
    """Advanced AiiDA parser class for the output of CP2K."""

    def _parse_stdout(self):
        """Advanced CP2K output file parser."""

        # Read the standard output of CP2K.
        exit_code, output_string = self._read_stdout()
        if exit_code:
            return exit_code

        # Check the standard output for errors.
        exit_code = self._check_stdout_for_errors(output_string)

        # Return the error code if an error was severe enough to stop the parsing.
        if exit_code in self.SEVERE_ERRORS:
            return exit_code

        # Parse the standard output.
        result_dict = utils.parse_cp2k_output_advanced(output_string)

        # Compute the bandgap for Spin1 and Spin2 if eigen was parsed (works also with smearing!)
        if "eigen_spin1_au" in result_dict:
            if result_dict["dft_type"] == "RKS":
                result_dict["eigen_spin2_au"] = result_dict["eigen_spin1_au"]

            lumo_spin1_idx = result_dict["init_nel_spin1"]
            lumo_spin2_idx = result_dict["init_nel_spin2"]
            if (lumo_spin1_idx > len(result_dict["eigen_spin1_au"]) - 1) or (
                lumo_spin2_idx > len(result_dict["eigen_spin2_au"]) - 1
            ):
                # electrons jumped from spin1 to spin2 (or opposite): assume last eigen is lumo
                lumo_spin1_idx = len(result_dict["eigen_spin1_au"]) - 1
                lumo_spin2_idx = len(result_dict["eigen_spin2_au"]) - 1
            homo_spin1 = result_dict["eigen_spin1_au"][lumo_spin1_idx - 1]
            homo_spin2 = result_dict["eigen_spin2_au"][lumo_spin2_idx - 1]
            lumo_spin1 = result_dict["eigen_spin1_au"][lumo_spin1_idx]
            lumo_spin2 = result_dict["eigen_spin2_au"][lumo_spin2_idx]
            result_dict["bandgap_spin1_au"] = lumo_spin1 - homo_spin1
            result_dict["bandgap_spin2_au"] = lumo_spin2 - homo_spin2

        kpoint_data = result_dict.pop("kpoint_data", None)
        if kpoint_data:
            bnds = BandsData()
            bnds.set_kpoints(kpoint_data["kpoints"])
            bnds.labels = kpoint_data["labels"]
            bnds.set_bands(
                kpoint_data["bands"],
                units=kpoint_data["bands_unit"],
            )
            self.out("output_bands", bnds)

        self.out("output_parameters", orm.Dict(dict=result_dict))
        return exit_code


class Cp2kToolsParser(Cp2kBaseParser):
    """AiiDA parser class for the output of CP2K based on the cp2k-output-tools project."""

    def _parse_stdout(self):
        """Very advanced CP2K output file parser."""

        from cp2k_output_tools import parse_iter

        # Read the standard output of CP2K.
        exit_code, output_string = self._read_stdout()
        if exit_code:
            return exit_code

        # Check the standard output for errors.
        exit_code = self._check_stdout_for_errors(output_string)

        # Return the error code if an error was severe enough to stop the parsing.
        if exit_code in self.SEVERE_ERRORS:
            return exit_code

        # Parse the standard output.

        result_dict = {}

        # the CP2K output parser is a block-based parser return blocks of data, each under a block key
        # merge them into one dict
        for match in parse_iter(output_string, key_mangling=True):
            result_dict.update(match)

        try:
            # the cp2k-output-tools parser is more hierarchical, be compatible with
            # the basic parser here and provide the total force eval energy as energy
            result_dict["energy"] = result_dict["energies"]["total_force_eval"]
            result_dict["energy_units"] = "a.u."
        except KeyError:
            pass

        self.out("output_parameters", orm.Dict(dict=result_dict))
        return exit_code
