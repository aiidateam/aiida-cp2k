# -*- coding: utf-8 -*-
import sys

from aiida.cmdline.baseclass import (
    VerdiCommandRouter, VerdiCommandWithSubcommands)
from data import Importable
from aiida import load_dbenv

class _Gaussianpseudo(VerdiCommandWithSubcommands, Importable):
    """
    Setup and manage basis set for GPW cpde to be used
    This command allows to list and configure the sets.
    """

    def __init__(self):
        """
        A dictionary with valid commands and functions to be called.
        """
        from aiida.orm.data.upf import UpfData

        self.dataclass = UpfData
        self.valid_subcommands = {
            'uploadpseudo': (self.uploadpseudo, self.complete_auto),
            'listpseudo': (self.listpseudo, self.complete_none),
            'printpseudo': (self.printpseudo, self.complete_none),
        }

    def uploadpseudo (self, *args):
        """
        Upload pseudo potentials from a file
        """
        
        
        import os.path

        filename = os.path.abspath(args[0])

    def listpseudo(self, *args):
        """
        Print on screen the list of upf families installed
        """
        import argparse
    def printpseudo(self, filename, **kwargs):
        """
        Importer from UPF.
        """
        print "Print pseudo"


