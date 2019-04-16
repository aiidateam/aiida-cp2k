# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Setting up CP2K plugin for AiiDA"""
from __future__ import absolute_import

import json

from setuptools import setup, find_packages


def run_setup():
    with open("setup.json", "r") as info:
        kwargs = json.load(info)
    setup(
        include_package_data=True,
        packages=find_packages(),
        long_description=open("README.md").read(),
        long_description_content_type="text/markdown",
        **kwargs
    )


if __name__ == "__main__":
    run_setup()
