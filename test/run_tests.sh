#z!/bin/bash -e
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################

set -x
pre-commit run --all-files || ( git status --short ; git diff ; exit 1 )
python check_version.py

# start the daemon
sudo service postgresql start
sudo service rabbitmq-server start
verdi daemon start

# run actual tests
verdi run test_mm.py        cp2k@localhost
verdi run test_dft.py       cp2k@localhost
verdi run test_geopt.py     cp2k@localhost
verdi run test_no_struct.py cp2k@localhost
verdi run test_restart.py   cp2k@localhost
verdi run test_failure.py   cp2k@localhost
verdi run test_precision.py cp2k@localhost

echo "All tests have passed :-)"
