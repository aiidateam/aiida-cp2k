#!/usr/bin/env python2
# -*- coding: utf-8 -*-
###########################################################################
# Copyright (c), The AiiDA team. All rights reserved.                     #
# This file is part of the AiiDA code.                                    #
#                                                                         #
# The code is hosted on GitHub at https://github.com/cp2k/aiida-cp2k      #
# For further information on the license, see the LICENSE.txt file        #
# For further information please visit http://www.aiida.net               #
###########################################################################

from __future__ import print_function

import os
import sys
import time
import subprocess


# ==============================================================================
def wait_for_calc(calc, timeout_secs=5*60.0, ensure_finished_ok=True):
    print("Waiting for end of execution...")
    start_time = time.time()
    exited_with_timeout = True
    while time.time() - start_time < timeout_secs:
        sys.stdout.flush()
        time.sleep(10)  # Wait a few seconds
        # print some debug info, both for debugging reasons and to avoid
        # that the test machine is shut down because there is no output
        print("#"*78)
        print("####### TIME ELAPSED: {} s".format(time.time() - start_time))
        print("#"*78)
        print("Output of 'verdi calculation list':")
        try:
            cmd = ["verdi", "calculation", "list"]
            print(subprocess.check_output(cmd, stderr=subprocess.STDOUT))
        except subprocess.CalledProcessError as e:
            print("Note: the command failed, message: {}".format(e.message))
        if calc.has_finished():
            print("Calculation terminated its execution.")
            exited_with_timeout = False
            break

    # check for timeout
    if exited_with_timeout:
        print("Timeout - did not complete after %i seconds" % timeout_secs)
        os.system("cat ~/.aiida/daemon/log/aiida_daemon.log")
        sys.exit(2)

    print("Calculation finished with state: " + calc.get_state())

    # check calculation status
    if ensure_finished_ok and not calc.has_finished_ok():
        print("Calculation failed.")
        os.system("cat ~/.aiida/daemon/log/aiida_daemon.log")
        sys.exit(2)

# EOF
