###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K output parser."""

from aiida.common import exceptions
from aiida.engine import ExitCode
from aiida.orm import Dict

# +
from aiida.parsers import Parser
from aiida.plugins import DataFactory

from aiida_cp2k import utils

# -

StructureData = DataFactory("core.structure")  # pylint: disable=invalid-name
BandsData = DataFactory("core.array.bands")  # pylint: disable=invalid-name


class Cp2kBaseParser(Parser):
    """Basic AiiDA parser for the output of CP2K."""

    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        try:
            _ = self.retrieved
        except exceptions.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        exit_code = self._parse_stdout()
        if exit_code is not None:
            return exit_code

        try:
            returned = self._parse_trajectory()
            if isinstance(returned, StructureData):
                self.out("output_structure", returned)
            else:  # in case this is an error code
                return returned
        except exceptions.NotExistent:
            pass

        return ExitCode(0)

    def _parse_stdout(self):
        """Basic CP2K output file parser."""

        # Read the standard output of CP2K.
        exit_code, output_string = self._read_stdout()
        if exit_code:
            return exit_code

        # Check the standard output for errors.
        exit_code = self._check_stdout_for_errors(output_string)
        if exit_code:
            return exit_code

        # Parse the standard output.
        result_dict = utils.parse_cp2k_output(output_string)
        self.out("output_parameters", Dict(dict=result_dict))
        return None

    def _parse_trajectory(self):
        """CP2K trajectory parser."""

        from ase import Atoms

        fname = (
            self.node.process_class._DEFAULT_RESTART_FILE_NAME
        )  # pylint: disable=protected-access

        # Check if the restart file is present.
        if fname not in self.retrieved.base.repository.list_object_names():
            raise exceptions.NotExistent(
                "No restart file available, so the output trajectory can't be extracted"
            )

        # Read the restart file.
        try:
            output_string = self.retrieved.base.repository.get_object_content(fname)
        except OSError:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ

        return StructureData(ase=Atoms(**utils.parse_cp2k_trajectory(output_string)))

    def _check_stdout_for_errors(self, output_string):
        """This function checks the CP2K output file for some basic errors."""

        if "ABORT" in output_string:
            return self.exit_codes.ERROR_OUTPUT_CONTAINS_ABORT

        if "exceeded requested execution time" in output_string:
            return self.exit_codes.ERROR_OUT_OF_WALLTIME

        if "PROGRAM STOPPED IN" not in output_string:
            return self.exit_codes.ERROR_OUTPUT_INCOMPLETE

        return None

    def _read_stdout(self):
        """Read the standard output file. If impossible, return a non-zero exit code."""

        fname = self.node.base.attributes.get("output_filename")

        if fname not in self.retrieved.base.repository.list_object_names():
            return self.exit_codes.ERROR_OUTPUT_STDOUT_MISSING, None
        try:
            output_string = self.retrieved.base.repository.get_object_content(fname)
        except OSError:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ, None

        return None, output_string


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
        if exit_code:
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

        self.out("output_parameters", Dict(dict=result_dict))
        return None


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
        if exit_code:
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

        self.out("output_parameters", Dict(dict=result_dict))
        return None
