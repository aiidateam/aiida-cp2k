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

# Run precommit
pre-commit run --all-files || ( git status --short ; git diff ; exit 1 )

# Run pytest
pytest test

# Run single calculation tests
verdi run ./examples/single_calculations/test_mm.py                      cp2k@localhost
verdi run ./examples/single_calculations/test_dft.py                     cp2k@localhost
verdi run examples/single_calculations/test_structure_through_file.py    cp2k@localhost
verdi run ./examples/single_calculations/test_dft_atomic_kinds.py        cp2k@localhost
verdi run ./examples/single_calculations/test_multiple_force_eval.py     cp2k@localhost
# Cp2k on Ubuntu 18.xx fails to run band structure calculations
#verdi run ./examples/single_calculations/test_bands.py                   cp2k@localhost
verdi run ./examples/single_calculations/test_geopt.py                   cp2k@localhost
verdi run ./examples/single_calculations/test_no_struct.py               cp2k@localhost
verdi run ./examples/single_calculations/test_restart.py                 cp2k@localhost
verdi run ./examples/single_calculations/test_failure.py                 cp2k@localhost
verdi run ./examples/single_calculations/test_precision.py               cp2k@localhost

# Run workchains
verdi run ./examples/workchains/test_base.py                             cp2k@localhost
verdi run ./examples/workchains/test_multistage_Al.py                    cp2k@localhost
verdi run ./examples/workchains/test_multistage_h2o_fail.py              cp2k@localhost
verdi run ./examples/workchains/test_multistage_h2o-.py                  cp2k@localhost
verdi run ./examples/workchains/test_multistage_h2o_singlepoint.py       cp2k@localhost
verdi run ./examples/workchains/test_multistage_h2o.py                   cp2k@localhost
verdi run ./examples/workchains/test_multistage_h2o_testfile.py          cp2k@localhost

# If all tests ran successfully
echo "All tests have passed :-)"
