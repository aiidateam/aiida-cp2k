# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from __future__ import absolute_import

import io
from os import path

import numpy as np
from aiida_cp2k.utils import parse_cp2k_output


TEST_DIR = path.dirname(path.realpath(__file__))


def test_condnum():
    with io.open(path.join(TEST_DIR, "files/cp2k_condnum_test01.out"), "r") as fobj:
        data = parse_cp2k_output(fobj)

    assert "overlap_matrix_condition_number" in data

    omcn = data["overlap_matrix_condition_number"]

    expected = [
        [2.393e001, 5.554e003, 1.329e005, 5.1235],
        [2.393e001, 5.554e003, 1.329e005, 5.1235],
        [7.014e000, 4.389e-004, 1.598e004, 4.2036],
    ]

    results = [
        [omcn["1-norm (estimate)"][k] for k in ("|A|", "|A^-1|", "CN", "Log(CN)")],
        [
            omcn["1-norm (using diagonalization)"][k]
            for k in ("|A|", "|A^-1|", "CN", "Log(CN)")
        ],
        [
            omcn["2-norm (using diagonalization)"][k]
            for k in ("max EV", "min EV", "CN", "Log(CN)")
        ],
    ]

    assert np.allclose(expected, results)
