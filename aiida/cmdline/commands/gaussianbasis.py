# -*- coding: utf-8 -*-
import sys

from aiida.cmdline.baseclass import (
    VerdiCommandRouter, VerdiCommandWithSubcommands)
from data import Importable
from aiida import load_dbenv

class _Gaussianbasis(VerdiCommandWithSubcommands, Importable):
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
            'uploadbasis': (self.uploadbasis, self.complete_auto),
            'listbasis': (self.listbasis, self.complete_none),
            'printbasis': (self.printbasisset, self.complete_none)
        }

    def uploadbasis(self, *args):
        """
        Upload basis sets from a file
        
        """
        
        
        import os.path

        

        filename = os.path.abspath(args[0])
       # print filename

        load_dbenv()
        from aiida.orm.data.gaussianbasis import upload_cp2k_basissetfile

        upload_cp2k_basissetfile(filename)

    def listbasis(self, *args):
        """
        Print on screen the list of gaussian basissets installed
        """
        # note that the following command requires that the upfdata has a
        # key called element. As such, it is not well separated.
        import argparse
        parser = argparse.ArgumentParser(
            prog=self.get_full_command_name(),
            description='List AiiDA upf families.')
        parser.add_argument('-e', '--element', type=str, default=None,
                            help="Filter the families only to those containing "
                                 "a pseudo for each of the specified elements")
        parser.add_argument('tags',metavar='tag',type=str,nargs='*',help='tags')
        parser.set_defaults(with_description=False)
        args = list(args)
        parsed_args = parser.parse_args(args)
        load_dbenv()
        from aiida.orm.data.gaussianbasis import GaussianbasisData as BasisSet
        basissets = BasisSet.get_basis_sets(filter_elements = parsed_args.element, filter_tags=parsed_args.tags)
        for basisset in basissets:
            print ("Found a basis set for the element {} of type "
            "{}".format(basisset.element,
            ", ".join(basisset.tags)))

    def printbasisset(self, *args):
        """
        Print on screen a given basiset
        """
        import argparse
        output_formats=['cp2k','gaussian','gamess','nwchem']
        parser = argparse.ArgumentParser(
            prog=self.get_full_command_name(),
            description='Print a particular AiiDA gaussian basisset.')
        parser.add_argument('-e', '--element', type=str, default=None,
                            help="Filter the families only to those containing "
                                 "a pseudo for each of the specified elements")
        parser.add_argument('tags',metavar='tag',type=str,nargs='*',help='tags')
        parser.add_argument('-f', '--format', type=str,
                            default='cp2k',
                            help="Chose the output format for the "
                                  "basiset: "+', '.join(output_formats))
        args = list(args)
        parsed_args = parser.parse_args(args)
        load_dbenv()

        if parsed_args.format not in output_formats:
            raise NameError("Format "+parsed_args.format+" is not known. Please "
                            "use -h option to get a list of available formats")
        from aiida.orm.data.gaussianbasis import GaussianbasisData as BasisSet
        basissets = BasisSet.get_basis_sets(filter_elements =
        parsed_args.element, filter_tags=parsed_args.tags)
        for basisset in basissets:
            if parsed_args.format == 'cp2k':
                basisset.print_cp2k()
            if parsed_args.format == 'gaussian':
                raise NameError("Gaussian format in not yet implemented")
