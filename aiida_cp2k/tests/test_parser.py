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


def test_mulliken_rks():
    from io import StringIO

    with io.open(path.join(TEST_DIR, "files/cp2k_condnum_test01.out"), "r") as fobj:
        data = parse_cp2k_output(fobj)

    assert "mulliken_population_analysis" in data

    expected_pa = StringIO(
        u"""
1         11.999203                              0.000797
1         11.999971                              0.000029
1         12.000244                             -0.000244
1         11.999971                              0.000029
1         12.000244                             -0.000244
1         11.999971                              0.000029
1         12.001289                             -0.001289
1         11.999971                              0.000029
1         11.998769                              0.001231
1         11.999970                              0.000030
1         11.999813                              0.000187
1         11.999970                              0.000030
1         11.999813                              0.000187
1         11.999971                              0.000029
1         12.000859                             -0.000859
1         11.999971                              0.000029
    """
    )

    expected_pa = np.genfromtxt(expected_pa)

    expected_total = [192.000000, 0.000000]

    results = data["mulliken_population_analysis"]

    fields = ("kind", "population", "charge")
    assert np.allclose(expected_total, [results["total"][f] for f in fields[1:]])
    assert np.allclose(
        expected_pa, [[line[f] for f in fields] for line in results["per-atom"]]
    )
    assert set(l["element"] for l in results["per-atom"]) == {"Hg"}


def test_mulliken_uks():
    from io import StringIO

    with io.open(
        path.join(TEST_DIR, "files/cp2k_mulliken_uks_test01.out"), "r"
    ) as fobj:
        data = parse_cp2k_output(fobj)

    assert "mulliken_population_analysis" in data

    expected_pa = StringIO(
        u"""
1         9.069583     6.930417     0.000000     2.139166
1         9.069582     6.930418    -0.000000     2.139164
"""
    )

    expected_pa = np.genfromtxt(expected_pa)

    expected_total = [18.139165, 13.860835, 0.000000, 4.278330]

    results = data["mulliken_population_analysis"]

    fields = ("kind", "population_alpha", "population_beta", "charge", "spin")
    assert np.allclose(expected_total, [results["total"][f] for f in fields[1:]])
    assert np.allclose(
        expected_pa, [[line[f] for f in fields] for line in results["per-atom"]]
    )
    assert set(l["element"] for l in results["per-atom"]) == {"Fe"}
