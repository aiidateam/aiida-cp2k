# -*- coding: utf-8 -*-
# pylint: disable=import-outside-toplevel
###############################################################################
# Copyright (c), The AiiDA-CP2K authors.                                      #
# SPDX-License-Identifier: MIT                                                #
# AiiDA-CP2K is hosted on GitHub at https://github.com/aiidateam/aiida-cp2k   #
# For further information on the license, see the LICENSE.txt file.           #
###############################################################################
"""Create Gaussian basisset and pseudopotential data in the database"""

import sys
from io import StringIO

from aiida.common.exceptions import LoadingEntryPointError, MissingEntryPointError, UniquenessError
from aiida.plugins import DataFactory

try:
    BasisSet = DataFactory("gaussian.basisset")  # pylint: disable=invalid-name
    Pseudo = DataFactory("gaussian.pseudo")  # pylint: disable=invalid-name
except (LoadingEntryPointError, MissingEntryPointError):
    if hasattr(sys, '_called_from_test'):
        import pytest
        pytest.skip("Gaussian Datatypes are not available", allow_module_level=True)
    else:
        sys.exit("For this example to run, please make sure the aiida-gaussian-datatypes package is installed")


def load_data(prefix="MY-"):
    """
    This is something the user will usually do only ONCE and most likely by
    using the CLI of the aiida-gaussian-datatypes.
    """

    # Note: the basissets and pseudos deliberately have a prefix to avoid matching
    #       any CP2K provided entries which may creep in via the DATA_DIR

    bset_input = """\
     H  {prefix}AUTO-DZVP-MOLOPT-GTH {prefix}AUTO-DZVP-MOLOPT-GTH-q1
     1
     2 0 1 7 2 1
         11.478000339908  0.024916243200 -0.012512421400  0.024510918200
          3.700758562763  0.079825490000 -0.056449071100  0.058140794100
          1.446884268432  0.128862675300  0.011242684700  0.444709498500
          0.716814589696  0.379448894600 -0.418587548300  0.646207973100
          0.247918564176  0.324552432600  0.590363216700  0.803385018200
          0.066918004004  0.037148121400  0.438703133000  0.892971208700
          0.021708243634 -0.001125195500 -0.059693171300  0.120101316500

     O  {prefix}AUTO-DZVP-MOLOPT-SR-GTH {prefix}AUTO-DZVP-MOLOPT-SR-GTH-q6
     1
     2 0 2 5 2 2 1
         10.389228018317  0.126240722900  0.069215797900 -0.061302037200 -0.026862701100  0.029845227500
          3.849621072005  0.139933704300  0.115634538900 -0.190087511700 -0.006283021000  0.060939733900
          1.388401188741 -0.434348231700 -0.322839719400 -0.377726982800 -0.224839187800  0.732321580100
          0.496955043655 -0.852791790900 -0.095944016600 -0.454266086000  0.380324658600  0.893564918400
          0.162491615040 -0.242351537800  1.102830348700 -0.257388983000  1.054102919900  0.152954188700
    """.format(prefix=prefix)

    pseudo_input = """\
    #
    H {prefix}AUTO-GTH-PADE-q1 {prefix}AUTO-GTH-LDA-q1 {prefix}AUTO-GTH-PADE {prefix}AUTO-GTH-LDA
        1
         0.20000000    2    -4.18023680     0.72507482
        0

    O {prefix}AUTO-GTH-PADE-q6 {prefix}AUTO-GTH-LDA-q6 {prefix}AUTO-GTH-PADE {prefix}AUTO-GTH-LDA
        2    4
         0.24762086    2   -16.58031797     2.39570092
        2
         0.22178614    1    18.26691718
         0.25682890    0
    """.format(prefix=prefix)

    fhandle_bset = StringIO(bset_input)
    fhandle_pseudo = StringIO(pseudo_input)

    try:
        bsets = {b.element: b for b in BasisSet.from_cp2k(fhandle_bset, duplicate_handling='error')}
        pseudos = {p.element: p for p in Pseudo.from_cp2k(fhandle_pseudo, duplicate_handling='error')}
    except UniquenessError:  # if the user already ran the script, fetch the data from the db instead
        bsets = {
            "H": BasisSet.get("H", "{prefix}AUTO-DZVP-MOLOPT-GTH".format(prefix=prefix)),
            "O": BasisSet.get("O", "{prefix}AUTO-DZVP-MOLOPT-SR-GTH".format(prefix=prefix)),
        }
        pseudos = {
            "H": Pseudo.get("H", "{prefix}AUTO-GTH-PADE-q1".format(prefix=prefix)),
            "O": Pseudo.get("O", "{prefix}AUTO-GTH-PADE-q6".format(prefix=prefix)),
        }

    return bsets, pseudos
