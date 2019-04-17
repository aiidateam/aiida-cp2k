#!/bin/bash
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

set -o errexit
set -o nounset
set -o pipefail

pre-commit run --all-files || ( git status --short ; git diff ; exit 1 )

pytest -v

# if all tests ran successfully
echo "All tests have passed :-)"
