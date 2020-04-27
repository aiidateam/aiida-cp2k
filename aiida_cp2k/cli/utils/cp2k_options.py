# -*- coding: utf-8 -*-
"""Helpers to setup command line options"""

from aiida.cmdline.params import types
from aiida.cmdline.params.options import OverridableOption

DAEMON = OverridableOption("-d",
                           "--daemon",
                           is_flag=True,
                           default=False,
                           show_default=True,
                           help="Submit the process to the daemon instead of running it directly.")

STRUCTURE = OverridableOption("-s",
                              "--structure",
                              type=types.DataParamType(sub_classes=("aiida.data:structure",)),
                              help="StructureData node.")
