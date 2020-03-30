# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Setting up CP2K plugin for AiiDA"""

import json

from io import open  # pylint: disable=redefined-builtin
from setuptools import setup, find_packages


def run_setup():
    with open('setup.json', 'r', encoding='utf-8') as info:
        kwargs = json.load(info)
    setup(include_package_data=True,
          packages=find_packages(),
          long_description=open('README.md', encoding='utf-8').read(),
          long_description_content_type='text/markdown',
          **kwargs)


if __name__ == '__main__':
    run_setup()
