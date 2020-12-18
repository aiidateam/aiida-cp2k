# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test writing structures to xyz format"""
from ase import Atoms
from aiida_cp2k.calculations import _atoms_to_xyz


def test_atoms_to_xyz():
    """Test that writing atoms to xyz format is handled correctly in the presence of tags"""
    h2o = Atoms('H2O')
    h2o[0].charge = -1
    h2o[0].tag = 1
    h2o[1].tag = 2

    xyz = _atoms_to_xyz(h2o)  # pylint: disable=protected-access

    assert 'H1' in xyz, xyz
    assert 'H2' in xyz, xyz
