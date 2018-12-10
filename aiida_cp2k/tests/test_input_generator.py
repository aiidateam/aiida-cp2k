# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################


from aiida_cp2k.utils import Cp2kInput


def test_render_empty():
    inp = Cp2kInput()
    assert inp.to_string() == f"{inp.DISCLAIMER}"

def test_render_str_val():
    inp = Cp2kInput({'FOO': 'bar'})
    assert inp.to_string() == f"{inp.DISCLAIMER}\nFOO bar"
