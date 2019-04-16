# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from __future__ import absolute_import

import pytest

from aiida_cp2k.utils import Cp2kInput


def test_render_empty():
    inp = Cp2kInput()
    assert inp.render() == inp.DISCLAIMER


def test_render_str_val():
    inp = Cp2kInput({"FOO": "bar"})
    assert inp.render() == "{inp.DISCLAIMER}\nFOO  bar".format(inp=inp)


def test_add_keyword():
    inp = Cp2kInput({"FOO": "bar"})
    inp.add_keyword("BAR", "boo")
    assert inp.render() == "{inp.DISCLAIMER}\nBAR  boo\nFOO  bar".format(inp=inp)


def test_multiple_force_eval():
    inp = Cp2kInput({"FORCE_EVAL": [{"FOO": "bar"}, {"FOO": "bar"}, {"FOO": "bar"}]})
    assert (
        inp.render()
        == """{inp.DISCLAIMER}
&FORCE_EVAL
   FOO  bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO  bar
&END FORCE_EVAL
&FORCE_EVAL
   FOO  bar
&END FORCE_EVAL""".format(
            inp=inp
        )
    )


def test_invalid_lowercase_key():
    inp = Cp2kInput({"foo": "bar"})
    with pytest.raises(ValueError):
        inp.render()


def test_invalid_preprocessor():
    inp = Cp2kInput({"@SET": "bar"})
    with pytest.raises(ValueError):
        inp.render()
