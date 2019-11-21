# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""AiiDA-CP2K output parser"""
from __future__ import absolute_import

import io
import os
from aiida.common import exceptions

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode
from aiida.orm import Dict


class Cp2kBaseParser(Parser):
    """Basic AiiDA parser for the output of CP2K"""

    def parse(self, **kwargs):
        """Receives in input a dictionary of retrieved nodes. Does all the logic here."""

        try:
            out_folder = self.retrieved
        except exceptions.NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        exit_code = self._parse_stdout(out_folder)
        if exit_code is not None:
            return exit_code

        try:
            structure = self._parse_trajectory(out_folder)
            self.out('output_structure', structure)
        except Exception:  # pylint: disable=broad-except
            pass

        return ExitCode(0)

    def _parse_stdout(self, out_folder):
        """Basic CP2K output file parser."""

        from aiida_cp2k.utils import parse_cp2k_output

        # pylint: disable=protected-access

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

    def _parse_trajectory(self, out_folder):
        """CP2K trajectory parser."""

        from ase import Atoms
        from aiida.orm import StructureData
        from aiida_cp2k.utils import parse_cp2k_trajectory

        # pylint: disable=protected-access
        fname = self.node.process_class._DEFAULT_RESTART_FILE_NAME

        if fname not in out_folder._repository.list_object_names():
            raise Exception("parsing trajectory requested, but no trajectory file available")

        # read restart file
        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fname)
        with io.open(abs_fn, mode="r", encoding="utf-8") as fobj:
            atoms = Atoms(**parse_cp2k_trajectory(fobj))

        return StructureData(ase=atoms)


class Cp2kAdvancedParser(Cp2kBaseParser):
    """Advanced AiiDA parser class for the output of CP2K."""

    def _parse_stdout(self, out_folder):
        """Advanced CP2K output file parser"""

        from aiida.orm import BandsData
        from aiida_cp2k.utils import parse_cp2k_output_advanced

        # pylint: disable=protected-access

        fname = self.node.process_class._DEFAULT_OUTPUT_FILE
        if fname not in out_folder._repository.list_object_names():
            raise OutputParsingError("Cp2k output file not retrieved")

        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fname)
        with io.open(abs_fn, mode="r", encoding="utf-8") as fobj:
            result_dict = parse_cp2k_output_advanced(fobj)

        # nwarnings is the last thing to be printed in th eCP2K output file:
        # if it is not there, CP2K didn't finish properly
        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly.")

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

        if "kpoint_data" in result_dict:
            bnds = BandsData()
            bnds.set_kpoints(result_dict["kpoint_data"]["kpoints"])
            bnds.labels = result_dict["kpoint_data"]["labels"]
            bnds.set_bands(
                result_dict["kpoint_data"]["bands"],
                units=result_dict["kpoint_data"]["bands_unit"],
            )
            self.out("output_bands", bnds)
            del result_dict["kpoint_data"]

        self.out("output_parameters", Dict(dict=result_dict))
