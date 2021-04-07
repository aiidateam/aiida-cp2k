# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test Cp2k input generator"""

import pytest

from aiida_cp2k.utils import Cp2kInput


def test_render_empty():
    inp = Cp2kInput()
    assert inp.render() == inp.DISCLAIMER


def test_render_str_val():
    inp = Cp2kInput({"FOO": "bar"})
    assert inp.render() == f"{inp.DISCLAIMER}\nFOO bar"


def test_add_keyword():
    """Test  add_keyword()"""
    inp = Cp2kInput({"FOO": "bar"})
    inp.add_keyword("BAR", "boo")
    assert inp.render() == f"{inp.DISCLAIMER}\nBAR boo\nFOO bar"

    inp.add_keyword("BOO/BAZ", "boo")
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
&END BOO
FOO bar"""

    inp.add_keyword(["BOO", "BII"], "boo")
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BII", "bzzzzzz", override=False)
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BII/BCC", "bcr", override=False)
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BII/BCC", "bcr")
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   &BII
      BCC bcr
   &END BII
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BII", "boo", override=False)
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   &BII
      BCC bcr
   &END BII
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BII", "boo", override=True)
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BII", "boo", override=True)
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BIP", "bzz", override=False, conflicting_keys=['BII'])
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BIP", "bzz", override=False, conflicting_keys=[])
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
   BIP bzz
&END BOO
FOO bar"""

    inp.add_keyword("BOO/BEE", "bee", override=True, conflicting_keys=['BAZ', 'BII'])
    assert inp.render() == f"""{inp.DISCLAIMER}
BAR boo
&BOO
   BEE bee
   BIP bzz
&END BOO
FOO bar"""


def test_add_keyword_invariant_inp():
    """Check that the input dictionary is not modified by add_keyword()"""
    param = {"FOO": "bar"}
    inp = Cp2kInput(param)
    inp.add_keyword("BAR", "boo")
    assert inp.render() == f"{inp.DISCLAIMER}\nBAR boo\nFOO bar"
    assert param == {"FOO": "bar"}


def test_multiple_force_eval():
    inp = Cp2kInput({"FORCE_EVAL": [{"FOO": "bar"}, {"FOO": "bar"}, {"FOO": "bar"}]})
    assert inp.render() == f"""{inp.DISCLAIMER}
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL"""


def test_kinds():
    inp = Cp2kInput({"KIND": [{"_": "H"}, {"_": "O"}]})
    assert inp.render() == f"""{inp.DISCLAIMER}
&KIND H
&END KIND
&KIND O
&END KIND"""


def test_invariant_under_render():
    """Check that the input dictionary is not modified by Cp2kInput.render()"""
    param = {"KIND": [{"_": "H"}, {"_": "O"}]}
    Cp2kInput(param).render()
    assert param == {"KIND": [{"_": "H"}, {"_": "O"}]}

    param = {"SEC": {"_": "H"}}
    Cp2kInput(param).render()
    assert param == {"SEC": {"_": "H"}}


def test_invalid_lowercase_key():
    inp = Cp2kInput({"foo": "bar"})
    with pytest.raises(ValueError):
        inp.render()


def test_invalid_preprocessor():
    inp = Cp2kInput({"@SET": "bar"})
    with pytest.raises(ValueError):
        inp.render()


def test_get_keyword_value():
    """Test get_keyword_value()"""
    inp = Cp2kInput({"FOO": "bar", "A": {"KW1": "val1"}})
    assert inp.get_keyword_value("FOO") == "bar"
    assert inp.get_keyword_value("/FOO") == "bar"
    assert inp.get_keyword_value("A/KW1") == "val1"
    assert inp.get_keyword_value("/A/KW1") == "val1"
    assert inp.get_keyword_value(["A", "KW1"]) == "val1"
    with pytest.raises(TypeError):
        inp.get_keyword_value("A")
    with pytest.raises(KeyError):
        inp.get_keyword_value("B")


def test_get_section_dict():
    """Test get_section_dict()"""
    orig_dict = {"FOO": "bar", "A": {"KW1": "val1"}}
    inp = Cp2kInput(orig_dict)
    assert inp.get_section_dict("/") == orig_dict
    assert inp.get_section_dict("////") == orig_dict
    assert inp.get_section_dict("") == orig_dict
    assert inp.get_section_dict() == orig_dict
    assert inp.get_section_dict("/") is not orig_dict  # make sure we get a distinct object
    assert inp.get_section_dict("A") == orig_dict["A"]
    assert inp.get_section_dict("/A") == orig_dict["A"]
    assert inp.get_section_dict(["A"]) == orig_dict["A"]
    with pytest.raises(TypeError):
        inp.get_section_dict("FOO")
    with pytest.raises(KeyError):
        inp.get_section_dict("BAR")


def test_get_section_dict_repeated():
    """Test NotImplementedError for repeated sections in get_section_dict()"""
    inp = Cp2kInput({"FOO": [{"KW1": "val1_1"}, {"KW1": "val1_2"}]})
    with pytest.raises(NotImplementedError):
        inp.get_keyword_value("/FOO/KW1")
