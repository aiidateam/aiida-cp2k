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

from aiida.parsers import Parser
from aiida.common import OutputParsingError, NotExistent
from aiida.engine import ExitCode

from aiida_cp2k.utils import parse_cp2k_output, parse_cp2k_trajectory


class Cp2kParser(Parser):
    """Parser for the output of CP2K."""

    def parse(self, **kwargs):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """
        try:
            out_folder = self.retrieved
        except NotExistent:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        self._parse_stdout(out_folder)

        try:
            structure = self._parse_trajectory(out_folder)
            self.out('output_structure', structure)
        except Exception:  # pylint: disable=broad-except
            pass

        return ExitCode(0)

    def _parse_stdout(self, out_folder):
        """CP2K output parser"""

        from aiida.orm import BandsData, Dict

        # pylint: disable=protected-access

        fname = self.node.process_class._DEFAULT_OUTPUT_FILE
        if fname not in out_folder._repository.list_object_names():
            raise OutputParsingError("Cp2k output file not retrieved")

        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fname)

        with io.open(abs_fn, mode="r", encoding="utf-8") as fobj:
            result_dict = parse_cp2k_output(fobj)

        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly.")

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

    def _parse_trajectory(self, out_folder):
        """CP2K trajectory parser"""

        from ase import Atoms
        from aiida.orm import StructureData

        # pylint: disable=protected-access

        fname = self.node.process_class._DEFAULT_RESTART_FILE_NAME

        if fname not in out_folder._repository.list_object_names():
            raise Exception("parsing trajectory requested, but no trajectory file available")

        # read restart file
        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fname)

        with io.open(abs_fn, mode="r", encoding="utf-8") as fobj:
            atoms = Atoms(**parse_cp2k_trajectory(fobj))

        return StructureData(ase=atoms)
