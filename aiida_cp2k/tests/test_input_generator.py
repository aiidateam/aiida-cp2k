# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from __future__ import absolute_import

import io

import pytest

from aiida_cp2k.utils import Cp2kInput


def test_render_empty():
    inp = Cp2kInput()
    assert inp.to_string() == inp.DISCLAIMER


def test_render_str_val():
    inp = Cp2kInput({"FOO": "bar"})
    assert inp.to_string() == "{inp.DISCLAIMER}\nFOO bar".format(inp=inp)


def test_add_keyword():
    inp = Cp2kInput({"FOO": "bar"})
    inp.add_keyword("BAR", "boo")
    assert inp.to_string() == "{inp.DISCLAIMER}\nBAR boo\nFOO bar".format(inp=inp)

    inp.add_keyword("BOO/BAZ", "boo")
    assert (
        inp.to_string()
        == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
&END BOO
FOO bar""".format(
            inp=inp
        )
    )

    inp.add_keyword(["BOO", "BII"], "boo")
    assert (
        inp.to_string()
        == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar""".format(
            inp=inp
        )
    )


def test_add_keyword_invariant_input():
    param = {"FOO": "bar"}
    inp = Cp2kInput(param)
    inp.add_keyword("BAR", "boo")
    assert inp.to_string() == "{inp.DISCLAIMER}\nBAR boo\nFOO bar".format(inp=inp)
    assert param == {"FOO": "bar"}


def test_multiple_force_eval():
    inp = Cp2kInput({"FORCE_EVAL": [{"FOO": "bar"}, {"FOO": "bar"}, {"FOO": "bar"}]})
    assert (
        inp.to_string()
        == """{inp.DISCLAIMER}
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL""".format(
            inp=inp
        )
    )


def test_kinds():
    inp = Cp2kInput({"KIND": [{"_": "H"}, {"_": "O"}]})
    assert (
        inp.to_string()
        == """{inp.DISCLAIMER}
&KIND H
&END KIND
&KIND O
&END KIND""".format(
            inp=inp
        )
    )


def test_invariant_under_render():
    param = {"KIND": [{"_": "H"}, {"_": "O"}]}
    Cp2kInput(param).to_string()
    assert param == {"KIND": [{"_": "H"}, {"_": "O"}]}

    param = {"SEC": {"_": "H"}}
    Cp2kInput(param).to_string()
    assert param == {"SEC": {"_": "H"}}


def test_invalid_lowercase_key():
    inp = Cp2kInput({"foo": "bar"})
    with pytest.raises(ValueError):
        inp.to_string()


def test_invalid_preprocessor():
    inp = Cp2kInput({"@SET": "bar"})
    with pytest.raises(ValueError):
        inp.to_string()


def test_string_file_equal_output():
    params = {
        "FORCE_EVAL": {
            "METHOD": "Quickstep",
            "DFT": {
                "CHARGE": 0,
                "KPOINTS": {
                    "SCHEME MONKHORST-PACK": "1 1 1",
                    "SYMMETRY": "OFF",
                    "WAVEFUNCTIONS": "REAL",
                    "FULL_GRID": ".TRUE.",
                    "PARALLEL_GROUP_SIZE": 0,
                },
                "MGRID": {"CUTOFF": 600, "NGRIDS": 4, "REL_CUTOFF": 50},
                "UKS": False,
                "BASIS_SET_FILE_NAME": "BASIS_MOLOPT",
                "POTENTIAL_FILE_NAME": "GTH_POTENTIALS",
                "QS": {"METHOD": "GPW", "EXTRAPOLATION": "USE_GUESS"},
                "POISSON": {"PERIODIC": "XYZ"},
                "SCF": {
                    "EPS_SCF": 1.0e-4,
                    "ADDED_MOS": 1,
                    "SMEAR": {"METHOD": "FERMI_DIRAC", "ELECTRONIC_TEMPERATURE": 300},
                    "DIAGONALIZATION": {"ALGORITHM": "STANDARD", "EPS_ADAPT": 0.01},
                    "MIXING": {
                        "METHOD": "BROYDEN_MIXING",
                        "ALPHA": 0.2,
                        "BETA": 1.5,
                        "NBROYDEN": 8,
                    },
                },
                "XC": {"XC_FUNCTIONAL": {"_": "PBE"}},
                "PRINT": {
                    "MO_CUBES": {  # this is to print the band gap
                        "STRIDE": "1 1 1",
                        "WRITE_CUBE": "F",
                        "NLUMO": 1,
                        "NHOMO": 1,
                    },
                    "BAND_STRUCTURE": {
                        "KPOINT_SET": [
                            {
                                "NPOINTS": 10,
                                "SPECIAL_POINT": ["GAMMA 0.0 0.0 0.0", "X 0.5 0.0 0.5"],
                                "UNITS": "B_VECTOR",
                            },
                            {
                                "NPOINTS": 10,
                                "SPECIAL_POINT": [
                                    "X 0.5 0.0 0.5",
                                    "U 0.625 0.25 0.625",
                                ],
                                "UNITS": "B_VECTOR",
                            },
                            {
                                "NPOINTS": 10,
                                "SPECIAL_POINT": [
                                    "K 0.375 0.375 0.75",
                                    "GAMMA 0.0 0.0 0.0",
                                ],
                                "UNITS": "B_VECTOR",
                            },
                            {
                                "NPOINTS": 10,
                                "SPECIAL_POINT": ["GAMMA 0.0 0.0 0.0", "L 0.5 0.5 0.5"],
                                "UNITS": "B_VECTOR",
                            },
                            {
                                "NPOINTS": 10,
                                "SPECIAL_POINT": ["L 0.5 0.5 0.5", "W 0.5 0.25 0.75"],
                                "UNITS": "B_VECTOR",
                            },
                            {
                                "NPOINTS": 10,
                                "SPECIAL_POINT": ["W 0.5 0.25 0.75", "X 0.5 0.0 0.5"],
                                "UNITS": "B_VECTOR",
                            },
                        ]
                    },
                },
            },
            "SUBSYS": {
                "KIND": [
                    {
                        "_": "Si",
                        "BASIS_SET": "DZVP-MOLOPT-SR-GTH",
                        "POTENTIAL": "GTH-PBE-q4",
                    }
                ]
            },
            "PRINT": {  # this is to print forces (may be necessary for problems
                # detection)
                "FORCES": {"_": "ON"}
            },
        },
        "GLOBAL": {"EXTENDED_FFT_LENGTHS": True},  # Needed for large systems
    }

    inp = Cp2kInput(params)

    # io.StringIO() is a unicode file-like, similar to a io.open(..., encoding="utf8")
    with io.StringIO() as fhandle:
        inp.to_file(fhandle)
        assert inp.to_string() == fhandle.getvalue()
