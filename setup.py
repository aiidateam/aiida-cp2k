# -*- coding: utf-8 -*-
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

from setuptools import setup, find_packages
import json


if __name__ == '__main__':
    with open('setup.json', 'r') as info:
        kwargs = json.load(info)
    setup(
        include_package_data=True,
        packages=find_packages(),
        **kwargs
    )
