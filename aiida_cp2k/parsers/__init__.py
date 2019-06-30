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
import re
from re import DOTALL
import math
from six.moves import map

import ase
import numpy as np

from aiida.parsers import Parser
from aiida.orm import Dict, StructureData
from aiida.common import OutputParsingError


class Cp2kParser(Parser):
    """Parser for the output of CP2K."""

    # --------------------------------------------------------------------------
    def parse(self, **kwargs):
        """
        Receives in input a dictionary of retrieved nodes.
        Does all the logic here.
        """
        from aiida.engine import ExitCode
        from aiida.common import NotExistent

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

    # --------------------------------------------------------------------------
    def _parse_stdout(self, out_folder):
        """CP2K output parser"""
        fname = self.node.process_class._DEFAULT_OUTPUT_FILE  # pylint: disable=protected-access
        if fname not in out_folder._repository.list_object_names():  # pylint: disable=protected-access
            raise OutputParsingError("Cp2k output file not retrieved")

        result_dict = {'exceeded_walltime': False}
        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fname)  # pylint: disable=protected-access
        with io.open(abs_fn, mode="r", encoding="utf-8") as fobj:
            lines = fobj.readlines()
            for i_line, line in enumerate(lines):
                if line.startswith(' ENERGY| '):
                    result_dict['energy'] = float(line.split()[8])
                    result_dict['energy_units'] = "a.u."
                if 'The number of warnings for this run is' in line:
                    result_dict['nwarnings'] = int(line.split()[-1])
                if 'exceeded requested execution time' in line:
                    result_dict['exceeded_walltime'] = True
                if "KPOINTS| Band Structure Calculation" in line:
                    from aiida.orm import BandsData
                    bnds = BandsData()
                    kpoints, labels, bands = self._parse_bands(lines, i_line)
                    bnds.set_kpoints(kpoints)
                    bnds.labels = labels
                    bnds.set_bands(bands, units='eV')
                    self.out('output_bands', bnds)

        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly.")

        self.out('output_parameters', Dict(dict=result_dict))

    # --------------------------------------------------------------------------
    @staticmethod
    def _parse_bands(lines, n_start):
        """Parse band structure from cp2k output"""
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
                kpoint = tuple(map(float, splitted[-3:]))
                if " ".join(splitted[-5:-3]) != "not specified":
                    label = splitted[-4]
                    known_kpoints[kpoint] = label
            elif pattern.match(line):
                spin = int(splitted[3])
                kpoint = tuple(map(float, splitted[-3:]))
                kpoint_n_lines = int(math.ceil(int(selected_lines[current_line + 1]) / 4.))
                band = list(
                    map(float, ' '.join(selected_lines[current_line + 2:current_line + 2 + kpoint_n_lines]).split()))
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

    # --------------------------------------------------------------------------
    def _parse_trajectory(self, out_folder):
        """CP2K trajectory parser"""
        fname = self.node.process_class._DEFAULT_RESTART_FILE_NAME  # pylint: disable=protected-access
        if fname not in out_folder._repository.list_object_names():  # pylint: disable=protected-access
            raise Exception  # not every run type produces a trajectory

        # read restart file
        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fname)  # pylint: disable=protected-access
        with io.open(abs_fn, mode="r", encoding="utf-8") as fobj:
            content = fobj.read()

        # parse coordinate section
        match = re.search(r'\n\s*&COORD\n(.*?)\n\s*&END COORD\n', content, DOTALL)
        coord_lines = [line.strip().split() for line in match.group(1).splitlines()]
        symbols = [line[0] for line in coord_lines]
        positions_str = [line[1:] for line in coord_lines]
        positions = np.array(positions_str, np.float64)

        # parse cell section
        match = re.search(r'\n\s*&CELL\n(.*?)\n\s*&END CELL\n', content, re.DOTALL)
        cell_lines = [line.strip().split() for line in match.group(1).splitlines()]
        cell_str = [line[1:] for line in cell_lines if line[0] in 'ABC']
        cell = np.array(cell_str, np.float64)

        # create StructureData
        atoms = ase.Atoms(symbols=symbols, positions=positions, cell=cell)
        return StructureData(ase=atoms)


# EOF
