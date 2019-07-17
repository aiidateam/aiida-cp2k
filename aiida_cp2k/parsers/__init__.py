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
        result_dict['warnings'] = []
        line_is = None
        energy = None
        BOHR2ANG = 0.529177208590000

        abs_fn = os.path.join(out_folder._repository._get_base_folder().abspath, fname)  # pylint: disable=protected-access
        with io.open(abs_fn, mode="r", encoding="utf-8") as fobj:
            lines = fobj.readlines()
            for i_line, line in enumerate(lines):
                if line.startswith(' ENERGY| '):
                    energy = float(line.split()[8])
                    result_dict['energy'] = energy
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

                # now starting complex parsing (print level MEDIUM)
                if line.startswith(' GLOBAL| Run type'):
                    result_dict['run_type'] = line.split()[-1]

                if line.startswith(' MD| Ensemble Type'):
                    result_dict['run_type'] += '-'
                    result_dict['run_type'] += line.split()[-1] #e.g., 'MD-NPT_F'

                if line.startswith(' DFT| ') and not 'dft_type' in result_dict.keys():
                    result_dict['dft_type'] = line.split()[-1] # RKS, UKS or ROKS

                # read the number of electrons in the first scf (NOTE: it may change but it is not updated!)
                if re.search('Number of electrons: ', line):
                    if not 'init_nel_spin1' in result_dict.keys():
                        result_dict['init_nel_spin1'] = int(line.split()[3])
                        if result_dict['dft_type'] == 'RKS':
                            result_dict['init_nel_spin1']//=2 #// returns an integer
                            result_dict['init_nel_spin2'] = result_dict['init_nel_spin1']
                    elif not 'init_nel_spin2' in result_dict.keys():
                        result_dict['init_nel_spin2'] = int(line.split()[3])

                # Printed at every outer OT, and needed for understanding if something is going wrong (if !=0)
                if re.search('Total charge density on r-space grids:', line):
                    edens_rspace_grid = float(line.split()[-1])

                if re.search('- Atoms: ', line):
                    result_dict['natoms'] = int(line.split()[-1])

                if re.search('Smear method', line):
                    result_dict['smear_method'] = line.split()[-1]

                if re.search("subspace spin", line):
                    if int(line.split()[-1]) == 1:
                        line_is = 'eigen_spin1_au'
                        if not 'eigen_spin1_au' in result_dict.keys():
                            result_dict['eigen_spin1_au'] = []
                    elif int(line.split()[-1]) == 2:
                        line_is = 'eigen_spin2_au'
                        if not 'eigen_spin2_au' in result_dict.keys():
                            result_dict['eigen_spin2_au'] = []
                    continue

                # Parse warnings
                if re.search("Using a non-square number of", line):
                    result_dict['warnings'] = 'Using a non-square number of MPI ranks'
                if re.search("SCF run NOT converged", line):
                    warn = "One or more SCF run did not converge"
                    if warn not in result_dict['warnings']:
                        result_dict['warnings'] = warn

                # If a tag has been detected, now read the following line knowing what they are
                if line_is!=None:
                    # Read eigenvalues as 4-columns row, then convert to float
                    if line_is in ['eigen_spin1_au', 'eigen_spin2_au']:
                        if re.search("-------------", line) or re.search("Reached convergence", line):
                            continue
                        if len(line.split()) > 0 and len(line.split()) <= 4:
                            result_dict[line_is] += [float(x) for x in line.split()]
                        else:
                            line_is = None

                ####################################################################
                #  THIS SECTION PARSES THE PROPERTIES AT GOE_OPT/CELL_OPT/MD STEP  #
                #  BC: it can be unstable!                                         #
                ####################################################################
                if 'run_type' in result_dict.keys() and result_dict['run_type'] in ['ENERGY','ENERGY_FORCE','GEO_OPT','CELL_OPT','MD','MD-NVT','MD-NPT_F']:
                  # Initialization
                  if not 'motion_step_info' in result_dict:
                     result_dict['motion_opt_converged'] = False
                     result_dict['motion_step_info'] = { 'step' : [],
                                                         'energy_au': [],
                                                         'dispersion_energy_au': [],
                                                         'pressure_bar': [],
                                                         'cell_vol_angs3': [],
                                                         'cell_a_angs': [],
                                                         'cell_b_angs': [],
                                                         'cell_c_angs': [],
                                                         'cell_alp_deg': [],
                                                         'cell_bet_deg': [],
                                                         'cell_gam_deg': [],
                                                         'max_step_au': [],
                                                         'rms_step_au': [],
                                                         'max_grad_au': [],
                                                         'rms_grad_au': [],
                                                         'scf_converged': [],
                                                        }
                     step = 0
                     energy = None
                     dispersion = None #Needed if no dispersions are included
                     pressure = None
                     max_step = None
                     rms_step = None
                     max_grad = None
                     rms_grad = None
                     scf_converged = True

                  print_now=False
                  data= line.split()
                  # Parse general info
                  if line.startswith(' CELL|'):
                     if re.search("Volume", line):    cell_vol=float(data[3])
                     if re.search("Vector a", line):  cell_a=float(data[9])
                     if re.search("Vector b", line):  cell_b=float(data[9])
                     if re.search("Vector c", line):  cell_c=float(data[9])
                     if re.search("alpha", line):     cell_alp=float(data[5])
                     if re.search("beta", line):      cell_bet=float(data[5])
                     if re.search("gamma", line):     cell_gam=float(data[5])

                  if re.search("Dispersion energy", line):  dispersion=float(data[2])
                  if re.search("SCF run NOT converged", line): scf_converged = False

                  # Parse specific info
                  if result_dict['run_type'] in ['ENERGY', 'ENERGY_FORCE']:
                      if energy != None and len(result_dict['motion_step_info']['step'])==0 :
                          print_now=True
                  if result_dict['run_type'] in ['GEO_OPT','CELL_OPT']:
                      #Note: with CELL_OPT/LBFGS there is no "STEP 0", while there is with CELL_OPT/BFGS
                      if re.search("Informations at step", line):  	step=int(data[5])
                      if re.search("Max. step size             =", line): max_step=float(data[-1])
                      if re.search("RMS step size              =", line): rms_step=float(data[-1])
                      if re.search("Max. gradient              =", line): max_grad=float(data[-1])
                      if re.search("RMS gradient               =", line): rms_grad=float(data[-1])
                      if len(data)==1 and data[0]=='---------------------------------------------------': print_now=True # 51('-')
                      if re.search("Reevaluating energy at the minimum", line): #not clear why it is doing a last one...
                         result_dict['motion_opt_converged'] = True

                  if result_dict['run_type']=='CELL_OPT':
                      if re.search("Internal Pressure", line): pressure=float(data[4])
                  if result_dict['run_type']=='MD-NVT':
                      if re.search("STEP NUMBER", line):           step=int(data[3])
                      if re.search("INITIAL PRESSURE\[bar\]", line): pressure=float(data[3]); print_now=True
                      if re.search("PRESSURE \[bar\]", line):        pressure=float(data[3]); print_now=True
                  if result_dict['run_type']=='MD-NPT_F':
                      if re.search("STEP NUMBER", line):           step=int(data[3])
                      if re.search("INITIAL PRESSURE\[bar\]", line): pressure=float(data[3]); print_now=True
                      if re.search("PRESSURE \[bar\]", line):        pressure=float(data[3]);
                      if re.search("VOLUME\[bohr\^3\]", line):        cell_vol=float(data[3])*(BOHR2ANG**3)
                      if re.search("CELL LNTHS\[bohr\]", line):
                                                                cell_a=float(data[3])*BOHR2ANG
                                                                cell_b=float(data[4])*BOHR2ANG
                                                                cell_c=float(data[5])*BOHR2ANG
                      if re.search("CELL ANGLS\[deg\]", line):
                                                                cell_alp=float(data[3])
                                                                cell_bet=float(data[4])
                                                                cell_gam=float(data[5])
                                                                print_now=True

                  if print_now and energy != None:
                      result_dict['motion_step_info']['step'].append(step)
                      result_dict['motion_step_info']['energy_au'].append(energy)
                      result_dict['motion_step_info']['dispersion_energy_au'].append(dispersion)
                      result_dict['motion_step_info']['pressure_bar'].append(pressure)
                      result_dict['motion_step_info']['cell_vol_angs3'].append(cell_vol)
                      result_dict['motion_step_info']['cell_a_angs'].append(cell_a)
                      result_dict['motion_step_info']['cell_b_angs'].append(cell_b)
                      result_dict['motion_step_info']['cell_c_angs'].append(cell_c)
                      result_dict['motion_step_info']['cell_alp_deg'].append(cell_alp)
                      result_dict['motion_step_info']['cell_bet_deg'].append(cell_bet)
                      result_dict['motion_step_info']['cell_gam_deg'].append(cell_gam)
                      result_dict['motion_step_info']['max_step_au'].append(max_step)
                      result_dict['motion_step_info']['rms_step_au'].append(rms_step)
                      result_dict['motion_step_info']['max_grad_au'].append(max_grad)
                      result_dict['motion_step_info']['rms_grad_au'].append(rms_grad)
                      result_dict['motion_step_info']['scf_converged'].append(scf_converged)
                ####################################################################
                #  END PARSING GEO_OPT/CELL_OPT/MD STEP                            #
                ####################################################################

        # After having parsed the out file

        # nwarnings is the last thing to be printed: if it is not there, CP2K didn't finish properly
        if 'nwarnings' not in result_dict:
            raise OutputParsingError("CP2K did not finish properly.")

        # Compute the bandgap for Spin1 and Spin2 (works also with smearing!)
        if result_dict['dft_type'] == "RKS":
            result_dict['eigen_spin2_au'] =  result_dict['eigen_spin1_au']

        lumo_spin1_idx = result_dict['init_nel_spin1']
        lumo_spin2_idx = result_dict['init_nel_spin2']
        if (lumo_spin1_idx > len(result_dict['eigen_spin1_au'])-1) or \
           (lumo_spin2_idx > len(result_dict['eigen_spin2_au'])-1):
            #electrons jumped from spin1 to spin2 (or opposite): assume last eigen is lumo
            lumo_spin1_idx = len(result_dict['eigen_spin1_au'])-1
            lumo_spin2_idx = len(result_dict['eigen_spin2_au'])-1
        homo_spin1 = result_dict['eigen_spin1_au'][lumo_spin1_idx-1]
        homo_spin2 = result_dict['eigen_spin2_au'][lumo_spin2_idx-1]
        lumo_spin1 = result_dict['eigen_spin1_au'][lumo_spin1_idx]
        lumo_spin2 = result_dict['eigen_spin2_au'][lumo_spin2_idx]
        result_dict['bandgap_spin1_au'] = lumo_spin1-homo_spin1
        result_dict['bandgap_spin2_au'] = lumo_spin2-homo_spin2

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
