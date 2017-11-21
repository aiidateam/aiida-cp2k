#!/bin/bash -e

set -x
flake8 ../

# start the daemon
sudo service postgresql start
verdi daemon start

# run actual tests
./test_mm.py        cp2k@localhost
./test_dft.py       cp2k@localhost
./test_geopt.py     cp2k@localhost
./test_walltime.py  cp2k@localhost
./test_no_struct.py cp2k@localhost

#EOF