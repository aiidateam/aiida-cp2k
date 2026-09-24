###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Test the optional cp2k-output-tools parser dependency."""

import builtins

import pytest

from aiida_cp2k.parsers import Cp2kToolsParser


def test_tools_parser_reports_missing_optional_dependency(monkeypatch):
    """Explain how to install the dependency when its parser is selected."""

    original_import = builtins.__import__

    def import_without_output_tools(name, *args, **kwargs):
        if name == "cp2k_output_tools":
            raise ImportError("simulated missing optional dependency")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_output_tools)

    with pytest.raises(
        ImportError,
        match=r"Install aiida-cp2k\[output-tools\] to use this parser",
    ):
        Cp2kToolsParser._parse_stdout(object())
