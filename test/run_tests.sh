#!/bin/bash -e

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