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
    assert inp.render() == "{inp.DISCLAIMER}\nFOO bar".format(inp=inp)


def test_add_keyword():
    """Test  add_keyword()"""
    inp = Cp2kInput({"FOO": "bar"})
    inp.add_keyword("BAR", "boo")
    assert inp.render() == "{inp.DISCLAIMER}\nBAR boo\nFOO bar".format(inp=inp)

    inp.add_keyword("BOO/BAZ", "boo")
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword(["BOO", "BII"], "boo")
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BII", "bzzzzzz", override=False)
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BII/BCC", "bcr", override=False)
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BII/BCC", "bcr")
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   &BII
      BCC bcr
   &END BII
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BII", "boo", override=False)
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   &BII
      BCC bcr
   &END BII
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BII", "boo", override=True)
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BII", "boo", override=True)
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BIP", "bzz", override=False, conflicting_keys=['BII'])
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BIP", "bzz", override=False, conflicting_keys=[])
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BAZ boo
   BII boo
   BIP bzz
&END BOO
FOO bar""".format(inp=inp)

    inp.add_keyword("BOO/BEE", "bee", override=True, conflicting_keys=['BAZ', 'BII'])
    assert inp.render() == """{inp.DISCLAIMER}
BAR boo
&BOO
   BEE bee
   BIP bzz
&END BOO
FOO bar""".format(inp=inp)


def test_add_keyword_invariant_inp():
    """Check that the input dictionary is not modified by add_keyword()"""
    param = {"FOO": "bar"}
    inp = Cp2kInput(param)
    inp.add_keyword("BAR", "boo")
    assert inp.render() == "{inp.DISCLAIMER}\nBAR boo\nFOO bar".format(inp=inp)
    assert param == {"FOO": "bar"}


def test_multiple_force_eval():
    inp = Cp2kInput({"FORCE_EVAL": [{"FOO": "bar"}, {"FOO": "bar"}, {"FOO": "bar"}]})
    assert inp.render() == """{inp.DISCLAIMER}
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO bar
&END FORCE_EVAL""".format(inp=inp)


def test_kinds():
    inp = Cp2kInput({"KIND": [{"_": "H"}, {"_": "O"}]})
    assert inp.render() == """{inp.DISCLAIMER}
&KIND H
&END KIND
&KIND O
&END KIND""".format(inp=inp)


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
