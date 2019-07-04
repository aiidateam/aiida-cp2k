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
python check_version.py

pytest --ignore=test_single_calculation/ ..

# start the daemon
sudo service postgresql start
sudo service rabbitmq-server start
verdi daemon start

# run single calculation tests
verdi run ./test_single_calculation/test_mm.py                  cp2k@localhost
verdi run ./test_single_calculation/test_dft.py                 cp2k@localhost
verdi run ./test_single_calculation/test_multiple_force_eval.py cp2k@localhost
verdi run ./test_single_calculation/test_bands.py               cp2k@localhost
verdi run ./test_single_calculation/test_geopt.py               cp2k@localhost
verdi run ./test_single_calculation/test_no_struct.py           cp2k@localhost
verdi run ./test_single_calculation/test_restart.py             cp2k@localhost
verdi run ./test_single_calculation/test_failure.py             cp2k@localhost
verdi run ./test_single_calculation/test_precision.py           cp2k@localhost

#  run workflows
verdi run ./test_workflow/test_base.py        cp2k@localhost

# if all tests ran successfully
echo "All tests have passed :-)"
