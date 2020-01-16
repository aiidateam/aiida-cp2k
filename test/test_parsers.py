# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test Cp2k output parsers."""
from __future__ import absolute_import
import os

from aiida_cp2k.utils import parse_cp2k_output_bsse

CWD = os.path.dirname(os.path.realpath(__file__))


def test_bsse_parser():
    """Testing BSSE parser."""
    with open(os.path.join(CWD, 'outputs', 'BSSE_output_v5.1_.out')) as fobj:
        res = parse_cp2k_output_bsse(fobj)
        assert res["exceeded_walltime"] is False
        assert res["energy_description_list"] == [
            "Energy of A with basis set A", "Energy of B with basis set B", "Energy of A with basis set of A+B",
            "Energy of B with basis set of A+B", "Energy of A+B with basis set of A+B"
        ]
        assert res["energy_list"] == [
            -792.146217025347, -37.76185844385889, -792.1474366957273, -37.76259020339316, -829.920698393915
        ]
        assert res["energy_dispersion_list"] == [
            -0.15310795077994, -0.0009680299214, -0.15310795077994, -0.0009680299214, -0.16221221242898
        ]
        assert res["energy"] == -829.920698393915
        assert res["energy_units"] == "a.u."
        assert res["binding_energy_raw"] == -33.14148882373938
        assert res["binding_energy_corr"] == -28.018009583204375
        assert res["binding_energy_bsse"] == -5.123479240535005
        assert res["binding_energy_unit"] == "kJ/mol"
        assert res["binding_energy_dispersion"] == -21.361676400918867
