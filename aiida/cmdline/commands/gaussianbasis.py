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
            'import': (self.importfile, self.complete_none),
        }

    def uploadbasis(self, *args):
        """
        Upload basis sets from a file
        
        """
        
        
        import os.path

        

        filename = os.path.abspath(args[0])
       # print filename

        load_dbenv()
        from aiida.orm.data.cp2k_basis import upload_basissetfile

        upload_basissetfile(filename)



    def listbasis(self, *args):
        """
        Print on screen the list of upf families installed
        """
        # note that the following command requires that the upfdata has a
        # key called element. As such, it is not well separated.
        import argparse

        from aiida.orm.data.upf import UPFGROUP_TYPE

        parser = argparse.ArgumentParser(
            prog=self.get_full_command_name(),
            description='List AiiDA upf families.')
        parser.add_argument('-e', '--element', nargs='+', type=str, default=None,
                            help="Filter the families only to those containing "
                                 "a pseudo for each of the specified elements")
        parser.add_argument('-d', '--with-description',
                            dest='with_description', action='store_true',
                            help="Show also the description for the UPF family")
        parser.set_defaults(with_description=False)

        args = list(args)
        parsed_args = parser.parse_args(args)

        load_dbenv()

        from aiida.orm import DataFactory

        BasisSet = DataFactory('gaussian_basis')
        
        basissets = BasisSet.get_basis_sets(filter_elements = parsed_args.element)
        for basisset in basissets:
            print basisset
        
        UpfData = DataFactory('upf')

        groups = UpfData.get_upf_groups(filter_elements=parsed_args.element)

        if groups:
            for g in groups:
                pseudos = UpfData.query(dbgroups=g.dbgroup).distinct()
                num_pseudos = pseudos.count()

                pseudos_list = pseudos.filter(
                    dbattributes__key="element").values_list(
                    'dbattributes__tval', flat=True)

                new_ps = pseudos.filter(
                    dbattributes__key="element").values_list(
                    'dbattributes__tval', flat=True)

                if parsed_args.with_description:
                    description_string = ": {}".format(g.description)
                else:
                    description_string = ""

                if num_pseudos != len(set(pseudos_list)):
                    print ("x {} [INVALID: {} pseudos, for {} elements]{}"
                           .format(g.name, num_pseudos, len(set(pseudos_list)),
                                   description_string))
                    print ("  Maybe the pseudopotential family wasn't "
                           "setup with the uploadfamily function?")

                else:
                    print "* {} [{} pseudos]{}".format(g.name, num_pseudos,
                                                       description_string)
        else:
            print "No valid UPF pseudopotential family found."

    def _import_upf(self, filename, **kwargs):
        """
        Importer from UPF.
        """
        try:
            node, _ = self.dataclass.get_or_create(filename)
            print node
        except ValueError as e:
            print e


