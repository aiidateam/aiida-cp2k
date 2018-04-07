#!/bin/bash -e
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/cp2k/aiida-cp2k        #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

set -x
flake8 ../
./test_version.py

# start the daemon
sudo service postgresql start
verdi daemon start

# run actual tests
./test_mm.py        cp2k@localhost
./test_dft.py       cp2k@localhost
./test_geopt.py     cp2k@localhost
./test_no_struct.py cp2k@localhost
./test_restart.py   cp2k@localhost
./test_failure.py   cp2k@localhost
./test_precision.py cp2k@localhost

echo "All tests have passed :-)"
#EOF