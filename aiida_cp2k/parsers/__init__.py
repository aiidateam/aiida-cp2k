# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K output parser."""

import io
import os
from aiida.common import exceptions

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode
from aiida.orm import Dict
from aiida.plugins import DataFactory

StructureData = DataFactory('structure')  # pylint: disable=invalid-name
BandsData = DataFactory('array.bands')  # pylint: disable=invalid-name


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
                self.out('output_structure', returned)
            else:  # in case this is an error code
                return returned
        except exceptions.NotExistent:
            pass

        return ExitCode(0)

    def _parse_stdout(self):
        """Basic CP2K output file parser."""

        from aiida_cp2k.utils import parse_cp2k_output

        fname = self.node.get_attribute('output_filename')

        if fname not in self.retrieved.list_object_names():
            return self.exit_codes.ERROR_OUTPUT_STDOUT_MISSING

        try:
            output_string = self.retrieved.get_object_content(fname)
        except IOError:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ

        result_dict = parse_cp2k_output(output_string)

        if "aborted" in result_dict:
            return self.exit_codes.ERROR_OUTPUT_CONTAINS_ABORT

        self.out("output_parameters", Dict(dict=result_dict))

        return None

    def _parse_trajectory(self):
        """CP2K trajectory parser."""

        from ase import Atoms
        from aiida_cp2k.utils import parse_cp2k_trajectory

        fname = self.node.process_class._DEFAULT_RESTART_FILE_NAME  # pylint: disable=protected-access

        # Check if the restart file is present.
        if fname not in self.retrieved.list_object_names():
            raise exceptions.NotExistent("No restart file available, so the output trajectory can't be extracted")

        # Read the restart file.
        try:
            output_string = self.retrieved.get_object_content(fname)
        except IOError:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ

        return StructureData(ase=Atoms(**parse_cp2k_trajectory(output_string)))


class Cp2kAdvancedParser(Cp2kBaseParser):
    """Advanced AiiDA parser class for the output of CP2K."""

    def _parse_stdout(self):
        """Advanced CP2K output file parser."""

        from aiida_cp2k.utils import parse_cp2k_output_advanced

        fname = self.node.process_class._DEFAULT_OUTPUT_FILE  # pylint: disable=protected-access
        if fname not in self.retrieved.list_object_names():
            raise OutputParsingError("CP2K output file not retrieved.")

        try:
            output_string = self.retrieved.get_object_content(fname)
        except IOError:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ

        result_dict = parse_cp2k_output_advanced(output_string)

        # nwarnings is the last thing to be printed in th eCP2K output file:
        # if it is not there, CP2K didn't finish properly
        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly.")

        if "aborted" in result_dict:
            return self.exit_codes.ERROR_OUTPUT_CONTAINS_ABORT

        # Compute the bandgap for Spin1 and Spin2 if eigen was parsed (works also with smearing!)
        if 'eigen_spin1_au' in result_dict:
            if result_dict['dft_type'] == "RKS":
                result_dict['eigen_spin2_au'] = result_dict['eigen_spin1_au']

            lumo_spin1_idx = result_dict['init_nel_spin1']
            lumo_spin2_idx = result_dict['init_nel_spin2']
            if (lumo_spin1_idx > len(result_dict['eigen_spin1_au'])-1) or \
               (lumo_spin2_idx > len(result_dict['eigen_spin2_au'])-1):
                #electrons jumped from spin1 to spin2 (or opposite): assume last eigen is lumo
                lumo_spin1_idx = len(result_dict['eigen_spin1_au']) - 1
                lumo_spin2_idx = len(result_dict['eigen_spin2_au']) - 1
            homo_spin1 = result_dict['eigen_spin1_au'][lumo_spin1_idx - 1]
            homo_spin2 = result_dict['eigen_spin2_au'][lumo_spin2_idx - 1]
            lumo_spin1 = result_dict['eigen_spin1_au'][lumo_spin1_idx]
            lumo_spin2 = result_dict['eigen_spin2_au'][lumo_spin2_idx]
            result_dict['bandgap_spin1_au'] = lumo_spin1 - homo_spin1
            result_dict['bandgap_spin2_au'] = lumo_spin2 - homo_spin2

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

        fname = self.node.process_class._DEFAULT_OUTPUT_FILE  # pylint: disable=protected-access
        if fname not in self.retrieved.list_object_names():
            raise OutputParsingError("CP2K output file not retrieved.")

        try:
            output_string = self.retrieved.get_object_content(fname)
        except IOError:
            return self.exit_codes.ERROR_OUTPUT_STDOUT_READ

        result_dict = {}

        # the CP2K output parser is a block-based parser return blocks of data, each under a block key
        # merge them into one dict
        for match in parse_iter(output_string, key_mangling=True):
            result_dict.update(match)

        # nwarnings is the last thing to be printed in the CP2K output file:
        # if it is not there, CP2K didn't finish properly most likely
        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly")

        if "aborted" in result_dict:
            return self.exit_codes.ERROR_OUTPUT_CONTAINS_ABORT

        try:
            # the cp2k-output-tools parser is more hierarchical, be compatible with
            # the basic parser here and provide the total force eval energy as energy
            result_dict["energy"] = result_dict["energies"]["total_force_eval"]
            result_dict["energy_units"] = "a.u."
        except KeyError:
            pass

        self.out("output_parameters", Dict(dict=result_dict))
        return None
